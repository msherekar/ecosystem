#!/bin/bash

echo "🧬 Setting up Gliaent Electron UI with MCP Integration..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install Node.js first:"
    echo "   - Visit https://nodejs.org/"
    echo "   - Or use Homebrew: brew install node"
    exit 1
fi

# Check if npm is available
if ! command -v npm &> /dev/null; then
    echo "❌ npm not found. Please install npm first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Install dependencies
echo "📦 Installing npm dependencies..."
npm install

# Check if Python and conda are available
if ! command -v python &> /dev/null; then
    echo "❌ Python not found. Please install Python first."
    exit 1
fi

echo "✅ Python version: $(python --version)"

# Check if MCP server dependencies are installed
echo "🐍 Checking MCP server dependencies..."
python -c "
import sys
required_packages = [
    'asyncio', 'logging', 'pathlib', 'dataclasses', 
    'typing', 'pydantic', 'numpy', 'pandas'
]

missing_packages = []
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

if missing_packages:
    print(f'Missing packages: {missing_packages}')
    sys.exit(1)
else:
    print('✅ Core Python packages available')
" || {
    echo "⚠️  Installing core Python dependencies..."
    pip install pydantic numpy pandas
}

# Check if bioinformatics packages are available (optional but recommended)
echo "🧬 Checking bioinformatics dependencies..."
python -c "import scanpy, pandas, numpy, matplotlib, seaborn" 2>/dev/null || {
    echo "⚠️  Bioinformatics packages missing. Installing..."
    pip install scanpy pandas numpy matplotlib seaborn plotly
}

# Check MCP server structure
echo "🔍 Verifying MCP server structure..."
if [ ! -d "src/mcp/servers" ]; then
    echo "❌ MCP servers directory not found at src/mcp/servers"
    echo "Please ensure your MCP server files are in the correct location"
    exit 1
fi

if [ ! -f "src/mcp/servers/__main__.py" ]; then
    echo "❌ MCP orchestrator not found at src/mcp/servers/__main__.py"
    echo "Please ensure your MCP orchestrator is properly installed"
    exit 1
fi

echo "✅ MCP server structure verified"

# Test MCP server can be imported
echo "🧪 Testing MCP server import..."
python -c "
import sys
sys.path.append('.')
try:
    from src.mcp.servers import MCPServerOrchestrator
    print('✅ MCP server orchestrator can be imported')
except ImportError as e:
    print(f'❌ MCP import failed: {e}')
    sys.exit(1)
" || {
    echo "⚠️  MCP server import test failed. Check dependencies."
}

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p src/ui
mkdir -p config
mkdir -p data
mkdir -p logs

# Create basic UI if it doesn't exist
if [ ! -f "src/ui/index.html" ]; then
    echo "📄 Creating basic UI template..."
    cat > src/ui/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gliaent - Bioinformatics Analysis Platform</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .status {
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }
        .status.connected { background: #d4edda; color: #155724; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.loading { background: #fff3cd; color: #856404; }
        .servers {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .server-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            background: #f9f9f9;
        }
        .server-card h3 {
            margin-top: 0;
            color: #333;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin: 5px;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧬 Gliaent</h1>
            <p>Bioinformatics Analysis Platform</p>
        </div>
        
        <div id="status" class="status loading">
            🔄 Connecting to MCP servers...
        </div>
        
        <div class="servers" id="servers">
            <!-- Server cards will be populated here -->
        </div>
    </div>

    <script>
        // Basic MCP integration test
        document.addEventListener('DOMContentLoaded', async () => {
            const statusEl = document.getElementById('status');
            const serversEl = document.getElementById('servers');
            
            try {
                // Test MCP connection
                const connectionStatus = await window.electronAPI?.invoke('mcp:get-connection-status');
                
                if (connectionStatus?.success) {
                    statusEl.className = 'status connected';
                    statusEl.innerHTML = '✅ Connected to MCP servers';
                    
                    // Load available servers
                    const serversResult = await window.electronAPI?.invoke('mcp:get-available-servers');
                    if (serversResult?.success) {
                        displayServers(serversResult.servers);
                    }
                } else {
                    statusEl.className = 'status error';
                    statusEl.innerHTML = '❌ Failed to connect to MCP servers';
                }
            } catch (error) {
                statusEl.className = 'status error';
                statusEl.innerHTML = '❌ Electron API not available';
                console.error('MCP connection error:', error);
            }
        });
        
        function displayServers(servers) {
            const serversEl = document.getElementById('servers');
            serversEl.innerHTML = servers.map(server => `
                <div class="server-card">
                    <h3>${server.toUpperCase()} Server</h3>
                    <p>Bioinformatics analysis server for ${server} data</p>
                    <button onclick="startServer('${server}')">Start Server</button>
                    <button onclick="getServerStatus('${server}')">Check Status</button>
                </div>
            `).join('');
        }
        
        async function startServer(serverType) {
            try {
                const result = await window.electronAPI?.invoke('mcp:start-server', serverType);
                console.log('Server start result:', result);
                alert(result.success ? `${serverType} server started!` : `Failed to start ${serverType}: ${result.error}`);
            } catch (error) {
                console.error('Server start error:', error);
                alert('Failed to start server');
            }
        }
        
        async function getServerStatus(serverType) {
            try {
                const result = await window.electronAPI?.invoke('mcp:get-server-status', serverType);
                console.log('Server status:', result);
                alert(`${serverType} status: ${JSON.stringify(result.status, null, 2)}`);
            } catch (error) {
                console.error('Server status error:', error);
                alert('Failed to get server status');
            }
        }
        
        // Listen for MCP events
        if (window.electronAPI) {
            window.electronAPI.on('backend-status', (data) => {
                console.log('Backend status:', data);
                const statusEl = document.getElementById('status');
                if (data.status === 'connected') {
                    statusEl.className = 'status connected';
                    statusEl.innerHTML = '✅ ' + data.message;
                } else if (data.status === 'error') {
                    statusEl.className = 'status error';
                    statusEl.innerHTML = '❌ ' + data.message;
                }
            });
            
            window.electronAPI.on('server-started', (data) => {
                console.log('Server started:', data);
                alert(`${data.server_type} server started successfully!`);
            });
        }
    </script>
</body>
</html>
EOF
    echo "✅ Basic UI template created"
fi

echo "🚀 Setup complete! You can now run:"
echo "   1. Start the Electron app: npm run dev"
echo "   2. Or build for production: npm run build"
echo ""
echo "📚 The app will automatically start the MCP server orchestrator."
echo "🔧 All bioinformatics servers (RNA-seq, scRNA-seq, ATAC-seq, etc.) are integrated!"
echo ""
echo "🧪 To test MCP integration:"
echo "   python -m src.mcp.servers  # Test MCP orchestrator directly"