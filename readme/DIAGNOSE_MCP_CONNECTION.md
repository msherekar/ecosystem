# MCP Connection Diagnostic Guide

## Quick Diagnosis Steps

### Step 1: Check How You're Running the App

```bash
# ❌ WRONG - Browser only (no Electron, no MCP)
npm run dev:vite

# ✅ CORRECT - Full Electron + MCP
npm run dev
```

**Expected**: When running `npm run dev`, you should see BOTH:
- Vite dev server starting on http://localhost:3000
- Electron window opening with the app

### Step 2: Check Electron Console

**How to Access**:
1. Run `npm run dev`
2. In the Electron window: **View → Toggle Developer Tools**
3. Check the **Console** tab

**What to Look For**:

✅ **Good Signs**:
```
🔌 Initializing MCP connection...
✅ MCP connection established
✅ Electron modules loaded successfully
🔗 Starting MCP Server Orchestrator...
📨 MCP Message: {type: 'ready', ...}
```

❌ **Bad Signs**:
```
⚠️ Not running in Electron environment
❌ Failed to initialize MCP: ...
MCP Error: ModuleNotFoundError
Failed to start MCP orchestrator
```

### Step 3: Check Terminal Output

When running `npm run dev`, check the terminal for:

✅ **Good**:
```
[0] > vite
[0] VITE v4.4.0  ready in 500 ms
[1] 📚 Gliaent main process loading...
[1] ✅ Electron modules loaded successfully
[1] 🧬 Initializing Gliaent Electron App with MCP Integration...
[1] 🔗 Starting MCP Server Orchestrator...
[1] MCP Output: Starting server orchestrator...
```

❌ **Bad**:
```
Error: spawn python ENOENT
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'ServerManager'
```

### Step 4: Check Python Environment

```bash
# 1. Check Python is installed
python --version
# Should be Python 3.8+

# 2. Check if MCP modules can be imported
python -c "from src.mcp.servers import MCPServerOrchestrator; print('OK')"

# 3. Check dependencies
pip list | grep -E "streamlit|pandas|numpy|scanpy"
```

### Step 5: Test MCP Backend Independently

```bash
# Try running the MCP server directly
cd /Users/mukulsherekar/Projects/Gliaent
python -m src.mcp.servers
```

**Expected Output**:
```
Starting MCP Server Orchestrator...
Listening for Electron Bridge commands on stdin...
Available servers: ['rnaseq', 'scrnaseq', 'atacseq', 'proteomics']
```

## Common Issues & Fixes

### Issue 1: "Not running in Electron environment"

**Cause**: Running in browser instead of Electron

**Fix**:
```bash
# Stop current process
# Run full Electron app
npm run dev
```

### Issue 2: "spawn python ENOENT"

**Cause**: Python not found in PATH

**Fix**:
```bash
# Check which python
which python
which python3

# If python3 works but python doesn't, modify backendManager.js line 25:
# Change: spawn('python', ...)
# To: spawn('python3', ...)
```

### Issue 3: "ModuleNotFoundError: No module named 'src'"

**Cause**: PYTHONPATH not set correctly or running from wrong directory

**Fix**:
1. Ensure you're running from project root
2. Check backendManager.js line 34 sets PYTHONPATH:
   ```javascript
   env: {
     PYTHONPATH: process.cwd(),
     // ...
   }
   ```

### Issue 4: "ImportError: Missing dependencies"

**Cause**: Python dependencies not installed

**Fix**:
```bash
# Install Python dependencies
pip install -r requirements.txt

# Or if you prefer conda:
conda install streamlit pandas numpy scipy scanpy
```

### Issue 5: Connection Timeout

**Cause**: Backend takes too long to initialize

**Fix**: Increase timeout in backendManager.js line 100:
```javascript
setTimeout(async () => {
  // ...
}, 2000);  // Increase from 1000 to 2000
```

## Verification Checklist

- [ ] Running with `npm run dev` (not `npm run dev:vite`)
- [ ] Electron window opens successfully
- [ ] Browser console shows "MCP connection established"
- [ ] Terminal shows "MCP Server Orchestrator" starting
- [ ] Python is installed and accessible
- [ ] Python dependencies are installed
- [ ] Header shows green "MCP Connected" status
- [ ] Header shows "X/Y servers running"

## Debug Mode

Enable detailed logging:

**1. In App.tsx** (line 27):
```typescript
console.log('🔌 Initializing MCP connection...')
// Add more logs
```

**2. In backendManager.js** (add at line 103):
```javascript
console.log('Raw MCP output:', data.toString())
```

**3. Run Python backend with debug**:
```bash
DEBUG=1 python -m src.mcp.servers
```

## Still Not Working?

Check these files for issues:

1. **Frontend Connection**: `src/ui-react/App.tsx` (lines 23-73)
2. **MCP Service**: `src/ui-react/services/mcpService.ts` (lines 26-52)
3. **Electron Main**: `main.js` (lines 39-75)
4. **Backend Manager**: `electron/backendManager.js` (lines 19-101)
5. **Python Entry**: `src/mcp/servers/__main__.py`

## Expected Full Flow

```
1. User runs: npm run dev
   ↓
2. Concurrently starts:
   - Vite dev server (port 3000)
   - Electron main process
   ↓
3. Electron main process:
   - Loads main.js
   - Creates BrowserWindow
   - Spawns Python backend
   ↓
4. Python backend:
   - Starts MCPServerOrchestrator
   - Initializes ElectronBridge
   - Sends 'ready' message via stdout
   ↓
5. Electron receives 'ready':
   - Sets isConnected = true
   - Sends 'mcp-ready' to renderer
   ↓
6. React frontend:
   - App.tsx receives connection
   - Shows "MCP Connected" in header
   - Enables analysis features
```

## Need More Help?

Check the logs at:
- Browser Console (F12 in Electron window)
- Terminal output (where you ran npm run dev)
- Python stderr/stdout in terminal
