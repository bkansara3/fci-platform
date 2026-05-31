import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Incidents from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import Insights from './pages/Insights'

// 1. IMPORT THE PROVIDER
import { ThemeProvider } from './contexts/ThemeContext'

function PrivateLayout() {
    const token = localStorage.getItem('fci_token')
    if (!token) return <Navigate to="/login" replace />

    return (
        <div className="layout">
            <Sidebar />
            <main className="main">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/incidents" element={<Incidents />} />
                    <Route path="/incidents/:id" element={<IncidentDetail />} />
                    <Route path="/insights" element={<Insights />} />
                </Routes>
            </main>
        </div>
    )
}

export default function App() {
    return (
        // 2. WRAP YOUR WHOLE APP IN THE PROVIDER
        <ThemeProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/*" element={<PrivateLayout />} />
                </Routes>
            </BrowserRouter>
        </ThemeProvider>
    )
}