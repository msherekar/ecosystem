// UI Components for Gliaent Interface
console.log('🎨 UI Components Loading...');

// Loading overlay management
class LoadingOverlay {
    constructor() {
        this.overlay = document.getElementById('loading-overlay');
        this.message = document.getElementById('loading-message');
        this.isVisible = false;
    }
    
    show(message = 'Loading...') {
        if (this.overlay) {
            this.overlay.style.display = 'flex';
            this.isVisible = true;
            
            if (this.message) {
                this.message.textContent = message;
            }
        }
    }
    
    hide() {
        if (this.overlay) {
            this.overlay.style.display = 'none';
            this.isVisible = false;
        }
    }
    
    updateMessage(message) {
        if (this.message) {
            this.message.textContent = message;
        }
    }
}

// File upload component
class FileUploadHandler {
    constructor() {
        this.setupFileInputs();
        this.setupDragAndDrop();
    }
    
    setupFileInputs() {
        const fileInputAreas = document.querySelectorAll('.file-input-area');
        fileInputAreas.forEach(area => {
            area.addEventListener('click', () => {
                this.openFileDialog(area);
            });
        });
    }
    
    setupDragAndDrop() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });
        
        // Handle file drops
        document.addEventListener('drop', (e) => {
            this.handleDrop(e);
        }, false);
        
        // Visual feedback for drag operations
        document.addEventListener('dragenter', (e) => {
            document.body.classList.add('drag-over');
        });
        
        document.addEventListener('dragleave', (e) => {
            if (e.clientX === 0 && e.clientY === 0) {
                document.body.classList.remove('drag-over');
            }
        });
        
        document.addEventListener('drop', (e) => {
            document.body.classList.remove('drag-over');
        });
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    openFileDialog(area) {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = '.csv,.tsv,.txt,.xlsx,.h5,.h5ad,.rds,.bed,.bam,.fastq,.fasta';
        
        input.onchange = (e) => {
            this.handleFiles(e.target.files, area);
        };
        
        input.click();
    }
    
    handleDrop(e) {
        const files = e.dataTransfer.files;
        const targetArea = e.target.closest('.file-input-area') || 
                          document.querySelector('.file-input-area');
        
        if (files.length > 0) {
            this.handleFiles(files, targetArea);
        }
    }
    
    handleFiles(files, targetArea) {
        console.log(`📁 Files selected: ${files.length}`);
        
        // Update UI to show selected files
        if (targetArea) {
            const fileList = Array.from(files).map(file => 
                `<div class="file-item">${file.name} (${this.formatFileSize(file.size)})</div>`
            ).join('');
            
            targetArea.innerHTML = `
                <div class="files-selected">
                    <h4>Selected Files:</h4>
                    ${fileList}
                    <button class="btn-secondary" onclick="window.UIComponents.clearFiles(this)">Clear</button>
                </div>
            `;
        }
        
        // Store files for processing
        this.selectedFiles = Array.from(files);
        
        // Emit file selection event
        if (window.GliaentApp) {
            window.GliaentApp.emit && window.GliaentApp.emit('files-selected', {
                files: this.selectedFiles,
                area: targetArea
            });
        }
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    clearFiles(button) {
        const targetArea = button.closest('.file-input-area');
        if (targetArea) {
            targetArea.innerHTML = '<p>Drag & drop files or click to select</p>';
        }
        this.selectedFiles = [];
    }
}

// Analysis parameter form handler
class ParameterFormHandler {
    constructor() {
        this.forms = new Map();
        this.setupParameterForms();
    }
    
    setupParameterForms() {
        const parameterForms = document.querySelectorAll('.parameters-form');
        parameterForms.forEach(form => {
            const analysisType = this.getAnalysisType(form);
            this.createParameterForm(form, analysisType);
        });
    }
    
    getAnalysisType(form) {
        const screen = form.closest('.screen');
        if (screen) {
            return screen.id.replace('-screen', '');
        }
        return 'default';
    }
    
    createParameterForm(container, analysisType) {
        const parameters = this.getDefaultParameters(analysisType);
        
        let formHTML = '<div class="parameter-form">';
        parameters.forEach(param => {
            formHTML += this.createParameterInput(param);
        });
        formHTML += '<button class="btn-primary" onclick="window.UIComponents.runAnalysis(\'' + analysisType + '\')">Run Analysis</button>';
        formHTML += '</div>';
        
        container.innerHTML = formHTML;
        this.forms.set(analysisType, container);
    }
    
