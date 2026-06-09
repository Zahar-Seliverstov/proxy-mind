import axios from 'axios'

const api = axios.create({ baseURL: '/api/ai' })

function formatDetail(detail) {
    if (Array.isArray(detail)) {
        return detail.map(d => {
            const loc = Array.isArray(d.loc) ? d.loc.join('.') : ''
            const msg = d.msg ?? JSON.stringify(d)
            return loc ? `${loc}: ${msg}` : msg
        }).join('; ')
    }
    if (detail && typeof detail === 'object') return JSON.stringify(detail)
    return detail
}

api.interceptors.response.use(r => r, e => Promise.reject(formatDetail(e.response?.data?.detail) ?? e.message))

export const getModes        = ()        => api.get('/modes').then(r => r.data.modes)
export const validate        = (payload) => api.post('/validate', payload).then(r => r.data)
export const getQuestions    = (payload) => api.post('/questions', payload).then(r => r.data)
export const generate        = (payload) => api.post('/generate', payload).then(r => r.data)
export const run             = (payload) => api.post('/run', payload).then(r => r.data)
export const getRun          = (paneId)  => api.get(`/runs/${encodeURIComponent(paneId)}`).then(r => r.data)
export const stopRun         = (paneId)  => api.post(`/runs/${encodeURIComponent(paneId)}/stop`).then(r => r.data)
export const pauseRun        = (paneId)  => api.post(`/runs/${encodeURIComponent(paneId)}/pause`).then(r => r.data)
export const unpauseRun      = (paneId)  => api.post(`/runs/${encodeURIComponent(paneId)}/unpause`).then(r => r.data)
export const resumeRun       = (paneId)  => api.post(`/runs/${encodeURIComponent(paneId)}/resume`).then(r => r.data)
