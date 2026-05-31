import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    async function handleLogin() {
        setLoading(true); setError(null)
        try {
            // OAuth2 requires form data, not JSON
            const form = new URLSearchParams()
            form.append('username', username)
            form.append('password', password)

            const res = await fetch('/api/v1/auth/login', {
                method: 'POST',
                body: form,
            })

            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.detail)
            }

            const data = await res.json()
            localStorage.setItem('fci_token', data.access_token)  // store token
            navigate('/')     // go to dashboard
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: 'var(--bg)' }}>
            <div className="card" style={{ width: 320, padding: 32 }}>
                <h2 style={{ color: '#fff', marginBottom: 24 }}>FCI Platform</h2>

                <input className="fi" style={{ width: '100%', marginBottom: 10 }}
                    placeholder="Username"
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                />
                <input className="fi" style={{ width: '100%', marginBottom: 16 }}
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleLogin()}
                />

                {error && <div className="errmsg" style={{ marginBottom: 12 }}>⚠ {error}</div>}

                <button className="gen-btn" style={{ width: '100%' }}
                    onClick={handleLogin} disabled={loading}>
                    {loading ? 'Signing in...' : 'Sign In'}
                </button>

                <p style={{ color: 'var(--dim)', fontSize: 11, marginTop: 16, textAlign: 'center' }}>
                    
                </p>
            </div>
        </div>
    )
}