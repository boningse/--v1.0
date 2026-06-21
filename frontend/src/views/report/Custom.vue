<template>
  <div class="report-custom">
    <el-card shadow="hover">
      <template #header>
        <div class="report-header">
          <div class="report-title">定制报表</div>
          <div class="report-controls">
            <el-radio-group v-model="rptType" size="small" @change="load">
              <el-radio-button value="energy">总用电</el-radio-button>
              <el-radio-button value="service">支路</el-radio-button>
              <el-radio-button value="tenement">分户</el-radio-button>
            </el-radio-group>
            <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" size="small" @change="load" style="width:240px" />
            <el-button type="primary" size="small" @click="exportCSV">导出CSV</el-button>
          </div>
        </div>
      </template>

      <!-- 统计卡片 -->
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="8"><div class="metric-card"><div class="metric-label">数据量</div><div class="metric-value">{{ rows.length }}<span class="metric-unit"> 条</span></div></div></el-col>
        <el-col :span="8"><div class="metric-card"><div class="metric-label">数据类型</div><div class="metric-value">{{ {energy:'总用电',service:'支路',tenement:'分户'}[rptType] }}</div></div></el-col>
        <el-col :span="8"><div class="metric-card"><div class="metric-label">日期范围</div><div class="metric-value">{{ dateRange[0] || '--' }} ~ {{ dateRange[1] || '--' }}</div></div></el-col>
      </el-row>

      <!-- 数据表格 -->
      <el-table :data="rows" stripe border size="small" max-height="550" style="width:100%">
        <el-table-column v-for="c in cols" :key="c" :prop="c" :label="colLabel(c)" min-width="120" show-overflow-tooltip />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/index'
import { getCustomReport } from '@/api/index'
import { today, monthStart } from '@/utils/index'

const app = useAppStore()
const rptType = ref<'energy' | 'service' | 'tenement'>('energy')
const dateRange = ref<[string, string]>([monthStart(), today()])
const rows = ref<any[]>([])

const cols = computed(() => {
  if (rows.value.length === 0) return []
  return Object.keys(rows.value[0])
})

function colLabel(key: string) {
  const map: Record<string, string> = {
    timefrom: '时间', energyid: '功能ID', sign: '编号',
    data: '数值', mark: '通道', meter_sign: '电表编号',
    meter_id: '电表ID',
  }
  return map[key] || key
}

async function load() {
  const [s, e] = dateRange.value || []
  if (!s || !e) return
  const res: any = await getCustomReport({
    sign: app.buildingSign, start_date: s, end_date: e, report_type: rptType.value,
  })
  if (res.success) rows.value = res.data || []
}

function exportCSV() {
  if (rows.value.length === 0) return
  const headers = cols.value.map((c: string) => colLabel(c))
  const csv = headers.join(',') + '\n' + rows.value.map(r =>
    cols.value.map(c => r[c] != null ? String(r[c]).replace(/,/g, ' ') : '').join(',')
  ).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
  a.download = `custom_${rptType.value}_${dateRange.value[0]}_${dateRange.value[1]}.csv`; a.click()
}

onMounted(load)
</script>

<style scoped>
.report-custom { display: flex; flex-direction: column; gap: 0; }
.report-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.report-title { font-size: 16px; font-weight: 600; }
.report-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.metric-card { background: #f5f7fa; border-radius: 8px; padding: 16px 20px; border: 1px solid #e8eaef; }
.metric-label { font-size: 13px; color: #8c8c8c; margin-bottom: 4px; }
.metric-value { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.metric-unit { font-size: 12px; font-weight: 400; color: #8c8c8c; }
</style>
