"""
Event system for training data collection with Electron integration.
Provides real-time updates and communication with frontend.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum

class EventType(Enum):
    """Training system event types"""
    # Data collection events
    CONVERSATION_COLLECTED = "conversation_collected"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    
    # Storage events
    DATASET_SAVED = "dataset_saved"
    DATA_EXPORTED = "data_exported"
    CLEANUP_COMPLETED = "cleanup_completed"
    
    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    CONFIG_UPDATED = "config_updated"
    ERROR_OCCURRED = "error_occurred"
    
    # UI events
    STATS_UPDATED = "stats_updated"
    PROGRESS_UPDATED = "progress_updated"

@dataclass
class TrainingEvent:
    """Training system event data structure"""
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict[str, Any]
    source: str = "training_system"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "source": self.source
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), default=str)

class EventBus:
    """Async event bus for training system events"""
    
    def __init__(self):
        self.logger = logging.getLogger("event_bus")
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._event_history: List[TrainingEvent] = []
        self._max_history = 1000
        self._websocket_clients: Set[Any] = set()
    
    def subscribe(self, event_type: EventType, callback: Callable) -> str:
        """Subscribe to specific event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        self._subscribers[event_type].append(callback)
        subscription_id = str(uuid.uuid4())
        
        self.logger.debug(f"Subscribed to {event_type.value}: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """Unsubscribe from event type"""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self.logger.debug(f"Unsubscribed from {event_type.value}")
            except ValueError:
                pass
    
    async def emit(self, event_type: EventType, data: Dict[str, Any], 
                   source: str = "training_system") -> None:
        """Emit event to all subscribers"""
        event = TrainingEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            source=source
        )
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Notify subscribers
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                except Exception as e:
                    self.logger.error(f"Error in event callback: {e}")
        
        # Send to WebSocket clients (Electron)
        await self._broadcast_to_websockets(event)
        
        self.logger.debug(f"Emitted event: {event_type.value}")
    
    async def _broadcast_to_websockets(self, event: TrainingEvent) -> None:
        """Broadcast event to WebSocket clients"""
        if not self._websocket_clients:
            return
        
        message = event.to_json()
        disconnected_clients = set()
        
        for client in self._websocket_clients:
            try:
                await client.send(message)
            except Exception as e:
                self.logger.warning(f"Failed to send to WebSocket client: {e}")
                disconnected_clients.add(client)
        
        # Remove disconnected clients
        self._websocket_clients -= disconnected_clients
    
    def add_websocket_client(self, client) -> None:
        """Add WebSocket client for real-time updates"""
        self._websocket_clients.add(client)
        self.logger.info("WebSocket client connected")
    
    def remove_websocket_client(self, client) -> None:
        """Remove WebSocket client"""
        self._websocket_clients.discard(client)
        self.logger.info("WebSocket client disconnected")
    
    def get_event_history(self, event_type: EventType = None, 
                         limit: int = 100) -> List[TrainingEvent]:
        """Get recent event history"""
        events = self._event_history[-limit:]
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return events

class ElectronBridge:
    """Bridge for communicating with Electron frontend"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.logger = logging.getLogger("electron_bridge")
        self._setup_electron_handlers()
    
    def _setup_electron_handlers(self) -> None:
        """Setup event handlers for Electron communication"""
        # Subscribe to all events for forwarding to Electron
        for event_type in EventType:
            self.event_bus.subscribe(event_type, self._forward_to_electron)
    
    async def _forward_to_electron(self, event: TrainingEvent) -> None:
        """Forward events to Electron renderer process"""
        try:
            # This would integrate with actual Electron IPC
            # For now, we'll use WebSocket communication
            pass
        except Exception as e:
            self.logger.error(f"Failed to forward event to Electron: {e}")
    
    async def handle_electron_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messages from Electron frontend"""
        try:
            action = message.get("action")
            data = message.get("data", {})
            
            if action == "get_stats":
                return await self._get_system_stats()
            elif action == "export_data":
                return await self._export_data(data)
            elif action == "update_config":
                return await self._update_config(data)
            elif action == "get_event_history":
                return await self._get_event_history(data)
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            self.logger.error(f"Error handling Electron message: {e}")
            return {"error": str(e)}
    
    async def _get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics for Electron UI"""
        # This would integrate with the main training system
        return {
            "status": "success",
            "data": {
                "total_conversations": 0,
                "active_sessions": 0,
                "storage_usage": "0 MB"
            }
        }
    
    async def _export_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data export request from Electron"""
        try:
            # Emit progress events during export
            await self.event_bus.emit(
                EventType.PROGRESS_UPDATED,
                {"operation": "export", "progress": 0}
            )
            
            # Simulate export process
            for i in range(1, 101, 20):
                await asyncio.sleep(0.1)  # Simulate work
                await self.event_bus.emit(
                    EventType.PROGRESS_UPDATED,
                    {"operation": "export", "progress": i}
                )
            
            await self.event_bus.emit(
                EventType.DATA_EXPORTED,
                {"filename": "export.jsonl", "format": "jsonl"}
            )
            
            return {"status": "success", "filename": "export.jsonl"}
        
        except Exception as e:
            await self.event_bus.emit(
                EventType.ERROR_OCCURRED,
                {"error": str(e), "operation": "export"}
            )
            return {"status": "error", "error": str(e)}
    
    async def _update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle configuration update from Electron"""
        try:
            await self.event_bus.emit(
                EventType.CONFIG_UPDATED,
                {"updated_fields": list(config_data.keys())}
            )
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def _get_event_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get event history for Electron UI"""
        try:
            event_type_str = params.get("event_type")
            limit = params.get("limit", 100)
            
            event_type = None
            if event_type_str:
                event_type = EventType(event_type_str)
            
            events = self.event_bus.get_event_history(event_type, limit)
            
            return {
                "status": "success",
                "events": [event.to_dict() for event in events]
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global event bus instance
_event_bus: Optional[EventBus] = None

def get_event_bus() -> EventBus:
    """Get or create global event bus"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

def create_electron_bridge() -> ElectronBridge:
    """Create Electron bridge with event bus"""
    return ElectronBridge(get_event_bus())

# Convenience functions for common events
async def emit_conversation_collected(conversation_data: Dict[str, Any]) -> None:
    """Emit conversation collected event"""
    await get_event_bus().emit(EventType.CONVERSATION_COLLECTED, conversation_data)

async def emit_system_started(config_data: Dict[str, Any]) -> None:
    """Emit system started event"""
    await get_event_bus().emit(EventType.SYSTEM_STARTED, config_data)

async def emit_error(error_message: str, context: Dict[str, Any] = None) -> None:
    """Emit error event"""
    data = {"error": error_message}
    if context:
        data.update(context)
    await get_event_bus().emit(EventType.ERROR_OCCURRED, data)


def main():
    """Test the event system"""
    import asyncio
    
    async def test_events():
        print("Testing Training Event System")
        print("=" * 40)
        
        # Create event bus
        event_bus = get_event_bus()
        
        # Test subscriber
        received_events = []
        
        async def test_handler(event: TrainingEvent):
            received_events.append(event)
            print(f"Received: {event.event_type.value}")
        
        # Subscribe to events
        event_bus.subscribe(EventType.CONVERSATION_COLLECTED, test_handler)
        event_bus.subscribe(EventType.SYSTEM_STARTED, test_handler)
        
        # Emit test events
        await emit_conversation_collected({
            "user_message": "Test message",
            "success": True
        })
        
        await emit_system_started({
            "config": "test_config"
        })
        
        await emit_error("Test error", {"component": "test"})
        
        # Test Electron bridge
        bridge = create_electron_bridge()
        
        response = await bridge.handle_electron_message({
            "action": "get_stats"
        })
        print(f"Electron response: {response}")
        
        # Check results
        print(f"✓ Received {len(received_events)} events")
        print(f"✓ Event history: {len(event_bus.get_event_history())} events")
        print("✓ Event system test completed")
    
    asyncio.run(test_events())
    
if __name__ == "__main__":
    main()