"""
REST and WebSocket API for training system Electron integration.
Provides HTTP endpoints and real-time WebSocket communication.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .events import get_event_bus, EventType, create_electron_bridge
from .main import get_training_system, log_mcp_interaction

# Pydantic models for API requests/responses
class ConversationRequest(BaseModel):
    """Request model for logging conversations"""
    user_message: str = Field(..., description="User's message")
    assistant_response: str = Field(..., description="Assistant's response")
    tool_results: List[str] = Field(default=[], description="Tool execution results")
    success: bool = Field(default=True, description="Whether interaction was successful")
    user_feedback: Optional[str] = Field(None, description="User feedback")
    context: Dict[str, Any] = Field(default={}, description="Additional context")

class ExportRequest(BaseModel):
    """Request model for data export"""
    output_format: str = Field(default="jsonl", description="Export format")
    filter_analysis_type: Optional[str] = Field(None, description="Filter by analysis type")
    min_success_rate: float = Field(default=0.8, description="Minimum success rate")

class ConfigUpdateRequest(BaseModel):
    """Request model for configuration updates"""
    data_dir: Optional[str] = None
    collect_enabled: Optional[bool] = None
    anonymize_data: Optional[bool] = None
    auto_save_interval: Optional[int] = None
    max_file_size_mb: Optional[int] = None

class APIResponse(BaseModel):
    """Standard API response model"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class TrainingAPI:
    """FastAPI application for training system"""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="Training Data Collection API",
            description="API for MCP training data collection system",
            version="1.0.0"
        )
        self.logger = logging.getLogger("training_api")
        self.event_bus = get_event_bus()
        self.electron_bridge = create_electron_bridge()
        self.websocket_clients: List[WebSocket] = []
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self) -> None:
        """Setup CORS and other middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, restrict to Electron app
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self) -> None:
        """Setup API routes"""
        
        @self.app.get("/", response_model=APIResponse)
        async def root():
            """Root endpoint"""
            return APIResponse(
                success=True,
                data={"message": "Training Data Collection API", "version": "1.0.0"}
            )
        
        @self.app.get("/health", response_model=APIResponse)
        async def health_check():
            """Health check endpoint"""
            try:
                system = get_training_system()
                stats = system.get_system_stats()
                return APIResponse(
                    success=True,
                    data={"status": "healthy", "stats": stats}
                )
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/conversations", response_model=APIResponse)
        async def log_conversation(request: ConversationRequest):
            """Log a conversation for training"""
            try:
                success = await log_mcp_interaction(
                    user_request=request.user_message,
                    mcp_response=request.assistant_response,
                    tools_used=request.tool_results,
                    success=request.success,
                    context=request.context
                )
                
                if success:
                    await self.event_bus.emit(
                        EventType.CONVERSATION_COLLECTED,
                        {
                            "user_message_length": len(request.user_message),
                            "assistant_response_length": len(request.assistant_response),
                            "tools_count": len(request.tool_results),
                            "success": request.success
                        }
                    )
                
                return APIResponse(
                    success=success,
                    data={"logged": success}
                )
            except Exception as e:
                self.logger.error(f"Error logging conversation: {e}")
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/statistics", response_model=APIResponse)
        async def get_statistics():
            """Get system statistics"""
            try:
                system = get_training_system()
                stats = system.get_system_stats()
                return APIResponse(success=True, data=stats)
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/export", response_model=APIResponse)
        async def export_data(request: ExportRequest):
            """Export training data"""
            try:
                system = get_training_system()
                
                # Emit progress start
                await self.event_bus.emit(
                    EventType.PROGRESS_UPDATED,
                    {"operation": "export", "progress": 0}
                )
                
                output_file = await system.export_training_data(
                    output_format=request.output_format,
                    filter_analysis_type=request.filter_analysis_type,
                    min_success_rate=request.min_success_rate
                )
                
                # Emit completion
                await self.event_bus.emit(
                    EventType.DATA_EXPORTED,
                    {"filename": output_file, "format": request.output_format}
                )
                
                return APIResponse(
                    success=True,
                    data={"output_file": output_file}
                )
            except Exception as e:
                await self.event_bus.emit(
                    EventType.ERROR_OCCURRED,
                    {"error": str(e), "operation": "export"}
                )
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/datasets", response_model=APIResponse)
        async def list_datasets():
            """List available datasets"""
            try:
                system = get_training_system()
                datasets = system.storage.list_datasets()
                return APIResponse(success=True, data={"datasets": datasets})
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.post("/config", response_model=APIResponse)
        async def update_config(request: ConfigUpdateRequest):
            """Update system configuration"""
            try:
                system = get_training_system()
                
                # Build update dict from non-None values
                updates = {
                    k: v for k, v in request.dict().items() 
                    if v is not None
                }
                
                if updates:
                    system.config = system.config.update(**updates)
                    
                    await self.event_bus.emit(
                        EventType.CONFIG_UPDATED,
                        {"updated_fields": list(updates.keys())}
                    )
                
                return APIResponse(
                    success=True,
                    data={"updated": list(updates.keys())}
                )
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.get("/events", response_model=APIResponse)
        async def get_events(event_type: Optional[str] = None, limit: int = 100):
            """Get event history"""
            try:
                event_type_enum = None
                if event_type:
                    event_type_enum = EventType(event_type)
                
                events = self.event_bus.get_event_history(event_type_enum, limit)
                
                return APIResponse(
                    success=True,
                    data={
                        "events": [event.to_dict() for event in events],
                        "count": len(events)
                    }
                )
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.delete("/cleanup")
        async def cleanup_data(max_age_days: int = 365):
            """Clean up old training data"""
            try:
                system = get_training_system()
                removed_count = await system.cleanup_old_data(max_age_days)
                
                await self.event_bus.emit(
                    EventType.CLEANUP_COMPLETED,
                    {"removed_files": removed_count, "max_age_days": max_age_days}
                )
                
                return APIResponse(
                    success=True,
                    data={"removed_files": removed_count}
                )
            except Exception as e:
                return APIResponse(success=False, error=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.websocket_clients.append(websocket)
            self.event_bus.add_websocket_client(websocket)
            
            try:
                # Send initial connection message
                await websocket.send_text(json.dumps({
                    "type": "connection",
                    "message": "Connected to training system",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Listen for client messages
                while True:
                    data = await websocket.receive_text()
                    message = json.loads(data)
                    
                    # Handle client requests
                    response = await self.electron_bridge.handle_electron_message(message)
                    await websocket.send_text(json.dumps(response))
                    
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
                self.event_bus.remove_websocket_client(websocket)
                self.logger.info("WebSocket client disconnected")
            except Exception as e:
                self.logger.error(f"WebSocket error: {e}")
                if websocket in self.websocket_clients:
                    self.websocket_clients.remove(websocket)
                self.event_bus.remove_websocket_client(websocket)
    
    async def start_server(self) -> None:
        """Start the API server"""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        self.logger.info(f"Starting Training API server on {self.host}:{self.port}")
        await self.event_bus.emit(
            EventType.SYSTEM_STARTED,
            {"api_host": self.host, "api_port": self.port}
        )
        
        await server.serve()
    
    def run(self) -> None:
        """Run the API server (blocking)"""
        asyncio.run(self.start_server())

class ElectronAPIManager:
    """Manager for Electron-specific API functionality"""
    
    def __init__(self, api: TrainingAPI):
        self.api = api
        self.logger = logging.getLogger("electron_api")
    
    async def send_notification(self, title: str, message: str, 
                               notification_type: str = "info") -> None:
        """Send notification to Electron app"""
        notification_data = {
            "type": "notification",
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to all connected WebSocket clients
        for client in self.api.websocket_clients:
            try:
                await client.send_text(json.dumps(notification_data))
            except Exception as e:
                self.logger.error(f"Failed to send notification: {e}")
    
    async def update_progress(self, operation: str, progress: int, 
                             message: str = None) -> None:
        """Update progress in Electron UI"""
        progress_data = {
            "type": "progress",
            "operation": operation,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in self.api.websocket_clients:
            try:
                await client.send_text(json.dumps(progress_data))
            except Exception as e:
                self.logger.error(f"Failed to send progress update: {e}")

# Global API instance
_api_instance: Optional[TrainingAPI] = None

def get_api_instance(host: str = "localhost", port: int = 8000) -> TrainingAPI:
    """Get or create global API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = TrainingAPI(host, port)
    return _api_instance

def create_electron_api_manager(api: TrainingAPI = None) -> ElectronAPIManager:
    """Create Electron API manager"""
    if api is None:
        api = get_api_instance()
    return ElectronAPIManager(api)


def main():
    """Run the training API server"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Training Data Collection API Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    
    args = parser.parse_args()
    
    if args.test:
        print("Testing Training API")
        print("=" * 30)
        
        api = TrainingAPI(args.host, args.port)
        print(f"✓ API instance created: {args.host}:{args.port}")
        
        electron_manager = create_electron_api_manager(api)
        print("✓ Electron manager created")
        
        print("✓ API routes configured:")
        for route in api.app.routes:
            if hasattr(route, 'path'):
                print(f"  {route.methods} {route.path}")
        
        print("\nStart server with: python api.py")
    else:
        # Start the server
        api = get_api_instance(args.host, args.port)
        api.run()
    
if __name__ == "__main__":
    main()