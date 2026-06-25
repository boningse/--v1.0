<template><div class="login-page"><div class="login-box"><h2>能耗监测子系统</h2><el-form :model="f" size="large"><el-form-item><el-input v-model="f.useraccount" placeholder="账号" prefix-icon="User"/></el-form-item><el-form-item><el-input v-model="f.userpassword" type="password" placeholder="密码" prefix-icon="Lock" show-password @keyup.enter="doLogin"/></el-form-item><el-form-item><el-button type="primary" :loading="loading" style="width:100%" @click="doLogin">登 录</el-button></el-form-item></el-form></div>
<div v-if="showSelector" class="building-overlay">
  <div class="building-dialog">
    <h3>请选择建筑</h3>
    <div class="building-list">
      <div v-for="b in buildings" :key="b.sign" class="building-card" @click="selectBuilding(b)">
        <div class="bc-name">{{ b.name }}</div>
        <div class="bc-sign">{{ b.sign }}</div>
      </div>
    </div>
  </div>
</div>
</div></template>
<script setup lang="ts">
import { reactive, ref } from 'vue'; import { useRouter } from 'vue-router'; import { useAuthStore, useAppStore } from '@/stores/index'; import { login, getMyBuilding, getTitle, getBuildings } from '@/api/index'; import { ElMessage } from 'element-plus'
const router = useRouter(); const auth = useAuthStore(); const app = useAppStore()
const loading = ref(false); const f = reactive({ useraccount: 'admin', userpassword: '' })
const showSelector = ref(false); const buildings = ref<any[]>([])
function selectBuilding(b: any) { app.setBuilding(b.sign, b.name); showSelector.value = false; router.push('/home'); ElMessage.success('登录成功 - ' + b.name) }
async function doLogin() {
  loading.value = true
  try {
    const r: any = await login(f)
    if (!r.success) { ElMessage.error(r.message); return }
    auth.setToken(r.token); auth.setUser(r.user)
    const br: any = await getBuildings()
    if (br.success) {
      const list = br.data || []
      if (list.length === 0) { ElMessage.error('无建筑权限'); return }
      if (list.length === 1 || !br.is_admin) {
        app.setBuilding(list[0].sign, list[0].name)
        router.push('/home'); ElMessage.success('登录成功')
      } else {
        buildings.value = list; showSelector.value = true
      }
    }
  } catch { ElMessage.error('登录失败') }
  finally { loading.value = false }
}
</script>
<style scoped>.login-page{height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0f2027,#203a43,#2c5364);position:relative}.login-box{width:380px;background:#fff;border-radius:8px;padding:40px 36px 30px;box-shadow:0 8px 40px rgba(0,0,0,.3)}.login-box h2{text-align:center;margin-bottom:28px;color:#1a1a2e;font-size:22px}
.building-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9999;display:flex;align-items:center;justify-content:center}
.building-dialog{background:#fff;border-radius:12px;padding:32px;width:420px;max-height:70vh;overflow-y:auto}
.building-dialog h3{text-align:center;margin-bottom:20px;color:#1a1a2e;font-size:18px}
.building-list{display:flex;flex-direction:column;gap:10px}
.building-card{padding:14px 18px;border:1px solid #f0f0f0;border-radius:8px;cursor:pointer;transition:all .2s}
.building-card:hover{border-color:#1890ff;background:#e6f7ff}
.bc-name{font-size:15px;font-weight:600;color:#333;margin-bottom:2px}
.bc-sign{font-size:11px;color:#999}
</style>
