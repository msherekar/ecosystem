"""
Enhanced utility functions with security, caching, and Electron integration.
Provides improved anonymization, context extraction, and session management.
"""

import hashlib
import logging
import secrets
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Protocol, Union, Callable
from abc import ABC, abstractmethod
from functools import wraps, lru_cache
import weakref

class SessionProvider(Protocol):
    """Protocol for session state providers with enhanced features"""
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from session state"""
        ...
    
    def set(self, key: str, value: Any) -> None:
        """Set value in session state"""
        ...
    
    def delete(self, key: str) -> None:
        """Delete key from session state"""
        ...
    
    def clear(self) -> None:
        """Clear all session data"""
        ...

class EnhancedUserAnonymizer:
    """Enhanced user anonymization with better security and caching"""
    
    def __init__(self, salt: str = None, cache_size: int = 1000):
        self.salt = salt or self._generate_secure_salt()
        self.logger = logging.getLogger("user_anonymizer")
        self._cache: Dict[str, str] = {}
        self._cache_size = cache_size
        self._access_log: Dict[str, datetime] = {}
    
    def _generate_secure_salt(self) -> str:
        """Generate cryptographically secure salt"""
        return secrets.token_hex(32)
    
    def anonymize_user_id(self, user_identifier: str) -> str:
        """Create anonymized but consistent user ID with caching"""
        if not user_identifier:
            return "anonymous"
        
        # Check cache first
        if user_identifier in self._cache:
            self._access_log[user_identifier] = datetime.now()
            return self._cache[user_identifier]
        
        # Log access for audit
        self._access_log[user_identifier] = datetime.now()
        
        # Create consistent hash for user
        salted_id = f"{user_identifier}_{self.salt}"
        hash_value = hashlib.sha256(salted_id.encode()).hexdigest()
        
        # Use first 16 characters for readability
        anonymized = f"user_{hash_value[:16]}"
        
        # Cache management
        if len(self._cache) >= self._cache_size:
            self._cleanup_cache()
        
        self._cache[user_identifier] = anonymized
        return anonymized
    
    def _cleanup_cache(self) -> None:
        """Clean up old cache entries"""
        # Remove entries older than 1 hour, or remove oldest if too many
        cutoff = datetime.now() - timedelta(hours=1)
        old_entries = [
            key for key, access_time in self._access_log.items()
            if access_time < cutoff
        ]
        
        # If not enough old entries, remove oldest by access time
        if len(old_entries) < len(self._cache) - self._cache_size + 10:
            sorted_entries = sorted(
                self._access_log.items(), 
                key=lambda x: x[1]
            )
            entries_to_remove = len(self._cache) - self._cache_size + 10
            old_entries.extend([key for key, _ in sorted_entries[:entries_to_remove]])
        
        for key in old_entries:
            self._cache.pop(key, None)
            self._access_log.pop(key, None)
    
    def generate_session_id(self, session_data: str = None) -> str:
        """Generate a unique session ID with enhanced entropy"""
        if not session_data:
            session_data = f"{datetime.now().isoformat()}_{secrets.token_hex(8)}"
        
        return hashlib.sha256(session_data.encode()).hexdigest()[:16]
    
    def get_anonymization_stats(self) -> Dict[str, Any]:
        """Get anonymization statistics"""
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._cache_size,
            "total_anonymizations": len(self._access_log),
            "recent_activity": len([
                t for t in self._access_log.values()
                if t > datetime.now() - timedelta(minutes=10)
            ])
        }

class EnhancedContextExtractor:
    """Enhanced context extraction with caching and validation"""
    
    def __init__(self, session_provider: SessionProvider = None):
        self.session_provider = session_provider
        self.logger = logging.getLogger("context_extractor")
        self._context_cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=5)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    def extract_analysis_context(self, use_cache: bool = True) -> Dict[str, Any]:
        """Extract analysis-specific context with caching"""
        cache_key = "analysis_context"
        
        # Check cache
        if use_cache and self._is_cache_valid(cache_key):
            return self._context_cache[cache_key].copy()
        
        if not self.session_provider:
            return {}
        
        context = {
            "analysis_state": self._extract_analysis_state(),
            "available_tools": self._extract_available_tools(),
            "pipeline_progress": self._extract_pipeline_progress(),
            "data_characteristics": self._extract_data_characteristics(),
            "user_preferences": self._extract_user_preferences(),
            "system_state": self._extract_system_state()
        }
        
        # Add current step and parameters
        context["current_step"] = self.session_provider.get("scrna_current_step", "unknown")
        context["analysis_params"] = self._extract_analysis_parameters()
        
        # Cache the result
        self._context_cache[cache_key] = context.copy()
        self._cache_timestamps[cache_key] = datetime.now()
        
        return context
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._context_cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False
        
        return datetime.now() - timestamp < self._cache_ttl
    
    def _extract_analysis_state(self) -> Dict[str, Any]:
        """Extract current analysis state"""
        if not self.session_provider:
            return {}
        
        return {
            "analysis_started": self.session_provider.get("analysis_started", False),
            "last_operation": self.session_provider.get("last_operation"),
            "operation_timestamp": self.session_provider.get("operation_timestamp"),
            "errors_encountered": self.session_provider.get("errors_encountered", [])
        }
    
    def _extract_available_tools(self) -> List[str]:
        """Extract list of available tools"""
        if not self.session_provider:
            return []
        
        # Common bioinformatics tools
        default_tools = ["scanpy", "pandas", "numpy", "matplotlib", "seaborn"]
        return self.session_provider.get("available_tools", default_tools)
    
    def _extract_pipeline_progress(self) -> Dict[str, bool]:
        """Extract pipeline progress flags"""
        if not self.session_provider:
            return {}
        
        pipeline_flags = [
            "qc_done", "filtering_done", "normalization_done", 
            "dimred_done", "clustering_done", "dea_done",
            "pathway_done", "visualization_done"
        ]
        
        return {
            flag: self.session_provider.get(flag, False) 
            for flag in pipeline_flags
        }
    
    def _extract_data_characteristics(self) -> Dict[str, Any]:
        """Extract data characteristics with validation"""
        if not self.session_provider:
            return {}
        
        characteristics = {}
        
        # AnnData characteristics
        anndata = self.session_provider.get("anndata")
        if anndata is not None:
            characteristics.update({
                "n_cells": getattr(anndata, 'n_obs', 0),
                "n_genes": getattr(anndata, 'n_vars', 0),
                "has_raw": hasattr(anndata, 'raw') and anndata.raw is not None,
                "data_type": "anndata"
            })
        
        # DataFrame characteristics
        df = self.session_provider.get("uploaded_df")
        if df is not None:
            characteristics.update({
                "n_rows": len(df),
                "n_columns": len(df.columns),
                "data_type": "dataframe",
                "column_types": df.dtypes.to_dict() if hasattr(df, 'dtypes') else {}
            })
        
        # Add data quality metrics
        characteristics["quality_metrics"] = self._calculate_data_quality_metrics()
        
        return characteristics
    
    def _extract_user_preferences(self) -> Dict[str, Any]:
        """Extract user preferences and settings"""
        if not self.session_provider:
            return {}
        
        return {
            "theme": self.session_provider.get("theme", "default"),
            "auto_save": self.session_provider.get("auto_save", True),
            "notifications_enabled": self.session_provider.get("notifications_enabled", True),
            "preferred_plot_format": self.session_provider.get("preferred_plot_format", "png"),
            "analysis_verbosity": self.session_provider.get("analysis_verbosity", "normal")
        }
    
    def _extract_system_state(self) -> Dict[str, Any]:
        """Extract system state information"""
        return {
            "memory_usage": self._get_memory_usage(),
            "active_sessions": self._get_active_sessions_count(),
            "last_backup": self.session_provider.get("last_backup") if self.session_provider else None,
            "system_health": "healthy"  # Could be enhanced with actual health checks
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            return {
                "rss_mb": memory_info.rss / 1024 / 1024,
                "vms_mb": memory_info.vms / 1024 / 1024,
                "percent": process.memory_percent()
            }
        except ImportError:
            return {"status": "psutil not available"}
    
    def _get_active_sessions_count(self) -> int:
        """Get number of active sessions"""
        # This would integrate with session manager
        return 1  # Placeholder
    
    def _calculate_data_quality_metrics(self) -> Dict[str, Any]:
        """Calculate basic data quality metrics"""
        if not self.session_provider:
            return {}
        
        metrics = {}
        
        # Check for common data issues
        anndata = self.session_provider.get("anndata")
        if anndata is not None:
            try:
                # Basic quality checks
                metrics["has_missing_genes"] = hasattr(anndata, 'var') and anndata.var.isnull().any().any()
                metrics["has_missing_cells"] = hasattr(anndata, 'obs') and anndata.obs.isnull().any().any()
                metrics["data_sparsity"] = self._calculate_sparsity(anndata)
            except Exception as e:
                metrics["quality_check_error"] = str(e)
        
        return metrics
    
    def _calculate_sparsity(self, anndata) -> float:
        """Calculate data sparsity"""
        try:
            import numpy as np
            if hasattr(anndata, 'X'):
                total_elements = anndata.X.shape[0] * anndata.X.shape[1]
                if hasattr(anndata.X, 'nnz'):  # Sparse matrix
                    non_zero = anndata.X.nnz
                else:  # Dense matrix
                    non_zero = np.count_nonzero(anndata.X)
                return 1.0 - (non_zero / total_elements)
        except Exception:
            pass
        return 0.0
    
    def _extract_analysis_parameters(self) -> Dict[str, Any]:
        """Extract analysis parameters from session"""
        if not self.session_provider:
            return {}
        
        params = {}
        
        # Common parameters with validation
        param_definitions = {
            "n_top_genes": (int, 2000, 100, 10000),
            "min_genes": (int, 200, 1, 5000),
            "min_cells": (int, 3, 1, 1000),
            "max_genes": (int, 5000, 100, 50000),
            "max_cells": (int, 20000, 100, 100000),
            "target_sum": (float, 10000, 1000, 100000),
            "n_comps": (int, 50, 2, 200),
            "n_neighbors": (int, 15, 2, 100),
            "resolution": (float, 0.5, 0.1, 2.0)
        }
        
        for param_name, (param_type, default, min_val, max_val) in param_definitions.items():
            value = self.session_provider.get(param_name)
            if value is not None:
                try:
                    # Type conversion and validation
                    converted_value = param_type(value)
                    if min_val <= converted_value <= max_val:
                        params[param_name] = converted_value
                    else:
                        self.logger.warning(f"Parameter {param_name} out of range: {converted_value}")
                        params[param_name] = default
                except (ValueError, TypeError):
                    self.logger.warning(f"Invalid parameter type for {param_name}: {value}")
                    params[param_name] = default
        
        return params
    
    def determine_analysis_type(self) -> str:
        """Determine the type of analysis being performed with caching"""
        cache_key = "analysis_type"
        
        if self._is_cache_valid(cache_key):
            return self._context_cache[cache_key]
        
        if not self.session_provider:
            analysis_type = "general"
        elif self.session_provider.get("anndata") is not None:
            analysis_type = "scrna_seq"
        elif self.session_provider.get("uploaded_df") is not None:
            # Try to determine from data characteristics
            df = self.session_provider.get("uploaded_df")
            if hasattr(df, 'columns'):
                columns = [str(col).lower() for col in df.columns]
                if any('gene' in col or 'ensembl' in col for col in columns):
                    analysis_type = "rna_seq"
                elif any('protein' in col or 'peptide' in col for col in columns):
                    analysis_type = "proteomics"
                else:
                    analysis_type = "tabular"
            else:
                analysis_type = "tabular"
        elif self.session_provider.get("rna_seq_data") is not None:
            analysis_type = "rna_seq"
        elif self.session_provider.get("proteomics_data") is not None:
            analysis_type = "proteomics"
        else:
            analysis_type = "general"
        
        # Cache the result
        self._context_cache[cache_key] = analysis_type
        self._cache_timestamps[cache_key] = datetime.now()
        
        return analysis_type
    
    def clear_cache(self) -> None:
        """Clear context cache"""
        self._context_cache.clear()
        self._cache_timestamps.clear()

class EnhancedToolUsageExtractor:
    """Enhanced tool usage extraction with performance monitoring"""
    
    def __init__(self):
        self.logger = logging.getLogger("tool_extractor")
        self._tool_performance: Dict[str, List[float]] = {}
    
    def extract_tools_used(self, tool_results: List[str]) -> List[Dict[str, Any]]:
        """Extract enhanced tool usage information"""
        tools = []
        
        for result in tool_results:
            try:
                tool_info = self._parse_tool_result(result)
                if tool_info:
                    # Add performance tracking
                    self._track_tool_performance(tool_info)
                    tools.append(tool_info)
            except Exception as e:
                self.logger.error(f"Failed to parse tool result: {e}")
        
        return tools
    
    def _parse_tool_result(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse individual tool result with enhanced information"""
        if not result or "Tool " not in result:
            return None
        
        parts = result.split(":", 1)
        if len(parts) != 2:
            return None
        
        tool_name = parts[0].replace("Tool ", "").strip()
        tool_output = parts[1].strip()
        
        # Extract timing information if available
        execution_time = self._extract_execution_time(tool_output)
        
        # Determine tool category
        tool_category = self._categorize_tool(tool_name)
        
        return {
            "name": tool_name,
            "category": tool_category,
            "success": not any(word in result.lower() for word in ["failed", "error", "exception"]),
            "timestamp": datetime.now().isoformat(),
            "output_length": len(tool_output),
            "has_error": any(word in result.lower() for word in ["error", "failed", "exception"]),
            "execution_time_ms": execution_time,
            "performance_score": self._calculate_performance_score(tool_name, execution_time)
        }
    
    def _extract_execution_time(self, output: str) -> Optional[int]:
        """Extract execution time from tool output"""
        import re
        
        # Look for time patterns like "completed in 1.23s" or "took 500ms"
        time_patterns = [
            r'(?:completed|finished|took|execution time:|in) (\d+\.?\d*)s',  # seconds
            r'(?:completed|finished|took|execution time:) (\d+\.?\d*)ms',    # milliseconds
            r'(\d+\.?\d*)ms',  # standalone milliseconds
            r'(\d+\.?\d*)s'    # standalone seconds
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, output.lower())
            if match:
                time_value = float(match.group(1))
                # Convert to milliseconds if pattern indicates seconds
                if 's' in pattern and 'ms' not in pattern:
                    return int(time_value * 1000)
                else:
                    return int(time_value)
        
        return None
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool by type"""
        categories = {
            "data_processing": ["scanpy", "pandas", "numpy", "scipy"],
            "visualization": ["matplotlib", "seaborn", "plotly", "bokeh"],
            "analysis": ["sklearn", "statsmodels", "pydeseq2"],
            "io": ["h5py", "zarr", "pickle"],
            "utility": ["os", "sys", "pathlib"]
        }
        
        tool_lower = tool_name.lower()
        for category, tools in categories.items():
            if any(t in tool_lower for t in tools):
                return category
        
        return "other"
    
    def _calculate_performance_score(self, tool_name: str, execution_time: Optional[int]) -> float:
        """Calculate performance score for tool usage"""
        if execution_time is None:
            return 0.5  # Neutral score
        
        # Get historical performance
        if tool_name in self._tool_performance:
            avg_time = sum(self._tool_performance[tool_name]) / len(self._tool_performance[tool_name])
            
            # Score based on how this execution compares to average
            if execution_time <= avg_time * 0.8:
                return 1.0  # Excellent
            elif execution_time <= avg_time * 1.2:
                return 0.8  # Good
            elif execution_time <= avg_time * 2.0:
                return 0.6  # Fair
            else:
                return 0.3  # Poor
        
        # No historical data, score based on absolute time
        if execution_time < 1000:  # < 1 second
            return 0.9
        elif execution_time < 5000:  # < 5 seconds
            return 0.7
        elif execution_time < 30000:  # < 30 seconds
            return 0.5
        else:
            return 0.3
    
    def _track_tool_performance(self, tool_info: Dict[str, Any]) -> None:
        """Track tool performance for future scoring"""
        tool_name = tool_info["name"]
        execution_time = tool_info.get("execution_time_ms")
        
        if execution_time is not None:
            if tool_name not in self._tool_performance:
                self._tool_performance[tool_name] = []
            
            # Keep only last 50 measurements
            self._tool_performance[tool_name].append(execution_time)
            if len(self._tool_performance[tool_name]) > 50:
                self._tool_performance[tool_name] = self._tool_performance[tool_name][-50:]
    
    def get_tool_performance_stats(self) -> Dict[str, Any]:
        """Get tool performance statistics"""
        stats = {}
        for tool_name, times in self._tool_performance.items():
            if times:
                stats[tool_name] = {
                    "average_time_ms": sum(times) / len(times),
                    "min_time_ms": min(times),
                    "max_time_ms": max(times),
                    "usage_count": len(times),
                    "reliability_score": sum(1 for t in times if t < 10000) / len(times)  # % under 10s
                }
        return stats

class ElectronSessionProvider:
    """Session provider for Electron applications with IPC support"""
    
    def __init__(self, ipc_handler=None):
        self.data: Dict[str, Any] = {}
        self.ipc_handler = ipc_handler
        self.change_listeners: List[Callable] = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with Electron IPC support"""
        value = self.data.get(key, default)
        
        # Notify Electron if IPC handler is available
        if self.ipc_handler:
            try:
                self.ipc_handler.send('session-get', {'key': key, 'value': value})
            except Exception as e:
                logging.getLogger("electron_session").error(f"IPC error: {e}")
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value with change notification"""
        old_value = self.data.get(key)
        self.data[key] = value
        
        # Notify change listeners
        for listener in self.change_listeners:
            try:
                listener(key, value, old_value)
            except Exception as e:
                logging.getLogger("electron_session").error(f"Listener error: {e}")
        
        # Notify Electron
        if self.ipc_handler:
            try:
                self.ipc_handler.send('session-set', {'key': key, 'value': value})
            except Exception as e:
                logging.getLogger("electron_session").error(f"IPC error: {e}")
    
    def delete(self, key: str) -> None:
        """Delete key with notification"""
        if key in self.data:
            old_value = self.data.pop(key)
            
            # Notify listeners
            for listener in self.change_listeners:
                try:
                    listener(key, None, old_value)
                except Exception as e:
                    logging.getLogger("electron_session").error(f"Listener error: {e}")
    
    def clear(self) -> None:
        """Clear all data"""
        self.data.clear()
        
        # Notify Electron
        if self.ipc_handler:
            try:
                self.ipc_handler.send('session-clear', {})
            except Exception as e:
                logging.getLogger("electron_session").error(f"IPC error: {e}")
    
    def add_change_listener(self, listener: Callable) -> None:
        """Add change listener"""
        self.change_listeners.append(listener)
    
    def remove_change_listener(self, listener: Callable) -> None:
        """Remove change listener"""
        if listener in self.change_listeners:
            self.change_listeners.remove(listener)

class StreamlitSessionProvider:
    """Enhanced Streamlit session provider with caching"""
    
    def __init__(self, session_state):
        self.session_state = session_state
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=1)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with caching"""
        # Check cache first
        if key in self._cache and self._is_cache_valid(key):
            return self._cache[key]
        
        # Get from session state
        value = getattr(self.session_state, key, default)
        
        # Cache the value
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value and update cache"""
        setattr(self.session_state, key, value)
        self._cache[key] = value
        self._cache_timestamps[key] = datetime.now()
    
    def delete(self, key: str) -> None:
        """Delete key from session and cache"""
        if hasattr(self.session_state, key):
            delattr(self.session_state, key)
        self._cache.pop(key, None)
        self._cache_timestamps.pop(key, None)
    
    def clear(self) -> None:
        """Clear session and cache"""
        # Clear Streamlit session
        for key in list(self.session_state.keys()):
            delattr(self.session_state, key)
        
        # Clear cache
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached value is still valid"""
        if key not in self._cache_timestamps:
            return False
        return datetime.now() - self._cache_timestamps[key] < self._cache_ttl