    createParameterInput(param) {
        switch(param.type) {
            case 'number':
                return `
                    <div class="parameter-input">
                        <label>${param.label}</label>
                        <input type="number" name="${param.name}" value="${param.default || ''}" 
                               min="${param.min || ''}" max="${param.max || ''}" step="${param.step || ''}">
                        <small>${param.description || ''}</small>
                    </div>
                `;
            case 'select':
                const options = param.options.map(opt => 
                    `<option value="${opt.value}" ${opt.selected ? 'selected' : ''}>${opt.label}</option>`
                ).join('');
                return `
                    <div class="parameter-input">
                        <label>${param.label}</label>
                        <select name="${param.name}">
                            ${options}
                        </select>
                        <small>${param.description || ''}</small>
                    </div>
                `;
            case 'checkbox':
                return `
                    <div class="parameter-input">
                        <label>
                            <input type="checkbox" name="${param.name}" ${param.default ? 'checked' : ''}>
                            ${param.label}
                        </label>
                        <small>${param.description || ''}</small>
                    </div>
                `;
            default:
                return `
                    <div class="parameter-input">
                        <label>${param.label}</label>
                        <input type="text" name="${param.name}" value="${param.default || ''}" 
                               placeholder="${param.placeholder || ''}">
                        <small>${param.description || ''}</small>
                    </div>
                `;
        }
    }
    
    getDefaultParameters(analysisType) {
        const parameterSets = {
            'rnaseq': [
                { name: 'fdr_threshold', label: 'FDR Threshold', type: 'number', default: 0.05, min: 0, max: 1, step: 0.01, description: 'False Discovery Rate threshold' },
                { name: 'log2fc_threshold', label: 'Log2FC Threshold', type: 'number', default: 1, min: 0, max: 10, step: 0.1, description: 'Log2 fold change threshold' },
                { name: 'normalization', label: 'Normalization Method', type: 'select', 
                  options: [
                      { value: 'deseq2', label: 'DESeq2', selected: true },
                      { value: 'edger', label: 'EdgeR' },
                      { value: 'limma', label: 'Limma-Voom' }
                  ]
                }
            ],
            'scrnaseq': [
                { name: 'min_genes', label: 'Min Genes per Cell', type: 'number', default: 200, min: 0, description: 'Minimum number of genes per cell' },
                { name: 'min_cells', label: 'Min Cells per Gene', type: 'number', default: 3, min: 0, description: 'Minimum number of cells per gene' },
                { name: 'mt_threshold', label: 'MT Gene Threshold', type: 'number', default: 20, min: 0, max: 100, description: 'Mitochondrial gene percentage threshold' },
                { name: 'resolution', label: 'Clustering Resolution', type: 'number', default: 0.5, min: 0.1, max: 2, step: 0.1, description: 'Resolution for clustering' }
            ],
            'atacseq': [
                { name: 'peak_calling', label: 'Peak Calling Method', type: 'select',
                  options: [
                      { value: 'macs2', label: 'MACS2', selected: true },
                      { value: 'genrich', label: 'Genrich' }
                  ]
                },
                { name: 'fdr_threshold', label: 'FDR Threshold', type: 'number', default: 0.05, min: 0, max: 1, step: 0.01, description: 'False Discovery Rate for peaks' }
            ],
            'proteomics': [
                { name: 'normalization', label: 'Normalization Method', type: 'select',
                  options: [
                      { value: 'median', label: 'Median Normalization', selected: true },
                      { value: 'quantile', label: 'Quantile Normalization' },
                      { value: 'log2', label: 'Log2 Transformation' }
                  ]
                },
                { name: 'pvalue_threshold', label: 'P-value Threshold', type: 'number', default: 0.05, min: 0, max: 1, step: 0.01, description: 'P-value threshold for significance' },
                { name: 'fold_change', label: 'Fold Change Threshold', type: 'number', default: 1.5, min: 1, max: 10, step: 0.1, description: 'Minimum fold change threshold' }
            ]
        };
        
        return parameterSets[analysisType] || [
            { name: 'parameter1', label: 'Parameter 1', type: 'text', placeholder: 'Enter value' }
        ];
    }
    
