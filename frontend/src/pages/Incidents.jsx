import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import { Search } from 'lucide-react'
import { api } from '../lib/api'
import { useApi } from '../lib/useApi'

const ERR_COLORS = {
  DatabaseConnectionError: '#e05555',
  DependencyFailure:       '#9060d0',
  TimeoutError:            '#e0a030',
  AuthenticationError:     '#5090e0',
  ConfigurationError:      '#50d080',
  DataValidationError:     '#d4d435',
}

export default function Incidents() {
  const navigate = useNavigate()
  const [svc, setSvc]   = useState('')
  const [err, setErr]   = useState('')
  const [page, setPage] = useState(1)

  const { data, loading, error } = useApi(
    () => api.getFailures({ ...(svc && { service: svc }), ...(err && { error_type: err }), page, page_size: 25 }),
    [svc, err, page]
  )

  const totalPages = data ? Math.ceil(data.total / 25) : 1

  return (
    <div className="page">
      <div className="pt">Incidents</div>

      <div className="fbar">
        <div className="fi">
          <Search size={12} />
          <input placeholder="Filter by service…" value={svc}
            onChange={e => { setSvc(e.target.value); setPage(1) }} />
        </div>
        <div className="fi">
          <Search size={12} />
          <input placeholder="Filter by error type…" value={err}
            onChange={e => { setErr(e.target.value); setPage(1) }} />
        </div>
        {data && <span className="fcnt">{data.total} results</span>}
      </div>

      {loading && <div className="pcenter"><div className="spinner" /></div>}
      {error   && <div className="errmsg">⚠ {error}</div>}

      {data && (
        <>
          <div className="tbl-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th><th>Time</th><th>Service</th>
                  <th>Endpoint</th><th>Error Type</th><th>Message</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map(f => (
                  <tr key={f.id} className="irow" onClick={() => navigate(`/incidents/${f.id}`)}>
                    <td className="td-id">#{f.id}</td>
                    <td className="td-time">{format(new Date(f.timestamp), 'MMM d, HH:mm:ss')}</td>
                    <td><span className="tag-svc">{f.service_name}</span></td>
                    <td className="td-ep">
                      <span className="tag-meth">{f.http_method}</span>{f.endpoint}
                    </td>
                    <td>
                      <span className="tag-err" style={{ color: ERR_COLORS[f.error_type] || '#888', borderColor: `${ERR_COLORS[f.error_type] || '#888'}44` }}>
                        {f.error_type}
                      </span>
                    </td>
                    <td className="td-msg">{f.error_message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="pager">
            <button className="pbtn" onClick={() => setPage(p => p - 1)} disabled={page === 1}>← Prev</button>
            <span>Page {page} of {totalPages}</span>
            <button className="pbtn" onClick={() => setPage(p => p + 1)} disabled={page >= totalPages}>Next →</button>
          </div>
        </>
      )}
    </div>
  )
}
