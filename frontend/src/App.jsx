import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import Incidents from './pages/Incidents'
import IncidentDetail from './pages/IncidentDetail'
import Insights from './pages/Insights'

export default function App() {
  return (
    <BrowserRouter>
      <div className="layout">
        <Sidebar />
        <main className="main">
          <Routes>
            <Route path="/"              element={<Dashboard />} />
            <Route path="/incidents"     element={<Incidents />} />
            <Route path="/incidents/:id" element={<IncidentDetail />} />
            <Route path="/insights"      element={<Insights />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
