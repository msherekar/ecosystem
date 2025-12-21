from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import asyncio
import logging
from contextlib import asynccontextmanager

from . import MCPSystem, initialize_mcp_system, get_mcp_system, shutdown_mcp_system
from . import MCPSystemConfiguration

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class ChatRequest(BaseModel):
    message: str = Field(..., description="Message to send to the agent")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class ChatResponse(BaseModel):
    response: str
    suggestions: List[str] = []
    success: bool = True

class AnalysisRequest(BaseModel):
    analysis_type: str = Field(..., description="Type of analysis (e.g., 'rnaseq', 'scrnaseq')")
    context: Dict[str, Any] = Field(..., description="Analysis parameters and data")

class AnalysisResponse(BaseModel):
    result: Dict[str, Any]
    success: bool = True
    analysis_type: str

class SystemStatusResponse(BaseModel):
    version: str
    initialized: bool
    running: bool
    uptime: float
    components: Dict[str, Any]
    electron_mode: bool

class HealthCheckResponse(BaseModel):
    overall_healthy: bool
    components: Dict[str, Any]
    timestamp: str

# Global MCP system instance
mcp_system: Optional[MCPSystem] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for MCP system initialization and cleanup"""
    global mcp_system
    
    # Startup
    logger.info("🚀 Initializing MCP System for FastAPI...")
    try:
        # Initialize with API-optimized configuration
        config = MCPSystemConfiguration(
            name="mcp_fastapi_system",
            electron_mode=False,  # Disable electron for API-only mode
            debug=False,
            enable_intelligent_routing=True,
            enable_coordination=True,
            max_concurrent_operations=100,  # Higher for API usage
            operation_timeout=60,  # Longer timeout for complex analyses
        )
        
        mcp_system = await initialize_mcp_system(config)
        if not mcp_system.initialized:
            raise RuntimeError("Failed to initialize MCP system")
        
        logger.info("✅ MCP System initialized successfully")
        yield
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize MCP system: {e}")
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down MCP System...")
    try:
        if mcp_system:
            await mcp_system.shutdown()
        await shutdown_mcp_system()
        logger.info("✅ MCP System shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# Create FastAPI app with lifespan
app = FastAPI(
    title="MCP Bioinformatics API",
    description="API for the MCP (Model Context Protocol) Bioinformatics System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get MCP system
async def get_mcp_system_dependency() -> MCPSystem:
    """Dependency to get the initialized MCP system"""
    if not mcp_system or not mcp_system.initialized:
        raise HTTPException(status_code=503, detail="MCP system not initialized")
    return mcp_system

# API Routes

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "MCP Bioinformatics API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check(system: MCPSystem = Depends(get_mcp_system_dependency)):
    """Health check endpoint"""
    try:
        health_status = await system.health_check()
        
        # Determine overall health
        overall_healthy = all(
            component.get("healthy", False) 
            for component in health_status.values()
        )
        
        return HealthCheckResponse(
            overall_healthy=overall_healthy,
            components=health_status,
            timestamp=asyncio.get_event_loop().time()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/status", response_model=SystemStatusResponse)
async def get_status(system: MCPSystem = Depends(get_mcp_system_dependency)):
    """Get detailed system status"""
    try:
        status = await system.get_system_status()
        return SystemStatusResponse(**status)
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/tools", response_model=Dict[str, Any])
async def get_available_tools(system: MCPSystem = Depends(get_mcp_system_dependency)):
    """Get all available analysis tools"""
    try:
        tools = await system.get_available_tools()
        return tools
    except Exception as e:
        logger.error(f"Failed to get tools: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    system: MCPSystem = Depends(get_mcp_system_dependency)
):
    """Chat with the intelligent agent"""
    try:
        response, suggestions = await system.chat_with_agent(request.message)
        
        return ChatResponse(
            response=response,
            suggestions=suggestions,
            success=True
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/analysis", response_model=AnalysisResponse)
async def execute_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    system: MCPSystem = Depends(get_mcp_system_dependency)
):
    """Execute a bioinformatics analysis"""
    try:
        result = await system.execute_analysis(
            analysis_type=request.analysis_type,
            context=request.context
        )
        
        return AnalysisResponse(
            result=result,
            success=True,
            analysis_type=request.analysis_type
        )
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analysis/types", response_model=List[str])
async def get_analysis_types(system: MCPSystem = Depends(get_mcp_system_dependency)):
    """Get available analysis types"""
    try:
        # This would typically come from your system configuration
        # You might want to add a method to MCPSystem to get this
        return ["rnaseq", "scrnaseq", "atacseq", "proteomics", "visualization"]
    except Exception as e:
        logger.error(f"Failed to get analysis types: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analysis types: {str(e)}")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "success": False}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "success": False}
    )

# For running the API directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.mcp.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 