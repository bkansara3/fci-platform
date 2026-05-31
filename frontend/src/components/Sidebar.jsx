import { useState, useEffect } from 'react'
// Add 'Link' to your existing imports
import { NavLink, Link, useNavigate } from 'react-router-dom'
// 1. Added Sun and Moon icons for the toggle button
import { LayoutDashboard, List, Lightbulb, Activity, LogOut, User, Sun, Moon } from 'lucide-react'
import { jwtDecode } from 'jwt-decode'
import { useTheme } from '../contexts/ThemeContext'

const NAV = [
    { to: '/', label: 'Overview', Icon: LayoutDashboard },
    { to: '/incidents', label: 'Incidents', Icon: List },
    { to: '/insights', label: 'AI Insights', Icon: Lightbulb },
]

export default function Sidebar() {
    const navigate = useNavigate()
    const [currentUser, setCurrentUser] = useState(null)

    // 2. Initialize the theme hook
    const { theme, toggleTheme } = useTheme()

    useEffect(() => {
        const token = localStorage.getItem('fci_token')
        if (token) {
            try {
                const decoded = jwtDecode(token)
                setCurrentUser({
                    username: decoded.sub,
                    role: decoded.role
                })
            } catch (err) {
                console.error("Failed to decode token", err)
            }
        }
    }, [])

    function handleLogout() {
        localStorage.removeItem('fci_token')
        navigate('/login', { replace: true })
    }

    return (
        <aside className="sidebar">
            <Link to="/" className="slogo" style={{ textDecoration: 'none' }}>
                <Activity size={18} />
                FCI <em>Platform</em>
            </Link>

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

            <div className="sfoot" style={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: '12px' }}>

                {/* User Identity Badge */}
                {currentUser && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 8px', background: 'var(--s2)', borderRadius: '6px', border: '1px solid var(--border)' }}>
                        <div style={{ background: 'var(--s3)', padding: '4px', borderRadius: '50%', color: 'var(--dim)' }}>
                            <User size={14} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                            <span style={{ fontSize: '11px', color: '#fff', fontWeight: '500', textTransform: 'capitalize' }}>
                                {currentUser.username}
                            </span>
                            <span style={{ fontSize: '9px', color: currentUser.role === 'admin' ? 'var(--blue)' : 'var(--dim)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                {currentUser.role}
                            </span>
                        </div>
                    </div>
                )}

                {/* System Status, Theme Toggle, & Logout */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <div className="live-dot" /> Live
                    </div>

                    {/* Button Group Container */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>

                        {/* 3. The New Theme Toggle Button */}
                        <button
                            onClick={toggleTheme}
                            title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--dim)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                padding: '4px',
                                borderRadius: '4px',
                                transition: 'color 0.2s, background 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.color = '#fff'
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.color = 'var(--dim)'
                                e.currentTarget.style.background = 'none'
                            }}
                        >
                            {theme === 'light' ? <Moon size={14} /> : <Sun size={14} />}
                        </button>

                        <button
                            onClick={handleLogout}
                            title="Logout"
                            style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--dim)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                                fontSize: '11px',
                                padding: '4px 6px',
                                borderRadius: '4px',
                                transition: 'color 0.2s, background 0.2s'
                            }}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.color = 'var(--red)'
                                e.currentTarget.style.background = 'rgba(224, 85, 85, 0.1)'
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.color = 'var(--dim)'
                                e.currentTarget.style.background = 'none'
                            }}
                        >
                            <LogOut size={13} />
                        </button>
                    </div>
                </div>
            </div>
        </aside>
    )
}