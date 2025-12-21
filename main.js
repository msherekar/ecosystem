// Gliaent Electron Main Process - MCP Integration
console.log('📚 Gliaent main process loading...');

// Safe Electron import with error handling
let app, BrowserWindow, ipcMain;

try {
    const electron = require('electron');
    
    if (typeof electron === 'string') {
        console.error('❌ Electron returned path instead of API object:', electron);
        console.error('❌ This indicates a Node.js/Electron compatibility issue');
        process.exit(1);
    }
    
    ({ app, BrowserWindow, ipcMain } = electron);
    
    if (!app) {
        console.error('❌ Electron app object is undefined');
        console.error('❌ Make sure you are running this through Electron, not Node.js directly');
        process.exit(1);
    }
    
    console.log('✅ Electron modules loaded successfully');
    
} catch (error) {
    console.error('❌ Failed to load Electron:', error.message);
    console.error('❌ Make sure Electron is properly installed');
    process.exit(1);
}

const { WindowManager } = require('./electron/windowManager');
const { BackendManager } = require('./electron/backendManager');
const { IPCHandlers } = require('./electron/ipcHandlers');

let windowManager;
let backendManager;

async function initialize() {
    console.log('🧬 Initializing Gliaent Electron App with MCP Integration...');
    
    try {
        // Initialize managers
        windowManager = new WindowManager();
        backendManager = new BackendManager();
        
        // Setup IPC handlers with MCP integration
        setupMCPIpcHandlers();
        IPCHandlers.setupAll();
        
        // Create main window
        const mainWindow = await windowManager.createMainWindow();
        
        // Start MCP Backend (instead of FastAPI)
        console.log('🔗 Starting MCP Server Orchestrator...');
        await backendManager.start(mainWindow);
        
        // Setup MCP event listeners
        setupMCPEventListeners(mainWindow);
        
        console.log('✅ Gliaent initialized successfully with MCP backend');
        
    } catch (error) {
        console.error('❌ Failed to initialize Gliaent:', error);
        
        // Show error dialog if window exists
        if (windowManager?.getMainWindow()) {
            const { dialog } = require('electron');
            dialog.showErrorBox(
                'Initialization Error',
                `Failed to start Gliaent: ${error.message}\n\nPlease check that Python and required dependencies are installed.`
            );
        }
    }
}

function setupMCPIpcHandlers() {
    console.log('🔧 Setting up MCP IPC handlers...');

    // MCP Server Management
    ipcMain.handle('mcp:start-server', async (event, serverType, options) => {
        try {
            console.log(`📡 Starting MCP server: ${serverType}`);
            const result = await backendManager.startServer(serverType, options);
            return result;
        } catch (error) {
            console.error(`Failed to start server ${serverType}:`, error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:stop-server', async (event, serverType) => {
        try {
            console.log(`🛑 Stopping MCP server: ${serverType}`);
            const result = await backendManager.stopServer(serverType);
            return result;
        } catch (error) {
            console.error(`Failed to stop server ${serverType}:`, error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:execute-tool', async (event, serverType, toolName, parameters) => {
        try {
            console.log(`🔧 Executing tool: ${serverType}.${toolName}`);
            const result = await backendManager.executeTool(serverType, toolName, parameters);
            return result;
        } catch (error) {
            console.error(`Failed to execute tool ${toolName}:`, error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:get-available-servers', async (event) => {
        try {
            const servers = await backendManager.getAvailableServers();
            return { success: true, data: servers };
        } catch (error) {
            console.error('Failed to get available servers:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:get-system-status', async (event) => {
        try {
            const status = await backendManager.getSystemStatus();
            return { success: true, data: status };
        } catch (error) {
            console.error('Failed to get system status:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:get-server-status', async (event, serverType) => {
        try {
            const status = await backendManager.getServerStatus(serverType);
            return { success: true, data: status };
        } catch (error) {
            console.error('Failed to get server status:', error);
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:get-connection-status', (event) => {
        try {
            const status = backendManager.getConnectionStatus();
            return { success: true, data: status };
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    // Bioinformatics-specific handlers
    ipcMain.handle('mcp:analyze-rnaseq', async (event, parameters) => {
        try {
            const result = await backendManager.executeTool('rnaseq', 'analyze_differential_expression', parameters);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:analyze-scrnaseq', async (event, parameters) => {
        try {
            const result = await backendManager.executeTool('scrnaseq', 'analyze_single_cells', parameters);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:analyze-atacseq', async (event, parameters) => {
        try {
            const result = await backendManager.executeTool('atacseq', 'analyze_chromatin_accessibility', parameters);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:create-visualization', async (event, parameters) => {
        try {
            const result = await backendManager.executeTool('visualization', 'create_plot', parameters);
            return result;
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    console.log('✅ MCP IPC handlers setup complete');
}

function setupMCPEventListeners(mainWindow) {
    console.log('📻 Setting up MCP event listeners...');

    // These events are automatically forwarded by BackendManager
    // Just log them here for debugging
    const mcpEvents = [
        'backend-status',
        'mcp-ready', 
        'mcp-disconnected',
        'mcp-error',
        'server-started',
        'server-stopped',
        'tool-response',
        'system-status'
    ];

    mcpEvents.forEach(eventName => {
        // Events are already being sent by backendManager.notifyElectron()
        // We can add additional logging or processing here if needed
        console.log(`📡 Listening for MCP event: ${eventName}`);
    });
}

// App event handlers

app.whenReady().then(() => {
    initialize().catch(error => {
        console.error('Critical initialization error:', error);
        app.quit();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        try {
            await windowManager.createMainWindow();
        } catch (error) {
            console.error('Failed to recreate window:', error);
        }
    }
});

app.on('before-quit', (event) => {
    console.log('🚪 Application shutting down...');
    
    if (backendManager) {
        // Give MCP time to shutdown gracefully
        event.preventDefault();
        
        setTimeout(() => {
            backendManager.stop();
            setTimeout(() => {
                app.exit(0);
            }, 2000);
        }, 1000);
    }
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    
    // Try to show error dialog if possible
    try {
        const { dialog } = require('electron');
        dialog.showErrorBox('Critical Error', `Application error: ${error.message}`);
    } catch (e) {
        // Ignore dialog errors
    }
    
    // Cleanup and exit
    if (backendManager) {
        backendManager.stop();
    }
    
    setTimeout(() => {
        process.exit(1);
    }, 3000);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// Export for testing
module.exports = {
    initialize,
    setupMCPIpcHandlers,
    setupMCPEventListeners
};

console.log('📚 Gliaent main process loaded with MCP integration');