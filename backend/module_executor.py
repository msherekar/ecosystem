# Module Function Executor
import sys
import importlib.util
from pathlib import Path
from fastapi import HTTPException

async def execute_module_function(request: dict):
    """Execute a specific function from a Gliaent module."""
    module_name = request.get("module_name")
    function_name = request.get("function_name", "main")
    params = request.get("params", {})
    
    if not module_name:
        raise HTTPException(status_code=400, detail="Module name is required")
    
    try:
        module_path = Path(f"src/modules/{module_name}")
        if not module_path.exists():
            raise HTTPException(status_code=404, detail="Module not found")
        
        # Add the module path to sys.path temporarily
        sys.path.insert(0, str(module_path.parent))
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(
                f"gliaent.modules.{module_name}", 
                module_path / f"{function_name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Execute the function
            if hasattr(module, function_name):
                result = getattr(module, function_name)(**params)
                return {"success": True, "result": result}
            else:
                return {"success": False, "error": f"Function '{function_name}' not found in module"}
                
        finally:
            sys.path.pop(0)
            
    except Exception as e:
        return {"success": False, "error": str(e)} 