    runAnalysis(analysisType) {
        console.log(`🔬 Running ${analysisType} analysis`);
        
        const form = this.forms.get(analysisType);
        if (!form) {
            console.error(`Form not found for analysis type: ${analysisType}`);
            return;
        }
        
        // Collect form data manually from input elements
        const parameterForm = form.querySelector('.parameter-form');
        if (!parameterForm) {
            console.error(`Parameter form not found for analysis type: ${analysisType}`);
            return;
        }
        
        const parameters = {};
        const inputs = parameterForm.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (input.name) {
                if (input.type === 'checkbox') {
                    parameters[input.name] = input.checked;
                } else if (input.type === 'number') {
                    parameters[input.name] = parseFloat(input.value) || 0;
                } else {
                    parameters[input.name] = input.value;
                }
            }
        });
        
        console.log('Analysis parameters:', parameters);
        
        // Show loading
        window.UIComponents.loading.show(`Running ${analysisType} analysis...`);
        
        // Execute analysis via MCP
        if (window.MCPClient) {
            window.MCPClient.executeTool(analysisType, 'run_analysis', parameters)
                .then(result => {
                    console.log('Analysis result:', result);
                    window.UIComponents.loading.hide();
                    this.displayResults(analysisType, result);
                })
                .catch(error => {
                    console.error('Analysis failed:', error);
                    window.UIComponents.loading.hide();
                    alert(`Analysis failed: ${error.message}`);
                });
        } else {
            // Simulate analysis
            setTimeout(() => {
                window.UIComponents.loading.hide();
                this.displayResults(analysisType, { success: true, result: 'Simulated analysis complete' });
            }, 3000);
        }
    }
    
    displayResults(analysisType, result) {
        const resultsArea = document.querySelector(`#${analysisType}-results`);
        if (resultsArea) {
            resultsArea.innerHTML = `
                <div class="analysis-results">
                    <h4>Analysis Complete</h4>
                    <div class="result-summary">
                        <p>Status: ${result.success ? '✅ Success' : '❌ Failed'}</p>
                        <pre>${JSON.stringify(result, null, 2)}</pre>
                    </div>
                </div>
            `;
        }
    }
}

// Server status component
class ServerStatusComponent {
    constructor() {
        this.refreshButton = document.getElementById('refresh-servers');
        this.setupRefreshButton();
        this.startStatusPolling();
    }
    
    setupRefreshButton() {
        if (this.refreshButton) {
            this.refreshButton.addEventListener('click', () => {
                this.refreshServerStatus();
            });
        }
    }
    
    async refreshServerStatus() {
        console.log('🔄 Refreshing server status...');
        
        if (this.refreshButton) {
            this.refreshButton.disabled = true;
            this.refreshButton.textContent = 'Refreshing...';
        }
        
        try {
            if (window.MCPClient) {
                const status = await window.MCPClient.getSystemStatus();
                this.updateServerStatusDisplay(status);
            }
        } catch (error) {
            console.error('Failed to refresh server status:', error);
        } finally {
            if (this.refreshButton) {
                this.refreshButton.disabled = false;
                this.refreshButton.textContent = 'Refresh Status';
            }
        }
    }
    
    updateServerStatusDisplay(status) {
        const detailedList = document.getElementById('detailed-server-list');
        if (detailedList && status.available_servers) {
            const serverCards = status.available_servers.map(server => `
                <div class="detailed-server-card">
                    <h4>${server.toUpperCase()} Server</h4>
                    <div class="server-details">
                        <span class="status-badge ready">Ready</span>
                        <span class="server-type">${server}</span>
                    </div>
                </div>
            `).join('');
            
            detailedList.innerHTML = serverCards;
        }
    }
    
    startStatusPolling() {
        // Poll server status every 30 seconds
        setInterval(() => {
            if (window.GliaentApp && window.GliaentApp.currentScreen === 'servers-screen') {
                this.refreshServerStatus();
            }
        }, 30000);
    }
}

// Initialize UI components when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎯 Initializing UI Components...');
    
    // Initialize components
    window.UIComponents = {
        loading: new LoadingOverlay(),
        fileUpload: new FileUploadHandler(),
        parameterForms: new ParameterFormHandler(),
        serverStatus: new ServerStatusComponent()
    };
    
    // Add utility methods to global scope
    window.UIComponents.clearFiles = function(button) {
        window.UIComponents.fileUpload.clearFiles(button);
    };
    
    window.UIComponents.runAnalysis = function(analysisType) {
        window.UIComponents.parameterForms.runAnalysis(analysisType);
    };
    
    console.log('✅ UI Components initialized');
});

console.log('🎨 UI Components loaded'); 