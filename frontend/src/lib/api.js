const BASE = '/api/v1'

async function req(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json()
}

export const api = {
  getAnalytics:    ()           => req('/analytics'),
  getFailures:     (p = {})    => req(`/failures?${new URLSearchParams(p)}`),
  getFailure:      (id)        => req(`/failures/${id}`),
  getInsights:     ()          => req('/insights'),
  getGroups:       ()          => req('/insights/groups'),
  generateInsight: (svc, err)  => req('/insights/generate', {
    method: 'POST',
    body: JSON.stringify({ service_name: svc, error_type: err }),
  }),
}
