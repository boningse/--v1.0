<template>
  <div class="home">
    <!-- 建筑头部 -->
    <div class="building-hero">
      <div class="hero-overlay"></div>
      <div class="hero-content">
        <div class="hero-left">
          <h2>{{ data?.building?.name || '加载中...' }}</h2>
          <p class="hero-intro">{{ data?.building?.introduction || data?.building?.type || '' }}</p>
        </div>
        <div class="hero-right">
          <div class="hero-status">
            <span class="status-dot" :class="data?.stats?.status === '正常' ? 'dot-green' : 'dot-red'"></span>
            <span>{{ data?.stats?.status || '--' }}</span>
          </div>
          <div class="hero-time" v-if="data?.stats?.time">{{ data?.stats?.date }} {{ data?.stats?.time }}</div>
        </div>
      </div>
    </div>

    <!-- 指标卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="s in statCards" :key="s.key">
        <div class="stat-card" :style="{ background: s.bg }">
          <div class="stat-icon" :style="{ background: s.iconBg }">{{ s.icon }}</div>
          <div class="stat-body">
            <div class="stat-label">{{ s.label }}</div>
            <div class="stat-value">{{ s.value }} <span class="stat-unit">{{ s.unit }}</span></div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表 + 右侧面板 -->
    <el-row :gutter="16" style="display:flex;flex-wrap:wrap;align-items:stretch">
      <el-col :xs="24" :lg="16" style="display:flex">
        <el-card shadow="never" class="chart-card" style="flex:1;display:flex;flex-direction:column">
          <template #header>
            <div class="chart-header">
              <span class="chart-title">{{ data?.chart?.title || '今日能耗' }}</span>
              <div class="energy-switch">
                <el-radio-group v-model="curType" size="small" @change="switchType">
                  <el-radio-button v-for="et in (data?.energy_types || [])" :key="et.id" :value="et.id">
                    {{ et.name }}
                  </el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </template>
          <div ref="chartRef" style="min-height:418px;flex:1"></div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="8" style="display:flex;flex-direction:column">
        <!-- 概要面板 -->
        <el-card shadow="never" class="summary-card" style="flex:2">
          <template #header><span class="card-title">能耗概要</span></template>
          <div class="summary-items">
            <div class="summary-item" v-for="item in summaryItems" :key="item.label">
              <div class="si-label">{{ item.label }}</div>
              <div class="si-value">{{ item.value }}</div>
              <div class="si-unit">{{ item.unit }}</div>
            </div>
          </div>
        </el-card>

        <!-- 分项占比快速预览 -->
        <el-card shadow="never" class="cats-card" style="margin-top:12px;flex:1">
          <template #header><span class="card-title">分项占比</span></template>
          <div class="cat-bars">
            <div v-for="cat in catItems" :key="cat.name" class="cat-row">
              <div class="cat-name">{{ cat.name }}</div>
              <div class="cat-bar-wrap">
                <div class="cat-bar" :style="{ width: cat.pct + '%', background: cat.color }"></div>
              </div>
              <div class="cat-val">{{ cat.val }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { useAppStore } from '@/stores/index'
import { fmtNum } from '@/utils/index'
import request from '@/api/request'

const app = useAppStore()
const chartRef = ref()
const data = ref<any>(null)
const curType = ref(1)
let chartInstance: echarts.ECharts | null = null

const catColors = ['#13c785', '#1890ff', '#fa8c16', '#f5222d']

const statCards = computed(() => {
  const s = data.value?.stats || {}
  const t = data.value?.energy_types?.find((e: any) => e.id === curType.value)
  return [
    { key: 'total', label: t?.title?.replace('今日', '') || '总能耗', value: fmtNum(s.energy_total), unit: s.unit || 'kWh', bg: 'linear-gradient(135deg,#13c785,#0fa86b)', icon: '⚡', iconBg: 'rgba(255,255,255,.2)' },
    { key: 'area', label: '单位平米能耗', value: fmtNum(s.energy_by_area, 4), unit: s.unit_area || 'kWh/㎡', bg: 'linear-gradient(135deg,#1890ff,#40a9ff)', icon: '📐', iconBg: 'rgba(255,255,255,.2)' },
    { key: 'price', label: '参考价值', value: fmtNum(s.total_price), unit: '元', bg: 'linear-gradient(135deg,#fa8c16,#ffa940)', icon: '💰', iconBg: 'rgba(255,255,255,.2)' },
    { key: 'power', label: '最大功率', value: fmtNum(s.power_max), unit: 'kW', bg: 'linear-gradient(135deg,#722ed1,#b37feb)', icon: '📊', iconBg: 'rgba(255,255,255,.2)' },
  ]
})

const summaryItems = computed(() => {
  const s = data.value?.stats || {}
  return [
    { label: '当前状态', value: s.status || '--', unit: '' },
    { label: '今日总能耗', value: fmtNum(s.energy_total), unit: s.unit || 'kWh' },
    { label: '单位平米', value: fmtNum(s.energy_by_area, 4), unit: s.unit_area || 'kWh/㎡' },
    { label: '参考价值', value: fmtNum(s.total_price), unit: '元' },
    { label: '最大功率', value: fmtNum(s.power_max), unit: 'kW' },
    { label: '数据更新时间', value: s.time || '--', unit: '' },
  ]
})

const catItems = computed(() => {
  if (!data.value?.stats) return []
  const total = Number(data.value.stats.energy_total) || 1
  const raw = data.value.cats || {}
  const names = ['照明', '动力', '空调', '其他']
  return names.map((name, i) => {
    const val = raw[name] ? Number(raw[name]) : 0
    return { name, val: val.toFixed(1), pct: total > 0 ? Math.max(val / total * 100, 1) : 0, color: catColors[i] }
  }).filter(c => c.pct > 0 || true)
})

async function load(et: number = curType.value) {
  const sign = app.buildingSign
  if (!sign) return
  const res: any = await request.get('/dashboard/homepage', { params: { sign, energy_type: et } })
  if (res.success) {
    data.value = res.data
    await nextTick()
    renderChart()
  }
}

function renderChart() {
  if (!chartRef.value || !data.value?.chart?.data?.length) return
  if (chartInstance) {
    const h = (chartInstance as any).__resizeHandler
    if (h) window.removeEventListener('resize', h)
    chartInstance.dispose()
  }
  chartInstance = echarts.init(chartRef.value)
  const cd = data.value.chart

  chartInstance.setOption(
    {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `<strong>${p.axisValue}</strong><br/>${Number(p.value).toFixed(2)} ${cd.unit}`
      },
      axisPointer: { type: 'cross' }
    },
    grid: { top: 20, right: 30, bottom: 50, left: 65 },
    xAxis: {
      type: 'category', boundaryGap: true,
      data: cd.data.map((d: any) => d.time?.slice(11) || d.time),
      axisLabel: { interval: Math.max(1, Math.floor(cd.data.length / 12) - 1), fontSize: 10, color: '#8c8c8c' },
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value', name: cd.label || 'kWh',
      nameTextStyle: { fontSize: 11, color: '#8c8c8c' },
      nameLocation: 'middle',
      nameGap: 35,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } }
    },
    series: [{
      type: 'bar',
      barWidth: '50%',
      data: cd.data.map((d: any) => d.value),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#13c785' }, { offset: 1, color: '#0a8c5e' }
        ]),
        borderRadius: [6, 6, 0, 0]
      },
      emphasis: { itemStyle: { color: '#0a8c5e' } }
    }]
  })

  const onResize = () => chartInstance?.resize()
  window.addEventListener('resize', onResize)
  ;(chartInstance as any).__resizeHandler = onResize
}

