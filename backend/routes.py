# Backend Routes - All API endpoints
from fastapi import HTTPException
from .models import CodeRequest, CodeResponse, ModuleListResponse, ModuleInfoRequest
from .code_executor import execute_code
from .module_scanner import scan_modules, get_module_details

def setup_routes(app):
    """Setup all API routes."""
    
    @app.post("/execute", response_model=CodeResponse)
    async def execute_python_code(request: CodeRequest):
        """Execute Python code safely and return the output."""
        return await execute_code(request)
    
    @app.get("/modules", response_model=ModuleListResponse)
    async def list_available_modules():
        """List all available Gliaent modules."""
        modules = scan_modules()
        return ModuleListResponse(modules=modules)
    
    @app.post("/module-info")
    async def get_module_info(request: ModuleInfoRequest):
        """Get detailed information about a specific module."""
        return get_module_details(request.module_name)
    
    @app.post("/execute-module")
    async def execute_module_function(request: dict):
        """Execute a specific function from a Gliaent module."""
        from .module_executor import execute_module_function
        return await execute_module_function(request) 