class MockSessionProvider:
    """Enhanced mock session provider for testing"""
    
    def __init__(self, data: Dict[str, Any] = None):
        self.data = data or {}
        self.access_log: List[Dict[str, Any]] = []
        self.change_log: List[Dict[str, Any]] = []
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value with access logging"""
        value = self.data.get(key, default)
        self.access_log.append({
            "action": "get",
            "key": key,
            "value": value,
            "timestamp": datetime.now()
        })
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set value with change logging"""
        old_value = self.data.get(key)
        self.data[key] = value
        
        self.change_log.append({
            "action": "set",
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "timestamp": datetime.now()
        })
    
    def delete(self, key: str) -> None:
        """Delete key with logging"""
        if key in self.data:
            old_value = self.data.pop(key)
            self.change_log.append({
                "action": "delete",
                "key": key,
                "old_value": old_value,
                "timestamp": datetime.now()
            })
    
    def clear(self) -> None:
        """Clear all data with logging"""
        old_data = self.data.copy()
        self.data.clear()
        self.change_log.append({
            "action": "clear",
            "old_data": old_data,
            "timestamp": datetime.now()
        })
    
    def get_access_stats(self) -> Dict[str, Any]:
        """Get access statistics"""
        return {
            "total_accesses": len(self.access_log),
            "total_changes": len(self.change_log),
            "most_accessed_keys": self._get_most_accessed_keys(),
            "recent_activity": len([
                log for log in self.access_log 
                if log["timestamp"] > datetime.now() - timedelta(minutes=5)
            ])
        }
    
    def _get_most_accessed_keys(self) -> List[str]:
        """Get most frequently accessed keys"""
        key_counts = {}
        for log in self.access_log:
            key = log["key"]
            key_counts[key] = key_counts.get(key, 0) + 1
        
        return sorted(key_counts.keys(), key=lambda k: key_counts[k], reverse=True)[:5]