function switchType(et: number) {
  curType.value = et
  load(et)
}

onMounted(() => load())

onBeforeUnmount(() => {
  if (chartInstance) {
    const h = (chartInstance as any).__resizeHandler
    if (h) window.removeEventListener('resize', h)
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.home { display: flex; flex-direction: column; gap: 24px; max-width: 1400px; margin: 0 auto; position: relative; }

/* 建筑头部 */
.building-hero {
  position: relative;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 12px;
  padding: 28px 32px;
  overflow: hidden;
}
.hero-overlay {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse at 20% 50%, rgba(19,199,133,.12) 0%, transparent 60%);
}
.hero-content { position: relative; display: flex; justify-content: space-between; align-items: center; }
.hero-left h2 { font-size: 20px; font-weight: 700; color: #fff; margin: 0 0 4px; }
.hero-intro { font-size: 13px; color: rgba(255,255,255,.55); margin: 0; }
.hero-right { text-align: right; }
.hero-status { display: flex; align-items: center; gap: 6px; font-size: 13px; color: rgba(255,255,255,.8); justify-content: flex-end; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot-green { background: #52c41a; box-shadow: 0 0 8px rgba(82,196,26,.5); }
.dot-red { background: #ff4d4f; box-shadow: 0 0 8px rgba(255,77,79,.5); }
.hero-time { font-size: 11px; color: rgba(255,255,255,.4); margin-top: 4px; }

/* 指标卡片 */
.stat-row { margin-bottom: 0 !important; }
.stat-card {
  display: flex; align-items: center; gap: 24px;
  border-radius: 10px; padding: 36px 28px; color: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
  transition: transform .2s, box-shadow .2s;
}
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.12); }
.stat-icon {
  width: 64px; height: 64px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; flex-shrink: 0;
}
.stat-body { flex: 1; min-width: 0; }
.stat-label { font-size: 14px; opacity: .85; margin-bottom: 6px; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.3; }
.stat-unit { font-size: 12px; font-weight: 400; opacity: .7; }

/* 图表卡片 */
.chart-card {
  border-radius: 10px;
}
.chart-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
}
.chart-card :deep(.el-card__header) { border-bottom: 1px solid #f0f0f0; padding: 14px 20px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.chart-title { font-size: 15px; font-weight: 600; color: #1a1a2e; }
.energy-switch :deep(.el-radio-button__inner) { font-size: 11px; padding: 5px 12px; }

/* 摘要卡片 */
.summary-card {
  border-radius: 10px;
}
.summary-card :deep(.el-card__body) {
  flex: 1;
}
.summary-card :deep(.el-card__header),
.cats-card :deep(.el-card__header) { border-bottom: 1px solid #f0f0f0; padding: 14px 20px; }
.card-title { font-size: 16px; font-weight: 600; color: #1a1a2e; }
.summary-items { display: flex; flex-direction: column; gap: 0; }
.summary-item {
  display: flex; align-items: center; padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
}
.summary-item:last-child { border-bottom: none; }
.si-label { font-size: 12px; color: #8c8c8c; flex: 1; }
.si-value { font-size: 15px; font-weight: 600; color: #1a1a2e; min-width: 60px; text-align: right; }
.si-unit { font-size: 11px; color: #8c8c8c; min-width: 40px; text-align: right; }

/* 分项占比 */
.cat-card { border-radius: 10px; }
.cat-bars { display: flex; flex-direction: column; gap: 10px; }
.cat-row { display: flex; align-items: center; gap: 8px; }
.cat-name { font-size: 12px; color: #555; width: 40px; flex-shrink: 0; }
.cat-bar-wrap { flex: 1; height: 10px; background: #f0f0f0; border-radius: 5px; overflow: hidden; }
.cat-bar { height: 100%; border-radius: 5px; transition: width .6s ease; }
.cat-val { font-size: 12px; color: #8c8c8c; width: 60px; text-align: right; }

@media (max-width: 768px) {
  .building-hero { padding: 20px; }
  .hero-content { flex-direction: column; align-items: flex-start; gap: 8px; }
  .hero-right { text-align: left; width: 100%; }
  .hero-status { justify-content: flex-start; }
  .stat-card { padding: 14px 16px; }
  .stat-value { font-size: 18px; }
}

/* 背景装饰 — 柔和的径向光晕 */
.home::before {
  content: ''; position: absolute; top: 260px; left: -5%; width: 110%; height: 400px;
  background:
    radial-gradient(ellipse at 30% 50%, rgba(19,199,133,.05) 0%, transparent 60%),
    radial-gradient(ellipse at 70% 30%, rgba(24,144,255,.05) 0%, transparent 50%);
  pointer-events: none; z-index: 0;
}
.home { position: relative; }
.home > * { position: relative; z-index: 1; }

/* 卡片顶部装饰条 */
.chart-card { position: relative; overflow: hidden; }
.chart-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; z-index: 1;
  background: linear-gradient(90deg, #13c785, #1890ff, #fa8c16);
}
.summary-card { position: relative; overflow: hidden; }
.summary-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; z-index: 1;
  background: linear-gradient(90deg, #722ed1, #1890ff);
}
.cats-card { position: relative; overflow: hidden; }
.cats-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; z-index: 1;
  background: linear-gradient(90deg, #fa8c16, #13c785);
}

/* 统计图标内部质感 */
.stat-icon { position: relative; box-shadow: inset 0 1px 0 rgba(255,255,255,.25); }

/* 占比条细节 */
.cat-bar-wrap { box-shadow: inset 0 1px 2px rgba(0,0,0,.06); }

</style>
