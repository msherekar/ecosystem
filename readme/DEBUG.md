# Gliaent Electron + Monaco Debugging Guide

## 🔧 Fixed Issues

### 1. ✅ **Left Panel Buttons Not Working**

**Problem**: Module buttons in left panel weren't responding to clicks.

**Root Causes**:
- Module names mismatch: HTML had `scrnaseq` but modules were `scrna_seq`
- Monaco Editor path issues after file reorganization
- Event listener timing problems

**Solutions**:
- ✅ Fixed module names to match actual directory structure
- ✅ Updated file paths after moving to `src/ui/`
- ✅ Added debugging console.log statements
- ✅ Improved initialization timing

### 2. ✅ **File Organization**

**Problem**: All files in root directory was messy.

**Solution**: Reorganized to proper structure:
```
/
├── main.js                 # Electron main process
├── package.json           # Dependencies
├── python_backend.py      # FastAPI backend
├── start_gliaent.sh       # Startup script
└── src/
    ├── ui/
    │   ├── index.html     # Moved here
    │   └── renderer.js    # Moved here
    └── modules/           # Your existing modules
        ├── scrna_seq/
        ├── rna_seq/
        └── ...
```

## 🐛 Debugging Steps

### If Left Panel Still Not Working:

1. **Open DevTools** (automatically opens in dev mode):
   ```bash
   npm run dev
   ```

2. **Check Console for Errors**:
   - Look for JavaScript errors
   - Check if event listeners are being set up
   - Verify module names match

3. **Test Event Listeners**:
   ```javascript
   // In DevTools console:
   document.querySelectorAll('.module-item').forEach(item => {
       console.log(item.dataset.module);
   });
   ```

4. **Verify Backend Connection**:
   ```javascript
   // In DevTools console:
   fetch('http://localhost:8000/health')
       .then(r => r.json())
       .then(console.log);
   ```

### If Monaco Editor Not Loading:

1. **Check Monaco Path**:
   - Should be: `../../node_modules/monaco-editor/min/vs/`
   - Verify node_modules exists in root

2. **Check Network Tab**:
   - Look for 404 errors on Monaco files
   - Verify loader.js is found

3. **Test Monaco Manually**:
   ```javascript
   // In DevTools console:
   console.log(typeof monaco);  // Should not be 'undefined'
   ```

### If Python Backend Issues:

1. **Check Backend Status**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check Backend Logs**:
   - Look at terminal where npm run dev is running
   - Backend errors show as "Backend Error: ..."

3. **Test Module Discovery**:
   ```bash
   curl http://localhost:8000/modules
   ```

## 🚀 Quick Test Commands

```bash
# Full restart sequence
pkill -f "electron"           # Stop app
pkill -f "python_backend"     # Stop backend
./start_gliaent.sh           # Restart everything

# Test individual components
python test_integration.py   # Run integration tests
python python_backend.py     # Test backend standalone
```

## 📝 Console Commands for Testing

Open DevTools and try these:

```javascript
// Test if app is initialized
window.gliaentApp

// Test module selection manually
window.gliaentApp.selectModule('scrna_seq')

// Test code execution
window.gliaentApp.runCode()

// Check current module
window.gliaentApp.currentModule

// Test backend connection
window.gliaentApp.backendUrl
```

## 🎯 Expected Behavior

When working correctly:

1. **App starts**: Window opens with three panels
2. **Module selection**: Click any module in left panel
3. **Template loads**: Monaco editor shows module-specific code
4. **Status updates**: Bottom status bar shows "Module loaded"
5. **Chat message**: Right panel shows welcome message for module
6. **Code execution**: Run button executes code and shows output

## 📊 Verification Checklist

- [ ] Left panel modules are clickable
- [ ] Module selection changes editor content
- [ ] Status bar updates when module selected
- [ ] Chat shows module-specific welcome message
- [ ] Run button executes Python code
- [ ] Output appears in bottom panel
- [ ] File operations work (Ctrl+O, Ctrl+S)
- [ ] Chat input accepts messages

If any of these fail, check the console for error messages and refer to the debugging steps above. 