
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

pubmed_search = { "type": "function", 
               "function": {"name": "pubmed_search", "description": "Reader wants to search for scientific journal articles on a given topic on Pubmed", 
                            "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "The query to search PubMed for, e.g. 'cancer', 'cancer and immunotherapy', 'cancer and immunotherapy and immunotherapy' or any other topic of disease/interest"}}, "required": ["query"]}
        }
    }
geo_search = {
    "type": "function",
    "function": {
        "name": "geo_search",
        "description": "Reader wants to search for datasets in NCBI GEO",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", 
                          "description": "The query to search NCBI GEO for, e.g. 'cancer', 'cancer and immunotherapy', 'cancer and immunotherapy and immunotherapy' or any other topic of disease/interest"}
            },
            "required": ["query"]
        }
    }
}


tools = [file_upload, make_project_dir, pubmed_search, geo_search]