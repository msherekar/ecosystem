"""
Single-cell RNA-seq specific tools for the agent system.
"""

import streamlit as st
from modules.agent.registry import registry
from modules.scrna_seq.workflow import run_scrnaseq_pipeline

def register_scrnaseq_tools():
    registry.register_tool(
        name="run_scrnaseq",
        description="Set up and run the scRNA-seq analysis pipeline",
        parameters={},
        executor=run_scrnaseq_pipeline,
        analysis_type="scrnaseq",
        ui_message="✅ scRNA-seq analysis activated. Please upload the required files."
    )