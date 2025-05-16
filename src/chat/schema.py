# Code for function schema for various tools
# This schema helps the chatbot decide whether to stay local or send to OpenAI
# It also defines the structure for various database query functions

import json
from typing import Dict, Any, List, Optional

# Generic file operations
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

# Database search tools
geo_search = {
    "type": "function",
    "function": {
        "name": "geo_search",
        "description": (
            "Search genomics datasets in NCBI GEO (Gene Expression Omnibus). "
            "Use this for finding transcriptomics, microarray, and other genomics experiments."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'breast cancer RNA-seq'"
                },
                "organism": {
                    "type": "string",
                    "description": "Filter by organism, e.g. 'Homo sapiens', 'Mouse', 'Yeast'"
                },
                "date_from": {
                    "type": "string",
                    "description": "Start date in YYYY/MM format, e.g. '2020/01'"
                },
                "date_to": {
                    "type": "string",
                    "description": "End date in YYYY/MM format, e.g. '2020/12'"
                },
                "data_type": {
                    "type": "string",
                    "enum": ["gse", "gds", "all"],
                    "description": "Type of data, gse for series, gds for datasets, all for both"
                }
            },
            "required": ["query"]
        }
    }
}

tcga_search = {
    "type": "function",
    "function": {
        "name": "tcga_search",
        "description": (
            "Search cancer genomics data in The Cancer Genome Atlas (TCGA). "
            "Use this for finding cancer-related datasets, mutations, and expressions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'lung cancer mutations'"
                },
                "cancer_type": {
                    "type": "string",
                    "description": "Cancer type abbreviation, e.g. 'BRCA', 'LUAD', 'GBM'"
                },
                "data_category": {
                    "type": "string",
                    "enum": ["Transcriptome Profiling", "Copy Number Variation", "Simple Nucleotide Variation"],
                    "description": "Category of data to search for"
                },
                "experimental_strategy": {
                    "type": "string",
                    "enum": ["RNA-Seq", "WXS", "Genotyping Array"],
                    "description": "Experimental strategy used to generate the data"
                }
            },
            "required": ["query"]
        }
    }
}

uniprot_search = {
    "type": "function",
    "function": {
        "name": "uniprot_search",
        "description": (
            "Search protein information in UniProt database. "
            "Use this for finding protein sequences, functions, and structures."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'insulin human'"
                },
                "organism": {
                    "type": "string",
                    "description": "Organism name, e.g. 'Homo sapiens', 'Mouse'"
                },
                "protein_type": {
                    "type": "string",
                    "description": "Type of protein, e.g. 'enzyme', 'receptor', 'transcription factor'"
                },
                "reviewed": {
                    "type": "boolean",
                    "description": "Whether to return only reviewed (Swiss-Prot) entries"
                }
            },
            "required": ["query"]
        }
    }
}

# Generic search tool that can route to specific database searches
search = {
    "type": "function",
    "function": {
        "name": "search",
        "description": (
            "Search scientific datasets across multiple repositories. "
            "This function will automatically route to the appropriate database."
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
                    "enum": ["GEO", "TCGA", "UniProt", "ALL"],
                    "description": "Which repository to search"
                },
                "organism": {
                    "type": "string",
                    "description": "Filter by organism, e.g. 'Homo sapiens'"
                },
                # Optional: support UniProt-specific parameters in unified search
                "protein_type": {
                    "type": "string",
                    "description": "Type of protein, e.g. 'enzyme', 'receptor', 'transcription factor'"
                },
                "reviewed": {
                    "type": "boolean",
                    "description": "Whether to return only reviewed (Swiss-Prot) entries"
                },
                # Optional: support GEO-specific parameters too
                "date_from": {
                    "type": "string",
                    "description": "Start date in YYYY/MM format"
                },
                "date_to": {
                    "type": "string",
                    "description": "End date in YYYY/MM format"
                },
                "data_type": {
                    "type": "string",
                    "enum": ["gse", "gds", "all"],
                    "description": "GEO data type: series, dataset, or both"
                },
                # Optional: support TCGA-specific parameters
                "cancer_type": {
                    "type": "string",
                    "description": "Cancer type abbreviation, e.g. 'BRCA', 'LUAD', 'GBM'"
                },
                "data_category": {
                    "type": "string",
                    "enum": ["Transcriptome Profiling", "Copy Number Variation", "Simple Nucleotide Variation"],
                    "description": "TCGA data category"
                },
                "experimental_strategy": {
                    "type": "string",
                    "enum": ["RNA-Seq", "WXS", "Genotyping Array"],
                    "description": "TCGA experimental strategy"
                }
            },
            "required": ["query"]
        }
    }
}


# Data analysis tools
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
tools = [file_upload, make_project_dir, search, geo_search, tcga_search, uniprot_search, data, reader]

# Helper functions for working with schemas






