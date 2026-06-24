<template>
  <div class="data-table">
    <!-- 顶部控制栏 -->
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="filter-group">
          <span class="label">时间范围</span>
          <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" size="small" style="width:260px" range-separator=" - " />
          <el-button type="primary" size="small" :icon="Search" :loading="loading" @click="doSearch">查询</el-button>
        </div>
        <div class="filter-group" style="margin-left:auto">
          <span class="label">单位: {{ conversionInfo?.unit || 'kWh' }}</span>
        </div>
      </div>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="hover" style="margin-top:12px">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span style="font-size:14px;font-weight:600">支路原始数据</span>
          <span v-if="reportTotal" style="font-size:13px;color:var(--text-secondary)">总能耗: <strong style="color:#1890ff">{{ Number(reportTotal).toFixed(3) }}</strong> {{ conversionInfo?.unit || 'kWh' }}</span>
        </div>
      </template>
      <el-table :data="tableData" border stripe size="small" v-loading="loading" style="width:100%" :tree-props="{ children: 'children', hasChildren: 'has_children' }" row-key="id" default-expand-all>
        <el-table-column label="支路名称" min-width="180">
          <template #default="{ row }">
            <span :style="{ paddingLeft: row.level * 24 + 'px', fontWeight: row.level === 0 ? 600 : 400, color: 'var(--text-primary)' }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="查询时间" width="240" align="center">
          <template #default="{ row }">
            <span style="font-size:12px;color:var(--text-secondary)">{{ row.start_time }} ~ {{ row.end_time }}</span>
          </template>
        </el-table-column>
        <el-table-column label="起始数据" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.first_val !== null" style="color:#1890ff;font-weight:600;font-size:13px">{{ Number(row.first_val).toFixed(3) }}</span>
            <span v-else style="color:var(--text-secondary);font-size:12px">--</span>
          </template>
        </el-table-column>
        <el-table-column label="截止数据" width="120" align="right">
          <template #default="{ row }">
            <span v-if="row.last_val !== null" style="color:#1890ff;font-weight:600;font-size:13px">{{ Number(row.last_val).toFixed(3) }}</span>
            <span v-else style="color:var(--text-secondary);font-size:12px">--</span>
          </template>
        </el-table-column>
        <el-table-column label="总能耗" width="110" align="right">
          <template #default="{ row }">
            <span :style="{ fontWeight: row.level === 0 ? 600 : 400 }">{{ Number(row.total).toFixed(3) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="占比" width="70" align="right">
          <template #default="{ row }">
            <span>{{ row.pct }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.has_data ? 'success' : 'danger'" size="small">{{ row.has_data ? '有' : '无' }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!tableData.length && !loading" description="请选择时间范围后查询" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getServiceReport } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const tableData = ref<any[]>([])
const conversionInfo = ref<any>(null)
const reportTotal = ref(0)

const now = new Date()
const dateRange = ref<any>([
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`,
  now.toISOString().slice(0, 10)
])

async function doSearch() {
  if (!dateRange.value || !dateRange.value[0]) {
    ElMessage.warning('请选择时间范围')
    return
  }
  loading.value = true
  try {
    const r = await getServiceReport({
      sign: app.buildingSign,
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      conversion_type: 3,
    })
    if (r.success) {
      tableData.value = r.data || []
      conversionInfo.value = r.conversion || null
      reportTotal.value = r.total || 0
    }
  } catch {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (app.buildingSign) doSearch()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}
</style>
