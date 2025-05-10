
file_upload = { "type": "function", 
               "function": {"name": "file_upload", "description": "Display a widget to Upload a file", 
                            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }

make_project_dir = { "type": "function", 
               "function": {"name": "make_project_dir", "description": "Create a new directory for a project", 
                            "parameters": {"type": "object", "properties": {"project_name": {"type": "string", "description": "The name of the project"}}, "required": ["project_name"]}
        }
    }


tools = [file_upload, make_project_dir]
