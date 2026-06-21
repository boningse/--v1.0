<template>
  <div class="report-general">
    <el-card shadow="hover">
      <template #header>
        <div class="report-header">
          <div class="report-title">通用能耗报表</div>
          <div class="report-controls">
            <el-date-picker v-model="monthVal" type="month" value-format="YYYYMM" size="small" @change="load" style="width:140px" />
            <el-button type="primary" size="small" @click="exportCSV">导出CSV</el-button>
          </div>
        </div>
      </template>

      <!-- 指标卡片 -->
      <el-row :gutter="16" style="margin-bottom:16px">
        <el-col :span="6"><div class="metric-card"><div class="metric-label">月度总能耗</div><div class="metric-value">{{ fmtNum(monthlyTotal) }}<span class="metric-unit"> kWh</span></div></div></el-col>
        <el-col :span="6"><div class="metric-card"><div class="metric-label">日均能耗</div><div class="metric-value">{{ fmtNum(dailyAvg) }}<span class="metric-unit"> kWh</span></div></div></el-col>
        <el-col :span="6"><div class="metric-card"><div class="metric-label">最大日能耗</div><div class="metric-value">{{ fmtNum(maxDay) }}<span class="metric-unit"> kWh</span></div></div></el-col>
        <el-col :span="6"><div class="metric-card"><div class="metric-label">数据天数</div><div class="metric-value">{{ dailyData.length }}<span class="metric-unit"> 天</span></div></div></el-col>
      </el-row>

      <!-- 每日能耗明细 -->
      <div class="section-title">每日能耗明细</div>
      <el-table :data="dailyData" stripe border size="small" max-height="360" show-summary :summary-method="dailySummary" style="margin-bottom:16px">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="total" label="日能耗(kWh)" width="140" sortable />
        <el-table-column prop="pct" label="占比(%)" width="120">
          <template #default="{ row }">{{ row.pct }}</template>
        </el-table-column>
        <el-table-column prop="cum" label="累计(kWh)" width="140" />
        <el-table-column prop="cumPct" label="累计占比(%)" width="120" />
      </el-table>

      <!-- 支路能耗汇总 -->
      <el-tabs style="margin-top:4px">
        <el-tab-pane label="支路能耗汇总">
          <el-table :data="svcData" stripe border size="small" max-height="320" show-summary :summary-method="svcSummary">
            <el-table-column prop="name" label="支路名称" min-width="180" />
            <el-table-column prop="total" label="能耗(kWh)" width="140" sortable />
            <el-table-column prop="pct" label="占比(%)" width="120" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="分户能耗汇总">
          <el-table :data="tenData" stripe border size="small" max-height="320" show-summary :summary-method="svcSummary">
            <el-table-column prop="name" label="分户名称" min-width="180" />
            <el-table-column prop="total" label="能耗(kWh)" width="140" sortable />
            <el-table-column prop="pct" label="占比(%)" width="120" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/index'
import { getGeneralReport } from '@/api/index'
import { fmtNum, curMonth } from '@/utils/index'

const app = useAppStore()
const monthVal = ref(curMonth())
const dailyData = ref<any[]>([])
const svcData = ref<any[]>([])
const tenData = ref<any[]>([])
const monthlyTotal = ref(0)
const dailyAvg = ref(0)
const maxDay = ref(0)

function aggregateDaily(rows: any[]): any[] {
  const dayMap: Record<string, number> = {}
  for (const r of rows) {
    const d = (r.timefrom || '').slice(0, 10)
    if (d) dayMap[d] = (dayMap[d] || 0) + Number(r.data || 0)
  }
  const dates = Object.keys(dayMap).sort()
  const vals = dates.map(d => ({ date: d, total: Math.round(dayMap[d] * 100) / 100 }))
  const sum = vals.reduce((s, v) => s + v.total, 0)
  let cum = 0
  vals.forEach(v => {
    v.pct = sum > 0 ? (v.total / sum * 100).toFixed(1) : '0.0'
    cum += v.total
    v.cum = Math.round(cum * 100) / 100
    v.cumPct = sum > 0 ? (cum / sum * 100).toFixed(1) : '0.0'
  })
  return vals
}

