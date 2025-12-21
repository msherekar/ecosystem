/**
 * MCP Service - React interface to MCP backend
 * 
 * Provides methods for React components to communicate with
 * the MCP server orchestrator through Electron IPC
 */

interface MCPResponse {
  success: boolean;
  data?: any;
  error?: string;
}

interface ServerStatus {
  [serverType: string]: {
    status: 'running' | 'stopped' | 'error';
    last_activity?: string;
    capabilities?: string[];
  };
}

class MCPServiceClass {
  private ipcRenderer: any = null;
  private initialized = false;

  async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      // Get Electron IPC renderer
      const electron = (window as any).require('electron');
      this.ipcRenderer = electron.ipcRenderer;
      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize MCP service:', error);
      throw error;
    }
  }

  private async invoke(channel: string, ...args: any[]): Promise<MCPResponse> {
    if (!this.initialized) {
      throw new Error('MCP service not initialized');
    }

    try {
      const response = await this.ipcRenderer.invoke(channel, ...args);
      return response;
    } catch (error) {
      console.error(`IPC invoke failed for ${channel}:`, error);
      return { success: false, error: error.message };
    }
  }

  // Server Management
  async startServer(serverType: string, options: any = {}): Promise<MCPResponse> {
    return this.invoke('mcp:start-server', serverType, options);
  }

  async stopServer(serverType: string): Promise<MCPResponse> {
    return this.invoke('mcp:stop-server', serverType);
  }

  async getAvailableServers(): Promise<MCPResponse> {
    return this.invoke('mcp:get-available-servers');
  }

  async getSystemStatus(): Promise<MCPResponse> {
    return this.invoke('mcp:get-system-status');
  }

  async getServerStatus(serverType?: string): Promise<MCPResponse> {
    return this.invoke('mcp:get-server-status', serverType);
  }

  async getConnectionStatus(): Promise<MCPResponse> {
    return this.invoke('mcp:get-connection-status');
  }

  // Tool Execution
  async executeTool(serverType: string, toolName: string, parameters: any = {}): Promise<MCPResponse> {
    return this.invoke('mcp:execute-tool', serverType, toolName, parameters);
  }

  // Bioinformatics-specific methods
  async analyzeRNASeq(parameters: any): Promise<MCPResponse> {
    return this.invoke('mcp:analyze-rnaseq', parameters);
  }

  async analyzeSCRNASeq(parameters: any): Promise<MCPResponse> {
    return this.invoke('mcp:analyze-scrnaseq', parameters);
  }

  async analyzeATACSeq(parameters: any): Promise<MCPResponse> {
    return this.invoke('mcp:analyze-atacseq', parameters);
  }

  async createVisualization(parameters: any): Promise<MCPResponse> {
    return this.invoke('mcp:create-visualization', parameters);
  }

  // Event Listeners (for real-time updates)
  onServerStatusChange(callback: (status: ServerStatus) => void): () => void {
    if (!this.ipcRenderer) return () => {};

    const handler = (event: any, status: ServerStatus) => {
      callback(status);
    };

    this.ipcRenderer.on('server-status-update', handler);
    
    // Return cleanup function
    return () => {
      this.ipcRenderer.removeListener('server-status-update', handler);
    };
  }

  onSystemStatusChange(callback: (status: any) => void): () => void {
    if (!this.ipcRenderer) return () => {};

    const handler = (event: any, status: any) => {
      callback(status);
    };

    this.ipcRenderer.on('system-status', handler);

    return () => {
      this.ipcRenderer.removeListener('system-status', handler);
    };
  }

  onMCPReady(callback: (data: any) => void): () => void {
    if (!this.ipcRenderer) return () => {};

    const handler = (event: any, data: any) => {
      callback(data);
    };

    this.ipcRenderer.on('mcp-ready', handler);

    return () => {
      this.ipcRenderer.removeListener('mcp-ready', handler);
    };
  }
}

export const MCPService = new MCPServiceClass();
