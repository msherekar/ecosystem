// Window Management for Gliaent Electron App with MCP Integration
const { BrowserWindow } = require('electron');
const path = require('path');

class WindowManager {
    constructor() {
        this.mainWindow = null;
        this.secondaryWindows = new Map();
        /**
         * windowId -> plot payload, awaiting the renderer's 'viz:get-data'
         * call. Cleared when the window closes so payloads do not accumulate.
         * @type {Map<string, unknown>}
         */
        this.pendingPlotData = new Map();
    }

    /**
     * Plot payload for a visualization window.
     * @param {string} windowId
     * @returns {unknown} The payload, or undefined if unknown.
     */
    getPlotData(windowId) {
        return this.pendingPlotData.get(windowId);
    }

    async createMainWindow() {
        this.mainWindow = new BrowserWindow({
            width: 1600,
            height: 1000,
            minWidth: 1200,
            minHeight: 800,
            webPreferences: {
                // Every one of these was previously inverted. With
                // nodeIntegration on and contextIsolation off and no preload,
                // any script reaching the renderer had require('fs') and
                // require('child_process') -- including the Plotly bundle
                // that was fetched from a CDN over plain HTTP.
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: false, // preload needs require(); the bridge is still isolated
                webSecurity: true,
                allowRunningInsecureContent: false,
                // enableRemoteModule is not set: it was removed in Electron 14
                // and this app pins ^37, so it had been a silent no-op that
                // read as though @electron/remote still worked.
                preload: path.join(__dirname, 'preload.js')
            },
            titleBarStyle: 'hiddenInset',
            // `frame: false` on macOS combined with hiddenInset produced a
            // frameless window with no drag region and no traffic lights.
            frame: true,
            // Hidden until the renderer has painted, so the user does not see
            // a white rectangle. `show: true` made the ready-to-show handler
            // and the 2s failsafe below redundant.
            show: false,
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
            console.error('Failed to load the UI:', error);
            // No fallback to the repo-root index.html: that is the Vite SOURCE
            // template, whose <script type="module" src="/src/.../main.tsx">
            // cannot resolve over file://, so the "fallback" could never work.
            // Show an honest error instead of a blank window.
            const detail = String(error && error.message ? error.message : error)
                .replace(/[<>&]/g, '');
            await this.mainWindow.loadURL(
                'data:text/html;charset=utf-8,' +
                encodeURIComponent(
                    '<!doctype html><meta charset="utf-8">' +
                    '<title>Gliaent</title>' +
                    '<style>body{font:14px system-ui;padding:3rem;max-width:40rem}' +
                    'code{background:#f4f4f5;padding:.15em .35em;border-radius:3px}</style>' +
                    '<h1>Gliaent could not load its interface</h1>' +
                    '<p>The renderer bundle is missing. In development, start the ' +
                    'dev server first with <code>npm run dev</code>. For a packaged ' +
                    'build, run <code>npm run build</code> so <code>dist/</code> exists.</p>' +
                    '<p><strong>Error:</strong> ' + detail + '</p>'
                )
            );
        }
        
        // Shown once the renderer has painted. The failsafe timer that used
        // to force-show after 2s is gone: it existed to work around show:true
        // racing the load, which no longer happens.
        this.mainWindow.once('ready-to-show', () => {
            if (this.mainWindow && !this.mainWindow.isDestroyed()) {
                this.mainWindow.show();
                this.mainWindow.focus();
                this.updateWindowTitle('Ready');
            }
        });
        
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
        // ONE will-navigate handler. There were two: the first prevented any
        // navigation away from the current URL, so the second -- which tried
        // to treat a file:// navigation as a dropped file -- could never take
        // effect. `will-navigate` is not how file drops work in any case
        // (that is the renderer's `drop` event), so the advertised
        // drag-and-drop never functioned. The handler below does the one job
        // it can actually do: keep the app on its own origin.
        this.mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
            const current = this.mainWindow.webContents.getURL();
            if (navigationUrl !== current) {
                console.warn('Blocked navigation to', navigationUrl);
                event.preventDefault();
            }
        });

        // External links open in the user's browser rather than inside the
        // app, where they would run with the app's privileges.
        this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
            if (/^https?:\/\//.test(url)) {
                const { shell } = require('electron');
                shell.openExternal(url);
            }
            return { action: 'deny' };
        });

        // A Content-Security-Policy for the renderer. index.html carried no
        // CSP and neither did the main process, so nothing constrained script
        // origins. 'unsafe-inline' for styles is required by the CSS-in-JS
        // the UI uses; scripts are restricted to the bundle.
        const devServer = process.env.NODE_ENV === 'development'
            ? " http://localhost:3000 ws://localhost:3000"
            : '';
        this.mainWindow.webContents.session.webRequest.onHeadersReceived(
            (details, callback) => {
                callback({
                    responseHeaders: {
                        ...details.responseHeaders,
                        'Content-Security-Policy': [
                            `default-src 'self'${devServer};` +
                            `script-src 'self'${devServer};` +
                            `style-src 'self' 'unsafe-inline'${devServer};` +
                            "img-src 'self' data: blob:;" +
                            `connect-src 'self'${devServer};` +
                            "font-src 'self' data:;" +
                            "object-src 'none';" +
                            "base-uri 'none';" +
                            "form-action 'none';" +
                            "frame-ancestors 'none'"
                        ]
                    }
                });
            }
        );
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
                // Every one of these was previously inverted. With
                // nodeIntegration on and contextIsolation off and no preload,
                // any script reaching the renderer had require('fs') and
                // require('child_process') -- including the Plotly bundle
                // that was fetched from a CDN over plain HTTP.
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: false, // preload needs require(); the bridge is still isolated
                webSecurity: true,
                allowRunningInsecureContent: false,
                // enableRemoteModule is not set: it was removed in Electron 14
                // and this app pins ^37, so it had been a silent no-op that
                // read as though @electron/remote still worked.
                preload: path.join(__dirname, 'preload.js')
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
                // Every one of these was previously inverted. With
                // nodeIntegration on and contextIsolation off and no preload,
                // any script reaching the renderer had require('fs') and
                // require('child_process') -- including the Plotly bundle
                // that was fetched from a CDN over plain HTTP.
                nodeIntegration: false,
                contextIsolation: true,
                sandbox: false, // preload needs require(); the bridge is still isolated
                webSecurity: true,
                allowRunningInsecureContent: false,
                // enableRemoteModule is not set: it was removed in Electron 14
                // and this app pins ^37, so it had been a silent no-op that
                // read as though @electron/remote still worked.
                preload: path.join(__dirname, 'preload.js')
            },
            title: 'Visualization',
            show: false,
            ...options
        });

        // The plot payload is held here and handed to the renderer over the
        // preload bridge (see the 'viz:get-data' handler), NOT interpolated
        // into the page source. String-interpolating JSON into a <script>
        // body meant any `</script>` or U+2028 in the analysis data broke out
        // of the script element.
        this.pendingPlotData.set(windowId, plotData);
        vizWindow.gliaentWindowId = windowId;

        const vizUiPath = path.join(__dirname, 'visualization.html');
        try {
            await vizWindow.loadFile(vizUiPath);
        } catch (error) {
            console.error('Failed to load the visualization window:', error);
            this.pendingPlotData.delete(windowId);
            vizWindow.destroy();
            throw new Error(
                `Visualization window could not load ${vizUiPath}: ${error.message}`
            );
        }

        vizWindow.once('ready-to-show', () => {
            vizWindow.show();
        });

        vizWindow.on('closed', () => {
            this.secondaryWindows.delete(windowId);
            this.pendingPlotData.delete(windowId);
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