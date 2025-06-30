#!/bin/bash

echo "🎨 Creating Complete Gliaent UI Structure..."

# Create directory structure
mkdir -p src/ui/css
mkdir -p src/ui/js
mkdir -p src/ui/components
mkdir -p src/ui/assets/icons
mkdir -p src/ui/assets/images

# Run the comprehensive UI setup
./setup_electron.sh

echo ""
echo "🎉 Complete UI structure created!"
echo ""
echo "📁 Directory structure:"
echo "   src/ui/"
echo "   ├── index.html          (Main UI)"
echo "   ├── css/"
echo "   │   ├── main.css         (Main styles)"
echo "   │   └── components.css   (Component styles)"
echo "   ├── js/"
echo "   │   ├── app.js          (Main app logic)"
echo "   │   ├── mcp-client.js   (MCP communication)"
echo "   │   └── ui-components.js (UI components)"
echo "   ├── components/         (Future Vue/React components)"
echo "   └── assets/            (Icons and images)"
echo ""
echo "🚀 Ready to start! Run:"
echo "   ./start_gliaent.sh"
echo ""
echo "🔧 The UI includes:"
echo "   ✅ Dashboard with MCP server status"
echo "   ✅ RNA-seq, scRNA-seq, ATAC-seq analysis interfaces"
echo "   ✅ File drag & drop support"
echo "   ✅ Real-time server monitoring"
echo "   ✅ Bioinformatics workflow management"
echo "   ✅ Responsive design"