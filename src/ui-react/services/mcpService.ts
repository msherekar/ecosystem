/**
 * MCP Service - React interface to MCP backend
 * 
 * Provides methods for React components to communicate with
 * the MCP server orchestrator through Electron IPC
 */

/**
 * The IPC envelope every main-process handler returns.
 *
 * `data` is the payload. Four handlers in main.js used to return `status` or
 * `servers` instead, so `response.data` was undefined even on success — which
 * is why App.tsx's `if (status.success && status.data)` was false against a
 * perfectly healthy backend and the whole UI showed "disconnected".
 */
export interface MCPResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}

/** The bridge the preload script exposes. */
interface GliaentBridge {
  invoke(channel: string, ...args: unknown[]): Promise<MCPResponse>;
  on(channel: string, listener: (payload: unknown) => void): () => void;
  channels: { invoke: readonly string[]; events: readonly string[] };
  env: { isDev: boolean; platform: string };
}

declare global {
  interface Window {
    gliaent?: GliaentBridge;
  }
}

/** Normalise an unknown thrown value into a message. */
function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'string') return error;
  return String(error);
}

interface ServerStatus {
  [serverType: string]: {
    status: 'running' | 'stopped' | 'error';
    last_activity?: string;
    capabilities?: string[];
  };
}

class MCPServiceClass {
  private bridge: GliaentBridge | null = null;

  /**
   * Connect to the preload bridge.
   *
   * Previously did `(window as any).require('electron')`, which only worked
   * because nodeIntegration was on. With contextIsolation enabled the
   * renderer reaches the main process solely through `window.gliaent`.
   *
   * @throws If the preload script did not run.
   */
  async initialize(): Promise<void> {
    if (this.bridge) return;

    if (!window.gliaent) {
      throw new Error(
        'The Gliaent bridge is unavailable. The preload script did not load; '
        + 'this build cannot talk to the analysis backend.'
      );
    }
    this.bridge = window.gliaent;
  }

  /** Whether the bridge is connected. */
  get ready(): boolean {
    return this.bridge !== null;
  }

  private async invoke<T = unknown>(
    channel: string,
    ...args: unknown[]
  ): Promise<MCPResponse<T>> {
    if (!this.bridge) {
      return {
        success: false,
        error: 'MCP service not initialized. Call initialize() first.',
      };
    }

    try {
      return (await this.bridge.invoke(channel, ...args)) as MCPResponse<T>;
    } catch (error) {
      // `error.message` on an `unknown` catch binding is TS18046 under
      // strict mode; it shipped only because nothing type-checked the build.
      console.error(`IPC invoke failed for ${channel}:`, error);
      return { success: false, error: errorMessage(error) };
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

  /**
   * Subscribe to server start/stop events.
   *
   * This used to listen on 'server-status-update', a channel nothing ever
   * emitted, so live status never arrived. The real channels are
   * 'server-started' and 'server-stopped'.
   *
   * @returns An unsubscribe function.
   */
  onServerStatusChange(callback: (payload: unknown) => void): () => void {
    if (!this.bridge) return () => {};
    const offStarted = this.bridge.on('server-started', callback);
    const offStopped = this.bridge.on('server-stopped', callback);
    return () => {
      offStarted();
      offStopped();
    };
  }

  /** Subscribe to periodic system status. Returns an unsubscribe function. */
  onSystemStatusChange(callback: (status: unknown) => void): () => void {
    if (!this.bridge) return () => {};
    return this.bridge.on('system-status', callback);
  }

  /**
   * Subscribe to backend lifecycle changes.
   *
   * The event a missing Python installation produces. Nothing subscribed to
   * it before, so a backend that failed to start was invisible to the user.
   *
   * @returns An unsubscribe function.
   */
  onBackendStatusChange(
    callback: (payload: { status: string; message?: string }) => void
  ): () => void {
    if (!this.bridge) return () => {};
    const offStatus = this.bridge.on('backend-status', (p) =>
      callback(p as { status: string; message?: string })
    );
    const offError = this.bridge.on('mcp-error', (p) =>
      callback({ status: 'error', message: (p as { error?: string })?.error })
    );
    const offDisconnected = this.bridge.on('mcp-disconnected', () =>
      callback({ status: 'disconnected' })
    );
    return () => {
      offStatus();
      offError();
      offDisconnected();
    };
  }
}

export const MCPService = new MCPServiceClass();
