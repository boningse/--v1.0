import { defineStore } from 'pinia'; import { ref } from 'vue'
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
  function setBuilding(s: string, n: string) {
    buildingSign.value = s; buildingName.value = n
    localStorage.setItem('buildingSign', s); localStorage.setItem('buildingName', n)
  }
  function clearBuilding() { buildingSign.value = ''; buildingName.value = ''
    localStorage.removeItem('buildingSign'); localStorage.removeItem('buildingName') }
  return { buildingSign, buildingName, setBuilding, clearBuilding }
})
