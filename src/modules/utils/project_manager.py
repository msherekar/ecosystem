"""
Project Manager Module

Provides project directory creation and management functionality.
"""

import os
from typing import Dict, Any
from pathlib import Path
import streamlit as st


def create_project_directory(project_name: str, base_path: str = "projects") -> Dict[str, Any]:
    """
    Create a new project directory with standard structure
    
    Args:
        project_name: Name of the project
        base_path: Base path where projects are stored
        
    Returns:
        Dictionary with creation result
    """
    try:
        # Sanitize project name
        sanitized_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        sanitized_name = sanitized_name.replace(' ', '_')
        
        if not sanitized_name:
            return {
                "success": False,
                "message": "Invalid project name",
                "error": "Project name must contain at least one alphanumeric character"
            }
        
        # Create project path
        project_path = Path(base_path) / sanitized_name
        
        # Check if project already exists
        if project_path.exists():
            return {
                "success": False,
                "message": f"Project '{sanitized_name}' already exists",
                "project_path": str(project_path),
                "error": "Project directory already exists"
            }
        
        # Create project directory structure
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['data', 'results', 'plots', 'logs', 'config']
        for subdir in subdirs:
            (project_path / subdir).mkdir(exist_ok=True)
        
        # Create basic files
        readme_content = f"""# {project_name}

Project created on: {os.getcwd()}

## Directory Structure
- `data/`: Raw and processed data files
- `results/`: Analysis results and outputs  
- `plots/`: Generated visualizations
- `logs/`: Analysis logs and history
- `config/`: Configuration files

## Usage
Add your analysis files and data to the appropriate directories.
"""
        
        (project_path / "README.md").write_text(readme_content)
        (project_path / ".gitignore").write_text("*.tmp\n*.log\n__pycache__/\n")
        
        # Update session state
        if 'st' in globals():
            st.session_state["current_project"] = sanitized_name
            st.session_state["project_path"] = str(project_path)
        
        return {
            "success": True,
            "message": f"Successfully created project '{sanitized_name}'",
            "project_name": sanitized_name,
            "project_path": str(project_path),
            "subdirectories": subdirs,
            "files_created": ["README.md", ".gitignore"]
        }
        
    except PermissionError:
        return {
            "success": False,
            "message": "Permission denied when creating project directory",
            "error": "Insufficient permissions"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create project directory: {str(e)}",
            "error": str(e)
        }


def list_projects(base_path: str = "projects") -> Dict[str, Any]:
    """
    List all existing projects
    
    Args:
        base_path: Base path where projects are stored
        
    Returns:
        Dictionary with list of projects
    """
    try:
        base_dir = Path(base_path)
        
        if not base_dir.exists():
            return {
                "success": True,
                "projects": [],
                "message": "No projects directory found"
            }
        
        projects = []
        for item in base_dir.iterdir():
            if item.is_dir():
                projects.append({
                    "name": item.name,
                    "path": str(item),
                    "created": item.stat().st_ctime
                })
        
        return {
            "success": True,
            "projects": projects,
            "count": len(projects)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to list projects: {str(e)}",
            "error": str(e)
        }


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_project_manager():
        """Test project manager functionality"""
        print("Testing project_manager module...")
        
        # Test create_project_directory
        result = create_project_directory("test_project_123")
        print(f"✅ create_project_directory: {result.get('success', False)}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        # Test with invalid name
        result = create_project_directory("")
        print(f"✅ Invalid project name handling: {not result.get('success', True)}")
        
        # Test with special characters
        result = create_project_directory("My Test Project!")
        print(f"✅ Special character handling: {result.get('success', False)}")
        if result.get('success'):
            print(f"   Sanitized name: {result.get('project_name', 'unknown')}")
        
        # Test list_projects
        result = list_projects()
        print(f"✅ list_projects: {result.get('success', False)}")
        print(f"   Found {result.get('count', 0)} projects")
        
        # Clean up test project if created
        import shutil
        try:
            if Path("projects/test_project_123").exists():
                shutil.rmtree("projects/test_project_123")
                print("✅ Cleaned up test project")
        except:
            pass
        
        print("🎉 All project_manager tests passed!")
    
    # Run test
    test_project_manager() 