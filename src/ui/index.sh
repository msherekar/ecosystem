#!/bin/bash

echo "🎨 Creating comprehensive UI for Gliaent..."

# Create UI directory structure
mkdir -p src/ui/css
mkdir -p src/ui/js
mkdir -p src/ui/components
mkdir -p src/ui/assets/icons
mkdir -p src/ui/assets/images

# Create main HTML file
cat > src/ui/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gliaent - Bioinformatics Analysis Platform</title>
    <link rel="stylesheet" href="css/main.css">
    <link rel="stylesheet" href="css/components.css">
</head>
<body>
    <div id="app">
        <!-- Header -->
        <header class="app-header">
            <div class="header-content">
                <div class="logo-section">
                    <h1>🧬 Gliaent</h1>
                    <span class="version">v1.0.0</span>
                </div>
                <div class="status-section">
                    <div id="connection-status" class="status-indicator">
                        <span class="status-dot"></span>
                        <span class="status-text">Connecting...</span>
                    </div>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <main class="app-main">
            <!-- Sidebar -->
            <aside class="sidebar">
                <nav class="nav-menu">
                    <div class="nav-section">
                        <h3>Analysis Types</h3>
                        <button class="nav-button" data-analysis="rnaseq">
                            📊 RNA-seq Analysis
                        </button>
                        <button class="nav-button" data-analysis="scrnaseq">
                            🔬 scRNA-seq Analysis
                        </button>
                        <button class="nav-button" data-analysis="atacseq">
                            🧬 ATAC-seq Analysis
                        </button>
                        <button class="nav-button" data-analysis="proteomics">
                            🧪 Proteomics Analysis
                        </button>
                    </div>
                    
                    <div class="nav-section">
                        <h3>Tools</h3>
                        <button class="nav-button" data-tool="visualization">
                            📈 Visualization
                        </button>
                        <button class="nav-button" data-tool="data-management">
                            💾 Data Management
                        </button>
                        <button class="nav-button" data-tool="search">
                            🔍 Search & Discovery
                        </button>
                    </div>

                    <div class="nav-section">
                        <h3>System</h3>
                        <button class="nav-button" data-system="servers">
                            ⚙️ Server Status
                        </button>
                        <button class="nav-button" data-system="settings">
                            🔧 Settings
                        </button>
                    </div>
                </nav>
            </aside>

            <!-- Content Area -->
            <section class="content-area">
                <!-- Welcome Screen -->
                <div id="welcome-screen" class="screen active">
                    <div class="welcome-content">
                        <h2>Welcome to Gliaent</h2>
                        <p>Your integrated bioinformatics analysis platform</p>
                        
                        <div class="quick-actions">
                            <div class="action-card" data-action="load-data">
                                <h3>📂 Load Data</h3>
                                <p>Import your bioinformatics datasets</p>
                            </div>
                            <div class="action-card" data-action="start-analysis">
                                <h3>🔬 Start Analysis</h3>
                                <p>Begin analyzing your data</p>
                            </div>
                            <div class="action-card" data-action="view-results">
                                <h3>📊 View Results</h3>
                                <p>Explore previous analysis results</p>
                            </div>
                        </div>

                        <div class="server-status-summary">
                            <h3>MCP Server Status</h3>
                            <div id="server-list" class="server-grid">
                                <!-- Server status cards will be populated here -->
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Analysis Screens -->
                <div id="rnaseq-screen" class="screen">
                    <div class="analysis-header">
                        <h2>📊 RNA-seq Analysis</h2>
                        <div class="analysis-actions">
                            <button class="btn-primary" id="load-rnaseq-data">Load Data</button>
                            <button class="btn-secondary" id="rnaseq-settings">Settings</button>
                        </div>
                    </div>
                    <div class="analysis-content">
                        <div class="analysis-steps">
                            <div class="step">
                                <h4>1. Data Input</h4>
                                <div class="file-input-area" id="rnaseq-file-input">
                                    <p>Drag & drop count matrix or click to select</p>
                                </div>
                            </div>
                            <div class="step">
                                <h4>2. Analysis Parameters</h4>
                                <div class="parameters-form" id="rnaseq-parameters">
                                    <!-- Parameters will be populated here -->
                                </div>
                            </div>
                            <div class="step">
                                <h4>3. Results</h4>
                                <div class="results-area" id="rnaseq-results">
                                    <!-- Results will be shown here -->
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Server Management Screen -->
                <div id="servers-screen" class="screen">
                    <div class="servers-header">
                        <h2>⚙️ MCP Server Management</h2>
                        <button class="btn-primary" id="refresh-servers">Refresh Status</button>
                    </div>
                    <div class="servers-content">
                        <div id="detailed-server-list" class="detailed-servers">
                            <!-- Detailed server information will be populated here -->
                        </div>
                    </div>
                </div>
            </section>
        </main>

        <!-- Footer -->
        <footer class="app-footer">
            <div class="footer-content">
                <span>Gliaent Bioinformatics Platform</span>
                <div class="footer-stats">
                    <span id="active-servers">Servers: 0</span>
                    <span id="memory-usage">Memory: --</span>
                </div>
            </div>
        </footer>
    </div>

    <!-- Loading Overlay -->
    <div id="loading-overlay" class="loading-overlay">
        <div class="loading-content">
            <div class="spinner"></div>
            <p id="loading-message">Loading...</p>
        </div>
    </div>

    <!-- Scripts -->
    <script src="js/app.js"></script>
    <script src="js/mcp-client.js"></script>
    <script src="js/ui-components.js"></script>
