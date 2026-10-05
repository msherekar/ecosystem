// MCP Backend Management - Integrated with MCP Server Orchestrator
const { spawn } = require('child_process');
const { EventEmitter } = require('events');
const fs = require('fs');
const path = require('path');

/** Repo root, resolved from this file rather than the process CWD. */
const APP_ROOT = path.join(__dirname, '..');

/**
 * Locate a Python interpreter.
 *
 * `spawn('python', ...)` assumed a bare `python` on PATH. On many systems only
 * `python3` exists, and in a packaged app there is no conda environment at
 * all, so the backend simply never started.
 *
 * @returns {string} The interpreter to use.
 */
function resolvePython() {
    if (process.env.GLIAENT_PYTHON) {
        return process.env.GLIAENT_PYTHON;
    }
    const candidates = process.platform === 'win32'
        ? ['python.exe', 'python3.exe']
        : ['python3', 'python'];
    for (const candidate of candidates) {
        // An absolute path we can verify is preferred; otherwise fall through
        // to PATH resolution by spawn.
        for (const dir of (process.env.PATH || '').split(path.delimiter)) {
            if (!dir) continue;
            const full = path.join(dir, candidate);
            try {
                fs.accessSync(full, fs.constants.X_OK);
                return full;
            } catch {
                // Not here; keep looking.
            }
        }
    }
    return candidates[0];
}

class BackendManager extends EventEmitter {
    constructor() {
        super();
        this.mcpProcess = null;
        this.isConnected = false;
        this.stopping = false;
        /**
         * Session token for the local API, scraped from the backend's startup
         * line. The renderer needs it to call authenticated endpoints.
         * @type {string|null}
         */
        this.sessionToken = null;
        this.requestCallbacks = new Map();
        this.requestCounter = 0;
        this.mainWindow = null;
        
        // Connection state
        this.serverStatuses = {};
        this.availableServers = [];
    }

    async start(mainWindow) {
        console.log('🚀 Starting MCP Server Orchestrator...');
        this.mainWindow = mainWindow;
        
        try {
            // Start MCP orchestrator instead of FastAPI
            const python = resolvePython();
            console.log(`Starting analysis backend with ${python}`);

            // cwd and PYTHONPATH are APP_ROOT, not process.cwd(): for a
            // packaged app the CWD is wherever the user launched from, so
            // `-m src.mcp.servers` could not resolve.
            //
            // The ELECTRON_* variables that used to be set here were
            // meaningless to a Python child, and ELECTRON_RUN_AS_NODE in an
            // inherited environment turns any Electron binary spawned
            // downstream into unsandboxed Node. DEBUG was hardcoded 'true',
            // so production shipped in debug mode.
            const childEnv = { ...process.env };
            delete childEnv.ELECTRON_RUN_AS_NODE;
            delete childEnv.ELECTRON_NO_ATTACH_CONSOLE;
            delete childEnv.__ELECTRON_ENABLE_LOGGING__;

            this.mcpProcess = spawn(python, ['-m', 'src.mcp.servers'], {
                cwd: APP_ROOT,
                stdio: ['pipe', 'pipe', 'pipe'],
                env: {
                    ...childEnv,
                    ELECTRON_MODE: 'true',
                    PYTHONPATH: [APP_ROOT, path.join(APP_ROOT, 'src')].join(path.delimiter),
                    PYTHONUNBUFFERED: '1',
                    DEBUG: process.env.NODE_ENV === 'development' ? 'true' : 'false'
                }
            });

            // Without an 'error' listener on stdin, writing to a closed pipe
            // after the child dies raises an async EPIPE that crashes the
            // main process.
            this.mcpProcess.stdin.on('error', (error) => {
                console.error('Backend stdin error:', error.message);
                this.isConnected = false;
                this.notifyElectron('mcp-disconnected', { reason: error.message });
            });

            // Handle MCP orchestrator communication
            this.mcpProcess.stdout.on('data', (data) => {
                this.handleMCPOutput(data);
            });

            this.mcpProcess.stderr.on('data', (data) => {
                console.error(`MCP Error: ${data}`);
                this.handleMCPError(data);
            });

            this.mcpProcess.on('close', (code) => {
                console.log(`MCP orchestrator exited with code ${code}`);
                this.isConnected = false;
                this.notifyElectron('mcp-disconnected', { code });
            });

            this.mcpProcess.on('error', (error) => {
                console.error('Failed to start MCP orchestrator:', error);
                this.notifyElectron('mcp-error', { error: error.message });
            });

            // Initialize connection
            await this.initializeMCPConnection();

        } catch (error) {
            // Rethrown, not swallowed. This used to catch its own error and
            // return normally, so main.js's catch was unreachable and a
            // missing Python installation surfaced only as an IPC event that
            // no renderer code subscribed to — completely invisible.
            console.error('Failed to start the analysis backend:', error);
            this.notifyElectron('backend-status', {
                status: 'error',
                message: `Could not start the analysis backend: ${error.message}. `
                       + 'Check that Python 3.10+ is installed and that the '
                       + 'project dependencies are available '
                       + '(conda env create -f environment.yml).'
            });
            throw error;
        }
    }

