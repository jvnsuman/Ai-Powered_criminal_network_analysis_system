/**
 * dashboard/src/main.jsx
 *
 * Vite/React entrypoint — mounts <App /> into index.html's #root,
 * wrapped in ToastProvider so any component can fire notifications.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import { ToastProvider } from './components/Toast.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </React.StrictMode>
)
