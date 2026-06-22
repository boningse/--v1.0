<template>
  <div class="alert-table">
    <el-card shadow="hover">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:14px;font-weight:600">报警管理</span>
          <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:12px;color:#8c8c8c">共 <strong>{{ tableData.length }}</strong> 条报警</span>
            <el-button size="small" :icon="Search" :loading="loading" @click="loadAlerts">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table :data="tableData" border stripe size="small" v-loading="loading" style="width:100%">
        <el-table-column label="设备名称" min-width="200">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.level === '严重' ? 600 : 400 }">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column label="报警类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === '不上数' ? 'warning' : 'danger'" size="small">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.level === '严重' ? 'danger' : 'warning'" size="small" effect="dark">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后上传时间" width="170" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.level === '严重' ? '#ff4d4f' : '#faad14' }">{{ row.last_time || '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="100" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.value === 0 ? '#ff4d4f' : '#595959' }">{{ row.value !== null ? Number(row.value).toFixed(2) : '--' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="持续时长" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.duration_min !== null" :style="{ color: row.level === '严重' ? '#ff4d4f' : '#faad14', fontWeight:500 }">
              {{ formatDuration(row.duration_min) }}
            </span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column label="描述" min-width="200">
          <template #default="{ row }">
            <span style="color:#8c8c8c">{{ row.desc }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!tableData.length && !loading" description="暂无报警，所有设备运行正常" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getMonitorAlerts } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const tableData = ref<any[]>([])
let refreshTimer: any = null

function formatDuration(min: number): string {
  if (min < 60) return `${min}分钟`
  const h = Math.floor(min / 60)
  const m = min % 60
  return `${h}小时${m}分钟`
}

async function loadAlerts() {
  loading.value = true
  try {
    const r = await getMonitorAlerts(app.buildingSign)
    if (r.success) {
      tableData.value = r.data || []
    }
  } catch {
    ElMessage.error('加载报警数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (app.buildingSign) loadAlerts()
  refreshTimer = setInterval(loadAlerts, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
</style>
