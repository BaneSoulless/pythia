import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

// HOTWIRE ENTRY: MOUNT APP DIRECTLY
// NO ROUTER PROVIDERS. NO CONTEXT. RAW REACT.
ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
)
