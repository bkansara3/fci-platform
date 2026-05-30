import { NavLink } from 'react-router-dom'
import { LayoutDashboard, List, Lightbulb, Activity } from 'lucide-react'

const NAV = [
  { to: '/', label: 'Overview', Icon: LayoutDashboard },
  { to: '/incidents', label: 'Incidents', Icon: List },
  { to: '/insights', label: 'AI Insights', Icon: Lightbulb },
]

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="slogo">
        <Activity size={18} />
        FCI <em>Platform</em>
      </div>
      <nav className="snav">
        {NAV.map(({ to, label, Icon }) => (
          <NavLink
            key={to} to={to} end={to === '/'}
            className={({ isActive }) => `ni${isActive ? ' active' : ''}`}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sfoot">
        <div className="live-dot" /> Live
      </div>
    </aside>
  )
}
