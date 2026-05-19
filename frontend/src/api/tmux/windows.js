import api from './index.js'

export const create = (sessionName) => api.post('/windows', { session_name: sessionName })
export const remove = (windowId)    => api.delete(`/windows/${windowId}`)
