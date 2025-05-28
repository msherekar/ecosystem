# Agent System for Biology Tool

This module implements an agentic AI system that can understand natural language commands and execute appropriate actions within the biology tool.

## Key Features

- **Natural Language Understanding**: The agent can understand commands like "Run DESeq2" or "Perform GO enrichment" and execute the appropriate actions.
- **Tool Integration**: The agent can call various tools like DESeq2, GO enrichment, and file uploading.
- **Context Awareness**: The agent maintains memory of previous interactions to improve its responses.
- **Reasoning Capabilities**: The agent can reason about what tools to use based on the user's intent.

## Architecture

The agent system consists of:

1. **Core Agent**: The main agent class that processes commands and executes actions
2. **Tools**: Functions that the agent can call to perform tasks
3. **Integration with Chat Interface**: Connection to the Streamlit chat interface

## How It Works

1. When a user enters a message in the chat interface, the system checks if it appears to be a command.
2. If it's a command, the agent processes it and executes the appropriate actions.
3. The agent maintains a memory of previous interactions to provide context for future commands.
4. The agent can set the appropriate analysis mode based on the user's intent.

## Example Commands

- "Run DESeq2"
- "Perform GO enrichment analysis"
- "Run DESeq2 with p-value threshold of 0.01"
- "Upload a counts file for RNA-seq analysis"
- "Switch to RNA-seq analysis mode"

## Future Improvements

- Enhanced memory and reasoning capabilities
- Support for more complex multi-step workflows
- Improved natural language understanding for domain-specific terms
- Integration with more tools and analysis methods 