<template>
  <div class="layout">
    <el-container style="height:100vh">
      <div v-if="mobileOpen" class="mobile-overlay" @click="mobileOpen=false"></div>
      <el-aside :width="sidebarWidth" class="sidebar" :class="{ 'mobile-hide': isMobile && !mobileOpen }">
        <div class="logo">
          <span v-if="!isCollapsed || isMobile">{{ '能耗监测' }}</span>
          <span v-else>{{ '监' }}</span>
        </div>
        <el-menu :default-active="route.path" router :collapse="!isMobile && isCollapsed" background-color="#001529" text-color="#ffffffb3" active-text-color="#1890ff">
          <el-menu-item index="/home"><el-icon><Odometer/></el-icon><span>{{ '首页' }}</span></el-menu-item>
          <el-sub-menu index="energy"><template #title><el-icon><DataLine/></el-icon><span>{{ '分项能耗' }}</span></template>
            <el-menu-item index="/energy-analysis">{{ '分项分析' }}</el-menu-item>
            <el-menu-item index="/energy-compare">{{ '分项对比' }}</el-menu-item>
            <el-menu-item index="/energy-ratio">{{ '分项比例' }}</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="tenement"><template #title><el-icon><House/></el-icon><span>{{ '分户能耗' }}</span></template>
            <el-menu-item index="/tenement-analysis">{{ '分户分析' }}</el-menu-item>
            <el-menu-item index="/tenement-compare">{{ '分户对比' }}</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="equipment"><template #title><el-icon><Setting/></el-icon><span>{{ '设备能耗' }}</span></template>
            <el-menu-item index="/equipment-analysis">{{ '设备分析' }}</el-menu-item>
            <el-menu-item index="/equipment-compare">{{ '设备对比' }}</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="monitor"><template #title><el-icon><Cpu/></el-icon><span>{{ '监测数据' }}</span></template>
            <el-menu-item index="/realtime-data">{{ '实时数据' }}</el-menu-item>
            <el-menu-item index="/data-table">{{ '原始数据' }}</el-menu-item>
            <el-menu-item index="/data-alert">{{ '报警管理' }}</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="quota"><template #title><el-icon><Aim/></el-icon><span>{{ '定额管理' }}</span></template>
            <el-menu-item index="/quota-analysis">{{ '定额分析' }}</el-menu-item>
            <el-menu-item index="/quota-footprint">{{ '能耗足迹' }}</el-menu-item>
            <el-menu-item index="/quota-diagnosis">{{ '节能诊断' }}</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="report"><template #title><el-icon><Document/></el-icon><span>{{ '报表打印' }}</span></template>
            <el-menu-item index="/report-general">{{ '分项报表' }}</el-menu-item>
            <el-menu-item index="/report-branch">{{ '分户报表' }}</el-menu-item>
            <el-menu-item index="/report-equipment">{{ '设备报表' }}</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-button text size="small" class="menu-btn" @click="toggleMenu">{{ isMobile && !mobileOpen ? '☰' : !isCollapsed ? '✕' : '☰' }}</el-button>
            <el-select v-if="buildingList.length > 0" v-model="currSign" size="small" style="width:140px" @change="switchBuilding" :teleported="false">
              <el-option v-for="b in buildingList" :key="b.sign" :label="b.name" :value="b.sign" />
            </el-select>
            <span class="header-title">{{ buildingName || route.meta.title }}</span>
          </div>
          <div class="hr">
            <span class="user-name">{{ auth.user?.username }}</span>
            <el-button text size="small" @click="app.toggleDark()" :title="app.darkMode ? '切换日间模式' : '切换夜间模式'" style="font-size:18px">{{ app.darkMode ? '🌜' : '🌛' }}</el-button>
            <el-button text size="small" @click="doLogout" class="logout-btn">{{ '退出' }}</el-button>
          </div>
        </el-header>
        <el-main class="main"><router-view/></el-main>
      </el-container>
    </el-container>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'; import { useRoute, useRouter } from 'vue-router'; import { useAuthStore, useAppStore } from '@/stores/index'; import { getBuildings } from '@/api/index'
const route = useRoute(); const router = useRouter(); const auth = useAuthStore(); const app = useAppStore()
const isCollapsed = ref(false); const mobileOpen = ref(false)
const isMobile = ref(false)
const buildingList = ref<any[]>([]); const currSign = ref(''); const buildingName = ref('')
async function loadBuildings() {
  try {
    const r: any = await getBuildings()
    if (r.success && r.data) {
      buildingList.value = r.data
      currSign.value = app.buildingSign || r.data[0]?.sign || ''
      const cur = r.data.find((b: any) => b.sign === currSign.value)
      buildingName.value = cur?.name || app.buildingName || ''
    }
  } catch(e) { console.warn('load buildings error', e) }
}
function switchBuilding(sign: string) {
  const b = buildingList.value.find((x: any) => x.sign === sign)
  if (b) { app.setBuilding(b.sign, b.name); buildingName.value = b.name; location.reload() }
}
watch(() => app.buildingSign, (v) => { currSign.value = v || '' })
onMounted(() => { updateMobile(); window.addEventListener('resize', updateMobile); loadBuildings() })
function updateMobile() { isMobile.value = window.innerWidth < 768; if (!isMobile.value) mobileOpen.value = false }
onUnmounted(() => window.removeEventListener('resize', updateMobile))
// Auto-close mobile sidebar on route change
watch(() => route.path, () => { if (isMobile.value) mobileOpen.value = false })
const sidebarWidth = computed(() => { if (isMobile.value) return '200px'; return isCollapsed.value ? '64px' : '200px' })
function toggleMenu() { if (isMobile.value) mobileOpen.value = !mobileOpen.value; else isCollapsed.value = !isCollapsed.value }
function doLogout() { auth.logout(); app.clearBuilding(); router.push('/login') }
</script>
<style scoped>
.sidebar{background:#001529;transition:width .25s ease;overflow-y:auto;overflow-x:hidden;z-index:999}
.sidebar.mobile-hide{width:0!important;min-width:0!important;overflow:hidden;padding:0}
.mobile-overlay{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:998}
.logo{display:flex;align-items:center;padding:16px 20px;color:#fff;font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden}
.header{display:flex;align-items:center;justify-content:space-between;background:var(--header-bg);border-bottom:1px solid var(--header-border);padding:0 12px;height:48px;font-size:14px;color:var(--header-text);gap:8px}
.header-left{display:flex;align-items:center;gap:6px;min-width:0;flex:1}
.header-title{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.menu-btn{font-size:18px!important;padding:4px 6px!important;flex-shrink:0}
.hr{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-secondary);flex-shrink:0}
.user-name{display:none}
.logout-btn{flex-shrink:0}
.main{background:var(--main-bg);padding:12px}
@media(min-width:768px){.user-name{display:inline}}
@media(max-width:767px){
  .header{padding:0 8px;font-size:13px}
  .header-title{font-size:13px}
  .main{padding:8px}
  .el-menu-item,.el-sub-menu__title{font-size:13px!important}
}
</style>
