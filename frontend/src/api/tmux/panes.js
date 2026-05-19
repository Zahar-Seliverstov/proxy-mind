import api from './index.js'

export const create     = (windowId, vertical, startDirectory) => api.post('/panes', { window_id: windowId, vertical, start_directory: startDirectory })
export const remove     = (paneId)             => api.delete(`/panes/${paneId}`)
export const getContent = (paneId)             => api.get(`/panes/${paneId}/content`).then(r => r.data.content)
