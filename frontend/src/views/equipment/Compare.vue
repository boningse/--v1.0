<template>
  <div class="equipment-compare">
    <!-- ====== 顶部控制栏 ====== -->
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="convert-group">
          <el-button-group>
            <el-button v-for="btn in convertBtns" :key="btn.type" :type="conversionType===btn.type?'primary':'default'" size="small" @click="switchConversion(btn.type)">{{ btn.label }}</el-button>
          </el-button-group>
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

    <!-- ====== 主体: 左侧设备树 + 右侧图表 ====== -->
    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="5">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span>设备列表</span>
              <div class="tree-actions">
                <el-button link size="small" @click="checkAll">全选</el-button>
                <el-button link size="small" @click="uncheckAll">取消</el-button>
              </div>
            </div>
            </template>
            <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            show-checkbox
            check-strictly
            default-expand-all
            highlight-current
            @check="onTreeCheck"
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
              <span class="summary-value">{{ Number(summaryData.total_energy).toFixed(3) }}</span>
              <span class="summary-unit">{{ conversionInfo?.unit }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">单位面积能耗</span>
              <span class="summary-value">{{ Number(summaryData.per_area_energy).toFixed(3) }}</span>
              <span class="summary-unit">{{ conversionInfo?.unit }}/m²</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">参考价值</span>
              <span class="summary-value">{{ Number(summaryData.reference_value).toFixed(2) }}</span>
              <span class="summary-unit">元</span>
            </div>
            <div class="summary-item" :class="{ 'trend-up': summaryData.trend < 0, 'trend-down': summaryData.trend > 0 }">
              <span class="summary-label">
                能耗趋势
                <span v-if="summaryData.trend < 0" class="trend-arrow">↓</span>
                <span v-else-if="summaryData.trend > 0" class="trend-arrow">↑</span>
                <span v-else class="trend-arrow">→</span>
              </span>
              <span class="summary-value">{{ Math.abs(summaryData.trend) }}%</span>
              <span class="summary-unit">较上期</span>
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
import { getEquipmentTree, getEquipmentAnalysis } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref([])
const treeRef = ref(null)
const chartRef = ref(null)
let chartInstance: echarts.ECharts | null = null

const convertBtns = [
  { type: 3, label: '设备能耗' },
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
    const r = await getEquipmentTree(app.buildingSign)
    if (r.success) treeData.value = r.tree || r.data || []
  } catch { ElMessage.error('加载设备列表失败') }
  finally { loading.value = false }
}

function checkAll() { treeRef.value?.setCheckedKeys(treeData.value.map((n: any) => n.id)) }
function uncheckAll() { treeRef.value?.setCheckedKeys([]) }

async function doSearch() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (!checked.length) { ElMessage.warning('请选择设备'); return }
  const p: any = { sign: app.buildingSign, item_ids: checked.join(","), conversion_type: conversionType.value, xdate: timeType.value }
  if (timeType.value === 'day') { p.start_date = p.end_date = dateSingle.value }
  else if (timeType.value === 'month') { const [y, m] = dateMonth.value.split('-').map(Number); p.start_date = dateMonth.value + '-01'; p.end_date = dateMonth.value + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }
  else if (timeType.value === 'year') { p.start_date = dateYear.value + '-01-01'; p.end_date = dateYear.value + '-12-31' }
  else if (timeType.value === 'range' && dateRange.value) { p.start_date = dateRange.value[0]; p.end_date = dateRange.value[1] }
  loading.value = true
  try {
    const r = await getEquipmentAnalysis(p)
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
  const unit = conversionInfo.value?.unit || ''
  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: function (params: any) {
        if (!params || !params.length) return ''
        let html = '<div style="font-weight:600;margin-bottom:4px">' + params[0].axisValue + '</div>'
        params.forEach(function (p: any) {
          html += '<div style="display:flex;align-items:center;gap:6px;font-size:13px"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + p.color + '"></span>' + p.seriesName + ': <strong>' + Number(p.value).toFixed(3) + '</strong> ' + unit + '</div>'
        })
        return html
      }
    },
    legend: { data: (data.series || []).map((s: any) => s.name) },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: data.categories || [] },
    yAxis: { type: 'value', name: unit },
    series: (data.series || []).map((s: any) => ({
      name: s.name, type: 'line', data: s.data, smooth: true
    })),
    dataZoom: (data.categories || []).length > 30 ? [{ type: 'inside', start: 0, end: 100 }] : undefined
  })
}

function onTreeCheck() { doSearch() }
onMounted(() => { loadTree() })
watch(() => app.buildingSign, () => { loadTree() })
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
  border-radius: 10px;
  padding: 18px 20px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
  transition: transform .2s, box-shadow .2s;
  cursor: default;
}
.summary-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0,0,0,.12);
}
.summary-item:nth-child(1) { background: linear-gradient(135deg,#13c785,#0fa86b); }
.summary-item:nth-child(2) { background: linear-gradient(135deg,#1890ff,#40a9ff); }
.summary-item:nth-child(3) { background: linear-gradient(135deg,#fa8c16,#ffa940); }
.summary-item:nth-child(4) { background: linear-gradient(135deg,#722ed1,#b37feb); }
.summary-label { font-size: 12px; opacity: .8; margin-bottom: 2px; }
.summary-value { font-size: 22px; font-weight: 700; line-height: 1.2; }
.summary-unit { font-size: 12px; font-weight: 400; opacity: .7; margin-left: 4px; }
.summary-item.trend-down { background: linear-gradient(135deg,#ff4d4f,#cf1322); }
.summary-item.trend-up { background: linear-gradient(135deg,#52c41a,#389e0d); }
.trend-arrow { font-size: 14px; margin-left: 2px; }

@media (max-width: 992px) {
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 576px) {
  .summary-grid { grid-template-columns: 1fr; }
}
</style>