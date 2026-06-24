<template>
  <div class="quota-footprint">
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="filter-group">
          <span class="label"><el-icon><Clock /></el-icon></span>
          <el-date-picker v-model="queryYear" type="year" value-format="YYYY" size="small" style="width:140px" />
          <el-button type="primary" size="small" :icon="Search" :loading="loading" @click="loadData">查询</el-button>
          <span v-if="buildingInfo.name" style="font-size:13px;color:#666;margin-left:8px">{{ buildingInfo.name }} · {{ buildingInfo.type }}</span>
        </div>
        <div style="font-size:12px;color:#999">基于山东省公共机构用电定额标准 · 分项用电评价</div>
      </div>
    </el-card>
    <el-row :gutter="12" style="margin-top:12px">
      <el-col :span="6" v-for="item in summaryCards" :key="item.label">
        <div class="summary-item" :style="{ background: item.bg }">
          <span class="summary-label">{{ item.label }}</span>
          <div class="summary-row"><span class="summary-value">{{ item.value }}</span><span class="summary-unit">{{ item.unit }}</span></div>
        </div>
      </el-col>
    </el-row>
    <el-row :gutter="12" style="margin-top:12px">
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header><span class="card-title">用电足迹雷达</span></template>
          <div ref="chartRadarRef" style="width:100%;height:380px"></div>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><span class="card-title">年度用电趋势</span></template>
          <div ref="chartTrendRef" style="width:100%;height:380px"></div>
        </el-card>
      </el-col>
    </el-row>
    <el-card shadow="hover" style="margin-top:12px">
      <template #header><span class="card-title">分项用电足迹</span></template>
      <el-row :gutter="16">
        <el-col :span="8" v-for="item in footprintItems" :key="item.name" style="margin-bottom:12px">
          <div class="footprint-card">
            <div class="fp-header">
              <span class="fp-icon" :style="{ background: item.bg }">{{ item.icon }}</span>
              <span class="fp-name">{{ item.name }}</span>
            </div>
            <div class="fp-value">{{ item.actual }} <small>{{ item.unit }}</small></div>
            <div class="fp-bar-wrap">
              <div class="fp-bar-label">定额 {{ item.quota }}{{ item.unit }}</div>
              <el-progress :percentage="item.pct" :color="item.pct > 100 ? '#ff4d4f' : '#52c41a'" :stroke-width="8" />
            </div>
            <div class="fp-status">
              <el-tag :type="item.pct <= 100 ? 'success' : 'danger'" size="small">{{ item.pct <= 100 ? '达标' : '超标' }}</el-tag>
              <span class="fp-diff">{{ item.pct <= 100 ? '余量' : '超量' }} {{ item.diff }}{{ item.unit }}</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
    <div v-if="pageError" style="padding:40px;text-align:center;color:#ff4d4f">
      <h3>页面加载异常</h3><p style="font-size:12px;margin-top:8px">{{ pageError }}</p>
      <el-button size="small" style="margin-top:12px" @click="pageError='';loadData()">重试</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, onErrorCaptured } from 'vue'
