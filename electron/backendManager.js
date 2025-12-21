// MCP Backend Management - Integrated with MCP Server Orchestrator
const { spawn } = require('child_process');
const path = require('path');

class BackendManager {
    constructor() {
        this.mcpProcess = null;
        this.isConnected = false;
        this.messageQueue = [];
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
            this.mcpProcess = spawn('python', ['-m', 'src.mcp.servers'], {
                cwd: process.cwd(),
                stdio: ['pipe', 'pipe', 'pipe'],
                env: {
                    ...process.env,
                    ELECTRON_MODE: 'true',  // Tell MCP it's running in Electron
                    ELECTRON_RUN_AS_NODE: '1',  // Standard Electron environment variable
                    ELECTRON_NO_ATTACH_CONSOLE: '1',  // Standard Electron environment variable
                    __ELECTRON_ENABLE_LOGGING__: '1',  // Standard Electron environment variable
                    PYTHONPATH: process.cwd(),
                    DEBUG: 'true'
                }
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
            console.error('Failed to start MCP orchestrator:', error);
            this.notifyElectron('backend-status', {
                status: 'error',
                message: 'Failed to start MCP orchestrator. Check Python installation and dependencies.'
            });
        }
    }

    async initializeMCPConnection() {
        // Wait a brief moment for MCP to start
        setTimeout(async () => {
            try {
                // Send initial handshake
                await this.sendMCPCommand('initialize', {
                    electron_mode: true,
                    client_info: {
                        name: 'Gliaent Electron',
                        version: '1.0.0'
                    }
                });

                // Get available servers
                await this.getAvailableServers();

                // Get system status
                await this.getSystemStatus();

                this.isConnected = true;
                this.notifyElectron('backend-status', {
                    status: 'connected',
                    message: 'MCP Server Orchestrator connected successfully'
                });

            } catch (error) {
                console.error('MCP initialization failed:', error);
            }
        }, 1000);  // Give Python server time to fully initialize
    }

    handleMCPOutput(data) {
        const lines = data.toString().split('\n').filter(line => line.trim());
        
        for (const line of lines) {
            try {
                const message = JSON.parse(line);
                this.handleMCPMessage(message);
            } catch (e) {
                // Not JSON, treat as regular output
                console.log(`MCP Output: ${line}`);
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
                message: 'Missing Python dependencies. Please run: pip install -r requirements.txt'
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

    stop() {
        console.log('🛑 Stopping MCP Backend Manager...');
        
        if (this.mcpProcess) {
            try {
                // Send shutdown command first
                this.sendMCPCommand('shutdown').catch(() => {
                    // Ignore errors during shutdown
                });

                // Give it a moment to shutdown gracefully
                setTimeout(() => {
                    if (this.mcpProcess && !this.mcpProcess.killed) {
                        this.mcpProcess.kill('SIGTERM');
                        
                        // Force kill if still running after 5 seconds
                        setTimeout(() => {
                            if (this.mcpProcess && !this.mcpProcess.killed) {
                                this.mcpProcess.kill('SIGKILL');
                            }
                        }, 5000);
                    }
                }, 1000);

            } catch (error) {
                console.error('Error stopping MCP process:', error);
            } finally {
                this.mcpProcess = null;
                this.isConnected = false;
            }
        }

        // Clear all pending callbacks
        this.requestCallbacks.clear();
    }
}

module.exports = { BackendManager };