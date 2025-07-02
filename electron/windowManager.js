// Window Management for Gliaent Electron App with MCP Integration
const { BrowserWindow } = require('electron');
const path = require('path');

class WindowManager {
    constructor() {
        this.mainWindow = null;
        this.secondaryWindows = new Map();
    }

    async createMainWindow() {
        this.mainWindow = new BrowserWindow({
            width: 1600,
            height: 1000,
            minWidth: 1200,
            minHeight: 800,
            webPreferences: {
                nodeIntegration: true,
                contextIsolation: false,
                enableRemoteModule: true,
                webSecurity: false, // Allow loading local files for bioinformatics data
                allowRunningInsecureContent: true // For local development
            },
            titleBarStyle: 'hiddenInset',
            frame: process.platform !== 'darwin',
            show: true,  // Show window immediately
            // icon: this.getAppIcon(),  // Skip icon for now to avoid crashes
            title: 'Gliaent - Bioinformatics Analysis Platform'
        });

        // Load the main UI
        try {
            if (process.env.NODE_ENV === 'development') {
                // In development, load from Vite dev server
                console.log('🔧 Loading from Vite dev server...');
                await this.mainWindow.loadURL('http://localhost:3000');
                console.log('✅ Vite dev server loaded successfully');
            } else {
                // In production, load from built files
                const uiPath = path.join(__dirname, '..', 'dist', 'index.html');
                await this.mainWindow.loadFile(uiPath);
                console.log('✅ Production UI file loaded successfully');
            }
        } catch (error) {
            console.error('Failed to load UI file:', error);
            // Fallback: try loading from root index.html
            try {
                const fallbackPath = path.join(__dirname, '..', 'index.html');
                await this.mainWindow.loadFile(fallbackPath);
                console.log('✅ Fallback UI loaded successfully');
            } catch (fallbackError) {
                console.error('Fallback UI also failed:', fallbackError);
                // Last resort: simple HTML page
                await this.mainWindow.loadURL('data:text/html,<h1>Gliaent Loading...</h1><p>UI files not found. Please check installation.</p>');
            }
        }
        
        // Ensure window is visible and focused
        this.mainWindow.show();
        this.mainWindow.focus();
        this.updateWindowTitle('Ready');
        
        // Also keep the ready-to-show handler for additional setup
        this.mainWindow.once('ready-to-show', () => {
            console.log('🎯 Window ready-to-show event fired');
            this.mainWindow.show();
            this.mainWindow.focus();
        });
        
        // Failsafe: Force window to show after 2 seconds if not visible
        setTimeout(() => {
            if (this.mainWindow && !this.mainWindow.isDestroyed()) {
                if (!this.mainWindow.isVisible()) {
                    console.log('🔧 Failsafe: Forcing window to show');
                    this.mainWindow.show();
                    this.mainWindow.focus();
                    this.mainWindow.moveTop();
                }
            }
        }, 2000);
        
        // Open DevTools in development
        if (process.argv.includes('--dev') || process.env.NODE_ENV === 'development') {
            this.mainWindow.webContents.openDevTools();
        }

        // Handle window events
        this.setupWindowEvents();

        // Setup window-specific shortcuts
        this.setupKeyboardShortcuts();

        console.log('✅ Main window created successfully');
        return this.mainWindow;
    }

