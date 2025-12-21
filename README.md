# Gliaent 🧬

**Integrated Analysis Environment with MCP Architecture**

Gliaent is a comprehensive desktop application that provides integrated bioinformatics analysis capabilities through a modern Electron-based interface with Model Context Protocol (MCP) backend architecture. The platform supports multiple omics data types including RNA-seq, scRNA-seq, ATAC-seq, and proteomics analysis.

## 🌟 Features

### Core Analysis Modules
- **RNA-seq Analysis**: Differential expression analysis, quality control, and visualization
- **Single-cell RNA-seq**: Clustering, dimensionality reduction, and cell type identification
- **ATAC-seq Analysis**: Peak calling, motif analysis, and chromatin accessibility studies
- **Proteomics Analysis**: Protein identification, quantification, and pathway analysis
- **Image Analysis**: Computer vision tools for biological image processing

### Advanced Architecture
- **MCP Integration**: Model Context Protocol for scalable, modular server architecture
- **Electron Desktop App**: Cross-platform desktop application with native performance
- **React Frontend**: Modern, responsive UI with TypeScript and Tailwind CSS
- **Real-time Communication**: WebSocket-based communication between frontend and backend
- **Modular Design**: Pluggable analysis modules and extensible architecture

### Data Management
- **Multi-format Support**: Handles various biological data formats
- **Search Integration**: PubMed, GEO, TCGA, and UniProt data access
- **Cloud Integration**: Support for cloud-based data storage and processing
- **Data Visualization**: Interactive plots and charts for analysis results

## 🏗️ Architecture

```
Gliaent/
├── electron/                 # Electron main process
├── src/
│   ├── mcp/                 # Model Context Protocol implementation
│   │   ├── servers/         # Analysis servers (RNA-seq, scRNA-seq, etc.)
│   │   ├── agent/           # Intelligent routing and coordination
│   │   └── core/            # Core MCP functionality
│   ├── modules/             # Analysis modules
│   │   ├── rna_seq/         # RNA-seq analysis tools
│   │   ├── scrna_seq/       # Single-cell RNA-seq tools
│   │   ├── search/          # Data search and retrieval
│   │   └── image/           # Image analysis tools
│   └── ui-react/            # React frontend application
├── config/                  # Configuration files
└── data/                    # Data storage
```

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 16+**
- **npm 8+**
- **Conda** (recommended for Python environment management)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/gliaent.git
   cd gliaent
   ```

2. **Set up Python environment**
   ```bash
   conda env create -f environment.yml
   conda activate ra
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

4. **Start the development server**
   ```bash
   npm run dev
   ```

### Building for Production

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build:mac
npm run build:win
npm run build:linux
```

## 📊 Analysis Workflows

### RNA-seq Analysis
- Quality control and preprocessing
- Differential expression analysis with DESeq2
- Gene ontology enrichment analysis
- Volcano plots and heatmaps
- Pathway analysis

### Single-cell RNA-seq
- Quality control and filtering
- Normalization and scaling
- Dimensionality reduction (PCA, UMAP, t-SNE)
- Clustering analysis
- Cell type identification
- Differential expression analysis

### ATAC-seq Analysis
- Peak calling and annotation
- Motif analysis
- Chromatin accessibility visualization
- Integration with gene expression data

### Proteomics Analysis
- Protein identification and quantification
- Post-translational modification analysis
- Pathway and network analysis
- Statistical analysis

## 🔧 Configuration

### MCP Server Configuration
Configuration files are located in the `config/` directory:
- `servers.yaml`: Server definitions and endpoints
- `analysis_strategies.yaml`: Analysis workflow configurations
- `databases.json`: Database connection settings

### Environment Variables
```bash
# Development mode
NODE_ENV=development

# MCP server settings
MCP_HOST=localhost
MCP_PORT=8000

# Analysis settings
MAX_WORKERS=4
CACHE_DIR=./cache
```

## 🧪 Testing

### Python Tests
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m mcp

# Run with coverage
pytest --cov=src
```

### Frontend Tests
```bash
# Run linting
npm run lint

# Run tests (when implemented)
npm run test
```

## 📚 API Documentation

### MCP Servers
The platform uses Model Context Protocol for server communication:

- **RNA-seq Server**: `src/mcp/servers/rnaseq_server.py`
- **scRNA-seq Server**: `src/mcp/servers/scrnaseq_server.py`
- **ATAC-seq Server**: `src/mcp/servers/atacseq_server.py`
- **Proteomics Server**: `src/mcp/servers/proteomics_server.py`
- **Data Server**: `src/mcp/servers/data_server.py`
- **Search Server**: `src/mcp/servers/search_server.py`
- **Visualization Server**: `src/mcp/servers/visualization_server.py`

### Electron IPC Handlers
Main process handlers for frontend-backend communication:
- Server management
- File operations
- Analysis execution
- Real-time updates

## 🔍 Development

### Project Structure
- **`src/mcp/`**: MCP implementation and servers
- **`src/modules/`**: Analysis modules and utilities
- **`src/ui-react/`**: React frontend application
- **`electron/`**: Electron main process files
- **`config/`**: Configuration files
- **`data/`**: Data storage and cache

### Adding New Analysis Modules
1. Create module in `src/modules/`
2. Implement MCP server in `src/mcp/servers/`
3. Add UI components in `src/ui-react/pages/`
4. Update configuration files
5. Add tests

### Code Style
- **Python**: Black, isort, flake8, mypy
- **TypeScript/React**: ESLint, Prettier
- **Pre-commit hooks**: Automated code formatting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines
- Follow the existing code style
- Add comprehensive tests
- Update documentation
- Ensure cross-platform compatibility

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Electron, React, and Python
- Bioinformatics tools integration
- MCP architecture implementation
- Scientific computing libraries

## 📞 Support

For questions and support:
- Create an issue on GitHub
- Check the documentation in `readme/` directory
- Review the API documentation

---

**Gliaent** - Empowering bioinformatics research with integrated analysis tools and modern architecture.
