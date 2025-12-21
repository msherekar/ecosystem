#!/bin/bash

echo "🧬 Starting Gliaent Electron App with MCP Integration..."

# Check if conda environment is active
if [[ "$CONDA_DEFAULT_ENV" == "" ]]; then
    echo "⚠️  No conda environment detected. Activating ra environment..."
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate ra
    if [[ "$?" != "0" ]]; then
        echo "❌ Failed to activate conda environment 'ra'"
        echo "💡 Please run: conda activate ra"
        exit 1
    fi
fi

echo "✅ Conda environment: $CONDA_DEFAULT_ENV"

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please run setup_electron.sh first"
    exit 1
fi

echo "✅ Node.js version: $(node --version)"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found in current environment"
    exit 1
fi

echo "✅ Python version: $(python --version)"

# Check if npm dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies..."
    npm install
    if [[ "$?" != "0" ]]; then
        echo "❌ Failed to install npm dependencies"
        exit 1
    fi
fi

# Verify MCP server structure
echo "🔍 Verifying MCP server structure..."
if [ ! -d "src/mcp/servers" ]; then
    echo "❌ MCP servers directory not found at src/mcp/servers"
    echo "Please ensure your MCP server files are in the correct location"
    exit 1
fi

if [ ! -f "src/mcp/servers/__main__.py" ]; then
    echo "❌ MCP orchestrator not found at src/mcp/servers/__main__.py"
    exit 1
fi

# Test MCP server import
echo "🧪 Testing MCP server..."
python -c "
import sys
sys.path.append('.')
try:
    from src.mcp.servers import MCPServerOrchestrator
    print('✅ MCP server orchestrator ready')
except ImportError as e:
    print(f'❌ MCP import failed: {e}')
    sys.exit(1)
" || {
    echo "❌ MCP server test failed. Check dependencies."
    exit 1
}

# Kill any existing backend processes
echo "🧹 Cleaning up any existing processes..."
pkill -f "python_backend.py" 2>/dev/null || true
pkill -f "src.mcp.servers" 2>/dev/null || true

# Create logs directory
mkdir -p logs

echo "✅ Environment ready"
echo "🚀 Starting Electron app with MCP integration..."
echo ""
echo "📋 What will happen:"
echo "   1. Electron main process starts"
echo "   2. MCP Server Orchestrator spawns (python -m src.mcp.servers)"
echo "   3. Bioinformatics servers become available:"
echo "      - RNA-seq analysis server"
echo "      - scRNA-seq analysis server" 
echo "      - ATAC-seq analysis server"
echo "      - Proteomics analysis server"
echo "      - Data management server"
echo "      - Visualization server"
echo "      - Search server"
echo "   4. Electron UI connects to MCP system"
echo ""

# Start the app with development flags
ELECTRON_IS_DEV=1 npm run dev

# Cleanup on exit
trap 'echo "🛑 Shutting down..."; pkill -f "src.mcp.servers" 2>/dev/null || true' EXIT