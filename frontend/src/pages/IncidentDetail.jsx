import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Lightbulb, Loader } from 'lucide-react' // 1. Added Icons

// 1. The Helper Component
function RelatedFailures({ failure }) {
    const [related, setRelated] = useState([])
    
    // 2. Added state for AI Analysis
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [aiResult, setAiResult] = useState(null)

    useEffect(() => {
        if (!failure?.trace_id) return

        fetch(`/api/v1/failures/trace/${failure.trace_id}`)
            .then(res => res.json())
            .then(data => {
                const traceData = data.trace_tree || data || []
                setRelated(traceData)
            })
            .catch(err => console.error("Failed to fetch trace", err))
    }, [failure?.trace_id])

    // 3. Added the function to actually pass the trace_id!
    const handleTraceAnalysis = async () => {
        setIsAnalyzing(true)
        try {
            const res = await fetch('/api/v1/insights/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // THIS IS WHERE WE PASS THE TRACE ID
                body: JSON.stringify({ trace_id: failure.trace_id })
            })
            
            if (!res.ok) throw new Error("Failed to generate insight")
            
            const data = await res.json()
            setAiResult(data)
        } catch (err) {
            console.error("AI Analysis failed", err)
        } finally {
            setIsAnalyzing(false)
        }
    }

    if (!failure?.trace_id) return null
    if (related.length <= 1) return null

    return (
        <div className="dcard full" style={{ marginTop: '20px' }}>
            
            {/* Header with the new AI Button */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div>
                    <h3 style={{ marginBottom: '4px' }}>🔗 Distributed Trace — {failure.trace_id}</h3>
                    <p style={{ fontSize: 11, color: 'var(--dim)' }}>
                        Order: <strong>{failure.correlation_id}</strong> —
                        {related.length} failures across {new Set(related.map(f => f.service_name)).size} services
                    </p>
                </div>

                <button 
                    onClick={handleTraceAnalysis}
                    disabled={isAnalyzing}
                    style={{
                        display: 'flex', gap: '8px', alignItems: 'center',
                        background: 'var(--blue)', color: '#fff', 
                        border: 'none', padding: '8px 14px', borderRadius: '4px',
                        cursor: isAnalyzing ? 'wait' : 'pointer',
                        fontSize: '12px', fontWeight: '500'
                    }}
                >
                    {isAnalyzing ? <Loader size={14} className="spinner" style={{borderWidth: '2px', borderTopColor: 'transparent'}} /> : <Lightbulb size={14} />}
                    {isAnalyzing ? 'Analyzing Trace...' : 'AI Root Cause Analysis'}
                </button>
            </div>

            {/* Timeline of all services in this trace */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {related.map((f, i) => (
                    <div key={f.id || f.span_id} style={{
                        display: 'flex', alignItems: 'center', gap: 12,
                        padding: '8px 12px',
                        background: f.id === failure.id ? 'var(--s3)' : 'var(--bg)',
                        border: '1px solid var(--border)',
                        borderRadius: 5,
                    }}>
                        <div style={{
                            width: 22, height: 22, borderRadius: '50%',
                            background: 'var(--red)', color: '#fff',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: 10, fontWeight: 600, flexShrink: 0
                        }}>{i + 1}</div>

                        <div style={{ flex: 1 }}>
                            <span className="tag-svc">{f.service_name}</span>
                            <span style={{ marginLeft: 8, fontSize: 11, fontFamily: 'var(--mono)' }}>
                                {f.endpoint}
                            </span>
                        </div>

                        <span style={{ fontSize: 10, color: 'var(--red)' }}>
                            ❌ {f.error_type}
                        </span>

                        <span style={{ fontSize: 10, color: 'var(--dim)', fontFamily: 'var(--mono)' }}>
                            {f.timestamp ? new Date(f.timestamp).toLocaleTimeString() : 'N/A'}
                        </span>
                    </div>
                ))}
            </div>

            {/* 4. Render the AI Result directly in the Incident page */}
            {aiResult && (
                <div style={{ 
                    marginTop: '20px', 
                    padding: '16px', 
                    background: 'var(--s2)', 
                    borderLeft: '4px solid var(--blue)',
                    borderRadius: '0 4px 4px 0'
                }}>
                    <h4 style={{ color: 'var(--blue)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Lightbulb size={14} /> AI Trace Insight
                    </h4>
                    
                    <div style={{ marginBottom: '12px' }}>
                        <strong style={{ color: 'var(--text)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Root Cause</strong>
                        <p style={{ color: 'var(--dim)', fontSize: '12px', marginTop: '4px' }}>{aiResult.root_cause}</p>
                    </div>

                    <div>
                        <strong style={{ color: 'var(--text)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Remediation</strong>
                        <p style={{ color: 'var(--dim)', fontSize: '12px', marginTop: '4px' }}>{aiResult.risk_summary}</p>
                    </div>
                </div>
            )}
        </div>
    )
}

// 2. The Main Page Component
export default function IncidentDetail() {
    const { id } = useParams()
    const [failure, setFailure] = useState(null)

    useEffect(() => {
        fetch(`/api/v1/failures/${id}`)
            .then(res => {
                if (!res.ok) throw new Error("Network response was not ok")
                return res.json()
            })
            .then(data => setFailure(data))
            .catch(err => console.error("Failed to fetch failure", err))
    }, [id])

    if (!failure) {
        return <div style={{ padding: '20px' }}>Loading incident...</div>
    }

    return (
        <div style={{ padding: '20px' }}>
            <h2>Incident #{failure.id} - {failure.service_name}</h2>

            <div className="dcard full" style={{ marginBottom: '20px' }}>
                <p><strong>Error Type:</strong> {failure.error_type}</p>
                <p><strong>Message:</strong> {failure.error_message}</p>
                {failure.stack_trace && (
                    <pre style={{ background: '#111', color: '#ff7b72', padding: '10px', borderRadius: '5px', overflowX: 'auto', fontSize: '12px' }}>
                        {failure.stack_trace}
                    </pre>
                )}
            </div>

            <RelatedFailures failure={failure} />
        </div>
    )
}