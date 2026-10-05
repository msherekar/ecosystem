/**
 * Preload script: the only bridge between the renderer and Node.
 *
 * There was no preload script at all. Instead every window ran with
 * `nodeIntegration: true`, `contextIsolation: false`, `webSecurity: false`
 * and `allowRunningInsecureContent: true`, so any script reaching the
 * renderer — including the Plotly bundle that was pulled from a CDN over
 * plain HTTP — had `require('fs')` and `require('child_process')`.
 *
 * This file exposes a fixed, enumerated API over `contextBridge` instead.
 * The renderer can call exactly these channels and nothing else: it cannot
 * reach `ipcRenderer` itself, so it cannot invoke an arbitrary channel.
 */

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Channels the renderer may invoke. An allowlist rather than a passthrough:
 * exposing `invoke` directly would let any injected script call any handler
 * the main process registers.
 */
const INVOKE_CHANNELS = [
  'mcp:start-server',
  'mcp:stop-server',
  'mcp:execute-tool',
  'mcp:get-available-servers',
  'mcp:get-system-status',
  'mcp:get-server-status',
  'mcp:get-connection-status',
  'mcp:analyze-rnaseq',
  'mcp:analyze-scrnaseq',
  'mcp:analyze-atacseq',
  'mcp:create-visualization',
  'dialog:open-file',
  'dialog:open-files',
  'dialog:open-directory',
  'dialog:save-file',
  'file:read',
  'file:save',
  'export:results',
  'modules:list',
  'modules:get-path',
  'app:get-version',
  'app:get-session-token',
];

/**
 * Events the main process may push to the renderer.
 *
 * `server-status-update` is deliberately absent: the renderer subscribed to
 * it, but nothing ever emitted it, so live status never worked. The real
 * channel names are listed here.
 */
const EVENT_CHANNELS = [
  'backend-status',
  'mcp-ready',
  'mcp-disconnected',
  'mcp-error',
  'server-started',
  'server-stopped',
  'tool-response',
  'system-status',
];

contextBridge.exposeInMainWorld('gliaent', {
  /**
   * Invoke a main-process handler.
   *
   * @param {string} channel One of INVOKE_CHANNELS.
   * @param {...unknown} args Arguments forwarded to the handler.
   * @returns {Promise<{success: boolean, data?: unknown, error?: string}>}
   */
  invoke(channel, ...args) {
    if (!INVOKE_CHANNELS.includes(channel)) {
      return Promise.reject(
        new Error(`Channel "${channel}" is not exposed to the renderer.`)
      );
    }
    return ipcRenderer.invoke(channel, ...args);
  },

  /**
   * Subscribe to a main-process event.
   *
   * @param {string} channel One of EVENT_CHANNELS.
   * @param {(payload: unknown) => void} listener
   * @returns {() => void} Unsubscribe function. Returning one matters: the
   *   previous code had no way to detach, so a React effect could not clean
   *   up and listeners accumulated across re-renders.
   */
  on(channel, listener) {
    if (!EVENT_CHANNELS.includes(channel)) {
      throw new Error(`Event channel "${channel}" is not exposed.`);
    }
    // The raw IpcRendererEvent is not forwarded: it carries `sender`, which
    // would hand the renderer a way back into the main process.
    const wrapped = (_event, payload) => listener(payload);
    ipcRenderer.on(channel, wrapped);
    return () => ipcRenderer.removeListener(channel, wrapped);
  },

  /** Channel names, so the renderer can assert against them in dev. */
  channels: Object.freeze({
    invoke: Object.freeze([...INVOKE_CHANNELS]),
    events: Object.freeze([...EVENT_CHANNELS]),
  }),

  /**
   * Build-time environment. `App.tsx` read `process.env.NODE_ENV` in the
   * renderer, which only worked because nodeIntegration leaked Node's
   * `process` in — and would have thrown the moment that was fixed.
   */
  env: Object.freeze({
    isDev: process.env.NODE_ENV === 'development',
    platform: process.platform,
  }),
});
