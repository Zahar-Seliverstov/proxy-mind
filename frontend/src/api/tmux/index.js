import axios from 'axios'

const api = axios.create({ baseURL: '/api/tmux' })

api.interceptors.response.use(
  r => r,
  e => Promise.reject(e.response?.data?.detail ?? e.message)
)

export default api
