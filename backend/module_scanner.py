# Module Discovery and Information
from pathlib import Path
from fastapi import HTTPException

def scan_modules():
    """Scan and return available Gliaent modules."""
    modules = []
    src_path = Path("src/modules")
    
    if src_path.exists():
        for module_dir in src_path.iterdir():
            if (module_dir.is_dir() and 
                not module_dir.name.startswith('.') and 
                not module_dir.name.startswith('__') and
                module_dir.name not in ['__pycache__', '.DS_Store']):
                    
                module_info = {
                    "name": module_dir.name,
                    "path": str(module_dir),
                    "display_name": module_dir.name.replace('_', ' ').title(),
                    "available": True,
                    "type": get_module_type(module_dir)
                }
                modules.append(module_info)
    
    return modules

def get_module_type(module_dir):
    """Determine module type based on files present."""
    if (module_dir / "workflow.py").exists():
        return "workflow"
    elif (module_dir / "streamlit_app.py").exists():
        return "streamlit_app"
    else:
        return "module"

def get_module_details(module_name):
    """Get detailed information about a specific module."""
    module_path = Path(f"src/modules/{module_name}")
    
    if not module_path.exists():
        raise HTTPException(status_code=404, detail="Module not found")
    
    info = {
        "name": module_name,
        "path": str(module_path),
        "files": [{"name": f.name, "path": str(f), "type": "python"} 
                 for f in module_path.glob("*.py")],
        "examples": get_examples(module_name),
        "description": extract_description(module_path)
    }
    
    return info

def get_examples(module_name):
    """Get example files for a module."""
    examples_path = Path(f"examples/{module_name}")
    if examples_path.exists():
        return [{"name": f.name, "path": str(f)} for f in examples_path.glob("*.py")]
    return []

def extract_description(module_path):
    """Extract description from module docstring."""
    workflow_file = module_path / "workflow.py"
    if workflow_file.exists():
        try:
            with open(workflow_file, 'r') as f:
                content = f.read()
                if '"""' in content:
                    start = content.find('"""') + 3
                    end = content.find('"""', start)
                    if end > start:
                        return content[start:end].strip()
        except Exception:
            pass
    return "No description available" 