    /**
     * Handshake with the backend, retrying until it answers.
     *
     * The previous version wrapped the whole handshake in a bare
     * `setTimeout(async () => {...}, 1000)`, so the enclosing
     * `await this.initializeMCPConnection()` resolved immediately — the
     * function returned undefined, not a promise tied to the timer. main.js
     * then logged "initialized successfully" unconditionally while nothing had
     * happened yet, and the 1000ms constant raced the Python side's own 5s
     * startup window. The timer was never stored, so quitting inside that
     * first second fired a handshake at a dead process.
     *
     * @param {{attempts?: number, delayMs?: number}} [options]
     * @returns {Promise<boolean>} Whether the backend answered.
     */
    async initializeMCPConnection(options = {}) {
        const attempts = options.attempts ?? 15;
        const delayMs = options.delayMs ?? 1000;

        for (let attempt = 1; attempt <= attempts; attempt += 1) {
            if (this.stopping) {
                return false;
            }
            if (!this.mcpProcess || this.mcpProcess.exitCode !== null) {
                this.notifyElectron('backend-status', {
                    status: 'error',
                    message: 'The analysis backend exited before it finished starting.'
                });
                return false;
            }

            try {
                await this.sendMCPCommand('initialize', {
                    electron_mode: true,
                    client_info: { name: 'Gliaent Electron', version: '1.0.0' }
                });

                await this.getAvailableServers();
                await this.getSystemStatus();

                this.isConnected = true;
                this.notifyElectron('backend-status', {
                    status: 'connected',
                    message: 'Analysis backend connected.'
                });
                return true;
            } catch (error) {
                if (attempt === attempts) {
                    console.error(
                        `Backend handshake failed after ${attempts} attempts:`,
                        error.message
                    );
                    this.notifyElectron('backend-status', {
                        status: 'error',
                        message: `The analysis backend did not respond: ${error.message}`
                    });
                    return false;
                }
                await new Promise((resolve) => {
                    this.handshakeTimer = setTimeout(resolve, delayMs);
                });
            }
        }
        return false;
    }

    handleMCPOutput(data) {
        const lines = data.toString().split('\n').filter(line => line.trim());
        
        for (const line of lines) {
            try {
                const message = JSON.parse(line);
                this.handleMCPMessage(message);
            } catch (e) {
                // Not JSON. The backend logs its session token on startup;
                // capture it so the renderer can authenticate.
                const tokenMatch = line.match(/GLIAENT_SESSION_TOKEN=(\S+)/);
                if (tokenMatch) {
                    this.sessionToken = tokenMatch[1];
                    console.log('Captured backend session token.');
                    continue;
                }
                console.log(`Backend: ${line}`);
            }
        }
    }

