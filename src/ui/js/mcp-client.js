// MCP Client for Gliaent Electron Integration
console.log('🔗 MCP Client Loading...');

// MCP Client Class
class MCPClient {
    constructor() {
        this.connected = false;
        this.servers = [];
        this.eventHandlers = {};
        this.requestId = 0;
        this.pendingRequests = new Map();
        
        // Initialize if running in Electron
        if (window.require) {
            this.initializeElectron();
        }
    }
    
    initializeElectron() {
        try {
            const { ipcRenderer } = window.require('electron');
            this.ipc = ipcRenderer;
            this.setupElectronHandlers();
            console.log('✅ Electron IPC initialized');
        } catch (error) {
            console.warn('⚠️ Not running in Electron environment:', error);
            this.ipc = null;
        }
    }
    
    setupElectronHandlers() {
        if (!this.ipc) return;
        
        // Handle MCP events from main process
        this.ipc.on('mcp-ready', (event, data) => {
            console.log('📡 MCP Ready:', data);
            this.connected = true;
            this.servers = data.available_servers || [];
            this.emit('connected', data);
        });
        
        this.ipc.on('mcp-error', (event, error) => {
            console.error('❌ MCP Error:', error);
            this.emit('error', error);
        });
        
        this.ipc.on('mcp-disconnected', (event) => {
            console.warn('📡 MCP Disconnected');
            this.connected = false;
            this.emit('disconnected');
        });
        
        this.ipc.on('server-status', (event, data) => {
            console.log('📊 Server Status:', data);
            this.emit('server-status', data);
        });
    }
    
    async connect() {
        console.log('🔗 Connecting to MCP backend...');
        
        if (!this.ipc) {
            // Simulate connection for non-Electron environments
            return this.simulateConnection();
        }
        
        try {
            // Initialize MCP system
            const result = await this.ipc.invoke('mcp:get-system-status');
            if (result.success) {
                this.connected = true;
                this.servers = result.status.available_servers || [];
                console.log('✅ MCP connection established');
                return { success: true, servers: this.servers };
            } else {
                throw new Error(result.error || 'Failed to connect');
            }
        } catch (error) {
            console.error('❌ MCP connection failed:', error);
            throw error;
        }
    }
    
    async simulateConnection() {
        console.log('🔄 Simulating MCP connection...');
        
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        this.connected = true;
        this.servers = [
            'rnaseq', 'scrnaseq', 'atacseq', 
            'proteomics', 'data', 'visualization', 'search'
        ];
        
        console.log('✅ Simulated MCP connection established');
        return { success: true, servers: this.servers };
    }
    
    async getAvailableServers() {
        if (!this.ipc) {
            return this.servers;
        }
        
        try {
            const result = await this.ipc.invoke('mcp:get-available-servers');
            if (result.success) {
                this.servers = result.servers;
                return result.servers;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Failed to get available servers:', error);
            return this.servers; // Return cached servers
        }
    }
    
    async getSystemStatus() {
        if (!this.ipc) {
            return this.getSimulatedStatus();
        }
        
        try {
            const result = await this.ipc.invoke('mcp:get-system-status');
            if (result.success) {
                return result.status;
            } else {
                throw new Error(result.error);
            }
        } catch (error) {
            console.error('Failed to get system status:', error);
            return this.getSimulatedStatus();
        }
    }
    
    getSimulatedStatus() {
        return {
            orchestrator_running: true,
            active_servers_count: this.servers.length,
            active_servers: this.servers,
            available_servers: this.servers,
            system_health: {
                status: 'healthy',
                timestamp: new Date().toISOString()
            }
        };
    }
    
    async startServer(serverType, options = {}) {
        console.log(`🚀 Starting server: ${serverType}`);
        
        if (!this.ipc) {
            // Simulate server start
            await new Promise(resolve => setTimeout(resolve, 500));
            return { success: true, message: `${serverType} server started (simulated)` };
        }
        
        try {
            const result = await this.ipc.invoke('mcp:start-server', serverType, options);
            if (result.success) {
                console.log(`✅ Server started: ${serverType}`);
            } else {
                console.error(`❌ Failed to start server ${serverType}:`, result.error);
            }
            return result;
        } catch (error) {
            console.error(`❌ Error starting server ${serverType}:`, error);
            return { success: false, error: error.message };
        }
    }
    
    async stopServer(serverType) {
        console.log(`🛑 Stopping server: ${serverType}`);
        
        if (!this.ipc) {
            // Simulate server stop
            await new Promise(resolve => setTimeout(resolve, 500));
            return { success: true, message: `${serverType} server stopped (simulated)` };
        }
        
        try {
            const result = await this.ipc.invoke('mcp:stop-server', serverType);
            if (result.success) {
                console.log(`✅ Server stopped: ${serverType}`);
            } else {
                console.error(`❌ Failed to stop server ${serverType}:`, result.error);
            }
            return result;
        } catch (error) {
            console.error(`❌ Error stopping server ${serverType}:`, error);
            return { success: false, error: error.message };
        }
    }
    
    async executeTool(serverType, toolName, parameters = {}) {
        console.log(`🔧 Executing tool: ${serverType}.${toolName}`);
        
        if (!this.ipc) {
            // Simulate tool execution
            await new Promise(resolve => setTimeout(resolve, 1000));
            return { 
                success: true, 
                result: `Simulated result for ${toolName}`,
                parameters: parameters
            };
        }
        
        try {
            const result = await this.ipc.invoke('mcp:execute-tool', serverType, toolName, parameters);
            if (result.success) {
                console.log(`✅ Tool executed: ${serverType}.${toolName}`);
            } else {
                console.error(`❌ Tool execution failed: ${serverType}.${toolName}`, result.error);
            }
            return result;
        } catch (error) {
            console.error(`❌ Error executing tool ${serverType}.${toolName}:`, error);
            return { success: false, error: error.message };
        }
    }
    
    // Event handling
    on(event, handler) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(handler);
    }
    
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }
    
    emit(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    // Utility methods
    isConnected() {
        return this.connected;
    }
    
    getServers() {
        return [...this.servers];
    }
}

// Create global MCP client instance
window.MCPClient = new MCPClient();

// Setup global event handlers
window.MCPClient.on('connected', (data) => {
    console.log('🎉 MCP Client Connected:', data);
    if (window.updateConnectionStatus) {
        window.updateConnectionStatus('connected');
    }
    if (window.GliaentApp && window.GliaentApp.updateServerDisplay) {
        const servers = (data.available_servers || []).map(name => ({
            name: name.toUpperCase(),
            type: name,
            status: 'ready'
        }));
        window.GliaentApp.updateServerDisplay(servers);
    }
});

window.MCPClient.on('disconnected', () => {
    console.log('📡 MCP Client Disconnected');
    if (window.updateConnectionStatus) {
        window.updateConnectionStatus('disconnected');
    }
});

window.MCPClient.on('error', (error) => {
    console.error('❌ MCP Client Error:', error);
    if (window.updateConnectionStatus) {
        window.updateConnectionStatus('disconnected');
    }
});

console.log('✅ MCP Client loaded and ready'); 