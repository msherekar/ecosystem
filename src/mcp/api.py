from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from . import MCPSystem, initialize_mcp_system, shutdown_mcp_system
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
    #: ISO-8601 UTC. This was previously built from
    #: `asyncio.get_event_loop().time()`, a loop-relative float, which failed
    #: Pydantic validation against `str` and made /health return 500 for
    #: every caller — including test_api.py, which printed the error and
    #: still reported success.
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
        
        logger.info("MCP System initialized successfully")
    except Exception:
        logger.exception("Failed to initialize MCP system")
        raise

    try:
        yield
    finally:
        # `finally`, not a trailing block after `except ... raise`: previously
        # any exception out of `yield` re-raised past the shutdown code, so
        # mcp_system.shutdown() was skipped and websockets and background
        # tasks leaked on every error-terminated run.
        logger.info("Shutting down MCP System...")
        try:
            if mcp_system:
                await mcp_system.shutdown()
            await shutdown_mcp_system()
            logger.info("MCP System shutdown complete")
        except Exception:
            logger.exception("Error during MCP system shutdown")

# Create FastAPI app with lifespan
app = FastAPI(
    title="MCP Bioinformatics API",
    description="API for the MCP (Model Context Protocol) Bioinformatics System",
    version="1.0.0",
    lifespan=lifespan
)

def _allowed_origins() -> List[str]:
    """CORS allowlist for this app.

    `allow_origins=["*"]` with `allow_credentials=True` makes Starlette echo
    the request Origin, so any website the user visited could make
    credentialed calls to /chat, /analysis and /config. A literal "*" in the
    override is refused rather than silently accepted.

    Raises:
        ValueError: If the override contains "*".
    """
    raw = os.environ.get("GLIAENT_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError(
            "GLIAENT_ALLOWED_ORIGINS must not contain '*': a wildcard origin "
            "with credentials enabled lets any site call this API."
        )
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Gliaent-Token"],
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
            timestamp=datetime.now(timezone.utc).isoformat(),
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
    # Loopback by default. Binding 0.0.0.0 exposed an unauthenticated API
    # to the whole local network; `reload=True` is a development-only
    # feature and is not enabled implicitly.
    dev = os.environ.get("GLIAENT_DEV", "0").lower() in {"1", "true", "yes"}
    uvicorn.run(
        "src.mcp.api:app",
        host=os.environ.get("GLIAENT_HOST", "127.0.0.1"),
        port=int(os.environ.get("GLIAENT_PORT", "8000")),
        reload=dev,
        log_level="info",
    ) 