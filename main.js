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
        IPCHandlers.setupAll(backendManager);
        
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

    /**
     * Run a tool, starting its server first if it is not already up.
     *
     * executeTool fails with "Server <type> not running" unless the server is
     * in active_servers, and no renderer code ever called startServer, so the
     * analysis flows could not succeed on a clean launch.
     *
     * @param {string} serverType
     * @param {string} toolName
     * @param {object} parameters
     * @returns {Promise<{success: boolean, data?: unknown, error?: string}>}
     */
    async function runTool(serverType, toolName, parameters) {
        const connection = backendManager.getConnectionStatus();
        if (!connection || !connection.connected) {
            return {
                success: false,
                error: 'The analysis backend is not connected yet. Wait for it '
                     + 'to finish starting, or check the backend log.'
            };
        }

        const running = await backendManager.getServerStatus(serverType).catch(() => null);
        if (!running || running.status !== 'running') {
            const started = await backendManager.startServer(serverType, {});
            if (started && started.success === false) {
                return {
                    success: false,
                    error: `Could not start the ${serverType} server: ${started.error}`
                };
            }
        }
        return backendManager.executeTool(serverType, toolName, parameters);
    }

    /**
     * Plot payload for a visualization window.
     *
     * Replaces interpolating JSON.stringify(plotData) into the page's script
     * body, where a `</script>` in any analysis label broke out of the script.
     */
    ipcMain.handle('viz:get-data', (event) => {
        try {
            const sender = BrowserWindow.fromWebContents(event.sender);
            const windowId = sender && sender.gliaentWindowId;
            if (!windowId) {
                return { success: false, error: 'Not a visualization window.' };
            }
            const data = windowManager.getPlotData(windowId);
            if (data === undefined) {
                return { success: false, error: 'No plot data for this window.' };
            }
            return { success: true, data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    /** App version, for the About panel. */
    ipcMain.handle('app:get-version', () => {
        return { success: true, data: app.getVersion() };
    });

    /**
     * Session token for the local API.
     *
     * The backend prints GLIAENT_SESSION_TOKEN=<token> on startup; the
     * renderer needs it to call the authenticated endpoints.
     */
    ipcMain.handle('app:get-session-token', () => {
        const token = backendManager.sessionToken;
        return token
            ? { success: true, data: token }
            : { success: false, error: 'The backend has not issued a token yet.' };
    });

    // Bioinformatics-specific handlers
    ipcMain.handle('mcp:analyze-rnaseq', async (event, parameters) => {
        try {
            return await runTool('rnaseq', 'analyze_differential_expression', parameters);
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:analyze-scrnaseq', async (event, parameters) => {
        try {
            return await runTool('scrnaseq', 'analyze_single_cells', parameters);
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:analyze-atacseq', async (event, parameters) => {
        try {
            return await runTool('atacseq', 'analyze_chromatin_accessibility', parameters);
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    ipcMain.handle('mcp:create-visualization', async (event, parameters) => {
        try {
            return await runTool('visualization', 'create_plot', parameters);
        } catch (error) {
            return { success: false, error: error.message };
        }
    });

    console.log('✅ MCP IPC handlers setup complete');
}

/**
 * Forward backend lifecycle events to the renderer.
 *
 * This function previously looped over the event names and console.logged
 * each one, registering nothing. Combined with the renderer subscribing to
 * 'server-status-update' -- a channel nothing ever emitted -- there was no
 * live status anywhere in the app, only a one-shot poll on one page.
 *
 * @param {import('electron').BrowserWindow} mainWindow
 */
function setupMCPEventListeners(mainWindow) {
    if (!backendManager || typeof backendManager.on !== 'function') {
        console.warn('Backend manager does not emit events; live status is unavailable.');
        return;
    }

    const forwarded = [
        'backend-status',
        'mcp-ready',
        'mcp-disconnected',
        'mcp-error',
        'server-started',
        'server-stopped',
        'tool-response',
        'system-status'
    ];

    for (const eventName of forwarded) {
        backendManager.on(eventName, (payload) => {
            if (mainWindow && !mainWindow.isDestroyed()) {
                mainWindow.webContents.send(eventName, payload);
            }
        });
    }
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

/** Guards against re-entering the shutdown sequence. */
let shuttingDown = false;

app.on('before-quit', async (event) => {
    // Re-entrancy guard: window-all-closed also calls app.quit(), so without
    // this the handler preventDefault()s a second time and the quit loops.
    if (shuttingDown) {
        return;
    }
    shuttingDown = true;

    console.log('Application shutting down...');
    event.preventDefault();

    try {
        windowManager.cleanup();
    } catch (error) {
        // cleanup() unregisters global shortcuts. It was never called at all,
        // so CommandOrControl+R stayed grabbed system-wide after quitting.
        console.error('Window cleanup failed:', error);
    }

    try {
        // Awaited, so the backend is actually gone before we exit. The old
        // sequence called app.exit(0) on a 3s timer while stop()'s own
        // SIGTERM was scheduled for 4s and SIGKILL for 9s, so Electron always
        // exited before signalling the child.
        await backendManager.stop();
    } catch (error) {
        console.error('Backend shutdown failed:', error);
    }

    app.exit(0);
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