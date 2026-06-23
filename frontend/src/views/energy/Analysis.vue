<template>
  <div class="energy-analysis">
    <!-- ====== 顶部控制栏 ====== -->
    <el-card shadow="hover">
      <div class="toolbar">
        <!-- 换算按钮组 -->
        <div class="convert-group">
          <el-button-group>
            <el-button
              v-for="btn in convertBtns"
              :key="btn.type"
              :type="conversionType === btn.type ? 'primary' : 'default'"
              size="small"
              @click="switchConversion(btn.type)"
            >
              {{ btn.label }}
            </el-button>
          </el-button-group>
        </div>

        <!-- 粒度 + 日期 -->
        <div class="filter-group">
          <span class="label"><el-icon><Clock /></el-icon></span>
          <el-select v-model="timeType" style="width: 90px" size="small" @change="onTimeTypeChange">
            <el-option label="日" value="day" />
            <el-option label="月" value="month" />
            <el-option label="年" value="year" />
            <el-option label="时间段" value="range" />
          </el-select>

          <el-icon class="ml-2" style="color: #1890ff"><Calendar /></el-icon>

          <!-- 日: 单日期 -->
          <el-date-picker
            v-if="timeType === 'day'"
            v-model="dateSingle"
            type="date"
            value-format="YYYY-MM-DD"
            size="small"
            style="width: 140px"
          />
          <!-- 月: 月选择器 -->
          <el-date-picker
            v-else-if="timeType === 'month'"
            v-model="dateMonth"
            type="month"
            value-format="YYYY-MM"
            size="small"
            style="width: 140px"
          />
          <!-- 年: 年选择器 -->
          <el-date-picker
            v-else-if="timeType === 'year'"
            v-model="dateYear"
            type="year"
            value-format="YYYY"
            size="small"
            style="width: 140px"
          />
          <!-- 时间段: 范围选择器 -->
          <el-date-picker
            v-else-if="timeType === 'range'"
            v-model="dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            size="small"
            style="width: 260px"
            range-separator=" - "
          />

          <el-button type="primary" size="small" :icon="Search" @click="doSearch" :loading="loading">
            确定
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ====== 主体: 左侧分项树 + 右侧图表 ====== -->
    <el-row :gutter="16" style="margin-top:12px;display:flex;flex-wrap:wrap;align-items:stretch">
      <!-- 左侧: 分项树 -->
      <el-col :span="5">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span>分项类型</span>
            </div>
          </template>
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ children: 'children', label: 'name', disabled: 'disabled' }"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="onNodeClick"
          />
        </el-card>
      </el-col>

      <!-- 右侧: 图表 -->
      <el-col :span="19">
        <el-card shadow="hover">
          <template #header>
            <div class="chart-header">
              <span>能耗数据</span>
              <span v-if="conversionInfo" class="chart-unit">单位: {{ conversionInfo.unit }}</span>
            </div>
          </template>
          <div ref="chartRef" style="width: 100%; height: 420px"></div>
        </el-card>

        <!-- 汇总卡片 -->
        <el-card v-if="summaryData" shadow="hover" style="margin-top: 12px">
          <template #header>
            <div style="font-size: 14px; font-weight: 600">数据概览</div>
          </template>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">能耗合计</span>
              <div class="summary-row"><span class="summary-value">{{ Number(summaryData.total_energy).toFixed(3) }}</span><span class="summary-unit">{{ conversionInfo?.unit }}</span></div>
            </div>
            <div class="summary-item">
              <span class="summary-label">单位面积能耗</span>
              <div class="summary-row"><span class="summary-value">{{ Number(summaryData.per_area_energy).toFixed(3) }}</span><span class="summary-unit">{{ conversionInfo?.unit }}/m²</span></div>
            </div>
            <div class="summary-item">
              <span class="summary-label">参考价值</span>
              <div class="summary-row"><span class="summary-value">{{ Number(summaryData.reference_value).toFixed(2) }}</span><span class="summary-unit">元</span></div>
            </div>
            <div class="summary-item" :class="{ 'trend-up': summaryData.trend < 0, 'trend-down': summaryData.trend > 0 }">
              <span class="summary-label">能耗趋势</span>
              <div class="summary-row"><span class="summary-value">{{ Math.abs(summaryData.trend) }}%</span><span class="summary-unit">较上期</span></div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Clock, Calendar, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getEnergyItems, getEnergyAnalysis } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref<any[]>([])
