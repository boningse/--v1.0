import { defineStore } from 'pinia'; import { ref } from 'vue'
const DARK_KEY = 'darkMode'
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || ''); const user = ref<any>(null)
  function setToken(t: string) { token.value = t; localStorage.setItem('token', t) }
  function setUser(u: any) { user.value = u }
  function logout() { token.value = ''; user.value = null; localStorage.removeItem('token') }
  return { token, user, setToken, setUser, logout }
})

export const useAppStore = defineStore('app', () => {
  const buildingSign = ref(localStorage.getItem('buildingSign') || '')
  const buildingName = ref(localStorage.getItem('buildingName') || '')
  const darkMode = ref(localStorage.getItem(DARK_KEY) === 'true')
  function toggleDark() {
    darkMode.value = !darkMode.value
    localStorage.setItem(DARK_KEY, String(darkMode.value))
    applyDark(darkMode.value)
  }
  function applyDark(v: boolean) {
    document.documentElement.classList.toggle('dark', v)
  }
  function setBuilding(s: string, n: string) {
    buildingSign.value = s; buildingName.value = n
    localStorage.setItem('buildingSign', s); localStorage.setItem('buildingName', n)
  }
  function clearBuilding() { buildingSign.value = ''; buildingName.value = ''
    localStorage.removeItem('buildingSign'); localStorage.removeItem('buildingName') }
  return { buildingSign, buildingName, darkMode, toggleDark, applyDark, setBuilding, clearBuilding }
})
