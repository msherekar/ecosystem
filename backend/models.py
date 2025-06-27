# Pydantic Models for Gliaent Backend
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class CodeRequest(BaseModel):
    code: str
    timeout: Optional[int] = 10

class CodeResponse(BaseModel):
    output: str
    error: Optional[str] = None
    exit_code: int

class ModuleListResponse(BaseModel):
    modules: List[Dict[str, Any]]

class ModuleInfoRequest(BaseModel):
    module_name: str 