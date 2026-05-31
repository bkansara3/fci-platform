import { useNavigate, useSearchParams } from 'react-router-dom'
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
  const [searchParams, setSearchParams] = useSearchParams()

  // 1. URL-Driven State
  const svc  = searchParams.get('service') || ''
  const err  = searchParams.get('error') || ''
  const page = parseInt(searchParams.get('page') || '1', 10)

  // 2. Helper to safely update URL without losing other params
  function updateParam(key, value) {
    setSearchParams(prev => {
      if (value) prev.set(key, value)
      else prev.delete(key)
      
      if (key !== 'page') prev.set('page', '1')
      return prev
    }, { replace: true }) // replace: true prevents flooding the browser history with every keystroke
  }

  // 3. API Hook (unchanged, it reacts automatically to URL changes now!)
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
          <input 
            placeholder="Filter by service…" 
            value={svc}
            onChange={e => updateParam('service', e.target.value)} 
          />
        </div>
        <div className="fi">
          <Search size={12} />
          <input 
            placeholder="Filter by error type…" 
            value={err}
            onChange={e => updateParam('error', e.target.value)} 
          />
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
            <button 
              className="pbtn" 
              onClick={() => updateParam('page', (page - 1).toString())} 
              disabled={page === 1}
            >
              ← Prev
            </button>
            <span>Page {page} of {totalPages}</span>
            <button 
              className="pbtn" 
              onClick={() => updateParam('page', (page + 1).toString())} 
              disabled={page >= totalPages}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  )
}