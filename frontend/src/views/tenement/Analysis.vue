<template>
  <div class="tenement-analysis">
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

        <!-- 能源类型 -->
        <div class="filter-group">
          <span class="label">能源类型</span>
          <el-select v-model="energyType" size="small" style="width:100px" @change="loadTree">
            <el-option label="电" :value="1" />
            <el-option label="水" :value="2" />
            <el-option label="冷量" :value="3" />
            <el-option label="热量" :value="4" />
            <el-option label="燃气" :value="5" />
            <el-option label="蒸汽" :value="6" />
          </el-select>
        </div>

        <!-- 粒度 + 日期 -->
        <div class="filter-group">
          <el-icon><Clock /></el-icon>
          <el-select v-model="timeType" size="small" style="width:90px" @change="onTimeTypeChange">
            <el-option label="日" value="day" />
            <el-option label="月" value="month" />
            <el-option label="年" value="year" />
            <el-option label="时间段" value="range" />
          </el-select>

          <el-icon class="ml-2" style="color:#1890ff"><Calendar /></el-icon>

          <el-date-picker v-if="timeType==='day'" v-model="dateSingle" type="date" value-format="YYYY-MM-DD" size="small" style="width:140px" />
          <el-date-picker v-else-if="timeType==='month'" v-model="dateMonth" type="month" value-format="YYYY-MM" size="small" style="width:140px" />
          <el-date-picker v-else-if="timeType==='year'" v-model="dateYear" type="year" value-format="YYYY" size="small" style="width:140px" />
          <template v-if="timeType==='range'">
            <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" size="small" style="width:260px" range-separator=" - " />
          </template>

          <el-button type="primary" size="small" :icon="Search" :loading="loading" @click="doSearch">确定</el-button>
        </div>
      </div>
    </el-card>

    <!-- ====== 主体: 左侧分户树 + 右侧图表 ====== -->
    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="5">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span>分户列表</span>

            </div>

    </template>
            <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            default-expand-all
            highlight-current
            @node-click="onTreeNodeClick"
          />
          </el-card>      </el-col>
      <el-col :span="19">
        <el-card shadow="hover">
          <template #header><div style="font-size:14px;font-weight:600">能耗数据 <span v-if="conversionInfo" style="font-size:12px;font-weight:normal;color:#999;margin-left:8px">单位: {{ conversionInfo.unit }}</span></div></template>
          <div ref="chartRef" style="width:100%;height:420px"></div>
        </el-card>

        <el-card v-if="summaryData" shadow="hover" style="margin-top:12px">
          <template #header><div style="font-size:14px;font-weight:600">数据概览</div></template>
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
import { ref, onMounted, watch, nextTick } from 'vue'
import { Clock, Calendar, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getTenementList, getTenementAnalysis } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref([])
const treeRef = ref(null)
const chartRef = ref(null)
let chartInstance: echarts.ECharts | null = null
const energyType = ref(1)

const convertBtns = [
  { type: 3, label: '分户能耗' },
  { type: 1, label: '标准煤' },
  { type: 2, label: '碳排量' },
  { type: 4, label: '单位面积能耗' },
]
const conversionType = ref(3)
const conversionInfo = ref<any>(null)
const summaryData = ref<any>(null)
const timeType = ref('day')
const dateSingle = ref(new Date().toISOString().slice(0, 10))
const dateMonth = ref(new Date().toISOString().slice(0, 7))
const dateYear = ref(new Date().toISOString().slice(0, 4))
const dateRange = ref(null)

function switchConversion(t: number) { conversionType.value = t; doSearch() }
function onTimeTypeChange() { doSearch() }

async function loadTree() {
  summaryData.value = null
  conversionInfo.value = null
  chartInstance?.dispose()
  chartInstance = null
  loading.value = true
  try {
    const r = await getTenementList(app.buildingSign, energyType.value)
    if (r.success) {
      treeData.value = r.tree || r.data || []
      nextTick(() => {
        const first = treeData.value?.[0]
        if (first) {
          treeRef.value?.setCurrentKey(first.id)
          doSearch()
        }
      })
    }
  } catch { ElMessage.error('加载分户列表失败') }
  finally { loading.value = false }
}

async function doSearch() {
  const selectedIds = treeRef.value?.getCurrentKey()
  if (!selectedIds) { ElMessage.warning('请选择分户'); return }
  const p: any = { sign: app.buildingSign, item_ids: String(selectedIds), conversion_type: conversionType.value, xdate: timeType.value, energy_type: energyType.value }
  if (timeType.value === 'day') { p.start_date = p.end_date = dateSingle.value }
  else if (timeType.value === 'month') { const [y, m] = dateMonth.value.split('-').map(Number); p.start_date = dateMonth.value + '-01'; p.end_date = dateMonth.value + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }
  else if (timeType.value === 'year') { p.start_date = dateYear.value + '-01-01'; p.end_date = dateYear.value + '-12-31' }
  else if (timeType.value === 'range' && dateRange.value) { p.start_date = dateRange.value[0]; p.end_date = dateRange.value[1] }
  loading.value = true
  try {
    const r = await getTenementAnalysis(p)
    if (r.success && r.data) {
      conversionInfo.value = r.conversion || null
      summaryData.value = r.summary || null
      renderChart({
        categories: r.times || [],
        series: (r.data || []).map((t: any) => ({ name: t.name, data: t.data }))
      })
    }
  } catch { ElMessage.error('查询失败') }
  finally { loading.value = false }
}

function renderChart(data: any) {
  if (!chartRef.value) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: (data.series || []).map((s: any) => s.name) },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.categories || [] },
    yAxis: { type: 'value' },
    series: (data.series || []).map((s: any) => ({
      name: s.name, type: 'bar', data: s.data,
      itemStyle: { borderRadius: [4, 4, 0, 0] }
    }))
  })
}

function onTreeNodeClick() { doSearch() }
onMounted(() => { loadTree() })
watch(() => app.buildingSign, () => { loadTree() })
watch(energyType, () => { loadTree() })
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