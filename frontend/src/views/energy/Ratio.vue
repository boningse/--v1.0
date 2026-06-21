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
              <span class="summary-label">总能耗</span>
              <span class="summary-value">{{ summaryData.total_energy }}</span>
              <span class="summary-unit">{{ conversionInfo?.unit }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Clock, Calendar, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getEnergyItems, getEnergyRatio } from '@/api/index'

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
    if (r.success) treeData.value = r['总用电'] || r.data || []
  } catch { ElMessage.error('加载用电类型失败') }
  finally { loading.value = false }
}

async function doSearch() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (!checked.length) { ElMessage.warning('请选择用电类型'); return }
  const p: any = { sign: app.buildingSign, item_ids: checked, conversion_type: conversionType.value, xdate: timeType.value }
  if (timeType.value === 'day') { p.start_date = p.end_date = dateSingle.value }
  else if (timeType.value === 'month') { p.start_date = dateMonth.value + '-01'; p.end_date = dateMonth.value + '-31' }
  else if (timeType.value === 'year') { p.start_date = dateYear.value + '-01-01'; p.end_date = dateYear.value + '-12-31' }
  else if (timeType.value === 'range' && dateRange.value) { p.start_date = dateRange.value[0]; p.end_date = dateRange.value[1] }
  loading.value = true
  try {
    const r = await getEnergyRatio(p)
    if (r.success && r.data) {
      summaryData.value = { total_energy: r.total || 0 }
      conversionInfo.value = r.conversion || null
      renderChart(r.data)
    }
  } catch { ElMessage.error('查询失败') }
  finally { loading.value = false }
}

function renderChart(data: any) {
  if (!chartRef.value) return
  if (!chartInstance) chartInstance = echarts.init(chartRef.value)
  chartInstance.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: '0%' },
    series: [{
      type: 'pie', radius: ['40%', '70%'],
      data: (data.series || []).map((s: any) => ({ name: s.name, value: s.data?.[0] || 0 })),
      label: { show: true, formatter: '{b}: {d}%' }
    }]
  })
}

function onTreeCheck() { doSearch() }
onMounted(() => { loadTree() })
watch(() => app.buildingSign, () => { loadTree() })
</script>
<style scoped>
.toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.toolbar .filter-group { margin-left: auto; }
.convert-group { display: flex; align-items: center; gap: 4px; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.label { font-size: 13px; color: #666; white-space: nowrap; }
.ml-2 { margin-left: 8px; }
.tree-card { height: calc(100vh - 220px); overflow-y: auto; border-radius: 10px; }
.tree-header { display: flex; align-items: center; justify-content: space-between; font-weight: 600; color: #1a1a2e; }
.tree-actions { display: flex; gap: 4px; }
.summary-grid
 {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}
.summary-item {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 8px 16px;
  background: #fafafa;
  border-radius: 6px;
  min-width: 140px;
}
.summary-label {
  font-size: 13px;
  color: #666;
}
.summary-value {
  font-size: 18px;
  font-weight: 700;
  color: #1890ff;
}
.summary-unit {
  font-size: 12px;
  color: #999;
}
.summary-item.trend-down {
  background: #fff1f0;
}
.summary-item.trend-down .summary-value {
  color: #f5222d;
}
.summary-item.trend-up {
  background: #f6ffed;
}
.summary-item.trend-up .summary-value {
  color: #52c41a;
}
.trend-arrow {
  font-size: 14px;
  margin-left: 2px;
}
</style>
