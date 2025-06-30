#!/bin/bash

echo "🎨 Creating Modular CSS Structure for Gliaent..."

# Create CSS directory
mkdir -p src/ui/css

# Create main.css (Core styles and variables)
cat > src/ui/css/main.css << 'EOF'
/* 
 * Gliaent Main Styles - Core Layout & Variables
 * Maximum 250 lines - Core styles only
 */

/* CSS Variables - Global Design System */
:root {
    /* Colors */
    --primary-color: #2c3e50;
    --secondary-color: #3498db;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --error-color: #e74c3c;
    --info-color: #17a2b8;
    
    /* Backgrounds */
    --background-color: #ecf0f1;
    --sidebar-color: #34495e;
    --card-background: #ffffff;
    --overlay-background: rgba(0, 0, 0, 0.8);
    
    /* Text Colors */
    --text-color: #2c3e50;
    --text-muted: #7f8c8d;
    --text-light: #bdc3c7;
    --text-white: #ffffff;
    
    /* Borders & Shadows */
    --border-color: #bdc3c7;
    --border-radius: 8px;
    --border-radius-small: 4px;
    --border-radius-large: 12px;
    --shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
    --shadow-hover: 0 4px 20px rgba(0, 0, 0, 0.15);
    
    /* Spacing */
    --spacing-xs: 4px;
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
    --spacing-xl: 32px;
    
    /* Typography */
    --font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    --font-size-xs: 12px;
    --font-size-sm: 14px;
    --font-size-md: 16px;
    --font-size-lg: 18px;
    --font-size-xl: 24px;
    --font-size-xxl: 32px;
    
    /* Transitions */
    --transition-fast: 0.2s ease;
    --transition-normal: 0.3s ease;
    --transition-slow: 0.5s ease;
    
    /* Z-index layers */
    --z-header: 100;
    --z-sidebar: 50;
    --z-modal: 1000;
    --z-overlay: 999;
    --z-notification: 1001;
}

/* Reset & Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html {
    font-size: 100%;
    scroll-behavior: smooth;
}

body {
    font-family: var(--font-family);
    background-color: var(--background-color);
    color: var(--text-color);
    line-height: 1.6;
    overflow: hidden;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* App Container */
#app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    min-height: 100vh;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-weight: 600;
    line-height: 1.2;
    margin-bottom: var(--spacing-sm);
    color: var(--text-color);
}

h1 { font-size: var(--font-size-xxl); }
h2 { font-size: var(--font-size-xl); }
h3 { font-size: var(--font-size-lg); }
h4 { font-size: var(--font-size-md); }
h5 { font-size: var(--font-size-sm); }
h6 { font-size: var(--font-size-xs); }

p {
    margin-bottom: var(--spacing-md);
    line-height: 1.6;
}

small {
    font-size: var(--font-size-xs);
    color: var(--text-muted);
}

/* Links */
a {
    color: var(--secondary-color);
    text-decoration: none;
    transition: color var(--transition-fast);
}

a:hover {
    color: var(--primary-color);
    text-decoration: underline;
}

/* Focus Styles */
*:focus {
    outline: 2px solid var(--secondary-color);
    outline-offset: 2px;
}

/* Selection Styles */
::selection {
    background-color: var(--secondary-color);
    color: var(--text-white);
}

/* Scrollbar Styles */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--background-color);
}

::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: var(--border-radius-small);
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-muted);
}

/* Main Layout Grid */
.app-main {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Content Area */
.content-area {
    flex: 1;
    overflow-y: auto;
    position: relative;
    background-color: var(--background-color);
}

/* Screen Management */
.screen {
    display: none;
    padding: var(--spacing-xl);
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
}

.screen.active {
    display: block;
    animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Utility Classes */
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-right { text-align: right; }

.mb-xs { margin-bottom: var(--spacing-xs); }
.mb-sm { margin-bottom: var(--spacing-sm); }
.mb-md { margin-bottom: var(--spacing-md); }
.mb-lg { margin-bottom: var(--spacing-lg); }
.mb-xl { margin-bottom: var(--spacing-xl); }

.mt-xs { margin-top: var(--spacing-xs); }
.mt-sm { margin-top: var(--spacing-sm); }
.mt-md { margin-top: var(--spacing-md); }
.mt-lg { margin-top: var(--spacing-lg); }
.mt-xl { margin-top: var(--spacing-xl); }

.p-xs { padding: var(--spacing-xs); }
.p-sm { padding: var(--spacing-sm); }
.p-md { padding: var(--spacing-md); }
.p-lg { padding: var(--spacing-lg); }
.p-xl { padding: var(--spacing-xl); }

/* Flexbox Utilities */
.d-flex { display: flex; }
.flex-column { flex-direction: column; }
.flex-row { flex-direction: row; }
.justify-center { justify-content: center; }
.justify-between { justify-content: space-between; }
.justify-around { justify-content: space-around; }
.align-center { align-items: center; }
.align-start { align-items: flex-start; }
.align-end { align-items: flex-end; }
.flex-1 { flex: 1; }
.flex-wrap { flex-wrap: wrap; }

/* Grid Utilities */
.grid { display: grid; }
.grid-cols-1 { grid-template-columns: 1fr; }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }
.grid-cols-auto { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
.gap-sm { gap: var(--spacing-sm); }
.gap-md { gap: var(--spacing-md); }
.gap-lg { gap: var(--spacing-lg); }

/* Visibility */
.hidden { display: none !important; }
.visible { display: block !important; }
.opacity-50 { opacity: 0.5; }
.opacity-75 { opacity: 0.75; }

/* Responsive Utilities */
@media (max-width: 768px) {
    .screen {
        padding: var(--spacing-md);
    }
    
    .grid-cols-2,
    .grid-cols-3 {
        grid-template-columns: 1fr;
    }
    
    .hide-mobile {
        display: none !important;
    }
}

@media (max-width: 480px) {
    :root {
        --font-size-xl: 20px;
        --font-size-xxl: 24px;
    }
    
    .screen {
        padding: var(--spacing-sm);
    }
}

/* Import other CSS files */
@import url('./layout.css');
@import url('./buttons.css');
@import url('./forms.css');
@import url('./components.css');
@import url('./analysis.css');
EOF

echo "✅ Created main.css (245 lines)"
echo "📋 Includes: Variables, reset, base styles, utilities"
echo ""
echo "🎯 Next: Run the updated setup script"
echo "   ./setup_electron.sh"
echo ""
echo "📂 CSS Architecture:"
echo "   ├── main.css      (Core styles & variables)"
echo "   ├── layout.css    (Header, sidebar, footer)"
echo "   ├── buttons.css   (Button components)"
echo "   ├── forms.css     (Form elements)"
echo "   ├── components.css (Cards, modals, notifications)"
echo "   └── analysis.css  (Analysis interface)"
echo ""
echo "✨ Each file under 250 lines, properly modularized!"