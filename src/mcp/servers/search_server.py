"""
Search MCP Server

Provides MCP interface for database search tools including:
- NCBI GEO (Gene Expression Omnibus)  
- UniProt protein database
- PubMed literature search
- TCGA (The Cancer Genome Atlas)
- Other genomics and proteomics databases
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import streamlit as st

from ..core.server import MCPServer


class SearchMCPServer(MCPServer):
    """MCP Server for database search tools"""
    
    def __init__(self):
        super().__init__("search_server", "1.0.0")
        
    async def initialize(self) -> None:
        """Initialize the search server"""
        # Register search tools
        await self._register_search_tools()
        
        # Register resources
        await self._register_resources()
        
        # Register prompts
        await self._register_prompts()
        
        self.logger.info("Search MCP Server initialized")
    
    async def _register_search_tools(self):
        """Register database search tools"""
        
        # GEO search tool
        self.register_tool(
            name="search_geo",
            description="Search NCBI Gene Expression Omnibus (GEO) for genomics datasets",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for GEO database"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 20
                    }
                },
                "required": ["query"]
            },
            handler=self._search_geo
        )
        
        # UniProt search tool
        self.register_tool(
            name="search_uniprot", 
            description="Search UniProt protein database for protein information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for UniProt database"
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results to return",
                        "default": 20
                    }
                },
                "required": ["query"]
            },
            handler=self._search_uniprot
        )
        
        # PubMed search tool
        self.register_tool(
            name="search_pubmed",
            description="Search PubMed literature database for scientific articles",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for PubMed database"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 20
                    }
                },
                "required": ["query"]
            },
            handler=self._search_pubmed
        )
        
        # TCGA search tool
        self.register_tool(
            name="search_tcga",
            description="Search The Cancer Genome Atlas (TCGA) for cancer genomics data",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string", 
                        "description": "Search query for TCGA database"
                    },
                    "data_type": {
                        "type": "string",
                        "description": "Type of data to search for",
                        "enum": ["expression", "mutation", "copy_number", "clinical"],
                        "default": "expression"
                    }
                },
                "required": ["query"]
            },
            handler=self._search_tcga
        )
        
        # Generic genomics search tool
        self.register_tool(
            name="search_genomics",
            description="Search multiple genomics databases (GEO, TCGA) simultaneously",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for genomics databases"
                    },
                    "repository": {
                        "type": "string",
                        "description": "Repository to search",
                        "enum": ["ALL", "GEO", "TCGA"],
                        "default": "ALL"
                    }
                },
                "required": ["query"]
            },
            handler=self._search_genomics
        )
    
    async def _register_resources(self):
        """Register search-related resources"""
        
        # Search results resource
        self.register_resource(
            uri="search://results/latest",
            name="Latest Search Results",
            description="Most recent database search results",
            mime_type="application/json"
        )
        
        # Search history resource
        self.register_resource(
            uri="search://history",
            name="Search History",
            description="History of performed searches",
            mime_type="application/json"
        )
    
    async def _register_prompts(self):
        """Register search-related prompts"""
        
        # Search suggestion prompt
        self.register_prompt(
            name="suggest_search_terms",
            description="Suggest related search terms based on current query",
            template="Based on the search query '{query}' in {database}, suggest 5 related search terms that might help find additional relevant datasets."
        )
        
        # Results interpretation prompt
        self.register_prompt(
            name="interpret_search_results",
            description="Interpret and summarize search results",
            template="Summarize the following search results from {database} and highlight the most relevant datasets for {research_context}: {results}"
        )
    
    # Tool handler implementations
    
    async def _search_geo(self, query: str, page_size: int = 20) -> Dict[str, Any]:
        """Search GEO database"""
        try:
            # Import GEO search function
            from src.modules.search.geo import geo_search
            
            # Perform search
            results = geo_search(query, page_size=page_size)
            
            # Store results for center panel display
            if results.get("hits"):
                st.session_state["search_results"] = {
                    "provider": "geo",
                    "provider_display_name": "NCBI GEO",
                    "count": results.get("count", 0),
                    "hits": results.get("hits", []),
                    "query": query
                }
                st.session_state["agent_requested_search"] = True
                
                return {
                    "success": True,
                    "message": f"Found {len(results.get('hits', []))} GEO datasets matching '{query}'",
                    "result": {
                        "type": "search_results",
                        "data": results,
                        "display_results": True,
                        "count": results.get("count", 0),
                        "provider": "geo"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No GEO datasets found matching '{query}'. Try different keywords.",
                    "result": {
                        "type": "no_results",
                        "provider": "geo"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"GEO search failed: {str(e)}")
            return {
                "success": False,
                "message": f"GEO search failed: {str(e)}"
            }
    
    async def _search_uniprot(self, query: str, page_size: int = 20) -> Dict[str, Any]:
        """Search UniProt database"""
        try:
            # Import UniProt search function
            from src.modules.search.uniprot import uniprot_search
            
            # Perform search
            results = uniprot_search(query, page_size=page_size)
            
            # Store results for center panel display
            if results.get("hits"):
                st.session_state["search_results"] = {
                    "provider": "uniprot",
                    "provider_display_name": "UniProt",
                    "count": results.get("count", 0),
                    "hits": results.get("hits", []),
                    "query": query
                }
                st.session_state["agent_requested_search"] = True
                
                return {
                    "success": True,
                    "message": f"Found {len(results.get('hits', []))} UniProt proteins matching '{query}'",
                    "result": {
                        "type": "search_results",
                        "data": results,
                        "display_results": True,
                        "count": results.get("count", 0),
                        "provider": "uniprot"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No UniProt proteins found matching '{query}'. Try different keywords.",
                    "result": {
                        "type": "no_results", 
                        "provider": "uniprot"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"UniProt search failed: {str(e)}")
            return {
                "success": False,
                "message": f"UniProt search failed: {str(e)}"
            }
    
    async def _search_pubmed(self, query: str, max_results: int = 20) -> Dict[str, Any]:
        """Search PubMed database"""
        try:
            # Import PubMed search function
            from src.modules.reader.pubmed import fetch_pubmed_with_abstract
            
            # Perform search
            results = fetch_pubmed_with_abstract(query, max_results=max_results)
            
            if results:
                # Format results for consistency
                formatted_results = {
                    "count": len(results),
                    "hits": results,
                    "query": query,
                    "provider": "pubmed",
                    "provider_display_name": "PubMed"
                }
                
                # Store results for center panel display
                st.session_state["search_results"] = formatted_results
                st.session_state["agent_requested_search"] = True
                
                return {
                    "success": True,
                    "message": f"Found {len(results)} PubMed articles matching '{query}'",
                    "result": {
                        "type": "search_results",
                        "data": formatted_results,
                        "display_results": True,
                        "count": len(results),
                        "provider": "pubmed"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No PubMed articles found matching '{query}'. Try different keywords.",
                    "result": {
                        "type": "no_results",
                        "provider": "pubmed"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"PubMed search failed: {str(e)}")
            return {
                "success": False,
                "message": f"PubMed search failed: {str(e)}"
            }
    
    async def _search_tcga(self, query: str, data_type: str = "expression") -> Dict[str, Any]:
        """Search TCGA database"""
        try:
            # Import TCGA search function
            from src.modules.search.tcga import search_tcga
            
            # Perform search
            results = search_tcga(query, data_type=data_type)
            
            # Store results for center panel display
            if results.get("hits"):
                st.session_state["search_results"] = {
                    "provider": "tcga",
                    "provider_display_name": "TCGA",
                    "count": results.get("count", 0),
                    "hits": results.get("hits", []),
                    "query": query
                }
                st.session_state["agent_requested_search"] = True
                
                return {
                    "success": True,
                    "message": f"Found {len(results.get('hits', []))} TCGA datasets matching '{query}'",
                    "result": {
                        "type": "search_results",
                        "data": results,
                        "display_results": True,
                        "count": results.get("count", 0),
                        "provider": "tcga"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No TCGA datasets found matching '{query}'. Try different keywords.",
                    "result": {
                        "type": "no_results",
                        "provider": "tcga"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"TCGA search failed: {str(e)}")
            return {
                "success": False,
                "message": f"TCGA search failed: {str(e)}"
            }
    
    async def _search_genomics(self, query: str, repository: str = "ALL") -> Dict[str, Any]:
        """Search multiple genomics databases"""
        try:
            # Import genomics search function
            from src.modules.search.genomics import genomics_search
            
            # Perform search
            results = genomics_search(query, repository=repository)
            
            # Process and combine results
            combined_hits = []
            total_count = 0
            
            for db_name, db_results in results.items():
                if isinstance(db_results, dict) and "hits" in db_results:
                    hits = db_results.get("hits", [])
                    for hit in hits:
                        hit["source_db"] = db_name
                    combined_hits.extend(hits)
                    total_count += db_results.get("count", 0)
            
            if combined_hits:
                formatted_results = {
                    "count": total_count,
                    "hits": combined_hits,
                    "query": query,
                    "provider": "genomics",
                    "provider_display_name": f"Genomics Search ({repository})"
                }
                
                # Store results for center panel display
                st.session_state["search_results"] = formatted_results
                st.session_state["agent_requested_search"] = True
                
                return {
                    "success": True,
                    "message": f"Found {total_count} datasets across {len(results)} databases matching '{query}'",
                    "result": {
                        "type": "search_results",
                        "data": formatted_results,
                        "display_results": True,
                        "count": total_count,
                        "provider": "genomics"
                    }
                }
            else:
                return {
                    "success": True,
                    "message": f"No datasets found across genomics databases matching '{query}'. Try different keywords.",
                    "result": {
                        "type": "no_results",
                        "provider": "genomics"
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Genomics search failed: {str(e)}")
            return {
                "success": False,
                "message": f"Genomics search failed: {str(e)}"
            }

    def _get_server_specific_context(self) -> Dict[str, Any]:
        """Get search-specific context for MCP registry"""
        context = {
            "server_type": "search",
            "capabilities": [
                "database_search",
                "multi_database_search", 
                "result_caching",
                "search_history"
            ],
            "available_databases": [
                "GEO (NCBI Gene Expression Omnibus)",
                "UniProt (Protein Database)",
                "PubMed (Literature Database)",
                "TCGA (The Cancer Genome Atlas)",
                "Multi-database Genomics Search"
            ],
            "search_status": "ready"
        }
        
        # Add search history if available
        if "search_history" in st.session_state:
            context["recent_searches"] = len(st.session_state["search_history"])
        
        # Add current search results if available
        if "search_results" in st.session_state:
            results = st.session_state["search_results"]
            context["last_search"] = {
                "provider": results.get("provider"),
                "query": results.get("query"),
                "count": results.get("count", 0)
            }
        
        return context 