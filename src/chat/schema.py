# Code for function schema for various tools
# This code will help chatbot to decide whether to stay local or send to OpenAI

file_upload = { 
    "type": "function", 
    "function": {
        "name": "file_upload", 
        "description": "Display a widget to Upload a file", 
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

make_project_dir = { 
    "type": "function", 
    "function": {
        "name": "make_project_dir", 
        "description": "Create a new directory for a project", 
        "parameters": {
            "type": "object", 
            "properties": {
                "project_name": {
                    "type": "string", 
                    "description": "The name of the project"
                }
            }, 
            "required": ["project_name"]
        }
    }
}

search = {
    "type": "function",
    "function": {
        "name": "search",
        "description": (
            "Search omics datasets (transcriptomics, proteomics, etc.) "
            "across repositories like NCBI GEO and TCGA"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'breast cancer RNA-seq'"
                },
                "repository": {
                    "type": "string",
                    "enum": ["GEO", "TCGA", "ALL"],
                    "description": (
                        "Which repository to search. "
                        "Use 'ALL' to search both GEO and TCGA."
                    )
                },
                "organism": {
                    "type": "string",
                    "description": "Filter by organism, e.g. 'Homo sapiens'"
                }
            },
            "required": ["query"]
        }
    }
}

data = {
    "type": "function",
    "function": {
        "name": "data",
        "description": "Process and analyze tabular data",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

reader = {
    "type": "function",
    "function": {
        "name": "reader",
        "description": "Read and analyze PDF documents",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

# Define the tools to be available to the model
tools = [file_upload, make_project_dir, search, data, reader]