async function load() {
  const res: any = await getGeneralReport({ sign: app.buildingSign, year_month: monthVal.value })
  if (res.success) {
    const d = res.data
    monthlyTotal.value = d.monthly_total || 0
    dailyData.value = aggregateDaily(d.daily || [])
    dailyAvg.value = dailyData.value.length > 0 ? Math.round(monthlyTotal.value / dailyData.value.length * 100) / 100 : 0
    maxDay.value = dailyData.value.reduce((m, r) => Math.max(m, r.total), 0)

    svcData.value = (d.service_summary || []).map((s: any) => ({
      name: s.name, total: Math.round((s.total || 0) * 100) / 100,
      pct: monthlyTotal.value > 0 ? ((s.total || 0) / monthlyTotal.value * 100).toFixed(1) : '0.0'
    })).sort((a: any, b: any) => b.total - a.total)

    tenData.value = (d.tenement_summary || []).map((t: any) => ({
      name: t.name, total: Math.round((t.total || 0) * 100) / 100,
      pct: monthlyTotal.value > 0 ? ((t.total || 0) / monthlyTotal.value * 100).toFixed(1) : '0.0'
    })).sort((a: any, b: any) => b.total - a.total)
  }
}

function dailySummary(param: any) {
  const { columns, data } = param
  const sums = ['']
  for (let i = 1; i < columns.length; i++) {
    const prop = columns[i].property
    if (prop === 'pct' || prop === 'cumPct') { sums.push('-'); continue }
    const total = data.reduce((s: number, r: any) => s + (Number(r[prop]) || 0), 0)
    sums.push(prop === 'total' || prop === 'cum' ? Math.round(total * 100) / 100 + '' : total + '')
  }
  return ['合计', ...sums.slice(1)]
}

function svcSummary(param: any) {
  const { columns, data } = param
  const sums = ['合计']
  for (let i = 1; i < columns.length; i++) {
    const prop = columns[i].property
    if (prop === 'pct') { sums.push('100%'); continue }
    sums.push(Math.round(data.reduce((s: number, r: any) => s + (Number(r[prop]) || 0), 0) * 100) / 100 + '')
  }
  return sums
}

function exportCSV() {
  const rows = [['日期', '日能耗(kWh)', '占比(%)', '累计(kWh)', '累计占比(%)']]
  for (const r of dailyData.value) rows.push([r.date, String(r.total), r.pct, String(r.cum), r.cumPct])
  rows.push([])
  rows.push(['支路名称', '能耗(kWh)', '占比(%)'])
  for (const r of svcData.value) rows.push([r.name, String(r.total), r.pct])
  rows.push([])
  rows.push(['分户名称', '能耗(kWh)', '占比(%)'])
  for (const r of tenData.value) rows.push([r.name, String(r.total), r.pct])
  const csv = rows.map(r => r.join(',')).join('\n')
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
  a.download = `energy_report_${monthVal.value}.csv`; a.click()
}

onMounted(load)
</script>

<style scoped>
.report-general { display: flex; flex-direction: column; gap: 0; }
.report-header { display: flex; justify-content: space-between; align-items: center; }
.report-title { font-size: 16px; font-weight: 600; }
.report-controls { display: flex; gap: 8px; align-items: center; }
.metric-card { background: #f5f7fa; border-radius: 8px; padding: 16px 20px; border: 1px solid #e8eaef; }
.metric-label { font-size: 13px; color: #8c8c8c; margin-bottom: 4px; }
.metric-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.metric-unit { font-size: 13px; font-weight: 400; color: #8c8c8c; }
.section-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 8px; }
</style>
