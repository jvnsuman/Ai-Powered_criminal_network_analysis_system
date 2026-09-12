/**
 * dashboard/src/main.jsx
 *
 * Vite/React entrypoint — mounts <App /> into index.html's #root,
 * wrapped in ToastProvider so any component can fire notifications.
 *
 * Stylesheet order matters: theme.css defines the light-theme design
 * tokens (--bg, --primary, etc.) for the new sidebar-nav direction,
 * app-v2.css consumes those tokens. index.css (the original dark
 * theme) is no longer imported here — see index.css's own header
 * comment if you need to revert to the old look.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ToastProvider } from './components/Toast.jsx'
import './theme.css'
import './app-v2.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>
)
