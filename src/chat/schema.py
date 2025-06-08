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


# Test code to verify the module works independently
if __name__ == "__main__":
    def test_schema():
        """Test schema functionality"""
        print("Testing schema module...")
        
        # Test tools list
        print(f"✅ Defined {len(tools)} tools")
        
        # Test each tool structure
        for i, tool in enumerate(tools):
            tool_name = tool["function"]["name"]
            description = tool["function"]["description"]
            parameters = tool["function"]["parameters"]
            
            print(f"✅ Tool {i+1}: {tool_name}")
            print(f"   Description: {description[:50]}...")
            print(f"   Parameters: {len(parameters.get('properties', {}))} defined")
            print(f"   Required: {len(parameters.get('required', []))}")
            
            # Validate structure
            assert "type" in tool
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            assert "type" in tool["function"]["parameters"]
            assert "properties" in tool["function"]["parameters"]
            print(f"   ✅ Structure valid")
        
        # Test specific tools
        tool_names = [tool["function"]["name"] for tool in tools]
        expected_tools = ["file_upload", "make_project_dir", "pubmed_search", "geo_search"]
        
        for expected in expected_tools:
            if expected in tool_names:
                print(f"✅ Found expected tool: {expected}")
            else:
                print(f"❌ Missing expected tool: {expected}")
        
        # Test OpenAI function calling format compatibility
        for tool in tools:
            assert tool["type"] == "function"
            func = tool["function"]
            assert "name" in func and isinstance(func["name"], str)
            assert "description" in func and isinstance(func["description"], str)
            assert "parameters" in func and isinstance(func["parameters"], dict)
            
        print("✅ All tools are OpenAI function calling compatible")
        
        print("🎉 All schema tests passed!")
    
    # Run test
    test_schema()