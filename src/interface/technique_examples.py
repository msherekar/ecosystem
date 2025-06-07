"""
Examples of adding new analysis techniques to the scalable UI system.
This demonstrates how to add thousands of techniques with minimal code.
"""

import streamlit as st
from src.interface.technique_ui import technique_registry


def register_proteomics_technique():
    """Example: Add proteomics analysis in ~10 lines of code"""
    
    def proteomics_data_check():
        return st.session_state.get("proteomics_data") is not None
    
    def proteomics_workflow():
        # This would call the actual proteomics workflow
        return {"success": True, "message": "Proteomics analysis running"}
    
    technique_registry.register_technique(
        name="proteomics",
        title="Proteomics Analysis Pipeline",
        description="Mass spectrometry-based protein analysis",
        icon="🧪",
        server_name="proteomics",
        upload_message="Please upload your mass spectrometry files (.raw, .mzML) to begin.",
        data_check_function=proteomics_data_check,
        workflow_function=proteomics_workflow
    )


def register_metabolomics_technique():
    """Example: Add metabolomics analysis in ~10 lines of code"""
    
    def metabolomics_data_check():
        return st.session_state.get("metabolomics_data") is not None
    
    def metabolomics_workflow():
        # This would call the actual metabolomics workflow
        return {"success": True, "message": "Metabolomics analysis running"}
    
    technique_registry.register_technique(
        name="metabolomics",
        title="Metabolomics Analysis Pipeline",
        description="Small molecule metabolite analysis",
        icon="⚗️",
        server_name="metabolomics",
        upload_message="Please upload your metabolomics data files to begin.",
        data_check_function=metabolomics_data_check,
        workflow_function=metabolomics_workflow
    )


def register_spatial_transcriptomics_technique():
    """Example: Add spatial transcriptomics in ~10 lines of code"""
    
    def spatial_data_check():
        return (
            st.session_state.get("spatial_expression_data") is not None and
            st.session_state.get("spatial_coordinates") is not None
        )
    
    def spatial_workflow():
        # This would call the actual spatial transcriptomics workflow
        return {"success": True, "message": "Spatial transcriptomics analysis running"}
    
    technique_registry.register_technique(
        name="spatial_transcriptomics",
        title="Spatial Transcriptomics Analysis",
        description="Spatially resolved gene expression analysis",
        icon="🗺️",
        server_name="spatial",
        upload_message="Please upload expression data and spatial coordinates to begin.",
        data_check_function=spatial_data_check,
        workflow_function=spatial_workflow
    )


def register_imaging_technique():
    """Example: Add imaging analysis in ~10 lines of code"""
    
    def imaging_data_check():
        return st.session_state.get("imaging_data") is not None
    
    def imaging_workflow():
        # This would call the actual imaging workflow
        return {"success": True, "message": "Imaging analysis running"}
    
    technique_registry.register_technique(
        name="imaging",
        title="Biomedical Imaging Analysis",
        description="Medical and biological image analysis",
        icon="🔬",
        server_name="imaging",
        upload_message="Please upload your image files (.tiff, .png, .jpg) to begin.",
        data_check_function=imaging_data_check,
        workflow_function=imaging_workflow
    )


def register_multiomics_technique():
    """Example: Add multi-omics integration in ~10 lines of code"""
    
    def multiomics_data_check():
        # Check for multiple data types
        return (
            st.session_state.get("rnaseq_counts_df") is not None or
            st.session_state.get("anndata") is not None or
            st.session_state.get("proteomics_data") is not None
        )
    
    def multiomics_workflow():
        # This would call the actual multi-omics workflow
        return {"success": True, "message": "Multi-omics integration running"}
    
    technique_registry.register_technique(
        name="multiomics",
        title="Multi-Omics Integration",
        description="Integrate multiple omics data types",
        icon="🔗",
        server_name="multiomics",
        upload_message="Please upload multiple omics datasets to begin integration.",
        data_check_function=multiomics_data_check,
        workflow_function=multiomics_workflow
    )


# Auto-register all example techniques
def register_all_example_techniques():
    """Register all example techniques"""
    register_proteomics_technique()
    register_metabolomics_technique()
    register_spatial_transcriptomics_technique()
    register_imaging_technique()
    register_multiomics_technique()


# Demonstration of how easy it is to add techniques
TECHNIQUE_TEMPLATES = {
    "genomics": {
        "icon": "🧬",
        "server_name": "genomics",
        "upload_message": "Please upload your genomics files to begin."
    },
    "epigenomics": {
        "icon": "🔬",
        "server_name": "epigenomics", 
        "upload_message": "Please upload your ChIP-seq/ATAC-seq files to begin."
    },
    "microbiome": {
        "icon": "🦠",
        "server_name": "microbiome",
        "upload_message": "Please upload your 16S/metagenomic data to begin."
    },
    "pharmacogenomics": {
        "icon": "💊",
        "server_name": "pharmacogenomics",
        "upload_message": "Please upload your drug response data to begin."
    },
    "systems_biology": {
        "icon": "🕸️",
        "server_name": "systems",
        "upload_message": "Please upload your network data to begin."
    }
}


def auto_generate_technique(technique_name: str, template_key: str):
    """
    Auto-generate a technique from a template.
    This could be used to programmatically create hundreds of techniques.
    """
    if template_key not in TECHNIQUE_TEMPLATES:
        raise ValueError(f"Template {template_key} not found")
    
    template = TECHNIQUE_TEMPLATES[template_key]
    
    # Auto-generate data check function
    def auto_data_check():
        return st.session_state.get(f"{technique_name}_data") is not None
    
    # Auto-generate workflow function
    def auto_workflow():
        return {"success": True, "message": f"{technique_name} analysis running"}
    
    # Register the technique
    technique_registry.register_technique(
        name=technique_name,
        title=f"{technique_name.replace('_', ' ').title()} Analysis",
        description=f"Automated {technique_name} analysis pipeline",
        icon=template["icon"],
        server_name=template["server_name"],
        upload_message=template["upload_message"],
        data_check_function=auto_data_check,
        workflow_function=auto_workflow
    )


# Example: Generate 100 techniques programmatically
def generate_bulk_techniques():
    """
    Example of how to generate many techniques programmatically.
    This could easily scale to thousands of techniques.
    """
    
    # Example technique categories
    categories = [
        ("genomics", ["wgs", "wes", "gwas", "variant_calling", "structural_variants"]),
        ("transcriptomics", ["bulk_rnaseq", "single_cell", "spatial", "long_read"]),
        ("proteomics", ["shotgun", "targeted", "dda", "dia", "tmt"]),
        ("metabolomics", ["untargeted", "targeted", "lipidomics", "fluxomics"]),
        ("epigenomics", ["chip_seq", "atac_seq", "bisulfite", "cut_tag"])
    ]
    
    for category, techniques in categories:
        for technique in techniques:
            technique_name = f"{category}_{technique}"
            try:
                auto_generate_technique(technique_name, category)
                print(f"✅ Generated technique: {technique_name}")
            except Exception as e:
                print(f"❌ Failed to generate {technique_name}: {e}")


if __name__ == "__main__":
    # Example usage
    register_all_example_techniques()
    print("✅ Registered 5 example techniques")
    
    # Uncomment to generate bulk techniques
    # generate_bulk_techniques()
    # print("✅ Generated bulk techniques") 