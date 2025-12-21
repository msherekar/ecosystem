"""
Event System for Electron IPC Integration

Provides thread-safe event emission and handling for real-time communication
between Python backend and Electron frontend.
"""

import asyncio
import json
import logging
import threading
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Structured event data for IPC communication"""
    event: str
    data: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "python_backend"
    priority: int = 0  # 0=normal, 1=high, 2=critical
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization"""
        return {
            "event": self.event,
            "data": self.data,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "id": self.id,
            "source": self.source,
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event=data["event"],
            data=data.get("data"),
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            id=data.get("id", str(uuid.uuid4())),
            source=data.get("source", "python_backend"),
            priority=data.get("priority", 0)
        )


class EventEmitter:
    """Thread-safe event emitter for Electron IPC communication"""
    
    def __init__(self, max_queue_size: int = 1000):
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()
        self._event_queue: deque = deque(maxlen=max_queue_size)
        self._max_queue_size = max_queue_size
        self._stats = {
            "events_emitted": 0,
            "events_handled": 0,
            "handlers_registered": 0,
            "queue_overflows": 0
        }
        
        # Priority queues for different urgency levels
        self._priority_queues = {
            0: deque(maxlen=max_queue_size),  # Normal
            1: deque(maxlen=max_queue_size // 2),  # High
            2: deque(maxlen=max_queue_size // 4)   # Critical
        }
        
        # Event filtering
        self._event_filters: Set[str] = set()
        self._enabled = True
    
    def on(self, event_name: str, handler: Callable, priority: int = 0):
        """
        Register event handler
        
        Args:
            event_name: Name of event to handle
            handler: Callback function
            priority: Handler priority (higher = called first)
        """
        with self._lock:
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            
            # Insert handler based on priority
            handlers = self._handlers[event_name]
            inserted = False
            for i, (existing_handler, existing_priority) in enumerate(handlers):
                if priority > existing_priority:
                    handlers.insert(i, (handler, priority))
                    inserted = True
                    break
            
            if not inserted:
                handlers.append((handler, priority))
            
            self._stats["handlers_registered"] += 1
            logger.debug(f"Registered handler for event '{event_name}' with priority {priority}")
    
    def off(self, event_name: str, handler: Callable = None):
        """
        Remove event handler(s)
        
        Args:
            event_name: Name of event
            handler: Specific handler to remove (if None, removes all)
        """
        with self._lock:
            if event_name not in self._handlers:
                return
            
            if handler is None:
                # Remove all handlers for this event
                del self._handlers[event_name]
            else:
                # Remove specific handler
                self._handlers[event_name] = [
                    (h, p) for h, p in self._handlers[event_name] 
                    if h != handler
                ]
                
                # Clean up empty event entries
                if not self._handlers[event_name]:
                    del self._handlers[event_name]
    
    def emit(self, event_name: str, data: Any = None, metadata: Optional[Dict[str, Any]] = None, 
             priority: int = 0, sync: bool = False):
        """
        Emit event to handlers and queue for UI
        
        Args:
            event_name: Name of event to emit
            data: Event data
            metadata: Additional metadata
            priority: Event priority (0=normal, 1=high, 2=critical)
            sync: Whether to wait for handlers to complete
        """
        if not self._enabled:
            return
        
        if event_name in self._event_filters:
            logger.debug(f"Event '{event_name}' filtered out")
            return
        
        # Create event
        event = Event(
            event=event_name,
            data=data,
            metadata=metadata or {},
            priority=priority
        )
        
        with self._lock:
            # Add to appropriate queue
            if priority in self._priority_queues:
                queue = self._priority_queues[priority]
                if len(queue) >= queue.maxlen:
                    self._stats["queue_overflows"] += 1
                    logger.warning(f"Priority {priority} queue overflow for event '{event_name}'")
                queue.append(event)
            
            # Add to main queue
            if len(self._event_queue) >= self._max_queue_size:
                self._stats["queue_overflows"] += 1
            self._event_queue.append(event)
            
            self._stats["events_emitted"] += 1
        
        # Call handlers
        self._call_handlers(event_name, event, sync)
        
        logger.debug(f"Emitted event '{event_name}' with priority {priority}")
    
    def _call_handlers(self, event_name: str, event: Event, sync: bool = False):
        """Call registered handlers for an event"""
        handlers = []
        with self._lock:
            if event_name in self._handlers:
                handlers = self._handlers[event_name].copy()
        
        if not handlers:
            return
        
        # Sort handlers by priority (highest first)
        handlers.sort(key=lambda x: x[1], reverse=True)
        
        for handler, priority in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    if sync:
                        # Run async handler synchronously
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                # Create task for async execution
                                asyncio.create_task(handler(event))
                            else:
                                # Run in new event loop
                                asyncio.run(handler(event))
                        except RuntimeError:
                            # No event loop available
                            asyncio.create_task(handler(event))
                    else:
                        # Async handler, non-blocking
                        try:
                            asyncio.create_task(handler(event))
                        except RuntimeError:
                            # No event loop, log warning
                            logger.warning(f"No event loop available for async handler: {event_name}")
                else:
                    # Sync handler
                    handler(event)
                
                self._stats["events_handled"] += 1
                
            except Exception as e:
                logger.error(f"Error in event handler for '{event_name}': {e}")
                # Emit error event
                if event_name != "handler_error":  # Prevent infinite recursion
                    self.emit("handler_error", {
                        "original_event": event_name,
                        "error": str(e),
                        "handler": str(handler)
                    })
    
    def get_events(self, since: Optional[str] = None, limit: Optional[int] = None, 
                   priority_filter: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get events for Electron IPC polling
        
        Args:
            since: ISO timestamp to filter events after
            limit: Maximum number of events to return
            priority_filter: Filter by priority level
            
        Returns:
            List of event dictionaries
        """
        with self._lock:
            # Combine events from all queues, prioritizing high-priority
            all_events = []
            
            if priority_filter is not None:
                # Return only events from specific priority queue
                if priority_filter in self._priority_queues:
                    all_events = list(self._priority_queues[priority_filter])
            else:
                # Combine all queues, highest priority first
                for priority in sorted(self._priority_queues.keys(), reverse=True):
                    all_events.extend(self._priority_queues[priority])
                
                # Add remaining events from main queue
                main_events = [e for e in self._event_queue if e not in all_events]
                all_events.extend(main_events)
        
        # Filter by timestamp
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                all_events = [
                    e for e in all_events 
                    if datetime.fromisoformat(e.timestamp) > since_dt
                ]
            except ValueError:
                logger.warning(f"Invalid timestamp format: {since}")
        
        # Apply limit
        if limit:
            all_events = all_events[-limit:]
        
        # Convert to dictionaries
        return [event.to_dict() for event in all_events]
    
    def clear_events(self, priority: Optional[int] = None):
        """
        Clear event queue
        
        Args:
            priority: Clear only specific priority queue (None = all)
        """
        with self._lock:
            if priority is not None:
                if priority in self._priority_queues:
                    self._priority_queues[priority].clear()
            else:
                # Clear all queues
                self._event_queue.clear()
                for queue in self._priority_queues.values():
                    queue.clear()
        
        logger.debug(f"Cleared events (priority: {priority})")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event system statistics"""
        with self._lock:
            queue_sizes = {
                f"priority_{p}_queue_size": len(queue)
                for p, queue in self._priority_queues.items()
            }
            
            return {
                **self._stats.copy(),
                "main_queue_size": len(self._event_queue),
                "active_handlers": sum(len(handlers) for handlers in self._handlers.values()),
                "handler_events": len(self._handlers),
                **queue_sizes,
                "enabled": self._enabled
            }
    
    def set_enabled(self, enabled: bool):
        """Enable or disable event emission"""
        self._enabled = enabled
        logger.info(f"Event system {'enabled' if enabled else 'disabled'}")
    
    def add_filter(self, event_name: str):
        """Add event to filter list (won't be emitted)"""
        self._event_filters.add(event_name)
        logger.debug(f"Added event filter: {event_name}")
    
    def remove_filter(self, event_name: str):
        """Remove event from filter list"""
        self._event_filters.discard(event_name)
        logger.debug(f"Removed event filter: {event_name}")
    
    def reset_stats(self):
        """Reset statistics counters"""
        with self._lock:
            self._stats = {
                "events_emitted": 0,
                "events_handled": 0,
                "handlers_registered": 0,
                "queue_overflows": 0
            }


# Global event emitter instance
_global_emitter = EventEmitter()


def get_event_emitter() -> EventEmitter:
    """Get the global event emitter instance"""
    return _global_emitter


def emit_system_event(event_name: str, data: Any = None, **kwargs):
    """Convenience function to emit system events"""
    _global_emitter.emit(event_name, data, **kwargs)


def emit_ui_update(component: str, update_type: str, data: Any = None, **kwargs):
    """Convenience function to emit UI updates for Electron"""
    _global_emitter.emit("ui_update", {
        "component": component,
        "update_type": update_type,
        "data": data
    }, priority=1, **kwargs)


def emit_error(error_type: str, message: str, details: Any = None, **kwargs):
    """Convenience function to emit error events"""
    _global_emitter.emit("error", {
        "error_type": error_type,
        "message": message,
        "details": details
    }, priority=2, **kwargs)


if __name__ == "__main__":
    # Test event system
    print("Testing Event System")
    
    emitter = EventEmitter()
    
    # Test event handler
    def test_handler(event):
        print(f"Handler received: {event.event} with data: {event.data}")
    
    # Register handler
    emitter.on("test_event", test_handler)
    
    # Emit event
    emitter.emit("test_event", {"message": "Hello from events!"})
    
    # Test priority events
    emitter.emit("urgent_event", {"message": "Urgent!"}, priority=2)
    
    # Get events
    events = emitter.get_events(limit=5)
    print(f"✓ Retrieved {len(events)} events")
    
    # Test statistics
    stats = emitter.get_stats()
    print(f"✓ Event stats: {stats['events_emitted']} emitted, {stats['events_handled']} handled")
    
    print("\n✅ Event system test completed!") 