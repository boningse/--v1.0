<template>
  <div class="quota-analysis">
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="filter-group">
          <span class="label"><el-icon><Clock /></el-icon></span>
          <el-date-picker v-model="queryYear" type="year" value-format="YYYY" size="small" style="width:140px" />
          <el-button type="primary" size="small" :icon="Search" @click="loadData" :loading="loading">查询</el-button>
          <span v-if="buildingInfo.name" style="font-size:13px;color:#666;margin-left:8px">
            {{ buildingInfo.name }} · {{ buildingInfo.type }} · 面积 {{ fmtNum(buildingInfo.area) }} m²
          </span>
        </div>
        <div style="font-size:12px;color:#999">依据：山东省公共机构用电定额标准 DB37/T 2675（分项能耗数据）</div>
      </div>
    </el-card>
    <el-card shadow="hover" style="margin-top:12px">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="card-title">用电达标分析</span>
          <span style="font-size:12px;color:#999">年度：{{ queryYear }}年</span>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="6" v-for="item in compareCards" :key="item.label">
          <div class="compare-item" :class="item.cls">
            <div class="ci-label">{{ item.label }}</div>
            <div class="ci-value">{{ item.value }} <small>{{ item.unit }}</small></div>
            <div class="ci-sub" v-if="item.sub">{{ item.sub }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
    <el-row :gutter="12" style="margin-top:12px">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header><span class="card-title">月度用电 vs 定额标准</span></template>
          <div ref="chartBarRef" style="width:100%;height:380px"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header><span class="card-title">评价星级</span></template>
          <div class="eval-wrap">
            <div class="eval-score">{{ evalData.grade }}</div>
            <div class="eval-label">{{ evalData.label }}</div>
            <div class="eval-bar-wrap">
              <div class="eval-bar-bg">
                <div class="eval-bar-fill" :style="{ width: evalData.pct + '%' }"></div>
              </div>
              <div class="eval-bar-labels"><span>0</span><span>引导值</span><span>基准值</span><span>约束值</span></div>
            </div>
            <div class="eval-desc">{{ evalData.desc }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    <div v-if="loading" style="padding:40px;text-align:center;color:#999">加载中...</div>
    <div v-if="pageError" style="padding:40px;text-align:center;color:#ff4d4f">
      <h3>页面加载异常</h3>
      <p style="font-size:12px;margin-top:8px">{{ pageError }}</p>
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
const chartBarRef = ref<HTMLElement|null>(null)
let chartBar: echarts.ECharts|null = null

interface QuotaStd { constraint: number; baseline: number; guidance: number }
const QUOTA_STANDARDS: Record<string, QuotaStd> = {
  '行政机关': { constraint: 35, baseline: 28, guidance: 20 },
  '高等院校': { constraint: 30, baseline: 24, guidance: 17 },
  '中小学校': { constraint: 18, baseline: 13, guidance: 9 },
  '医疗机构': { constraint: 65, baseline: 50, guidance: 35 },
  '文化场馆': { constraint: 25, baseline: 18, guidance: 12 },
  '体育场馆': { constraint: 40, baseline: 30, guidance: 20 },
  '科研机构': { constraint: 32, baseline: 25, guidance: 18 },
}
const DEF_STD: QuotaStd = { constraint: 40, baseline: 30, guidance: 20 }

// 山东省公共机构月度能耗权重（基于一般用能特征：冬季供暖、夏季制冷、春秋过渡季节）
const MONTHLY_WEIGHTS = [0.105, 0.095, 0.08, 0.065, 0.06, 0.08, 0.095, 0.095, 0.075, 0.065, 0.08, 0.105]

const buildingInfo = reactive({ name: '', type: '', area: 0, people: 0 })
const energyData = reactive({ total: 0, perArea: 0, monthly: [] as number[], months: [] as string[] })

const stdData = computed<QuotaStd>(() => {
  const type = buildingInfo.type === 'A' ? '行政机关' : buildingInfo.type
  return QUOTA_STANDARDS[type] || DEF_STD
})

const compareCards = computed(() => {
  const s = stdData.value; const pa = energyData.perArea; const a = buildingInfo.area || 1
  return [
    { label: '实际能耗', value: fmtNum(energyData.total, 2), unit: 'tce', sub: energyData.total > 0 ? fmtNum(energyData.total, 2) + ' tce' : '', cls: 'ci-actual' },
    { label: '约束值', value: fmtNum(s.constraint * a / 1000, 2), unit: 'tce', sub: s.constraint + ' kgce/m² * ' + fmtNum(a) + ' m²', cls: pa > s.constraint ? 'ci-over' : 'ci-safe' },
    { label: '基准值', value: fmtNum(s.baseline * a / 1000, 2), unit: 'tce', sub: s.baseline + ' kgce/m² * ' + fmtNum(a) + ' m²', cls: pa > s.baseline ? 'ci-warn' : 'ci-safe' },
    { label: '引导值', value: fmtNum(s.guidance * a / 1000, 2), unit: 'tce', sub: s.guidance + ' kgce/m² * ' + fmtNum(a) + ' m²', cls: 'ci-safe' },
  ]
})

const evalData = computed(() => {
  const pa = energyData.perArea; const s = stdData.value
  let grade: string, label: string, pct: number
  if (pa <= s.guidance) { grade = 'A'; label = '优秀'; pct = 25 }
  else if (pa <= s.baseline) { grade = 'B'; label = '良好'; pct = 50 }
  else if (pa <= s.constraint) { grade = 'C'; label = '一般'; pct = 75 }
  else { grade = 'D'; label = '超标'; pct = 95 }
  return { grade, label, pct, desc: pa <= s.constraint ? '用电量在约束值范围内，管理基本合规' : '用电量已超出约束值，需立即采取节能措施' }
})

const monthlyStdData = computed(() => {
  const a = buildingInfo.area || 1; const s = stdData.value
  const at = (v: number) => v * a / 1000
  return {
    constraint: MONTHLY_WEIGHTS.map(w => Math.round(at(s.constraint) * w * 100) / 100),
    baseline: MONTHLY_WEIGHTS.map(w => Math.round(at(s.baseline) * w * 100) / 100),
    guidance: MONTHLY_WEIGHTS.map(w => Math.round(at(s.guidance) * w * 100) / 100),
    paConstraint: MONTHLY_WEIGHTS.map(w => Math.round(s.constraint * w * 100) / 100),
  }
})

const detailRows = computed(() => {
  const sd = monthlyStdData.value
  return (energyData.months || []).map((m, i) => {
    const actual = (energyData.monthly[i] || 0) * 1000
    const perArea = buildingInfo.area > 0 ? actual / buildingInfo.area : 0
    return {
      month: m, actual: actual.toFixed(1), perArea: perArea.toFixed(2), perAreaVal: perArea,
      stdTce: sd.constraint[i].toFixed(2), stdPa: sd.paConstraint[i].toFixed(2),
      stdBaseline: sd.baseline[i].toFixed(2), actualTce: (energyData.monthly[i] || 0).toFixed(2),
      overStd: perArea > sd.paConstraint[i],
    }
  })
})

function renderChart() {
  try {
    if (!chartBarRef.value) return
    chartBar?.dispose()
    chartBar = echarts.init(chartBarRef.value)
    const pa = buildingInfo.area > 0 ? buildingInfo.area : 1; const s = stdData.value
    const at = (v: number) => v * pa / 1000
    const mStd = (v: number) => MONTHLY_WEIGHTS.map(w => Math.round(at(v) * w * 100) / 100)
    chartBar.setOption({
      tooltip: { trigger: 'axis' }, legend: { data: ['实际能耗', '约束值', '基准值', '引导值'], top: 0 },
      grid: { left: 50, right: 20, top: 50, bottom: 30 },
      xAxis: { type: 'category', data: ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'], axisLabel: { fontSize: 11 } },
      yAxis: { type: 'value', name: 'tce' },
      series: [
        { name: '实际能耗', type: 'bar', data: energyData.monthly, itemStyle: { color: '#1890ff', borderRadius: [4,4,0,0] } },
        { name: '约束值', type: 'line', data: mStd(s.constraint), lineStyle: { color: '#ff4d4f', width: 2, type: 'dashed' }, symbol: 'circle', symbolSize: 4 },
        { name: '基准值', type: 'line', data: mStd(s.baseline), lineStyle: { color: '#fa8c16', width: 2, type: 'dashed' }, symbol: 'circle', symbolSize: 4 },
        { name: '引导值', type: 'line', data: mStd(s.guidance), lineStyle: { color: '#52c41a', width: 2, type: 'dashed' }, symbol: 'circle', symbolSize: 4 },
      ],
    })
  } catch (e) { console.warn('Chart error:', e) }
}

async function loadData() {
  loading.value = true; pageError.value = ''
  try {
    const br = await request.get('/dashboard/homepage', { params: { sign: app.buildingSign, energy_type: 1 } })
    if (br.success) { const b = br.data.building; buildingInfo.name = b.name || ''; buildingInfo.type = b.type || ''; buildingInfo.area = Number(b.area) || 0 }
    await fetchYearData(queryYear.value)
    await nextTick(); renderChart()
  } catch (e: any) { pageError.value = String(e); console.error('Load error:', e) }
  finally { loading.value = false }
}

async function fetchYearData(year: string) {
  const [sd, ed] = [year + '-01-01', year + '-12-31']
  const er = await request.get('/energy/analysis', { params: { sign: app.buildingSign, item_ids: 'total', start_date: sd, end_date: ed, xdate: 'year', conversion_type: 3 } })
  if (er.success) {
    const rawTotal = Number(er.summary?.total_energy) || 0
    energyData.total = rawTotal * SD_EF / 1000
    energyData.perArea = buildingInfo.area > 0 ? rawTotal * SD_EF / buildingInfo.area : 0
    const ts = (er.series || []).find((s: any) => s.name === '合计' || s.name === '总用电合计')
    if (ts?.data) {
      energyData.monthly = ts.data.map((v: any) => Number(v) * SD_EF / 1000 || 0)
      energyData.months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
    }
  }
}

onErrorCaptured((err) => { pageError.value = String(err); console.error(err); return false })
onMounted(() => { loadData() })
onUnmounted(() => { try { chartBar?.dispose() } catch(e) {} })
</script>

<style scoped>
.quota-analysis { position: relative; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: space-between; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.compare-item { border-radius: 10px; padding: 16px 20px; color: #fff; }
.ci-actual { background: linear-gradient(135deg,#13c785,#0fa86b); }
.ci-safe { background: linear-gradient(135deg,#1890ff,#40a9ff); }
.ci-warn { background: linear-gradient(135deg,#fa8c16,#ffa940); }
.ci-over { background: linear-gradient(135deg,#ff4d4f,#cf1322); }
.ci-label { font-size: 13px; opacity: .85; margin-bottom: 6px; }
.ci-value { font-size: 26px; font-weight: 700; } .ci-value small { font-size: 12px; font-weight: 400; opacity: .7; }
.ci-sub { font-size: 11px; opacity: .7; margin-top: 4px; }
.eval-wrap { padding: 20px; text-align: center; }
.eval-score { font-size: 64px; font-weight: 700; color: #1a1a2e; line-height: 1; }
.eval-label { font-size: 18px; color: #666; margin: 8px 0 24px; }
.eval-bar-wrap { margin: 0 10px 20px; }
.eval-bar-bg { height: 20px; background: #f0f0f0; border-radius: 10px; position: relative; overflow: hidden; }
.eval-bar-fill { height: 100%; background: linear-gradient(90deg,#52c41a,#fa8c16,#ff4d4f); border-radius: 10px; transition: width .5s ease; }
.eval-bar-labels { display: flex; justify-content: space-between; font-size: 10px; color: #999; margin-top: 4px; }
.eval-desc { font-size: 12px; color: #999; }
</style>