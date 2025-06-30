// Gliaent Main Application JavaScript
console.log('🧬 Gliaent App Loading...');

// Global state
window.GliaentApp = {
    initialized: false,
    currentScreen: 'welcome-screen',
    mcpClient: null,
    servers: [],
    connectionStatus: 'connecting'
};

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 DOM Ready - Initializing Gliaent App');
    initializeApp();
});

function initializeApp() {
    console.log('🚀 Initializing Gliaent Application');
    
    // Initialize UI components
    setupNavigation();
    setupConnectionStatus();
    setupQuickActions();
    
    // Connect to MCP backend
    connectToMCP();
    
    // Show welcome screen
    showScreen('welcome-screen');
    
    window.GliaentApp.initialized = true;
    console.log('✅ Gliaent App Initialized');
}

function setupNavigation() {
    // Handle navigation buttons
    const navButtons = document.querySelectorAll('.nav-button');
    navButtons.forEach(button => {
        button.addEventListener('click', function() {
            const analysisType = this.getAttribute('data-analysis');
            const toolType = this.getAttribute('data-tool');
            const systemType = this.getAttribute('data-system');
            
            if (analysisType) {
                showScreen(analysisType + '-screen');
            } else if (toolType) {
                handleToolAction(toolType);
            } else if (systemType) {
                showScreen(systemType + '-screen');
            }
        });
    });
    
    // Handle analysis option clicks in the analysis selection screen
    document.addEventListener('click', function(e) {
        if (e.target.closest('.analysis-option')) {
            const option = e.target.closest('.analysis-option');
            const analysisType = option.getAttribute('data-analysis');
            if (analysisType) {
                showScreen(analysisType + '-screen');
            }
        }
    });
}

function setupConnectionStatus() {
    const statusElement = document.getElementById('connection-status');
    const statusDot = statusElement.querySelector('.status-dot');
    const statusText = statusElement.querySelector('.status-text');
    
    // Update connection status
    function updateConnectionStatus(status) {
        window.GliaentApp.connectionStatus = status;
        
        statusDot.className = 'status-dot';
        switch(status) {
            case 'connected':
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
                break;
            case 'disconnected':
                statusDot.classList.add('disconnected');
                statusText.textContent = 'Disconnected';
                break;
            case 'connecting':
            default:
                statusDot.classList.add('connecting');
                statusText.textContent = 'Connecting...';
                break;
        }
    }
    
    // Start with connecting status
    updateConnectionStatus('connecting');
    
    // Expose globally
    window.updateConnectionStatus = updateConnectionStatus;
}

function setupQuickActions() {
    const actionCards = document.querySelectorAll('.action-card');
    actionCards.forEach(card => {
        card.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            handleQuickAction(action);
        });
    });
}

function showScreen(screenId) {
    console.log(`📱 Switching to screen: ${screenId}`);
    
    // Hide all screens
    const screens = document.querySelectorAll('.screen');
    screens.forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Show target screen
    const targetScreen = document.getElementById(screenId);
    if (targetScreen) {
        targetScreen.classList.add('active');
        window.GliaentApp.currentScreen = screenId;
    } else {
        console.warn(`⚠️ Screen not found: ${screenId}`);
        // Fallback to welcome screen
        document.getElementById('welcome-screen').classList.add('active');
        window.GliaentApp.currentScreen = 'welcome-screen';
    }
}

function handleQuickAction(action) {
    console.log(`⚡ Quick action: ${action}`);
    
    switch(action) {
        case 'load-data':
            showScreen('data-loading-screen');
            break;
        case 'start-analysis':
            showScreen('analysis-selection-screen');  
            break;
        case 'view-results':
            showScreen('results-screen');
            break;
        default:
            console.warn(`Unknown quick action: ${action}`);
    }
}

function handleToolAction(toolType) {
    console.log(`🔧 Tool action: ${toolType}`);
    
    switch(toolType) {
        case 'visualization':
            showScreen('visualization-screen');
            break;
        case 'data-management':
            showScreen('data-management-screen');
            break;
        case 'search':
            showScreen('search-screen');
            break;
        default:
            console.warn(`Unknown tool: ${toolType}`);
    }
}

function connectToMCP() {
    console.log('🔗 Attempting to connect to MCP backend...');
    
    // This will be handled by mcp-client.js
    if (window.MCPClient) {
        window.MCPClient.connect()
            .then(() => {
                console.log('✅ MCP connection established');
                window.updateConnectionStatus('connected');
                loadServerStatus();
            })
            .catch(error => {
                console.error('❌ MCP connection failed:', error);
                window.updateConnectionStatus('disconnected');
            });
    } else {
        // Fallback - simulate connection
        setTimeout(() => {
            console.log('🔄 Simulating MCP connection...');
            window.updateConnectionStatus('connected');
            loadServerStatus();
        }, 2000);
    }
}

function loadServerStatus() {
    console.log('📊 Loading server status...');
    
    // Default server list
    const defaultServers = [
        { name: 'RNA-seq', type: 'rnaseq', status: 'ready' },
        { name: 'scRNA-seq', type: 'scrnaseq', status: 'ready' },
        { name: 'ATAC-seq', type: 'atacseq', status: 'ready' },
        { name: 'Proteomics', type: 'proteomics', status: 'ready' },
        { name: 'Data Server', type: 'data', status: 'ready' },
        { name: 'Visualization', type: 'visualization', status: 'ready' },
        { name: 'Search', type: 'search', status: 'ready' }
    ];
    
    updateServerDisplay(defaultServers);
    window.GliaentApp.servers = defaultServers;
}

function updateServerDisplay(servers) {
    const serverList = document.getElementById('server-list');
    const activeServersCount = document.getElementById('active-servers');
    
    if (serverList) {
        serverList.innerHTML = '';
        
        servers.forEach(server => {
            const serverCard = document.createElement('div');
            serverCard.className = 'server-card';
            serverCard.innerHTML = `
                <div class="server-name">${server.name}</div>
                <div class="server-status ${server.status}">${server.status}</div>
            `;
            serverList.appendChild(serverCard);
        });
    }
    
    if (activeServersCount) {
        const activeCount = servers.filter(s => s.status === 'ready').length;
        activeServersCount.textContent = `Servers: ${activeCount}`;
    }
}

// Export functions for global access
window.GliaentApp.showScreen = showScreen;
window.GliaentApp.updateServerDisplay = updateServerDisplay;
window.GliaentApp.loadServerStatus = loadServerStatus;

console.log('📚 Gliaent App JavaScript loaded'); 