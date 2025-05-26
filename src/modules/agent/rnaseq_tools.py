"""
RNA-seq specific tools for the agent system.
"""

import streamlit as st
from modules.agent.registry import registry
from modules.rna_seq.workflow import run_rnaseq_pipeline



def register_rnaseq_tools():
    registry.register_tool(
        name="run_rnaseq",
        description="Set up and run the RNA-seq analysis pipeline",
        parameters={},
        executor=run_rnaseq_pipeline,
        analysis_type="rnaseq",
        ui_message="✅ RNA-seq analysis activated. Please upload the required files."
    )
    