# Backward compatibility aliases
UserAnonymizer = EnhancedUserAnonymizer
ContextExtractor = EnhancedContextExtractor
ToolUsageExtractor = EnhancedToolUsageExtractor

# Factory functions with enhanced features
def create_context_extractor(session_provider: SessionProvider = None) -> EnhancedContextExtractor:
    """Factory function to create enhanced context extractor"""
    return EnhancedContextExtractor(session_provider)

def create_user_anonymizer(salt: str = None, cache_size: int = 1000) -> EnhancedUserAnonymizer:
    """Factory function to create enhanced user anonymizer"""
    return EnhancedUserAnonymizer(salt, cache_size)

def create_tool_extractor() -> EnhancedToolUsageExtractor:
    """Factory function to create enhanced tool usage extractor"""
    return EnhancedToolUsageExtractor()

# Decorator for performance monitoring
def monitor_performance(func):
    """Decorator to monitor function performance"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logging.getLogger("performance").info(f"{func.__name__}: {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logging.getLogger("performance").error(f"{func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000
            logging.getLogger("performance").info(f"{func.__name__}: {execution_time:.2f}ms")
            return result
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logging.getLogger("performance").error(f"{func.__name__} failed after {execution_time:.2f}ms: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def main():
        """Test enhanced utilities"""
        print("Testing Enhanced Training Utilities")
        print("=" * 45)
        
        # Test enhanced anonymizer
        anonymizer = EnhancedUserAnonymizer()
        user_id = anonymizer.anonymize_user_id("user@example.com")
        session_id = anonymizer.generate_session_id()
        stats = anonymizer.get_anonymization_stats()
        
        print(f"✓ Enhanced anonymizer: {user_id}, {session_id}")
        print(f"✓ Anonymization stats: {stats}")
        
        # Test enhanced context extractor
        mock_session = MockSessionProvider({
            "qc_done": True,
            "scrna_current_step": "normalization",
            "n_top_genes": 2000,
            "anndata": type('MockAnnData', (), {'n_obs': 1000, 'n_vars': 2000})()
        })
        
        extractor = EnhancedContextExtractor(mock_session)
        context = extractor.extract_analysis_context()
        analysis_type = extractor.determine_analysis_type()
        
        print(f"✓ Enhanced context: {len(context)} sections")
        print(f"✓ Analysis type: {analysis_type}")
        
        # Test enhanced tool extractor
        tool_extractor = EnhancedToolUsageExtractor()
        tool_results = [
            "Tool scanpy: Successfully normalized data in 1.23s",
            "Tool matplotlib: Created plot in 500ms"
        ]
        tools = tool_extractor.extract_tools_used(tool_results)
        performance_stats = tool_extractor.get_tool_performance_stats()
        
        print(f"✓ Enhanced tools: {len(tools)} tools extracted")
        print(f"✓ Performance tracking: {len(performance_stats)} tools tracked")
        
        # Test mock session stats
        session_stats = mock_session.get_access_stats()
        print(f"✓ Session stats: {session_stats}")
        
        print("✓ All enhanced utility tests completed!")
    
if __name__ == "__main__":
    main()