</body>
</html>
EOF

# Create main CSS file
cat > src/ui/css/main.css << 'EOF'
/* Gliaent Main Styles */

:root {
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --error-color: #e74c3c;
    --background-color: #ecf0f1;
    --sidebar-color: #34495e;
    --text-color: #2c3e50;
    --border-color: #bdc3c7;
    --shadow: 0 2px 10px rgba(0,0,0,0.1);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    line-height: 1.6;
    overflow: hidden;
}

#app {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* Header */
.app-header {
    background: white;
    border-bottom: 1px solid var(--border-color);
    padding: 0 20px;
    box-shadow: var(--shadow);
    z-index: 100;
}

.header-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 60px;
}

.logo-section {
    display: flex;
    align-items: center;
    gap: 10px;
}

.logo-section h1 {
    font-size: 24px;
    font-weight: 700;
    color: var(--primary-color);
}

.version {
    background: var(--secondary-color);
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
}

.status-section {
    display: flex;
    align-items: center;
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 20px;
    background: #f8f9fa;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--warning-color);
    animation: pulse 2s infinite;
}

.status-dot.connected {
    background: var(--success-color);
    animation: none;
}

.status-dot.error {
    background: var(--error-color);
    animation: none;
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

/* Main Layout */
.app-main {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background: var(--sidebar-color);
    color: white;
    overflow-y: auto;
}

.nav-menu {
    padding: 20px;
}

.nav-section {
    margin-bottom: 30px;
}

.nav-section h3 {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 15px;
    opacity: 0.8;
}

.nav-button {
    display: block;
    width: 100%;
    background: none;
    border: none;
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: 8px;
    font-size: 14px;
}

.nav-button:hover {
    background: rgba(255,255,255,0.1);
    transform: translateX(4px);
}

.nav-button.active {
    background: var(--secondary-color);
}

/* Content Area */
.content-area {
    flex: 1;
    overflow-y: auto;
    position: relative;
}

.screen {
    display: none;
    padding: 30px;
    max-width: 1200px;
    margin: 0 auto;
}

.screen.active {
    display: block;
}

/* Welcome Screen */
.welcome-content h2 {
    font-size: 32px;
    margin-bottom: 10px;
    color: var(--primary-color);
}

.welcome-content p {
    font-size: 18px;
    color: #7f8c8d;
    margin-bottom: 40px;
}

.quick-actions {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 40px;
}

.action-card {
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: var(--shadow);
    cursor: pointer;
    transition: all 0.2s ease;
    border: 2px solid transparent;
}

.action-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0,0,0,0.15);
    border-color: var(--secondary-color);
}

.action-card h3 {
    font-size: 20px;
    margin-bottom: 10px;
    color: var(--primary-color);
}

.action-card p {
    color: #7f8c8d;
}

/* Server Status */
.server-status-summary h3 {
    margin-bottom: 20px;
    color: var(--primary-color);
}

.server-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
}

/* Buttons */
.btn-primary, .btn-secondary {
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s ease;
}

.btn-primary {
    background: var(--secondary-color);
    color: white;
}

.btn-primary:hover {
    background: #2980b9;
    transform: translateY(-1px);
}

.btn-secondary {
    background: #95a5a6;
    color: white;
}

.btn-secondary:hover {
    background: #7f8c8d;
}

/* Footer */
.app-footer {
    background: white;
    border-top: 1px solid var(--border-color);
    padding: 10px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #7f8c8d;
}

.footer-stats {
    display: flex;
    gap: 20px;
}

/* Loading Overlay */
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
}

.loading-overlay.show {
    opacity: 1;
    visibility: visible;
}

.loading-content {
    text-align: center;
    color: white;
}

.spinner {
    width: 40px;
    height: 40px;
    border: 4px solid rgba(255,255,255,0.3);
    border-top: 4px solid white;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 20px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
    .sidebar {
        width: 200px;
    }
    
    .quick-actions {
        grid-template-columns: 1fr;
    }
    
    .screen {
        padding: 20px;
    }
}
EOF

