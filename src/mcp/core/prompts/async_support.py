"""
Async Support for Domain Prompt System

Provides async/await wrappers and enhanced functionality for non-blocking operations.
Enables scalable concurrent processing of prompts and domain operations.
"""

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from contextlib import asynccontextmanager

from .core import DomainPrompt, DomainExpert, TechniqueMetadata, BiologicalContext
from .security import SecurityValidator
from .events import get_event_emitter, emit_system_event
from .performance import get_performance_monitor

logger = logging.getLogger(__name__)

# Type variables for generic async wrappers
T = TypeVar('T')
P = TypeVar('P')

# Global thread pool for CPU-bound operations
_thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="domain_prompts")


class AsyncDomainPrompt:
    """Async wrapper for DomainPrompt with enhanced features"""
    
    def __init__(self, prompt: DomainPrompt):
        self._prompt = prompt
        self._cache = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps = {}
        self._lock = asyncio.Lock()
        
        # Get global instances
        self._events = get_event_emitter()
        self._perf = get_performance_monitor()
    
    async def format_async(self, **kwargs) -> str:
        """
        Async format with security validation, caching, and monitoring
        
        Args:
            **kwargs: Template parameters
            
        Returns:
            Formatted prompt string
            
        Raises:
            ValueError: If validation fails or parameters are missing
        """
        # Start performance monitoring
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Validate parameters asynchronously
            validated_params = await self._validate_parameters_async(kwargs)
            
            # Check cache first
            cache_key = self._generate_cache_key(validated_params)
            cached_result = await self._get_cached_result(cache_key)
            if cached_result is not None:
                self._perf.increment_counter("prompt_cache_hits")
                return cached_result
            
            # Format prompt in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(
                _thread_pool, 
                self._format_sync, 
                validated_params
            )
            
            # Cache the result
            await self._cache_result(cache_key, result)
            
            # Emit success event
            self._events.emit("prompt_formatted", {
                "prompt_name": self._prompt.name,
                "parameters": list(kwargs.keys()),
                "output_length": len(result),
                "cached": False
            })
            
            return result
            
        except Exception as e:
            # Emit error event
            self._events.emit("prompt_error", {
                "prompt_name": self._prompt.name,
                "error": str(e),
                "error_type": type(e).__name__
            }, priority=1)
            raise
            
        finally:
            # Record performance metrics
            duration = asyncio.get_event_loop().time() - start_time
            self._perf.record_timing("async_prompt_format", duration)
    
    async def _validate_parameters_async(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Async parameter validation"""
        # Run validation in thread pool for CPU-intensive operations
        return await asyncio.get_event_loop().run_in_executor(
            _thread_pool,
            SecurityValidator.validate_parameters,
            params
        )
    
    def _format_sync(self, params: Dict[str, Any]) -> str:
        """Synchronous format operation"""
        return self._prompt.format(**params)
    
    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from parameters"""
        import hashlib
        key_str = f"{self._prompt.name}:{sorted(params.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def _get_cached_result(self, cache_key: str) -> Optional[str]:
        """Get cached result if still valid"""
        async with self._lock:
            if cache_key not in self._cache:
                return None
            
            # Check TTL
            timestamp = self._cache_timestamps.get(cache_key)
            if timestamp and datetime.now() - timestamp > self._cache_ttl:
                # Cache expired
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
                return None
            
            return self._cache[cache_key]
    
    async def _cache_result(self, cache_key: str, result: str):
        """Cache the result with timestamp"""
        async with self._lock:
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now()
            
            # Limit cache size (simple LRU)
            if len(self._cache) > 100:
                oldest_key = min(self._cache_timestamps.keys(), 
                               key=lambda k: self._cache_timestamps[k])
                del self._cache[oldest_key]
                del self._cache_timestamps[oldest_key]
    
    async def clear_cache(self):
        """Clear the prompt cache"""
        async with self._lock:
            self._cache.clear()
            self._cache_timestamps.clear()
    
    @property
    def prompt(self) -> DomainPrompt:
        """Access to underlying prompt"""
        return self._prompt


class AsyncDomainExpert:
    """Async wrapper for DomainExpert with concurrent operations"""
    
    def __init__(self, expert: DomainExpert):
        self._expert = expert
        self._async_prompts: Dict[str, AsyncDomainPrompt] = {}
        self._metadata_cache: Optional[TechniqueMetadata] = None
        self._prompts_cache: Optional[Dict[str, DomainPrompt]] = None
        self._cache_lock = asyncio.Lock()
        
        # Performance monitoring
        self._perf = get_performance_monitor()
    
    async def get_metadata_async(self) -> TechniqueMetadata:
        """Get metadata asynchronously with caching"""
        if self._metadata_cache is None:
            self._metadata_cache = await asyncio.get_event_loop().run_in_executor(
                _thread_pool, self._expert.get_metadata
            )
        return self._metadata_cache
    
    async def get_prompts_async(self) -> Dict[str, DomainPrompt]:
        """Get prompts asynchronously with caching"""
        async with self._cache_lock:
            if self._prompts_cache is None:
                self._prompts_cache = await asyncio.get_event_loop().run_in_executor(
                    _thread_pool, self._expert.get_prompts
                )
        return self._prompts_cache
    
    async def get_async_prompt(self, name: str) -> Optional[AsyncDomainPrompt]:
        """Get async wrapper for a specific prompt"""
        if name not in self._async_prompts:
            prompt = await self.get_prompt_by_name_async(name)
            if prompt:
                self._async_prompts[name] = AsyncDomainPrompt(prompt)
            else:
                return None
        
        return self._async_prompts[name]
    
    async def get_prompt_by_name_async(self, name: str) -> Optional[DomainPrompt]:
        """Get prompt by name asynchronously"""
        prompts = await self.get_prompts_async()
        return prompts.get(name)
    
    async def get_prompts_by_context_async(self, context: BiologicalContext) -> Dict[str, DomainPrompt]:
        """Get prompts by context asynchronously"""
        prompts = await self.get_prompts_async()
        return {
            name: prompt for name, prompt in prompts.items()
            if prompt.biological_context == context
        }
    
    async def validate_prompts_async(self) -> List[str]:
        """Validate prompts asynchronously"""
        return await asyncio.get_event_loop().run_in_executor(
            _thread_pool, self._expert.validate_prompts
        )
    
    async def batch_format_prompts(self, requests: List[Dict[str, Any]]) -> List[str]:
        """
        Format multiple prompts concurrently
        
        Args:
            requests: List of {prompt_name: str, parameters: dict}
            
        Returns:
            List of formatted prompts in the same order
        """
        tasks = []
        
        for request in requests:
            prompt_name = request["prompt_name"]
            parameters = request["parameters"]
            
            async def format_single(name: str, params: Dict[str, Any]) -> str:
                async_prompt = await self.get_async_prompt(name)
                if async_prompt:
                    return await async_prompt.format_async(**params)
                else:
                    raise ValueError(f"Prompt '{name}' not found")
            
            tasks.append(format_single(prompt_name, parameters))
        
        # Run all formatting operations concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error strings
        formatted_results = []
        for result in results:
            if isinstance(result, Exception):
                formatted_results.append(f"ERROR: {result}")
            else:
                formatted_results.append(result)
        
        return formatted_results
    
    @property
    def expert(self) -> DomainExpert:
        """Access to underlying expert"""
        return self._expert


async def create_async_expert(expert: DomainExpert) -> AsyncDomainExpert:
    """Create async wrapper for a domain expert"""
    return AsyncDomainExpert(expert)


@asynccontextmanager
async def async_timer(operation_name: str):
    """Async context manager for timing operations"""
    start_time = asyncio.get_event_loop().time()
    try:
        yield
    finally:
        duration = asyncio.get_event_loop().time() - start_time
        get_performance_monitor().record_timing(f"async_{operation_name}", duration)


def async_cached(ttl_minutes: int = 5):
    """Decorator for caching async function results"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_times = {}
        cache_lock = asyncio.Lock()
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            import hashlib
            key_str = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            async with cache_lock:
                # Check cache
                if cache_key in cache:
                    cache_time = cache_times[cache_key]
                    if datetime.now() - cache_time < timedelta(minutes=ttl_minutes):
                        return cache[cache_key]
                    else:
                        # Expired
                        del cache[cache_key]
                        del cache_times[cache_key]
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            async with cache_lock:
                cache[cache_key] = result
                cache_times[cache_key] = datetime.now()
                
                # Limit cache size
                if len(cache) > 50:
                    oldest_key = min(cache_times.keys(), key=lambda k: cache_times[k])
                    del cache[oldest_key]
                    del cache_times[oldest_key]
            
            return result
        
        return wrapper
    return decorator


async def shutdown_async_support():
    """Shutdown async support and cleanup resources"""
    global _thread_pool
    if _thread_pool:
        _thread_pool.shutdown(wait=True)
        logger.info("Async support shutdown completed")


if __name__ == "__main__":
    # Test async support
    async def test_async_support():
        print("Testing Async Support")
        
        # Import here to avoid circular imports
        from .core import DomainPrompt, BaseDomainExpert, TechniqueMetadata, ExpertiseLevel, BiologicalContext
        
        # Create test prompt
        prompt = DomainPrompt(
            name="test_async_prompt",
            description="Test prompt for async operations",
            template="Hello {name}, your async score is {score}",
            parameters=["name", "score"],
            expertise_level=ExpertiseLevel.BASIC,
            biological_context=BiologicalContext.QUALITY_CONTROL
        )
        
        # Create async wrapper
        async_prompt = AsyncDomainPrompt(prompt)
        
        # Test async formatting
        result = await async_prompt.format_async(name="Alice", score=95)
        print(f"✓ Async format result: {result}")
        
        # Test caching (second call should be cached)
        result2 = await async_prompt.format_async(name="Alice", score=95)
        print(f"✓ Cached result: {result2}")
        
        print("\n✅ Async support test completed!")
    
    # Run test
    try:
        asyncio.run(test_async_support())
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 