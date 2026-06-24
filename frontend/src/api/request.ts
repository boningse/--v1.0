import axios from 'axios'; import { ElMessage } from 'element-plus'
const r = axios.create({ baseURL: '/api', timeout: 30000 })
r.interceptors.request.use(c => { const t = sessionStorage.getItem('token'); if (t) c.headers.Authorization = `Bearer ${t}`; return c })
r.interceptors.response.use(v => v.data, e => { if (e.response?.status === 401) { sessionStorage.removeItem('token'); location.href = location.origin + location.pathname + '#/login'; location.reload() } else ElMessage.error(e.response?.data?.detail || '请求失败'); return Promise.reject(e) })
export default r
