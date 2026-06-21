<template>
  <div class="report-branch">
    <el-card shadow="hover">
      <template #header>
        <div class="report-header">
          <div class="report-title">支路能耗报表</div>
          <div class="report-controls">
            <el-select v-model="energyType" size="small" style="width:100px" @change="load">
              <el-option v-for="et in energyTypes" :key="et.id" :label="et.name" :value="et.id" />
            </el-select>
            <el-date-picker v-model="dates" type="daterange" value-format="YYYY-MM-DD" size="small" @change="load" style="width:240px" />
            <el-button type="primary" size="small" @click="exportCSV">导出CSV</el-button>
          </div>
        </div>
      </template>

      <!-- 指标卡片 -->
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="8"><div class="metric-card"><div class="metric-label">统计周期</div><div class="metric-value">{{ dates[0] || '--' }} ~ {{ dates[1] || '--' }}</div></div></el-col>
        <el-col :span="8"><div class="metric-card"><div class="metric-label">支路总数</div><div class="metric-value">{{ tableData.length }}<span class="metric-unit"> 条</span></div></div></el-col>
        <el-col :span="8"><div class="metric-card"><div class="metric-label">合计能耗</div><div class="metric-value">{{ fmtNum(allTotal) }}<span class="metric-unit"> kWh</span></div></div></el-col>
      </el-row>

      <!-- 支路数据表 -->
      <el-table :data="tableData" stripe border size="small" max-height="520" show-summary :summary-method="getSummaries">
        <el-table-column type="index" width="50" label="#" fixed />
        <el-table-column prop="name" label="支路名称" width="200" fixed />
        <el-table-column :prop="d" :label="d" min-width="90" v-for="d in days" :key="d">
          <template #default="{ row }">{{ row[d] ? Number(row[d]).toFixed(2) : '--' }}</template>
        </el-table-column>
        <el-table-column prop="_total" label="合计" width="110" fixed="right" sortable>
          <template #default="{ row }">{{ fmtNum(row._total) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/index'
import { getBranchReport } from '@/api/index'
import { fmtNum, today, monthStart } from '@/utils/index'

const app = useAppStore()
const dates = ref<[string, string]>([monthStart(), today()])
const energyType = ref(1)
const energyTypes = [
  { id: 1, name: '电' }, { id: 2, name: '水' }, { id: 3, name: '冷量' },
  { id: 4, name: '热量' }, { id: 5, name: '燃气' }, { id: 6, name: '蒸汽' },
]
const days = ref<string[]>([])
const tableData = ref<any[]>([])
const allTotal = ref(0)

async function load() {
  const [s, e] = dates.value || []
  if (!s || !e) return
  const res: any = await getBranchReport({
    sign: app.buildingSign, start_date: s, end_date: e, energy_type: energyType.value,
  })
  if (res.success) {
    days.value = res.data.days || []
    const items = (res.data.services || []).map((r: any) => {
      const total = days.value.reduce((s: number, d: string) => s + (Number(r[d]) || 0), 0)
      return { ...r, _total: Math.round(total * 100) / 100 }
    })
    tableData.value = items
    allTotal.value = items.reduce((s: number, r: any) => s + r._total, 0)
  }
}

function getSummaries(param: any) {
  const { columns, data } = param
  const sums: string[] = ['合计']
  for (let i = 1; i < columns.length; i++) {
    const col = columns[i].property
    if (col === 'index') { sums.push(''); continue }
    const sum = data.reduce((a: number, r: any) => a + (Number(r[col]) || 0), 0)
    sums.push(col === '_total' ? Math.round(sum * 100) / 100 + '' : Math.round(sum * 100) / 100 + '')
  }
  return sums
}

function exportCSV() {
  if (!tableData.value.length) return
  const headers = ['支路名称', ...days.value, '合计']
  const csv = headers.join(',') + '\n' + tableData.value.map(r =>
    [r.name, ...days.value.map(d => r[d] || 0), r._total].join(',')
  ).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
  a.download = `branch_report_${dates.value[0]}_${dates.value[1]}.csv`; a.click()
}

onMounted(load)
</script>

<style scoped>
.report-branch { display: flex; flex-direction: column; gap: 0; }
.report-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.report-title { font-size: 16px; font-weight: 600; }
.report-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.metric-card { background: #f5f7fa; border-radius: 8px; padding: 16px 20px; border: 1px solid #e8eaef; }
.metric-label { font-size: 13px; color: #8c8c8c; margin-bottom: 4px; }
.metric-value { font-size: 18px; font-weight: 700; color: #1a1a2e; }
.metric-unit { font-size: 12px; font-weight: 400; color: #8c8c8c; }
</style>
