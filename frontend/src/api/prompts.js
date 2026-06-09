import axios from 'axios'

const api = axios.create({ baseURL: '/api/ai' })
api.interceptors.response.use(r => r, e => Promise.reject(e.response?.data?.detail ?? e.message))

export const getPrompts    = ()                    => api.get('/prompts').then(r => r.data.prompts)
export const updatePrompt  = (name, content)       => api.patch(`/prompts/${name}`, { content }).then(r => r.data)
