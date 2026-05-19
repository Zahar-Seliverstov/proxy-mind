import axios from 'axios'

const api = axios.create({ baseURL: '/api/ollama' })
api.interceptors.response.use(r => r, e => Promise.reject(e.response?.data?.detail ?? e.message))

export const getModels = () => api.get('/models').then(r => r.data.models)
