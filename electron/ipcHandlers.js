// IPC Handlers for File Operations and MCP Integration
const { ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

/** Repo root, resolved from this file rather than the process CWD. */
const APP_ROOT = path.join(__dirname, '..');

/**
 * Resolve a user-supplied path and confirm it stays inside `root`.
 *
 * Several handlers joined renderer-supplied names straight into a path with
 * no checks: `get-module-path`, `list-example-files` and `get-server-config`
 * all accepted `'../../../../etc/passwd'`, and the last of those read the
 * file and returned its contents.
 *
 * @param {string} root Directory the result must stay within.
 * @param {string} candidate Untrusted path fragment.
 * @returns {string|null} The resolved path, or null if it escapes.
 */
function containedPath(root, candidate) {
    if (typeof candidate !== 'string' || candidate.length === 0) {
        return null;
    }
    const resolvedRoot = path.resolve(root);
    const resolved = path.resolve(resolvedRoot, candidate);
    const prefix = resolvedRoot.endsWith(path.sep)
        ? resolvedRoot
        : resolvedRoot + path.sep;
    if (resolved !== resolvedRoot && !resolved.startsWith(prefix)) {
        return null;
    }
    return resolved;
}

/**
 * Whether a name is a bare identifier-like segment.
 *
 * Checked in addition to containedPath, so a traversal needs two independent
 * failures rather than one.
 *
 * @param {string} name
 * @returns {boolean}
 */
function isSafeSegment(name) {
    return typeof name === 'string' && /^[A-Za-z0-9_.-]{1,128}$/.test(name)
        && !name.includes('..');
}


class IPCHandlers {
    /**
     * Register every handler.
     *
     * @param {import('./backendManager').BackendManager} [backendManager]
     *   Required by the routing handlers. Without it they report that the
     *   backend is unavailable — which is what they did unconditionally
     *   before, because they looked it up through a non-existent Electron API.
     */
    static setupAll(backendManager) {
        this.setupFileHandlers();
        this.setupDataHandlers();
        this.setupModuleHandlers();
        this.setupMCPRoutingHandlers(backendManager);
    }

    static setupFileHandlers() {
        ipcMain.handle('open-file', async (event) => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            const result = await dialog.showOpenDialog(mainWindow, {
                properties: ['openFile'],
                filters: [
                    { name: 'Python Files', extensions: ['py'] },
                    { name: 'Jupyter Notebooks', extensions: ['ipynb'] },
                    { name: 'R Scripts', extensions: ['R', 'r'] },
                    { name: 'Configuration Files', extensions: ['yaml', 'yml', 'json', 'toml'] },
                    { name: 'All Files', extensions: ['*'] }
                ]
            });
            
            if (!result.canceled && result.filePaths.length > 0) {
                const filePath = result.filePaths[0];
                const content = fs.readFileSync(filePath, 'utf8');
                return { 
                    success: true,
                    path: filePath, 
                    content,
                    name: path.basename(filePath),
                    extension: path.extname(filePath)
                };
            }
            return { success: false, error: 'No file selected' };
        });

        ipcMain.handle('save-file', async (event, filePath, content) => {
            try {
                // Ensure directory exists
                const dir = path.dirname(filePath);
                if (!fs.existsSync(dir)) {
                    fs.mkdirSync(dir, { recursive: true });
                }
                
                fs.writeFileSync(filePath, content, 'utf8');
                return { success: true, path: filePath };
            } catch (error) {
                console.error('Save error:', error);
                return { success: false, error: error.message };
            }
        });

        ipcMain.handle('save-file-as', async (event, content, defaultName = 'untitled') => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            const result = await dialog.showSaveDialog(mainWindow, {
                defaultPath: defaultName,
                filters: [
                    { name: 'Python Files', extensions: ['py'] },
                    { name: 'Jupyter Notebooks', extensions: ['ipynb'] },
                    { name: 'R Scripts', extensions: ['R'] },
                    { name: 'CSV Files', extensions: ['csv'] },
                    { name: 'JSON Files', extensions: ['json'] },
                    { name: 'All Files', extensions: ['*'] }
                ]
            });
            
            if (!result.canceled) {
                try {
                    fs.writeFileSync(result.filePath, content, 'utf8');
                    return { success: true, path: result.filePath };
                } catch (error) {
                    console.error('Save error:', error);
                    return { success: false, error: error.message };
                }
            }
            return { success: false, error: 'Save cancelled' };
        });

        // Export results handler
        ipcMain.handle('export-results', async (event, data, format = 'json') => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            const filters = {
                'json': { name: 'JSON Files', extensions: ['json'] },
                'csv': { name: 'CSV Files', extensions: ['csv'] },
                'xlsx': { name: 'Excel Files', extensions: ['xlsx'] },
                'pdf': { name: 'PDF Files', extensions: ['pdf'] },
                'png': { name: 'PNG Images', extensions: ['png'] },
                'svg': { name: 'SVG Images', extensions: ['svg'] }
            };

            const result = await dialog.showSaveDialog(mainWindow, {
                defaultPath: `analysis_results.${format}`,
                filters: [filters[format] || filters['json']]
            });

            if (!result.canceled) {
                try {
                    let content;
                    if (format === 'json') {
                        content = JSON.stringify(data, null, 2);
                    } else if (format === 'csv') {
                        // Simple CSV conversion - would need proper CSV library for complex data
                        content = typeof data === 'string' ? data : JSON.stringify(data);
                    } else {
                        content = typeof data === 'string' ? data : JSON.stringify(data);
                    }

                    fs.writeFileSync(result.filePath, content, 'utf8');
                    return { success: true, path: result.filePath };
                } catch (error) {
                    return { success: false, error: error.message };
                }
            }
            return { success: false, error: 'Export cancelled' };
        });
    }

    static setupDataHandlers() {
        ipcMain.handle('open-data-file', async (event, fileTypes = 'all') => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            // Define filter sets based on analysis type
            const filterSets = {
                'rnaseq': [
                    { name: 'Count Matrices', extensions: ['csv', 'tsv', 'txt'] },
                    { name: 'Excel Files', extensions: ['xlsx', 'xls'] },
                    { name: 'HDF5 Files', extensions: ['h5', 'hdf5'] }
                ],
                'scrnaseq': [
                    { name: 'AnnData Files', extensions: ['h5ad'] },
                    { name: '10X Files', extensions: ['h5', 'mtx', 'gz'] },
                    { name: 'CSV/TSV Files', extensions: ['csv', 'tsv', 'txt'] },
                    { name: 'Loom Files', extensions: ['loom'] }
                ],
                'atacseq': [
                    { name: 'Peak Files', extensions: ['bed', 'narrowPeak', 'broadPeak'] },
                    { name: 'BAM Files', extensions: ['bam', 'sam'] },
                    { name: 'BigWig Files', extensions: ['bw', 'bigwig'] },
                    { name: 'Matrix Files', extensions: ['csv', 'tsv', 'mtx'] }
                ],
                'proteomics': [
                    { name: 'Mass Spec Files', extensions: ['mzML', 'mzXML', 'raw'] },
                    { name: 'Protein Tables', extensions: ['csv', 'tsv', 'xlsx'] },
                    { name: 'FASTA Files', extensions: ['fasta', 'fa', 'fas'] }
                ],
                'all': [
                    { name: 'scRNA-seq Files', extensions: ['h5ad', 'h5', 'hdf5', 'loom'] },
                    { name: 'Count Matrices', extensions: ['csv', 'tsv', 'txt', 'mtx'] },
                    { name: 'Excel Files', extensions: ['xlsx', 'xls'] },
                    { name: '10X Files', extensions: ['gz', 'h5'] },
                    { name: 'Genomics Files', extensions: ['bed', 'bam', 'sam', 'bw', 'bigwig'] },
                    { name: 'Sequence Files', extensions: ['fasta', 'fa', 'fastq', 'fq'] },
                    { name: 'All Files', extensions: ['*'] }
                ]
            };
            
            const filters = filterSets[fileTypes] || filterSets['all'];
            
            const result = await dialog.showOpenDialog(mainWindow, {
                properties: ['openFile', 'multiSelections'],
                filters: filters
            });
            
            if (!result.canceled && result.filePaths.length > 0) {
                const files = result.filePaths.map(filePath => ({
                    path: filePath,
                    name: path.basename(filePath),
                    size: fs.statSync(filePath).size,
                    extension: path.extname(filePath),
                    directory: path.dirname(filePath)
                }));
                
                return { success: true, files };
            }
            return { success: false, error: 'No files selected' };
        });

        ipcMain.handle('select-directory', async (event) => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            const result = await dialog.showOpenDialog(mainWindow, {
                properties: ['openDirectory']
            });
            
            if (!result.canceled && result.filePaths.length > 0) {
                const dirPath = result.filePaths[0];
                return { 
                    success: true, 
                    path: dirPath,
                    name: path.basename(dirPath)
                };
            }
            return { success: false, error: 'No directory selected' };
        });

        // Batch file operations
        ipcMain.handle('select-multiple-files', async (event, options = {}) => {
            const { BrowserWindow } = require('electron');
            const mainWindow = BrowserWindow.getFocusedWindow();
            
            const result = await dialog.showOpenDialog(mainWindow, {
                properties: ['openFile', 'multiSelections'],
                filters: options.filters || [
                    { name: 'All Bioinformatics Files', extensions: ['h5ad', 'csv', 'tsv', 'xlsx', 'h5', 'bed', 'bam'] },
                    { name: 'All Files', extensions: ['*'] }
                ]
            });
            
            if (!result.canceled && result.filePaths.length > 0) {
                return {
                    success: true,
                    files: result.filePaths.map(fp => ({
                        path: fp,
                        name: path.basename(fp),
                        extension: path.extname(fp)
                    }))
                };
            }
            return { success: false, error: 'No files selected' };
        });
    }

    static setupModuleHandlers() {
        ipcMain.handle('get-module-path', async (event, moduleName) => {
            if (!isSafeSegment(moduleName)) {
                return { success: false, error: 'Invalid module name.' };
            }
            const roots = [
                path.join(APP_ROOT, 'src', 'modules'),
                path.join(APP_ROOT, 'src', 'mcp', 'servers')
            ];
            const candidates = [
                [roots[0], moduleName],
                [roots[1], `${moduleName}_server.py`],
                [roots[1], moduleName]
            ];

            for (const [root, name] of candidates) {
                const resolved = containedPath(root, name);
                if (resolved && fs.existsSync(resolved)) {
                    // Repo-relative, so the server's directory layout is not
                    // handed to the renderer.
                    return { success: true, path: path.relative(APP_ROOT, resolved) };
                }
            }

            return { success: false, error: `Module ${moduleName} not found` };
        });

        ipcMain.handle('list-example-files', async (event, moduleName) => {
            if (!isSafeSegment(moduleName)) {
                return { success: false, error: 'Invalid module name.' };
            }
            const examplesPath = containedPath(
                path.join(APP_ROOT, 'examples'),
                moduleName
            );
            if (examplesPath && fs.existsSync(examplesPath)) {
                try {
                    const files = fs.readdirSync(examplesPath);
                    const filteredFiles = files.filter(file => 
                        file.endsWith('.py') || 
                        file.endsWith('.ipynb') ||
                        file.endsWith('.R') ||
                        file.endsWith('.md')
                    );
                    return { success: true, files: filteredFiles };
                } catch (error) {
                    console.error('Error listing examples:', error);
                    return { success: false, error: error.message };
                }
            }
            return { success: false, error: 'Examples directory not found' };
        });

        // List available MCP servers
        ipcMain.handle('list-mcp-servers', async (event) => {
            try {
                const mcpServersPath = path.join(APP_ROOT, 'src', 'mcp', 'servers');
                if (!fs.existsSync(mcpServersPath)) {
                    return { success: false, error: 'MCP servers directory not found' };
                }

                const files = fs.readdirSync(mcpServersPath);
                const serverFiles = files.filter(file => 
                    file.endsWith('_server.py') && 
                    !file.startsWith('__')
                );

                const servers = serverFiles.map(file => {
                    const serverName = file.replace('_server.py', '');
                    return {
                        name: serverName,
                        file: file,
                        path: path.join(mcpServersPath, file)
                    };
                });

                return { success: true, servers };
            } catch (error) {
                return { success: false, error: error.message };
            }
        });

        // Get server configuration
        ipcMain.handle('get-server-config', async (event, serverName) => {
            if (!isSafeSegment(serverName)) {
                return { success: false, error: 'Invalid server name.' };
            }
            try {
                const configPath = containedPath(
                    path.join(APP_ROOT, 'config'),
                    `${serverName}_config.yaml`
                );
                if (configPath && fs.existsSync(configPath)) {
                    const content = fs.readFileSync(configPath, 'utf8');
                    return { success: true, config: content };
                }
                return { success: false, error: 'Configuration file not found' };
            } catch (error) {
                return { success: false, error: error.message };
            }
        });
    }

    /**
     * Routing handlers.
     *
     * These three previously did:
     *   const mainWindow = app.getMainWindow ? app.getMainWindow() : null;
     * `app.getMainWindow` is not an Electron API, so `mainWindow` was always
     * null — and a BrowserWindow has no `.backendManager` property in any
     * case, since nothing assigns one. All three returned
     * {success:false, error:'MCP backend not available'} unconditionally.
     *
     * The backend manager is now injected explicitly.
     *
     * @param {import('./backendManager').BackendManager} backendManager
     */
    static setupMCPRoutingHandlers(backendManager) {
        
        ipcMain.handle('routing:analyze-context', async (event, data) => {
            try {
                // Forward to MCP system via main process
                if (backendManager) {
                    const result = await backendManager.executeTool(
                        'search', // Use search server for context analysis
                        'analyze_context',
                        {
                            query: data.query,
                            session_id: data.sessionId,
                            user_id: data.userId || 'anonymous'
                        }
                    );
                    return result;
                }
                
                return { success: false, error: 'MCP backend not available' };
            } catch (error) {
                console.error('MCP context analysis error:', error);
                return { success: false, error: error.message };
            }
        });

        ipcMain.handle('routing:predict-workflow', async (event, data) => {
            try {
                if (backendManager) {
                    const result = await backendManager.executeTool(
                        'search',
                        'predict_workflow',
                        {
                            context: data.context,
                            session_id: data.sessionId
                        }
                    );
                    return result;
                }
                
                return { success: false, error: 'MCP backend not available' };
            } catch (error) {
                console.error('MCP workflow prediction error:', error);
                return { success: false, error: error.message };
            }
        });

        ipcMain.handle('routing:get-tool-recommendations', async (event, data) => {
            try {
                if (backendManager) {
                    const result = await backendManager.executeTool(
                        'search',
                        'get_tool_recommendations',
                        { context: data.context }
                    );
                    return result;
                }
                
                return { success: false, error: 'MCP backend not available' };
            } catch (error) {
                console.error('Tool recommendations error:', error);
                return { success: false, error: error.message };
            }
        });

        // Simplified handlers that don't require external FastAPI server
        ipcMain.handle('routing:analyze-files', async (event, data) => {
            try {
                // Simple file analysis without external server
                const analysis = {
                    file_count: data.files ? data.files.length : 0,
                    file_types: data.files ? data.files.map(f => path.extname(f)).filter((v, i, a) => a.indexOf(v) === i) : [],
                    suggested_analysis: 'general',
                    timestamp: new Date().toISOString()
                };

                // Basic analysis type detection
                if (data.files) {
                    const extensions = data.files.map(f => path.extname(f).toLowerCase());
                    
                    if (extensions.includes('.h5ad') || extensions.includes('.loom')) {
                        analysis.suggested_analysis = 'scrnaseq';
                    } else if (extensions.includes('.bed') || extensions.includes('.bam')) {
                        analysis.suggested_analysis = 'atacseq';
                    } else if (extensions.some(ext => ['.csv', '.tsv', '.xlsx'].includes(ext))) {
                        analysis.suggested_analysis = 'rnaseq';
                    }
                }

                return { success: true, data: analysis };
            } catch (error) {
                return { success: false, error: error.message };
            }
        });

        console.log('✅ MCP-integrated IPC handlers registered');
    }
}

module.exports = { IPCHandlers };