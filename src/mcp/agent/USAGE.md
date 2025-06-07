# Agent Usage Guide

## Overview

The agent system allows you to interact with the biology tool using natural language commands. Instead of having to select multiple dropdown options and buttons, you can simply type what you want to do, and the agent will handle the details.

## Getting Started

1. Launch the application with `streamlit run src/app.py`
2. Ensure your `.env` file contains your `OPENAI_API_KEY`
3. Type commands into the chat interface on the right side of the screen

## Example Commands

### RNA-seq Analysis

- **Start RNA-seq mode**: "I want to analyze RNA-seq data"
- **Upload files**: "I need to upload counts and metadata files"
- **Run DESeq2**: "Run DESeq2 analysis"
- **Run DESeq2 with parameters**: "Run DESeq2 with p-value 0.01 and log fold change 1.5"
- **Generate volcano plot**: "Generate a volcano plot of the results"
- **Run GO enrichment**: "Perform GO enrichment analysis on the significant genes"
- **Complete workflow**: "Run the complete RNA-seq workflow from preprocessing to GO enrichment"

### scRNA-seq Analysis

- **Start scRNA-seq mode**: "I want to analyze single-cell RNA-seq data"
- **Upload files**: "I need to upload scRNA-seq data"

### Search

- **PubMed search**: "Search for papers about CRISPR in cancer therapy"
- **GEO search**: "Find RNA-seq datasets for breast cancer"

## Tips for Effective Commands

1. **Be specific**: Include parameter values when needed (e.g., "Run DESeq2 with p-value 0.01")
2. **Start with verbs**: Commands that start with action words like "run", "perform", "analyze" are more easily recognized
3. **Use domain-specific terms**: Include terms like "DESeq2", "RNA-seq", "GO enrichment" when relevant
4. **Chain commands**: You can include multiple steps in one command (e.g., "Run DESeq2 and then perform GO enrichment")

## Troubleshooting

If the agent doesn't recognize your command:
1. Try rephrasing with more specific terms
2. Check that you have the necessary files uploaded (for commands that require data)
3. Make sure you're in the right analysis mode (RNA-seq, scRNA-seq, etc.)

## Advanced Usage

For complex analyses, you can:
1. Start with a high-level command ("Analyze differential expression")
2. Let the agent guide you through the necessary steps
3. Provide additional details when prompted 