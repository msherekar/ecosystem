import json 
import logging
from modules.search.genomics import genomics_search
from modules.search.utils import extract_terms, build_eutils_terms
from modules.data.tabular import tabular_data
from modules.reader.pdf import pdf_reader
from chat.format import format_search_results
from chat.schema import tools


def dispatch_tool_call(tool_call):
    function_name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}

    try:
        query = args.get("query", "")

        if function_name == "geo_search":
            parsed_terms = extract_terms(query)  # Get the full dictionary
            search_terms = parsed_terms.get("keywords", [])  # Extract keywords or handle as needed
            result = genomics_search(
                query=search_terms,
                repository="GEO",
                organism=args.get("organism")
            )
            formatted_result = format_search_results({"GEO": result})
            return {"content": formatted_result, "source": "local_geo"}  

        elif function_name == "tcga_search":
            result = genomics_search(
                query=query,
                repository="TCGA",
                organism=args.get("organism")
            )
            formatted_result = format_search_results({"TCGA": result})
            return {"content": formatted_result, "source": "local_tcga"}  

        elif function_name == "uniprot_search":
            # Currently unimplemented
            return {
                "content": "UniProt search is not yet implemented. Try a different query.",
                "source": "system"
            }

        elif function_name == "search":
            repository = args.get("repository", "ALL").upper()
            organism = args.get("organism")

            # Step 1: Extract structured terms from the natural language query
            parsed_terms = extract_terms(args.get("query", ""))
            
            # Step 2: Build E-Utils compatible search string
            search_query = " AND ".join(build_eutils_terms(parsed_terms))

            # Step 3: Optional – override organism if specified
            if organism and organism not in search_query:
                search_query += f" AND {organism}[orgn]"

            results = {}

            if repository in ("GEO", "ALL"):
                geo_result = genomics_search(query=search_query, repository="GEO", organism=organism)
                results["GEO"] = geo_result

            if repository in ("TCGA", "ALL"):
                tcga_result = genomics_search(query=search_query, repository="TCGA", organism=organism)
                results["TCGA"] = tcga_result

            # Optional future extension:
            # if repository in ("UNIPROT", "ALL"):
            #     uniprot_result = protein_search(...)

            formatted_result = format_search_results(results)
            return {"content": formatted_result, "source": "local_search"}


            # if repository in ("UNIPROT", "ALL"):
            #     uniprot_result = protein_search(
            #         query=search_terms,
            #         organism=organism,
            #         protein_type=args.get("protein_type"),
            #         reviewed=args.get("reviewed", False)
            #     )
            #     results["UniProt"] = uniprot_result

            formatted_result = format_search_results(results)
            return {"content": formatted_result, "source": "local_search"}


        elif function_name == "data":
            result = tabular_data(args)
            return {"content": json.dumps(result, indent=2), "source": "data_tool"}

        elif function_name == "reader":
            result = pdf_reader(args)
            return {"content": json.dumps(result, indent=2), "source": "reader_tool"}

        else:
            return {"content": f"Unknown function {function_name}", "source": "error"}

    except Exception as e:
        logging.error(f"Error in dispatch_tool_call for {function_name}: {str(e)}", exc_info=True)
        return {"content": f"Error executing {function_name}: {str(e)}", "source": "error"}
