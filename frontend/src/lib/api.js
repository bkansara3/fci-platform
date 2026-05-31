const BASE = '/api/v1'

function getToken() {
    return localStorage.getItem('fci_token')
}

async function req(path, opts = {}) {
    const token = getToken()

    // 1. Safely merge default headers with any custom headers passed in opts
    const headers = {
        'Content-Type': 'application/json',
        ...(opts.headers || {})
    }

    // 2. Explicitly attach the token inside the headers object
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    // 3. Pass the cleanly assembled headers to fetch
    const res = await fetch(`${BASE}${path}`, {
        ...opts,
        headers
    })
    if (res.status === 403 || res.status === 401) {
        throw new Error("Access Denied: You must be an administrator to execute analyze pipeline.")
    }
    if (res.status === 401) {
        localStorage.removeItem('fci_token')
        window.location.href = '/login'
        throw new Error('Unauthorized: Redirecting to login...') // Prevents downstream crashes
    }

    if (!res.ok) {
        const body = await res.text()
        throw new Error(`${res.status}: ${body}`)
    }

    return res.json()
}

export const api = {
    getAnalytics: () => req('/analytics'),
    getFailures: (p = {}) => req(`/failures?${new URLSearchParams(p)}`),
    getFailure: (id) => req(`/failures/${id}`),
    getInsights: () => req('/insights'),
    getGroups: () => req('/insights/groups'),
    generateInsight: (svc, err) => req('/insights/generate', {
        method: 'POST',
        body: JSON.stringify({ service_name: svc, error_type: err }),
    }),
}