    handleMCPMessage(message) {
        console.log('📨 MCP Message:', message);

        switch (message.type) {
            case 'ready':
                console.log('✅ MCP Server Ready');
                this.isConnected = true;
                this.availableServers = message.available_servers || [];
                this.notifyElectron('mcp-ready', {
                    ...message,
                    servers: this.availableServers
                });
                break;

            case 'bridge_ready':
                console.log('✅ MCP Bridge Ready');
                this.notifyElectron('mcp-ready', message);
                break;

            case 'server_started':
                this.handleServerStarted(message);
                break;

            case 'server_stopped':
                this.handleServerStopped(message);
                break;

            case 'tool_execution_response':
                this.handleToolResponse(message);
                break;

            case 'system_status':
                this.handleSystemStatus(message);
                break;

            case 'error':
                this.handleMCPErrorMessage(message);
                break;

            case 'response':
                this.handleMCPResponse(message);
                break;

            case 'bridge_shutdown':
                console.log('🔄 MCP Bridge shutting down');
                this.isConnected = false;
                this.notifyElectron('mcp-disconnected', { reason: 'bridge_shutdown' });
                break;

            default:
                console.log('Unknown MCP message type:', message.type);
        }
    }

    handleServerStarted(message) {
        const { server_type } = message.payload || message;
        this.serverStatuses[server_type] = 'running';
        
        this.notifyElectron('server-started', {
            server_type,
            timestamp: Date.now()
        });
    }

    handleServerStopped(message) {
        const { server_type } = message.payload || message;
        this.serverStatuses[server_type] = 'stopped';
        
        this.notifyElectron('server-stopped', {
            server_type,
            timestamp: Date.now()
        });
    }

    handleToolResponse(message) {
        this.notifyElectron('tool-response', message);
    }

    handleSystemStatus(message) {
        this.notifyElectron('system-status', message);
    }

    handleMCPErrorMessage(message) {
        console.error('MCP Error Message:', message);
        this.notifyElectron('mcp-error', message);
    }

    handleMCPResponse(message) {
        const { request_id } = message;
        if (request_id && this.requestCallbacks.has(request_id)) {
            const callback = this.requestCallbacks.get(request_id);
            callback(message);
            this.requestCallbacks.delete(request_id);
        }
    }

    handleMCPError(data) {
        const errorMsg = data.toString();
        console.error('MCP Stderr:', errorMsg);
        
        // Check for common Python errors
        if (errorMsg.includes('ModuleNotFoundError')) {
            this.notifyElectron('backend-status', {
                status: 'error',
                message: 'Missing Python dependencies. Please run: conda env create -f environment.yml'
            });
        } else if (errorMsg.includes('ImportError')) {
            this.notifyElectron('backend-status', {
                status: 'error',
                message: 'Python import error. Check MCP server installation.'
            });
        }
    }