const treeRef = ref<any>(null)
const chartRef = ref<HTMLElement | null>(null)
const selectedItemId = ref<number | null>(null)
let chartInstance: echarts.ECharts | null = null

const convertBtns = [
  { type: 3, label: '分项能耗' },
  { type: 1, label: '标准煤' },
  { type: 2, label: '碳排量' },
  { type: 4, label: '单位面积能耗' },
]
const conversionType = ref(3)
const conversionInfo = ref<any>(null)
const timeType = ref('day')
const dateSingle = ref(new Date().toISOString().slice(0, 10))
const dateMonth = ref(new Date().toISOString().slice(0, 7))
const dateYear = ref(new Date().toISOString().slice(0, 4))
const dateRange = ref<any>(null)
const summaryData = ref<any>(null)
const itemNameMap = ref<Record<number, string>>({})

const CHART_COLORS = [
  '#1890ff', '#73c0de', '#ffc53d', '#f56c6c',
  '#67c23a', '#909399', '#e6a23c', '#b37feb',
  '#36cfc9', '#ff85c0', '#597ef7', '#ffa39e',
]

function switchConversion(t: number) {
  conversionType.value = t
  doSearch()
}

function onTimeTypeChange() {
  doSearch()
}

function onNodeClick(data: any) {
  if (data.disabled) return
  selectedItemId.value = data.id
  treeRef.value?.setCurrentKey(data.id)
  doSearch()
}

async function loadTree() {
  loading.value = true
  try {
    const r = await getEnergyItems(app.buildingSign)
    if (r.success) {
      // 添加顶级根节点"分项能耗"，包装四大分项
      const children = r['总用电'] || []
      treeData.value = [{ id: 1, name: '分项能耗', disabled: false, children }]
      nextTick(() => {
        selectedItemId.value = 1
        treeRef.value?.setCurrentKey(1)
        doSearch()
      })
    }
  } catch {
    ElMessage.error('加载用电类型失败')
  } finally {
    loading.value = false
  }
}

