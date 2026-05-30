import { useState } from 'react'
import { Sparkles, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const RISK_CLASS = { critical: 'b-critical', high: 'b-high', medium: 'b-medium', low: 'b-low' }

// ── LangGraph Trace Visualizer ────────────────────────────────────────────
function TraceViewer({ trace }) {
  const [sel, setSel] = useState(0)
  if (!trace || trace.length === 0) return null

  const node = trace[sel]
  const outputEntries = node?.output ? Object.entries(node.output) : []

  return (
    <div className="trace">
      <h4>⚡ LangGraph Execution Trace</h4>

      {/* Flow diagram */}
      <div className="trace-flow">
        {trace.map((t, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center' }}>
            <div
              className={`trace-node${sel === i ? ' sel' : ''}`}
              onClick={() => setSel(i)}
            >
              {t.node}
            </div>
            {i < trace.length - 1 && <span className="trace-arrow">→</span>}
          </div>
        ))}
      </div>

      {/* Selected node output */}
      <div className="trace-detail">
        <div style={{ marginBottom: 6, color: 'var(--dim)', fontSize: 10, fontFamily: 'var(--mono)' }}>
          node: <span style={{ color: 'var(--blue)' }}>{node.node}</span>
          &nbsp;&nbsp;ts: {node.timestamp?.slice(11, 19)}
        </div>
        {outputEntries.map(([k, v]) => (
          <div key={k}>
            <span className="tk">{k}</span>
            <span style={{ color: 'var(--dim)' }}>: </span>
            <span className="tv">
              {typeof v === 'object' ? JSON.stringify(v) : String(v).slice(0, 120)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Single insight card ───────────────────────────────────────────────────
function InsightCard({ insight }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="ins-card">
      <div className="ins-hdr" onClick={() => setOpen(o => !o)}>
        <div className="ins-meta">
          <span className={`badge ${RISK_CLASS[insight.risk_level] || 'b-low'}`}>
            {insight.risk_level?.toUpperCase()}
          </span>
          <span className="ins-svc">{insight.service_name}</span>
          <span className="ins-sep">/</span>
          <span className="ins-err">{insight.error_type}</span>
        </div>
        <div className="ins-right">
          <span>{insight.failure_count} failures</span>
          <span className="ins-conf">{Math.round((insight.confidence || 0) * 100)}% conf</span>
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </div>
      </div>

      <div className="ins-sum">{insight.risk_summary}</div>

      {open && (
        <div className="ins-body">
          <h4>Root Cause Hypothesis</h4>
          <p>{insight.root_cause}</p>

          <div className="ins-two">
            <div>
              <h4>Recommended Fixes</h4>
              <ul>{(insight.recommended_fixes || []).map((f, i) => <li key={i}>{f}</li>)}</ul>
            </div>
            <div>
              <h4>Remediation Actions</h4>
              <ol>{(insight.remediation_actions || []).map((a, i) => <li key={i}>{a}</li>)}</ol>
            </div>
          </div>

          <TraceViewer trace={insight.graph_trace} />
        </div>
      )}
    </div>
  )
}

// ── Generate form ─────────────────────────────────────────────────────────
function GenerateForm({ onGenerated }) {
  const { data: groups } = useApi(() => api.getGroups(), [])
  const [selIdx, setSelIdx] = useState(0)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(null)
  const [progress, setProgress] = useState('')

  const NODES = ['planner', 'analyzer', 'risk_assessor', 'synthesizer']

  async function handleGenerate() {
    const group = groups?.[selIdx]
    if (!group) return
    setLoading(true); setErr(null); setProgress('')

    // Animate through LangGraph nodes while waiting
    let ni = 0
    const interval = setInterval(() => {
      setProgress(`Running node: ${NODES[ni % NODES.length]}…`)
      ni++
    }, 600)

    try {
      const insight = await api.generateInsight(group.service_name, group.error_type)
      clearInterval(interval)
      setProgress('')
      onGenerated(insight)
    } catch (e) {
      clearInterval(interval)
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="gen-form">
      <h3><Zap size={13} /> Run LangGraph Analysis Pipeline</h3>
      <div className="gen-row">
        <select
          value={selIdx}
          onChange={e => setSelIdx(Number(e.target.value))}
          disabled={loading}
        >
          {(groups || []).map((g, i) => (
            <option key={i} value={i}>
              {g.service_name} / {g.error_type} ({g.count} failures)
            </option>
          ))}
        </select>
        <button className="gen-btn" onClick={handleGenerate} disabled={loading || !groups?.length}>
          {loading
            ? <><div className="spinner" style={{ width: 12, height: 12, borderWidth: 1.5 }} /> Running…</>
            : <><Sparkles size={13} /> Analyze</>}
        </button>
      </div>
      {progress && (
        <div style={{ marginTop: 10, fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--blue)' }}>
          {progress}
        </div>
      )}
      {err && <div className="errmsg" style={{ marginTop: 8 }}>⚠ {err}</div>}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────
export default function Insights() {
  const { data, loading, error, refetch } = useApi(() => api.getInsights(), [])
  const [fresh, setFresh] = useState([])

  function handleGenerated(insight) {
    setFresh(prev => [insight, ...prev])
    refetch()
  }

  // Merge fresh + fetched, deduplicate by id
  const all = [...fresh, ...(data || [])].filter(
    (v, i, arr) => arr.findIndex(x => x.id === v.id) === i
  )

  return (
    <div className="page">
      <div className="pt">AI Insights</div>
      <div className="psub">
        Select a failure group and run the 4-node LangGraph pipeline:
        <strong style={{ color: 'var(--blue)' }}> planner → analyzer → risk_assessor → synthesizer</strong>.
        Each insight shows the full graph execution trace.
      </div>

      <GenerateForm onGenerated={handleGenerated} />

      {loading && <div className="pcenter"><div className="spinner" /></div>}
      {error   && <div className="errmsg">⚠ {error}</div>}

      <div>
        {all.length === 0 && !loading && (
          <div className="empty">No insights yet — select a group above and click Analyze.</div>
        )}
        {all.map(i => <InsightCard key={i.id} insight={i} />)}
      </div>
    </div>
  )
}
