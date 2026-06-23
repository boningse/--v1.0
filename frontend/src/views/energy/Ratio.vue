<template>
  <div class="energy-ratio">
    <!-- ====== 顶部控制栏 ====== -->
    <el-card shadow="hover">
      <div class="toolbar">
        <!-- 换算按钮组 -->
        <div class="convert-group">
          <span class="label">同比换算</span>
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
          <el-select v-model="timeType" style="width:90px" size="small" @change="onTimeTypeChange">
            <el-option label="日" value="day" />
            <el-option label="月" value="month" />
            <el-option label="年" value="year" />
            <el-option label="时间段" value="range" />
          </el-select>

          <el-icon class="ml-2" style="color:#13c785"><Calendar /></el-icon>

          <!-- 日: 单日期 -->
          <el-date-picker
            v-if="timeType === 'day'"
            v-model="dateSingle"
            type="date"
            value-format="YYYY-MM-DD"
            size="small"
            style="width:140px"
          />
          <!-- 月: 月选择器 -->
          <el-date-picker
            v-else-if="timeType === 'month'"
            v-model="dateMonth"
            type="month"
            value-format="YYYY-MM"
            size="small"
            style="width:140px"
          />
          <!-- 年: 年选择器 -->
          <el-date-picker
            v-else-if="timeType === 'year'"
            v-model="dateYear"
            type="year"
            value-format="YYYY"
            size="small"
            style="width:140px"
          />

          <!-- 时间段: 范围选择器 -->
          <template v-if="timeType === 'range'">
            <el-date-picker
              v-model="dateRange"
              type="daterange"
              value-format="YYYY-MM-DD"
              size="small"
              style="width:260px"
              range-separator=" - "
            />
          </template>

          <el-button type="primary" size="small" :icon="Search" :loading="loading" @click="doSearch()">
            确定
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- ====== 主体: 左侧分项树 + 右侧饼图 ====== -->
    <el-row :gutter="16" style="margin-top:12px">
      <el-col :span="5">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
            <span>用电类型</span>
            </div>

    </template>
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ children: 'children', label: 'name', disabled: 'disabled' }"
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
          <template #header><div style="font-size:14px;font-weight:600">能耗数据</div></template>
          <div ref="chartRef" style="width:100%;height:420px"></div>
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
import { ref, onMounted, watch, nextTick } from 'vue'
import { Clock, Calendar, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getEnergyItems, getEnergyRatio, getEnergyAnalysis } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref([])
const treeRef = ref(null)
const chartRef = ref(null)
let chartInstance: echarts.ECharts | null = null

const convertBtns = [
  { type: 3, label: '分项能耗' },
  { type: 1, label: '标准煤' },
  { type: 2, label: '碳排量' },
  { type: 4, label: '单位面积能耗' },
]
const conversionType = ref(3)
const summaryData = ref<any>(null)
const conversionInfo = ref<any>(null)
const timeType = ref('day')
const dateSingle = ref(new Date().toISOString().slice(0, 10))
const dateMonth = ref(new Date().toISOString().slice(0, 7))
const dateYear = ref(new Date().toISOString().slice(0, 4))
const dateRange = ref(null)

function switchConversion(t: number) { conversionType.value = t; doSearch() }
function onTimeTypeChange() { doSearch() }

async function loadTree() {
  loading.value = true
  try {
    const r = await getEnergyItems(app.buildingSign)
    if (r.success) {
      treeData.value = r['总用电'] || r.data || []
      nextTick(() => {
        // 默认勾选四大分项: 空调用电(11), 动力用电(12), 照明插座(13), 特殊用电(14)
        ;[11, 12, 13, 14].forEach(id => treeRef.value?.setChecked(id, true, false))
        doSearch()
      })
    }
  } catch { ElMessage.error('加载用电类型失败') }
  finally { loading.value = false }
}

async function doSearch() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (!checked.length) { ElMessage.warning('请选择用电类型'); return }
  const p: any = { sign: app.buildingSign, item_ids: checked.join(","), conversion_type: conversionType.value, xdate: timeType.value }
  if (timeType.value === 'day') { p.start_date = p.end_date = dateSingle.value }
  else if (timeType.value === 'month') { p.start_date = dateMonth.value + '-01'; const [y, m] = dateMonth.value.split('-').map(Number); p.end_date = dateMonth.value + '-' + String(new Date(y, m, 0).getDate()).padStart(2, '0') }
  else if (timeType.value === 'year') { p.start_date = dateYear.value + '-01-01'; p.end_date = dateYear.value + '-12-31' }
  else if (timeType.value === 'range' && dateRange.value) { p.start_date = dateRange.value[0]; p.end_date = dateRange.value[1] }
  loading.value = true
  try {
    const [ratioR, analysisR] = await Promise.all([
      getEnergyRatio(p),
      getEnergyAnalysis(p)
    ])
    if (ratioR.success && ratioR.data) {
      summaryData.value = analysisR.summary || { total_energy: ratioR.total || 0 }
      conversionInfo.value = analysisR.conversion || ratioR.conversion || null
      renderChart(ratioR.data)
    }
  } catch { ElMessage.error('查询失败') }
  finally { loading.value = false }
}

function renderChart(data: any) {
  if (!chartRef.value) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)
  const total = data.reduce((s: number, d: any) => s + (d.value || 0), 0)
  chartInstance.setOption({
    tooltip: {
      trigger: 'item',
      formatter: function (params: any) {
        return params.name + ': <strong>' + Number(params.value).toFixed(3) + '</strong> ' + (conversionInfo.value?.unit || '') + ' (' + params.percent + '%)'
      }
    },
    legend: { bottom: '0%' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: data,
      label: { show: true, formatter: '{b}: {d}%' }
    }]
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
</style>
