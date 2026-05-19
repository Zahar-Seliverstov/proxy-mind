import axios from 'axios'

const api = axios.create({ baseURL: '/api/fs' })
api.interceptors.response.use(r => r, e => Promise.reject(e.response?.data?.detail ?? e.message))

export const browse = (path, kind = 'dir') =>
  api.get('/browse', { params: { path: path || undefined, kind } }).then(r => r.data)
