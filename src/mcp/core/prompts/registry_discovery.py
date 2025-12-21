"""
Expert Discovery System for Registry

Handles automatic discovery and loading of domain expert modules with
concurrent processing and robust error handling.
"""

import asyncio
import importlib
import importlib.util
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Set, Type

from .core import DomainExpert
from .registry_core import EnhancedRegistryEntry
from .security import SecurityValidator, SecurityLevel
from .events import get_event_emitter, emit_system_event, emit_ui_update, emit_error

import logging
logger = logging.getLogger(__name__)


class ExpertDiscovery:
    """Expert discovery and loading system"""
    
    def __init__(self, max_workers: int = 4):
        self._discovery_paths: List[Path] = []
        self._loaded_modules: Set[str] = set()
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers, 
                                             thread_name_prefix="discovery")
        self._events = get_event_emitter()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def add_discovery_path(self, path: Path, security_check: bool = True) -> bool:
        """Add a path for expert discovery"""
        # Validate path for security
        if security_check:
            try:
                validated_path = SecurityValidator.validate_file_path(path, "read")
            except ValueError as e:
                logger.error(f"Security validation failed for discovery path {path}: {e}")
                if self._events:
                    emit_error("discovery_security_error", str(e), {"path": str(path)})
                return False
        else:
            validated_path = path
        
        if validated_path.exists() and validated_path.is_dir():
            with self._lock:
                if validated_path not in self._discovery_paths:
                    self._discovery_paths.append(validated_path)
                    logger.info(f"Added discovery path: {validated_path}")
                    
                    if self._events:
                        emit_system_event("discovery_path_added", {
                            "path": str(validated_path),
                            "total_paths": len(self._discovery_paths)
                        })
                    return True
        else:
            logger.warning(f"Discovery path does not exist or is not a directory: {path}")
            if self._events:
                emit_error("discovery_path_error", f"Invalid path: {path}")
            return False
    
    async def discover_experts_async(self, package_name: str = "techniques", 
                                   max_concurrent: int = 4) -> List[Type[DomainExpert]]:
        """Discover experts asynchronously with concurrent loading"""
        start_time = time.time()
        discovered_experts = []
        
        # Emit discovery start event
        if self._events:
            emit_ui_update("discovery", "started", {
                "package_name": package_name,
                "discovery_paths": len(self._discovery_paths)
            })
        
        try:
            # Check cache first
            cache_key = f"{package_name}:{hash(tuple(str(p) for p in self._discovery_paths))}"
            cached_result = await self._check_cache(cache_key)
            if cached_result:
                logger.debug("Using cached discovery results")
                discovered_experts = cached_result
            else:
                # Discover modules concurrently
                tasks = []
                for discovery_path in self._discovery_paths:
                    task = self._discover_in_path_async(discovery_path, package_name)
                    tasks.append(task)
                
                # Wait for all discovery tasks with progress reporting
                completed = 0
                total_tasks = len(tasks)
                
                for task in asyncio.as_completed(tasks):
                    try:
                        path_experts = await task
                        discovered_experts.extend(path_experts)
                        completed += 1
                        
                        # Report progress
                        if self._events:
                            emit_ui_update("discovery", "progress", {
                                "completed": completed,
                                "total": total_tasks,
                                "discovered_so_far": len(discovered_experts)
                            })
                            
                    except Exception as e:
                        logger.error(f"Discovery task failed: {e}")
                        if self._events:
                            emit_error("discovery_task_error", str(e))
                
                # Cache results
                await self._cache_results(cache_key, discovered_experts)
            
            # Emit completion event
            duration = time.time() - start_time
            logger.info(f"Discovered {len(discovered_experts)} experts in {duration:.2f}s")
            
            if self._events:
                emit_system_event("expert_discovery_completed", {
                    "discovered_count": len(discovered_experts),
                    "duration": duration,
                    "cached": cached_result is not None
                })
            
            return discovered_experts
            
        except Exception as e:
            error_msg = f"Expert discovery failed: {e}"
            logger.error(error_msg)
            if self._events:
                emit_error("expert_discovery_failed", error_msg)
            raise
    
    async def _discover_in_path_async(self, path: Path, package_name: str) -> List[Type[DomainExpert]]:
        """Discover experts in a specific path"""
        discovered_experts = []
        
        # Look for technique modules
        techniques_path = path / package_name
        if not techniques_path.exists():
            return discovered_experts
        
        module_files = list(techniques_path.glob("*.py"))
        module_files = [f for f in module_files if not f.name.startswith("_")]
        
        # Process modules with limited concurrency
        semaphore = asyncio.Semaphore(4)  # Limit concurrent module loads
        
        async def load_module_safe(module_file: Path) -> List[Type[DomainExpert]]:
            async with semaphore:
                return await self._load_module_async(module_file, package_name)
        
        tasks = [load_module_safe(mf) for mf in module_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                discovered_experts.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Module loading error: {result}")
        
        return discovered_experts
    
    async def _load_module_async(self, module_file: Path, package_name: str) -> List[Type[DomainExpert]]:
        """Load a single module and extract expert classes"""
        module_name = module_file.stem
        full_module_path = f"{package_name}.{module_name}"
        
        if full_module_path in self._loaded_modules:
            return []
        
        try:
            # Load module in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def load_module_sync():
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    
                    spec = importlib.util.spec_from_file_location(full_module_path, module_file)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        return module
                return None
            
            module = await loop.run_in_executor(self._thread_pool, load_module_sync)
            
            if module is None:
                return []
            
            # Look for DomainExpert subclasses
            expert_classes = []
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, DomainExpert) and 
                    attr is not DomainExpert):
                    expert_classes.append(attr)
            
            self._loaded_modules.add(full_module_path)
            logger.debug(f"Loaded module {full_module_path}: {len(expert_classes)} experts")
            return expert_classes
            
        except Exception as e:
            logger.error(f"Failed to load module {full_module_path}: {e}")
            return []
    
    async def _check_cache(self, cache_key: str) -> List[Type[DomainExpert]]:
        """Check if discovery results are cached"""
        # For now, return None (no caching of class objects)
        # In a real implementation, you might cache module paths instead
        return None
    
    async def _cache_results(self, cache_key: str, experts: List[Type[DomainExpert]]):
        """Cache discovery results"""
        # For now, skip caching class objects
        # In a real implementation, cache module information instead
        pass
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        with self._lock:
            return {
                "discovery_paths": len(self._discovery_paths),
                "loaded_modules": len(self._loaded_modules),
                "cache_entries": len(self._cache),
                "paths": [str(p) for p in self._discovery_paths],
                "modules": list(self._loaded_modules)
            }
    
    def clear_cache(self):
        """Clear discovery cache"""
        with self._lock:
            self._cache.clear()
            logger.debug("Discovery cache cleared")
    
    def shutdown(self):
        """Shutdown discovery system"""
        try:
            self._thread_pool.shutdown(wait=True)
            logger.info("Discovery system shutdown completed")
        except Exception as e:
            logger.error(f"Error during discovery shutdown: {e}")


if __name__ == "__main__":
    # Test discovery system
    async def test_discovery():
        print("Testing Expert Discovery System")
        
        discovery = ExpertDiscovery()
        
        # Add test discovery path
        test_path = Path(__file__).parent / "techniques"
        success = discovery.add_discovery_path(test_path)
        print(f"✓ Added discovery path: {success}")
        
        # Test async discovery
        try:
            experts = await discovery.discover_experts_async()
            print(f"✓ Discovered {len(experts)} expert classes")
        except Exception as e:
            print(f"✗ Discovery failed: {e}")
        
        # Get stats
        stats = discovery.get_discovery_stats()
        print(f"✓ Discovery stats: {stats['loaded_modules']} modules loaded")
        
        # Cleanup
        discovery.shutdown()
        
        print("\n✅ Discovery system test completed!")
    
    # Run test
    try:
        asyncio.run(test_discovery())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 