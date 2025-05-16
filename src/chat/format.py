def format_search_results(results: dict) -> str:
    output = "## Search Results\n\n"

    if "GEO" in results:
        output += "### GEO Results\n\n"
        # Handle the nested hits structure that comes from geo_ncbi_advanced_search
        geo_results = results["GEO"]
        
        # If results is a dictionary with hits key (from geo_ncbi_advanced_search)
        if isinstance(geo_results, dict) and "hits" in geo_results:
            hits = geo_results.get("hits", [])
            total_count = geo_results.get("count", 0)
            search_term = geo_results.get("term", "")
            
            # Add metadata about the search
            if search_term:
                output += f"**Search Query:** `{search_term}`\n\n"
            if total_count is not None:
                output += f"**Total Results:** {total_count}\n\n"
            
            if hits:
                for i, hit in enumerate(hits[:20], 1):  # Limit to top 20 for display
                    output += f"**{i}. {hit.get('title', 'No title')}**\n"
                    output += f"Accession: {hit.get('accession', 'Unknown')}\n"
                    summary = hit.get('summary', 'No summary')
                    output += f"{summary[:200]}"
                    if len(summary) > 200:
                        output += "..."
                    output += "\n\n"
                
                if len(hits) > 20:
                    output += f"*Showing 20 of {len(hits)} results*\n\n"
            else:
                output += "No GEO results found.\n\n"
        # Handle the list structure (from direct geo_ncbi_search)
        elif isinstance(geo_results, list):
            if geo_results:
                for i, hit in enumerate(geo_results, 1):
                    output += f"**{i}. {hit.get('title', 'No title')}**\n"
                    output += f"Accession: {hit.get('accession', 'Unknown')}\n"
                    output += f"{hit.get('summary', 'No summary')[:200]}...\n\n"
            else:
                output += "No GEO results found.\n\n"
        else:
            output += "No GEO results found or invalid result format.\n\n"

    if "TCGA" in results:
        output += "### TCGA Results\n\n"
        for i, hit in enumerate(results["TCGA"], 1):
            output += f"**{i}. {hit.get('name', 'No name')}**\n"
            output += f"Project ID: {hit.get('project_id', 'Unknown')}\n"
            output += f"{hit.get('full_name', 'No full name')}\n\n"
        if not results["TCGA"]:
            output += "No TCGA results found.\n\n"

    return output