import { Clock, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { fmtNum } from '@/utils/index'
import request from '@/api/request'
import * as echarts from 'echarts'

// 山东省用电=>标准煤折算系数
const SD_EF = 0.31 // kgce/kWh

const app = useAppStore()
const loading = ref(false)
const pageError = ref('')
const queryYear = ref(new Date().getFullYear().toString())
const chartRadarRef = ref<HTMLElement|null>(null)
const chartTrendRef = ref<HTMLElement|null>(null)
let chartRadar: echarts.ECharts|null = null
let chartTrend: echarts.ECharts|null = null

const buildingInfo = reactive({ name: '', type: '', area: 0 })
const energyData = reactive({ total: 0, perArea: 0, monthly: [] as number[] })

const subItems = reactive<Record<number, number>>({11:0,12:0,13:0,14:0})
const QUOTA: Record<string, { constraint: number; baseline: number; guidance: number }> = {
  '行政机关': { constraint: 35, baseline: 28, guidance: 20 },
  '高等院校': { constraint: 30, baseline: 24, guidance: 17 },
  '中小学校': { constraint: 18, baseline: 13, guidance: 9 },
  '医疗机构': { constraint: 65, baseline: 50, guidance: 35 },
  '文化场馆': { constraint: 25, baseline: 18, guidance: 12 },
  '体育场馆': { constraint: 40, baseline: 30, guidance: 20 },
  '科研机构': { constraint: 32, baseline: 25, guidance: 18 },
}
const DEF = { constraint: 40, baseline: 30, guidance: 20 }
const MONTHLY_WEIGHTS = [0.105, 0.095, 0.08, 0.065, 0.06, 0.08, 0.095, 0.095, 0.075, 0.065, 0.08, 0.105]
const stdVal = computed(() => QUOTA[buildingInfo.type] || DEF)
const evalData = computed(() => {
  const pa = energyData.perArea; const s = stdVal.value
  return { grade: pa <= s.guidance ? 'A' : pa <= s.baseline ? 'B' : pa <= s.constraint ? 'C' : 'D', label: pa <= s.guidance ? '优秀' : pa <= s.baseline ? '良好' : pa <= s.constraint ? '一般' : '超标' }
})
const summaryCards = computed(() => [
  { label: '综合评分', value: evalData.value.grade, unit: '', bg: 'linear-gradient(135deg,#13c785,#0fa86b)' },
  { label: '单位面积能耗', value: fmtNum(energyData.perArea, 2), unit: 'kgce/m²', bg: 'linear-gradient(135deg,#1890ff,#40a9ff)' },
  { label: '碳足迹估算', value: fmtNum(energyData.total * 2.6, 2), unit: 'tCO₂', bg: 'linear-gradient(135deg,#fa8c16,#ffa940)' },
  { label: '环境等级', value: evalData.value.grade, unit: '', bg: 'linear-gradient(135deg,#722ed1,#b37feb)' },
])
const monthlyStd = computed(() => {
  const s = stdVal.value; const a = buildingInfo.area || 1; const at = (v: number) => v * a / 1000
  return { constraint: MONTHLY_WEIGHTS.map(w => Math.round(at(s.constraint) * w * 100) / 100), baseline: MONTHLY_WEIGHTS.map(w => Math.round(at(s.baseline) * w * 100) / 100), guidance: MONTHLY_WEIGHTS.map(w => Math.round(at(s.guidance) * w * 100) / 100) }
})

const SUB_META: Record<number, {name: string; icon: string; bg: string}> = {
  11: { name: '照明', icon: '💡', bg: '#f9f0ff' },
  12: { name: '空调', icon: '❄️', bg: '#e6f7ff' },
  13: { name: '动力', icon: '⚙️', bg: '#fff7e6' },
  14: { name: '特殊', icon: '🔌', bg: '#fff1f0' },
}
const footprintItems = computed(() => {
  const s = stdVal.value; const area = buildingInfo.area || 1
  const totalActual = [11,12,13,14].reduce((a, id) => a + (subItems[id] || 0), 0) || 1
  const totalQuota = s.baseline * area / 1000
  return [11,12,13,14].map(id => {
    const actual = subItems[id] || 0
    const quota = totalQuota * (actual / totalActual)
    const meta = SUB_META[id]
    const pct = Math.round(actual / Math.max(quota, 0.01) * 100)
    return { ...meta, id, unit: 'tce', actual: +actual.toFixed(2), quota: +quota.toFixed(2), pct, diff: Math.abs(actual - quota).toFixed(1) }
  })
})

function initCharts() {
  try {
    if (chartRadarRef.value) {
      chartRadar?.dispose(); chartRadar = echarts.init(chartRadarRef.value)
      const fi = footprintItems.value || []
      const indicators = fi.map(i => ({ name: i.name, max: 100 }))
      const actualVals = fi.map(i => Math.min(i.pct, 100))
      chartRadar.setOption({
        radar: { indicator: indicators, shape: 'circle', center: ['50%','50%'], radius: '65%', axisName: { color: '#666', fontSize: 11 } },
        series: [{ type: 'radar', data: [{ value: actualVals, name: '本年度', areaStyle: { color: 'rgba(24,144,255,.2)' }, lineStyle: { color: '#1890ff', width: 2 } }, { value: fi.map(() => 100), name: '基准值', areaStyle: { color: 'rgba(19,199,133,.15)' }, lineStyle: { color: '#13c785', width: 2, type: 'dashed' } }] }],
        legend: { data: ['本年度', '基准值'], bottom: 0, textStyle: { fontSize: 11 } },
      })
    }
    if (chartTrendRef.value) {
      chartTrend?.dispose(); chartTrend = echarts.init(chartTrendRef.value)
      const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
      const cum = energyData.monthly.reduce((a: number[], v, i) => [...a, (a[i-1] || 0) + v], [] as number[])
      chartTrend.setOption({
        tooltip: { trigger: 'axis' }, legend: { data: ['月能耗', '累计能耗'] },
        grid: { left: 60, right: 20, top: 40, bottom: 30 },
        xAxis: { type: 'category', data: months, axisLabel: { fontSize: 11 } },
        yAxis: [{ type: 'value', name: '月(tce)' }, { type: 'value', name: '累计(tce)' }],
        series: [{ name: '月能耗', type: 'bar', data: energyData.monthly, itemStyle: { color: '#1890ff', borderRadius: [4,4,0,0] } }, { name: '累计能耗', type: 'line', yAxisIndex: 1, smooth: true, data: cum, symbol: 'diamond', symbolSize: 6, lineStyle: { color: '#13c785', width: 2 } }],
      })
    }
  } catch (e) { console.warn('Chart error:', e) }
}

async function loadData() {
  loading.value = true; pageError.value = ''
  try {
    const br = await request.get('/dashboard/homepage', { params: { sign: app.buildingSign, energy_type: 1 } })
    if (br.success) { const b = br.data.building; buildingInfo.name = b.name || ''; buildingInfo.type = b.type || ''; buildingInfo.area = Number(b.area) || 0 }
    const [sd, ed] = [queryYear.value + '-01-01', queryYear.value + '-12-31']
    const er = await request.get('/energy/analysis', { params: { sign: app.buildingSign, item_ids: 'total', start_date: sd, end_date: ed, xdate: 'year', conversion_type: 3 } })
    if (er.success) {
      // kWh=>tce(*0.31)
      const rawT = Number(er.summary?.total_energy) || 0
      energyData.total = rawT * SD_EF / 1000
      energyData.perArea = buildingInfo.area > 0 ? rawT * SD_EF / buildingInfo.area : 0
      const ts = (er.series || []).find((s: any) => s.name === '合计' || s.name === '总用电合计')
      energyData.monthly = ts?.data?.map((v: any) => Number(v) * SD_EF / 1000 || 0) || []
    }
    // Fetch sub-items (四大分项：照明/空调/动力/特殊)
    const subEr = await request.get('/energy/analysis', { params: { sign: app.buildingSign, item_ids: '11,12,13,14', start_date: sd, end_date: ed, xdate: 'year', conversion_type: 3 } })
    if (subEr.success) {
      Object.entries(subEr.summary?.item_totals || {}).forEach(([id, val]) => {
        subItems[Number(id)] = Number(val) * SD_EF / 1000
      })
    }
    await nextTick(); initCharts()
  } catch (e: any) { pageError.value = String(e); console.error(e) }
  finally { loading.value = false }
}

onErrorCaptured((err) => { pageError.value = String(err); console.error(err); return false })
onMounted(() => { loadData() })
onUnmounted(() => { try { chartRadar?.dispose(); chartTrend?.dispose() } catch(e) {} })
</script>

<style scoped>
.quota-footprint { position: relative; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: space-between; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.summary-item { display: flex; justify-content: space-between; align-items: center; height: 90px; padding: 12px 20px; border-radius: 10px; color: #fff; }
.summary-label { font-size: 14px; opacity: .85; }
.summary-row { display: flex; align-items: baseline; gap: 4px; }
.summary-value { font-size: 24px; font-weight: 700; } .summary-unit { font-size: 12px; opacity: .7; }
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.footprint-card { border: 1px solid #f0f0f0; border-radius: 10px; padding: 16px; transition: box-shadow .2s; }
.footprint-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.fp-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.fp-icon { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
.fp-name { font-size: 13px; font-weight: 600; color: #333; }
.fp-value { font-size: 28px; font-weight: 700; color: #1a1a2e; margin-bottom: 10px; }
.fp-value small { font-size: 12px; font-weight: 400; color: #999; }
.fp-bar-wrap { margin-bottom: 8px; } .fp-bar-label { font-size: 11px; color: #999; margin-bottom: 4px; }
.fp-status { display: flex; align-items: center; justify-content: space-between; }
.fp-diff { font-size: 12px; color: #999; }
</style>