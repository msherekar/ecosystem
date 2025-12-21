# Gliaent Electron + Monaco Integration Guide

## 🚀 Overview

This guide will help you integrate the new Electron + Monaco editor interface with your existing Gliaent bioinformatics platform, replacing the Streamlit UI with a modern VS Code/Cursor-like experience.

## 📁 New Files Added

- `index.html` - Main HTML interface with three-panel layout
- `renderer.js` - Frontend JavaScript handling Monaco editor and module integration
- `setup_electron.sh` - Setup script for dependencies
- Enhanced `main.js` - Electron main process with Python backend integration
- Enhanced `python_backend.py` - FastAPI backend with module discovery
- Updated `package.json` - Dependencies for Monaco and Axios

## 🏗️ Architecture

```
┌─────────────────┬─────────────────────┬─────────────────┐
│   Left Panel    │    Center Panel     │   Right Panel   │
│   (Modules)     │  (Monaco Editor)    │     (Chat)      │
│                 │                     │                 │
│ • scRNA-seq     │  ┌───────────────┐  │ AI Assistant    │
│ • RNA-seq       │  │ Monaco Editor │  │                 │
│ • Image Analysis│  │               │  │ Context-aware   │
│ • Tabular Data  │  │   Code Here   │  │ help for each   │
│ • Search        │  │               │  │ module          │
│ • Reader        │  └───────────────┘  │                 │
│ • Terminal      │  ┌───────────────┐  │                 │
│                 │  │    Output     │  │                 │
│                 │  └───────────────┘  │                 │
└─────────────────┴─────────────────────┴─────────────────┘
```

## 🔧 Setup Instructions

### 1. Install Node.js (if not already installed)

```bash
# macOS with Homebrew
brew install node

# Or download from https://nodejs.org/
```

### 2. Run the setup script

```bash
chmod +x setup_electron.sh
./setup_electron.sh
```

### 3. Start the application

```bash
# Development mode (with DevTools)
npm run dev

# Or start normally
npm start
```

## 🔗 Integration with Existing Modules

### Module Template System

Each module in your `src/modules/` directory is automatically detected and gets a template in the Monaco editor:

- **scRNA-seq**: Scanpy-based template with QC, normalization, clustering
- **RNA-seq**: DESeq2 template with differential expression
- **Image Analysis**: OpenCV/PIL template for ROI detection
- **Tabular Data**: Pandas/scikit-learn template for data analysis
- **Search**: Bio.Entrez template for database searches
- **Reader**: Literature mining template
- **Terminal**: System command interface

### Backend Integration

The enhanced `python_backend.py` provides:

1. **Code Execution**: Run Python code safely in isolated environment
2. **Module Discovery**: Automatically find and list your existing modules
3. **Module Information**: Get details about each module's capabilities
4. **Direct Module Execution**: Call functions from your modules directly

### API Endpoints

```python
# New endpoints added to python_backend.py:
GET  /modules          # List all available modules
POST /module-info      # Get detailed module information
POST /execute-module   # Execute specific module functions
GET  /health          # Health check
POST /execute         # Execute arbitrary Python code
```

## 🎨 UI Features

### Monaco Editor
- **Syntax highlighting** for Python
- **IntelliSense** and autocompletion
- **Error detection** and linting  
- **Vim/Emacs keybindings** support
- **Multi-cursor editing**
- **Code folding** and minimap

### Module Templates
Each module loads with a comprehensive template including:
- Import statements for relevant libraries
- Example usage patterns
- Available functions and methods
- Best practices for that analysis type

### Integrated Chat
- **Context-aware** responses based on selected module
- **Error assistance** when code execution fails  
- **Module guidance** and suggestions
- **Integration** with your existing chat system

## 🔄 Migration from Streamlit

### Layout Mapping
Your existing Streamlit layout system maps to the new Electron interface:

```python
# Streamlit (old)
left_area, center_area, right_area = layout_three_areas()

# Electron (new)  
# Left: Module selection and file browser
# Center: Monaco editor + output panel
# Right: AI chat assistant
```

### Module Integration
Your existing module structure is preserved:

```
src/modules/
├── scrna_seq/
│   ├── workflow.py      # ✅ Integrated
│   ├── qc.py           # ✅ Available
│   └── clustering.py   # ✅ Available
├── rna_seq/
│   ├── workflow.py     # ✅ Integrated
│   └── deseq.py       # ✅ Available
└── image/
    ├── streamlit_app.py # → Replaced by Monaco templates
    └── train_model.py   # ✅ Available
```

### Data Flow
```
User Action → Monaco Editor → Python Backend → Your Modules → Results
    ↓              ↓               ↓              ↓          ↓
Select Module → Load Template → Execute Code → Run Analysis → Display Output
```

## 🛠️ Advanced Integration

### Adding New Modules

1. **Create module directory** in `src/modules/`
2. **Add template** to `renderer.js` moduleTemplates
3. **Implement workflow** following existing patterns
4. **Backend auto-discovers** the new module

### Custom Chat Integration

Replace the simple chat responses in `renderer.js` with your existing chat system:

```javascript
// In renderer.js, replace generateChatResponse() with:
async generateChatResponse(userMessage) {
    // Call your existing chat API
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            message: userMessage, 
            module: this.currentModule 
        })
    });
    return await response.json();
}
```

### File Operations

Built-in support for:
- **Opening files** (Ctrl/Cmd+O)
- **Saving files** (Ctrl/Cmd+S)
- **Data file selection** with appropriate filters
- **Directory browsing** for projects

## 🔧 Customization

### Themes
Modify the CSS in `index.html` to match your preferred color scheme:
```css
/* Dark theme (default) */
body { background: #1e1e1e; color: #d4d4d4; }

/* Light theme */
body { background: #ffffff; color: #333333; }
```

### Monaco Editor Settings
Customize editor behavior in `renderer.js`:
```javascript
this.editor = monaco.editor.create(document.getElementById('editor'), {
    theme: 'vs-dark',        // or 'vs-light'
    fontSize: 14,            // Adjust font size
    wordWrap: 'on',         // Enable word wrap
    minimap: { enabled: true }, // Show/hide minimap
    // ... other options
});
```

## 🐛 Troubleshooting

### Common Issues

1. **Backend not starting**
   - Check Python dependencies: `pip install fastapi uvicorn`
   - Verify Python version compatibility
   - Check port 8000 is available

2. **Monaco editor not loading**
   - Ensure `npm install` completed successfully
   - Check browser console for errors
   - Verify node_modules/monaco-editor exists

3. **Module templates not working**
   - Check module path in `src/modules/`
   - Verify module structure matches expected format
   - Check backend logs for import errors

### Debug Mode

Start with debugging enabled:
```bash
npm run dev  # Opens DevTools automatically
```

## 🎯 Next Steps

1. **Test the setup** with a simple module
2. **Migrate module templates** to match your specific needs
3. **Integrate with your existing chat system**
4. **Customize the UI** to match your preferences
5. **Add keyboard shortcuts** for common operations
6. **Configure data visualization** integration

## 🤝 Benefits Over Streamlit

- **Faster development** with Monaco editor
- **Better code organization** with file management
- **Professional UI** similar to VS Code
- **Offline capability** without browser dependencies
- **Better performance** with native Electron
- **Extensible architecture** for future features
- **Integrated documentation** and examples

The new Electron interface provides a modern, extensible foundation for your bioinformatics platform while preserving all your existing module functionality! 