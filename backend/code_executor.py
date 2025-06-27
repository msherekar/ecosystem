# Code Execution Module
import subprocess
import tempfile
import os
import sys
from fastapi import HTTPException
from .models import CodeRequest, CodeResponse

async def execute_code(request: CodeRequest):
    """Execute Python code safely and return the output."""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(request.code)
            temp_file_path = temp_file.name
        
        try:
            # Execute the Python code in a subprocess
            result = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=request.timeout,
                cwd=tempfile.gettempdir()
            )
            
            return CodeResponse(
                output=result.stdout,
                error=result.stderr if result.stderr else None,
                exit_code=result.returncode
            )
            
        except subprocess.TimeoutExpired:
            return CodeResponse(
                output="",
                error="Code execution timed out",
                exit_code=-1
            )
        
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Execution error: {str(e)}") 