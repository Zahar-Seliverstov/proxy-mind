import axios from 'axios'

const api = axios.create({ baseURL: '/api/settings' })
api.interceptors.response.use(r => r, e => Promise.reject(e.response?.data?.detail ?? e.message))

export const getSettings    = ()        => api.get('').then(r => r.data)
export const updateSettings = (patch)   => api.patch('', patch).then(r => r.data)
