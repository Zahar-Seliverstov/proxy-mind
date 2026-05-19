import api from './index.js'

export const getAll  = ()                          => api.get('/sessions').then(r => r.data.sessions)
export const create  = (name, path)                => api.post('/sessions', { session_name: name || null, start_directory: path || null })
export const remove  = (name)                      => api.delete(`/sessions/${name}`)
export const attach  = (name, windowId, paneId)    => api.post(`/sessions/${name}/attach`, { terminal_name: 'konsole', window_id: windowId, pane_id: paneId })
