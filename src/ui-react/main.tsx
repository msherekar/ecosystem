import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './styles/globals.css'

/**
 * HashRouter, not BrowserRouter.
 *
 * A packaged Electron app loads its renderer with `loadFile`, i.e. over
 * `file://`. BrowserRouter pushes real paths like `/rnaseq`, which under
 * `file://` resolve to filesystem paths that do not exist — so any navigation
 * followed by a reload produced a dead window. It only appeared to work in
 * development because the Vite dev server served every path.
 */
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