    // Public API methods for IPC handlers
    async startServer(serverType, options = {}) {
        try {
            const response = await this.sendMCPCommand('start_server', {
                server_type: serverType,
                options
            });

            return {
                success: true,
                message: `Starting ${serverType} server`,
                data: response
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async stopServer(serverType) {
        try {
            const response = await this.sendMCPCommand('stop_server', {
                server_type: serverType
            });

            return {
                success: true,
                message: `Stopping ${serverType} server`,
                data: response
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async executeTool(serverType, toolName, parameters = {}) {
        try {
            const response = await this.sendMCPCommand('execute_tool', {
                server_type: serverType,
                tool_name: toolName,
                parameters
            });

            return {
                success: true,
                data: response
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }

    async getAvailableServers() {
        try {
            const response = await this.sendMCPCommand('get_available_servers');
            this.availableServers = response.servers || [];
            return this.availableServers;
        } catch (error) {
            console.error('Failed to get available servers:', error);
            return [];
        }
    }

    async getSystemStatus() {
        try {
            const response = await this.sendMCPCommand('get_system_status');
            return response;
        } catch (error) {
            console.error('Failed to get system status:', error);
            return null;
        }
    }

    async getServerStatus(serverType = null) {
        try {
            const response = await this.sendMCPCommand('get_server_status', {
                server_type: serverType
            });
            return response;
        } catch (error) {
            console.error('Failed to get server status:', error);
            return null;
        }
    }

    // Core communication methods
    async sendMCPCommand(command, payload = {}, timeout = 30000) {
        return new Promise((resolve, reject) => {
            if (!this.mcpProcess) {
                reject(new Error('MCP process not running'));
                return;
            }

            const requestId = `req_${++this.requestCounter}_${Date.now()}`;
            
            const message = {
                type: command,
                payload,
                request_id: requestId,
                timestamp: Date.now()
            };

            // Set up response callback
            const timeoutId = setTimeout(() => {
                this.requestCallbacks.delete(requestId);
                reject(new Error(`Request timeout: ${command}`));
            }, timeout);

            this.requestCallbacks.set(requestId, (response) => {
                clearTimeout(timeoutId);
                if (response.success === false) {
                    reject(new Error(response.error || 'MCP command failed'));
                } else {
                    resolve(response.data || response);
                }
            });

            // Send message
            try {
                const messageStr = JSON.stringify(message) + '\n';
                this.mcpProcess.stdin.write(messageStr);
            } catch (error) {
                this.requestCallbacks.delete(requestId);
                clearTimeout(timeoutId);
                reject(error);
            }
        });
    }

    notifyElectron(channel, data) {
        // Emitted as well as sent, so main.js can forward these to the
        // renderer. Previously the renderer subscribed to a channel
        // nothing emitted, so live status never worked.
        this.emit(event, data);
        if (this.mainWindow && !this.mainWindow.isDestroyed()) {
            this.mainWindow.webContents.send(channel, data);
        }
    }

    // Getters for status
    getConnectionStatus() {
        return {
            connected: this.isConnected,
            serverStatuses: this.serverStatuses,
            availableServers: this.availableServers
        };
    }

    /**
     * Stop the analysis backend, waiting until the process has actually exited.
     *
     * The previous implementation leaked the Python process on every quit, for
     * two independent reasons:
     *
     * 1. Its `finally` block set `this.mcpProcess = null` synchronously, right
     *    after scheduling the SIGTERM and SIGKILL timers. Both timers tested
     *    `if (this.mcpProcess && ...)`, which was false by the time they ran,
     *    so nothing was ever killed.
     * 2. It was synchronous, so `before-quit` called `app.exit(0)` on a 3s
     *    timer while the SIGTERM was scheduled for 4s.
     *
     * This version holds a local reference, awaits the real 'exit' event, and
     * escalates on a deadline.
     *
     * @param {{graceMs?: number, killMs?: number}} [options]
     * @returns {Promise<void>} Resolves once the child has exited.
     */
    async stop(options = {}) {
        const graceMs = options.graceMs ?? 2000;
        const killMs = options.killMs ?? 3000;

        if (this.stopping) {
            return;
        }
        this.stopping = true;

        // Local reference: the field is cleared below, but the timers and the
        // exit listener must keep working on the real process.
        const child = this.mcpProcess;
        this.isConnected = false;
        this.requestCallbacks.clear();

        if (!child || child.exitCode !== null || child.signalCode !== null) {
            this.mcpProcess = null;
            this.stopping = false;
            return;
        }

        const exited = new Promise((resolve) => {
            if (child.exitCode !== null || child.signalCode !== null) {
                resolve();
                return;
            }
            child.once('exit', () => resolve());
        });

        try {
            await this.sendMCPCommand('shutdown').catch(() => {
                // A backend that is already gone cannot acknowledge; proceed.
            });
        } catch {
            // Same.
        }

        const escalate = setTimeout(() => {
            if (child.exitCode === null && child.signalCode === null) {
                console.warn('Backend did not exit on request; sending SIGTERM.');
                try { child.kill('SIGTERM'); } catch { /* already gone */ }
            }
        }, graceMs);

        const force = setTimeout(() => {
            if (child.exitCode === null && child.signalCode === null) {
                console.warn('Backend ignored SIGTERM; sending SIGKILL.');
                try { child.kill('SIGKILL'); } catch { /* already gone */ }
            }
        }, graceMs + killMs);

        try {
            await exited;
            console.log('Analysis backend stopped.');
        } finally {
            clearTimeout(escalate);
            clearTimeout(force);
            this.mcpProcess = null;
            this.stopping = false;
        }
    }
}

module.exports = { BackendManager };