    setupWindowEvents() {
        // Handle window closed
        this.mainWindow.on('closed', () => {
            this.mainWindow = null;
        });

        // Handle window focus/blur for analytics
        this.mainWindow.on('focus', () => {
            this.sendToRenderer('window-focus', { timestamp: Date.now() });
        });

        this.mainWindow.on('blur', () => {
            this.sendToRenderer('window-blur', { timestamp: Date.now() });
        });

        // Handle window state changes
        this.mainWindow.on('maximize', () => {
            this.sendToRenderer('window-maximized');
        });

        this.mainWindow.on('unmaximize', () => {
            this.sendToRenderer('window-unmaximized');
        });

        // Handle window ready for MCP integration
        this.mainWindow.webContents.once('dom-ready', () => {
            console.log('🎯 Window DOM ready - initializing MCP integration');
            this.initializeMCPIntegration();
        });

        // Handle navigation errors
        this.mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL) => {
            console.error('Window failed to load:', errorCode, errorDescription, validatedURL);
        });
    }

    setupKeyboardShortcuts() {
        const { globalShortcut } = require('electron');

        // Register global shortcuts for common actions
        try {
            // Toggle DevTools
            globalShortcut.register('CommandOrControl+Shift+I', () => {
                if (this.mainWindow && !this.mainWindow.isDestroyed()) {
                    this.mainWindow.webContents.toggleDevTools();
                }
            });

            // Reload window
            globalShortcut.register('CommandOrControl+R', () => {
                if (this.mainWindow && !this.mainWindow.isDestroyed()) {
                    this.mainWindow.reload();
                }
            });

            // Force reload
            globalShortcut.register('CommandOrControl+Shift+R', () => {
                if (this.mainWindow && !this.mainWindow.isDestroyed()) {
                    this.mainWindow.webContents.reloadIgnoringCache();
                }
            });

        } catch (error) {
            console.warn('Failed to register global shortcuts:', error);
        }
    }

    initializeMCPIntegration() {
        // Send initial configuration to renderer
        this.sendToRenderer('mcp-config', {
            serverPath: path.join(__dirname, '..', 'src', 'mcp', 'servers'),
            configPath: path.join(__dirname, '..', 'config'),
            dataPath: path.join(__dirname, '..', 'data'),
            version: '1.0.0'
        });

        // Setup MCP-specific window features
        this.setupMCPFeatures();
    }

    setupMCPFeatures() {
        // Enable drag and drop for bioinformatics files
        this.mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
            // Prevent navigation away from the app
            if (navigationUrl !== this.mainWindow.webContents.getURL()) {
                event.preventDefault();
            }
        });

        // Handle file drops
        this.mainWindow.webContents.on('will-navigate', (event, url) => {
            if (url.startsWith('file://')) {
                event.preventDefault();
                // Extract file path and send to renderer
                const filePath = url.replace('file://', '');
                this.sendToRenderer('file-dropped', { filePath });
            }
        });
    }

    updateWindowTitle(status = '', details = '') {
        if (this.mainWindow && !this.mainWindow.isDestroyed()) {
            let title = 'Gliaent';
            
            if (status) {
                title += ` - ${status}`;
            }
            
            if (details) {
                title += ` (${details})`;
            }
            
            this.mainWindow.setTitle(title);
        }
    }

    sendToRenderer(channel, data = {}) {
        if (this.mainWindow && !this.mainWindow.isDestroyed()) {
            this.mainWindow.webContents.send(channel, data);
        }
    }

    // Create secondary windows for specific tasks
    async createAnalysisWindow(analysisType, options = {}) {
        const windowId = `analysis_${analysisType}_${Date.now()}`;
        
        const analysisWindow = new BrowserWindow({
            width: 1200,
            height: 800,
            parent: this.mainWindow,
            webPreferences: {
                nodeIntegration: true,
                contextIsolation: false,
                enableRemoteModule: true
            },
            title: `${analysisType.toUpperCase()} Analysis`,
            show: false,
            ...options
        });

        // Load analysis-specific UI
        const analysisUiPath = path.join(__dirname, '..', 'src', 'ui', 'analysis', `${analysisType}.html`);
        
        try {
            await analysisWindow.loadFile(analysisUiPath);
        } catch (error) {
            // Fallback to main UI with analysis parameter
            await analysisWindow.loadFile(path.join(__dirname, '..', 'src', 'ui', 'index.html'));
            analysisWindow.webContents.once('dom-ready', () => {
                analysisWindow.webContents.send('set-analysis-mode', { type: analysisType });
            });
        }

        analysisWindow.once('ready-to-show', () => {
            analysisWindow.show();
        });

        analysisWindow.on('closed', () => {
            this.secondaryWindows.delete(windowId);
        });

        this.secondaryWindows.set(windowId, analysisWindow);
        return { windowId, window: analysisWindow };
    }

    async createVisualizationWindow(plotData, options = {}) {
        const windowId = `viz_${Date.now()}`;
        
        const vizWindow = new BrowserWindow({
            width: 1000,
            height: 700,
            parent: this.mainWindow,
            webPreferences: {
                nodeIntegration: true,
                contextIsolation: false
            },
            title: 'Visualization',
            show: false,
            ...options
        });

        // Load visualization UI
        const vizUiPath = path.join(__dirname, '..', 'src', 'ui', 'visualization.html');
        
        try {
            await vizWindow.loadFile(vizUiPath);
        } catch (error) {
            // Create simple visualization HTML
            const vizHtml = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Visualization</title>
                    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                </head>
                <body>
                    <div id="plot" style="width:100%;height:100%;"></div>
                    <script>
                        const plotData = ${JSON.stringify(plotData)};
                        Plotly.newPlot('plot', plotData.data || [], plotData.layout || {});
                    </script>
                </body>
                </html>
            `;
            await vizWindow.loadURL(`data:text/html,${encodeURIComponent(vizHtml)}`);
        }

        vizWindow.once('ready-to-show', () => {
            vizWindow.show();
        });

        vizWindow.on('closed', () => {
            this.secondaryWindows.delete(windowId);
        });

        this.secondaryWindows.set(windowId, vizWindow);
        return { windowId, window: vizWindow };
    }

    getAppIcon() {
        // Return app icon path based on platform
        const iconName = process.platform === 'win32' ? 'icon.ico' : 
                        process.platform === 'darwin' ? 'icon.icns' : 'icon.png';
        
        const iconPath = path.join(__dirname, '..', 'assets', 'icons', iconName);
        
        // Check if icon exists, return path or undefined
        const fs = require('fs');
        return fs.existsSync(iconPath) ? iconPath : undefined;
    }

    closeSecondaryWindow(windowId) {
        const window = this.secondaryWindows.get(windowId);
        if (window && !window.isDestroyed()) {
            window.close();
        }
    }

    closeAllSecondaryWindows() {
        for (const [windowId, window] of this.secondaryWindows) {
            if (window && !window.isDestroyed()) {
                window.close();
            }
        }
        this.secondaryWindows.clear();
    }

    getMainWindow() {
        return this.mainWindow;
    }

    getAllWindows() {
        const windows = [];
        
        if (this.mainWindow && !this.mainWindow.isDestroyed()) {
            windows.push({ id: 'main', window: this.mainWindow, type: 'main' });
        }
        
        for (const [windowId, window] of this.secondaryWindows) {
            if (window && !window.isDestroyed()) {
                windows.push({ id: windowId, window, type: 'secondary' });
            }
        }
        
        return windows;
    }

    // Cleanup method
    cleanup() {
        const { globalShortcut } = require('electron');
        
        // Unregister all shortcuts
        globalShortcut.unregisterAll();
        
        // Close all secondary windows
        this.closeAllSecondaryWindows();
        
        // Main window will be closed by Electron automatically
    }
}

module.exports = { WindowManager };