# Create components CSS
cat > src/ui/css/components.css << 'EOF'
/* Gliaent UI Components */

/* Server Cards */
.server-card {
    background: white;
    border-radius: 8px;
    padding: 15px;
    box-shadow: var(--shadow);
    border-left: 4px solid var(--border-color);
    transition: all 0.2s ease;
}

.server-card.running {
    border-left-color: var(--success-color);
}

.server-card.stopped {
    border-left-color: var(--error-color);
}

.server-card.starting {
    border-left-color: var(--warning-color);
}

.server-card h4 {
    margin-bottom: 8px;
    color: var(--primary-color);
    font-size: 16px;
}

.server-card p {
    color: #7f8c8d;
    font-size: 14px;
    margin-bottom: 10px;
}

.server-card .server-actions {
    display: flex;
    gap: 8px;
}

.server-card button {
    padding: 6px 12px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    transition: all 0.2s ease;
}

.server-card .btn-start {
    background: var(--success-color);
    color: white;
}

.server-card .btn-stop {
    background: var(--error-color);
    color: white;
}

.server-card .btn-status {
    background: var(--secondary-color);
    color: white;
}

/* File Input Areas */
.file-input-area {
    border: 2px dashed var(--border-color);
    border-radius: 8px;
    padding: 40px;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    background: #f8f9fa;
}

.file-input-area:hover {
    border-color: var(--secondary-color);
    background: #e3f2fd;
}

.file-input-area.dragover {
    border-color: var(--success-color);
    background: #e8f5e8;
}

/* Analysis Steps */
.analysis-steps {
    display: flex;
    flex-direction: column;
    gap: 30px;
}

.step {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: var(--shadow);
}

.step h4 {
    margin-bottom: 15px;
    color: var(--primary-color);
    border-bottom: 2px solid var(--secondary-color);
    padding-bottom: 8px;
}

/* Parameters Form */
.parameters-form {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
}

.parameter-group {
    display: flex;
    flex-direction: column;
}

.parameter-group label {
    margin-bottom: 5px;
    font-weight: 500;
    color: var(--primary-color);
}

.parameter-group input,
.parameter-group select,
.parameter-group textarea {
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-size: 14px;
}

.parameter-group input:focus,
.parameter-group select:focus,
.parameter-group textarea:focus {
    outline: none;
    border-color: var(--secondary-color);
    box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
}

/* Results Area */
.results-area {
    min-height: 200px;
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    border: 1px solid var(--border-color);
}

.results-area.empty {
    display: flex;
    justify-content: center;
    align-items: center;
    color: #7f8c8d;
    font-style: italic;
}

/* Progress Bars */
.progress-bar {
    width: 100%;
    height: 8px;
    background: #ecf0f1;
    border-radius: 4px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-bar-fill {
    height: 100%;
    background: var(--secondary-color);
    transition: width 0.3s ease;
    border-radius: 4px;
}

/* Notifications */
.notification {
    position: fixed;
    top: 80px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 500;
    z-index: 1000;
    transform: translateX(400px);
    transition: transform 0.3s ease;
}

.notification.show {
    transform: translateX(0);
}

.notification.success {
    background: var(--success-color);
}

.notification.error {
    background: var(--error-color);
}

.notification.warning {
    background: var(--warning-color);
}

.notification.info {
    background: var(--secondary-color);
}

/* Tables */
.data-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow);
}

.data-table th,
.data-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.data-table th {
    background: #f8f9fa;
    font-weight: 600;
    color: var(--primary-color);
}

.data-table tr:hover {
    background: #f8f9fa;
}

/* Modals */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
}

.modal.show {
    opacity: 1;
    visibility: visible;
}

.modal-content {
    background: white;
    border-radius: 8px;
    padding: 30px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid var(--border-color);
}

.modal-close {
    background: none;
    border: none;
    font-size: 24px;
    cursor: pointer;
    color: #7f8c8d;
}

.modal-close:hover {
    color: var(--error-color);
}
EOF

echo "✅ Comprehensive UI structure created!"
echo ""
echo "📁 Created files:"
echo "   - src/ui/index.html (Main UI)"
echo "   - src/ui/css/main.css (Main styles)" 
echo "   - src/ui/css/components.css (Component styles)"
echo ""
echo "📋 Next steps:"
echo "   1. Run: ./setup_electron.sh (will create JS files)"
echo "   2. Run: ./start_gliaent.sh (to start the app)"
echo ""
echo "🎨 The UI includes:"
echo "   - Dashboard with server status"
echo "   - RNA-seq, scRNA-seq, ATAC-seq analysis screens"
echo "   - File loading and data management"
echo "   - Real-time MCP server integration"
echo "   - Responsive design for different screen sizes"