async function doSearch() {
  if (!selectedItemId.value) {
    ElMessage.warning('请选择分项类型')
    return
  }

  const params: any = {
    sign: app.buildingSign,
    item_ids: String(selectedItemId.value),
    conversion_type: conversionType.value,
    xdate: timeType.value,
  }

  if (timeType.value === 'day') {
    params.start_date = params.end_date = dateSingle.value
  } else if (timeType.value === 'month') {
    params.start_date = dateMonth.value + '-01'
    const [y, m] = dateMonth.value.split('-').map(Number)
    const lastDay = new Date(y, m, 0).getDate()
    params.end_date = dateMonth.value + '-' + String(lastDay).padStart(2, '0')
  } else if (timeType.value === 'year') {
    params.start_date = dateYear.value + '-01-01'
    params.end_date = dateYear.value + '-12-31'
  } else if (timeType.value === 'range' && dateRange.value) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  } else {
    return
  }

  loading.value = true
  try {
    const r = await getEnergyAnalysis(params)
    if (r.success) {
      // 后端返回的数据在根级: r.times, r.series, r.summary, r.conversion
      summaryData.value = r.summary || null
      conversionInfo.value = r.conversion || null

      // 构建分项名称映射
      if (r.items) {
        const map: Record<number, string> = {}
        r.items.forEach((i: any) => {
          map[i.id] = i.name === '总用电合计' ? '分项能耗' : i.name
        })
        itemNameMap.value = map
      }

      await nextTick()
      const filteredSeries = (r.series || []).filter((s: any) => s.name !== '合计')
      renderChart(r.times || [], filteredSeries)
    }
  } catch {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function renderChart(times: string[], series: any[]) {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const option: any = {
    tooltip: {
      trigger: 'axis',
      formatter: function (params: any) {
        if (!params || !params.length) return ''
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
        const unit = conversionInfo.value?.unit || ''
        params.forEach((p: any) => {
          html += `<div style="display:flex;align-items:center;gap:6px;font-size:13px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
            ${p.seriesName}: <strong>${Number(p.value).toFixed(3)}</strong> ${unit}
          </div>`
        })
        return html
      },
    },
    legend: {
      data: series.map((s) => s.name),
      top: 0,
      type: 'scroll',
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      data: times.map(t => t.length > 8 ? t.slice(5) : t),
      axisLabel: { rotate: times.length > 12 ? 45 : 0, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: conversionInfo.value?.unit || '',
      nameTextStyle: { fontSize: 12 },
    },
    series: series.map((s, idx) => ({
      name: s.name,
      type: 'bar',
      data: s.data,
      barMaxWidth: 40,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: CHART_COLORS[idx % CHART_COLORS.length],
      },
      emphasis: { focus: 'series' },
    })),
    dataZoom: times.length > 30 ? [{ type: 'inside', start: 0, end: 100 }] : undefined,
  }

  chartInstance.setOption(option, true)
  chartInstance.resize()
}

function onResize() {
  chartInstance?.resize()
}

onMounted(() => {
  loadTree()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  chartInstance?.dispose()
  chartInstance = null
})

watch(() => app.buildingSign, () => {
  selectedItemId.value = null
  loadTree()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.toolbar .filter-group {
  margin-left: auto;
}
.convert-group {
  display: flex;
  align-items: center;
  gap: 4px;
}
.convert-group .el-button-group .el-button {
  font-size: 12px;
}
.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}
.ml-2 {
  margin-left: 8px;
}
.tree-card {
  height: calc(100vh - 220px);
  overflow-y: auto;
}
.tree-card .el-card__header {
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #1a1a2e;
}
.tree-actions .el-button {
  font-size: 12px;
}
/* 无数据分项灰色不可选 */
.el-tree-node.is-disabled > .el-tree-node__content {
  color: #bbb;
  cursor: not-allowed;
}
.el-tree-node.is-disabled > .el-tree-node__content .el-tree-node__label {
  color: #bbb;
}
.el-tree-node.is-disabled .el-checkbox {
  display: none;
}
.chart-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
}
.chart-unit {
  font-size: 12px;
  font-weight: normal;
  color: #999;
}

/* === 美观大气的数据概览卡片 === */
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100px;
  padding: 12px 20px;
  border-radius: 10px;
  color: #fff;
}
.summary-item:nth-child(1) { background: linear-gradient(135deg,#13c785,#0fa86b); }
.summary-item:nth-child(2) { background: linear-gradient(135deg,#1890ff,#40a9ff); }
.summary-item:nth-child(3) { background: linear-gradient(135deg,#fa8c16,#ffa940); }
.summary-item:nth-child(4) { background: linear-gradient(135deg,#722ed1,#b37feb); }
.summary-label { font-size: 15px; opacity: .85; line-height: 1.4; }
.summary-row { display: flex; align-items: baseline; gap: 4px; }
.summary-value { font-size: 22px; font-weight: 700; line-height: 1.3; }
.summary-unit { font-size: 11px; font-weight: 400; opacity: .7; }
.summary-item.trend-down { background: linear-gradient(135deg,#ff4d4f,#cf1322); }
.summary-item.trend-up { background: linear-gradient(135deg,#52c41a,#389e0d); }

@media (max-width: 992px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 576px) {
  .summary-grid { grid-template-columns: 1fr; }
}


/* 背景装饰 — 柔和的径向光晕 */
.energy-analysis, .tenement-analysis, .equipment-analysis {
  position: relative;
}
.energy-analysis::before, .tenement-analysis::before, .equipment-analysis::before {
  content: ''; position: absolute; top: 200px; left: -5%; width: 110%; height: 400px;
  background:
    radial-gradient(ellipse at 30% 30%, rgba(19,199,133,.04) 0%, transparent 60%),
    radial-gradient(ellipse at 70% 50%, rgba(24,144,255,.04) 0%, transparent 50%);
  pointer-events: none; z-index: 0;
}
.energy-analysis > *, .tenement-analysis > *, .equipment-analysis > * { position: relative; z-index: 1; }

/* 卡片装饰条 */
.el-card { position: relative; overflow: visible; }
.el-card:not(.is-always-shadow) { overflow: hidden; }

</style>
