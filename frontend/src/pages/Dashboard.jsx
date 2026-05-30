import React, { useEffect } from 'react'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'
import { format, parseISO } from 'date-fns'
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis,
    Tooltip, ResponsiveContainer, CartesianGrid, Cell,
} from 'recharts'

const COLORS = ['#e05555', '#5090e0', '#9060d0', '#50d080', '#e0a030', '#d4d435']

const TIP_STYLE = { background: '#18181f', border: '1px solid #2a2a38', borderRadius: 5, fontSize: 11 }

export default function Dashboard() {
    // 1. Extract 'refetch' from your custom hook
    const { data, loading, error, refetch } = useApi(() => api.getAnalytics(), [])

    // 2. Place useEffect BEFORE any early returns
    useEffect(() => {
        // Safety check in case useApi doesn't return refetch immediately
        if (refetch) {
            const interval = setInterval(() => {
                refetch()   // re-calls api.getAnalytics()
            }, 15000)     // refresh every 15 seconds

            return () => clearInterval(interval)
        }
    }, [refetch]) // Add refetch to dependency array

    // 3. Early returns happen after hooks. 
    // '&& !data' ensures we don't flash a spinner on every 15s background refresh.
    if (loading && !data) return <div className="pcenter"><div className="spinner" /></div>
    if (error) return <div className="pcenter"><div className="errmsg">⚠ {error}</div></div>

    const services = (data?.top_services || []).map(s => s.service_name)
    const trendData = (data?.time_series || []).map(d => ({
        ...d, time: format(parseISO(d.bucket), 'HH:mm'),
    }))

    return (
        <div className="page">
            <div className="pt">Overview</div>

            <div className="stats">
                <div className="stat hi"><div className="stat-v">{data.total_failures}</div><div className="stat-l">Total Failures</div></div>
                <div className="stat"><div className="stat-v">{data.failures_last_hour}</div><div className="stat-l">Last Hour</div></div>
                <div className="stat"><div className="stat-v">{services.length}</div><div className="stat-l">Services Affected</div></div>
                <div className="stat"><div className="stat-v">{(data.top_error_types || []).length}</div><div className="stat-l">Error Types</div></div>
            </div>

            <div className="cg2">
                <div className="card">
                    <h3>Failure Trend (24h)</h3>
                    <ResponsiveContainer width="100%" height={180}>
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a38" />
                            <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#60607a' }} interval="preserveStartEnd" />
                            <YAxis tick={{ fontSize: 10, fill: '#60607a' }} />
                            <Tooltip contentStyle={TIP_STYLE} />
                            <Line type="monotone" dataKey="count" stroke="#e05555" strokeWidth={2} dot={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>

                <div className="card">
                    <h3>Top Failing Services</h3>
                    {(data.top_services || []).map((s, i) => {
                        const max = data.top_services[0]?.count || 1
                        return (
                            <div key={s.service_name} className="bar-row">
                                <div className="bar-lbl">{s.service_name}</div>
                                <div className="bar-track">
                                    <div className="bar-fill" style={{ width: `${(s.count / max * 100).toFixed(1)}%`, background: COLORS[i % COLORS.length] }} />
                                </div>
                                <div className="bar-cnt">{s.count}</div>
                            </div>
                        )
                    })}
                </div>
            </div>

            <div className="cg13">
                <div className="card">
                    <h3>Error Categories</h3>
                    {(data.top_error_types || []).map((e, i) => (
                        <div key={e.error_type} className="et-row">
                            <div className="et-dot" style={{ background: COLORS[i % COLORS.length] }} />
                            <span className="et-name">{e.error_type}</span>
                            <span className="et-cnt">{e.count}</span>
                        </div>
                    ))}
                </div>

                <div className="card" style={{ overflow: 'hidden' }}>
                    <h3>Heatmap — Service × Hour of Day</h3>
                    <Heatmap data={data.heatmap} services={services} />
                </div>
            </div>
        </div>
    )
}

function Heatmap({ data, services }) {
    const hours = Array.from({ length: 24 }, (_, i) => i)
    const map = {}
        ; (data || []).forEach(c => { map[`${c.service_name}:${c.hour}`] = c.count })
    const maxC = Math.max(...(data || []).map(c => c.count), 1)

    return (
        <div style={{ overflowX: 'auto' }}>
            <div className="hm-grid" style={{ gridTemplateColumns: `80px repeat(24, 14px)`, gap: 2 }}>
                <div />
                {hours.map(h => <div key={h} className="hm-hr">{h % 6 === 0 ? String(h).padStart(2, '0') : ''}</div>)}
                {services.map(svc => (
                    <React.Fragment key={svc}>
                        <div className="hm-svc">{svc.split('-')[0]}</div>
                        {hours.map(h => {
                            const v = map[`${svc}:${h}`] || 0
                            return (
                                <div
                                    key={h} className="hm-cell"
                                    title={`${svc} @ ${h}:00 — ${v} failures`}
                                    style={{ background: `rgba(224,85,85,${(v / maxC).toFixed(2)})`, minHeight: 14 }}
                                />
                            )
                        })}
                    </React.Fragment>
                ))}
            </div>
        </div>
    )
}