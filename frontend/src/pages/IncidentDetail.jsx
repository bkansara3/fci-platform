import { useParams, useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { ArrowLeft } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

export default function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: f, loading, error } = useApi(() => api.getFailure(id), [id])

  if (loading) return <div className="pcenter"><div className="spinner" /></div>
  if (error)   return <div className="pcenter"><div className="errmsg">⚠ {error}</div></div>
  if (!f) return null

  return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate(-1)}>
        <ArrowLeft size={13} /> Back to Incidents
      </button>
      <div className="pt">Incident #{f.id}</div>

      <div className="detail-grid" style={{ marginTop: 14 }}>
        <div className="dcard">
          <h3>Event Details</h3>
          <dl className="dl">
            <dt>Service</dt>      <dd>{f.service_name}</dd>
            <dt>Endpoint</dt>    <dd><span className="tag-meth">{f.http_method}</span>{f.endpoint}</dd>
            <dt>Status</dt>      <dd><span className="badge b-critical">{f.status_code}</span></dd>
            <dt>Error Type</dt>  <dd>{f.error_type}</dd>
            <dt>Environment</dt> <dd>{f.environment}</dd>
            <dt>Timestamp</dt>   <dd>{format(new Date(f.timestamp), 'PPpp')}</dd>
          </dl>
        </div>

        <div className="dcard">
          <h3>Error Message</h3>
          <pre className="code">{f.error_message}</pre>
        </div>

        {f.stack_trace && (
          <div className="dcard full">
            <h3>Stack Trace</h3>
            <pre className="code stack">{f.stack_trace}</pre>
          </div>
        )}

        {f.request_metadata && (
          <div className="dcard">
            <h3>Request Metadata</h3>
            <pre className="code">{JSON.stringify(f.request_metadata, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  )
}
