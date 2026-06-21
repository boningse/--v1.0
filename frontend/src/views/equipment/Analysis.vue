<template>
  <div class="equipment-analysis">
    <!-- ====== 顶部控制栏 ====== -->
    <el-card shadow="hover">
      <div class="toolbar">
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
          <template #header><div style="font-size:14px;font-weight:600">能耗数据</div></template>
          <div ref="chartRef" style="width:100%;height:420px"></div>
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
import { getEquipmentTree, getEquipmentAnalysis } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref([])
const treeRef = ref(null)
const chartRef = ref(null)
let chartInstance: echarts.ECharts | null = null

const timeType = ref('day')
const dateSingle = ref(new Date().toISOString().slice(0, 10))
const dateMonth = ref(new Date().toISOString().slice(0, 7))
const dateYear = ref(new Date().toISOString().slice(0, 4))
const dateRange = ref(null)

function onTimeTypeChange() { doSearch() }

async function loadTree() {
  loading.value = true
  try {
    const r = await getEquipmentTree(app.buildingSign)
    if (r.success) treeData.value = r['总用电'] || r.data || []
  } catch { ElMessage.error('加载设备列表失败') }
  finally { loading.value = false }
}

async function doSearch() {
  const selectedId = treeRef.value?.getCurrentKey()
  if (!selectedId) { ElMessage.warning('请选择设备'); return }
  const p: any = { sign: app.buildingSign, equipment_ids: [selectedId], xdate: timeType.value }
  if (timeType.value === 'day') { p.start_date = p.end_date = dateSingle.value }
  else if (timeType.value === 'month') { p.start_date = dateMonth.value + '-01'; p.end_date = dateMonth.value + '-31' }
  else if (timeType.value === 'year') { p.start_date = dateYear.value + '-01-01'; p.end_date = dateYear.value + '-12-31' }
  else if (timeType.value === 'range' && dateRange.value) { p.start_date = dateRange.value[0]; p.end_date = dateRange.value[1] }
  loading.value = true
  try {
    const r = await getEquipmentAnalysis(p)
    if (r.success && r.data) renderChart(r.data)
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
</script>
<style scoped>
.toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.convert-group { display: flex; align-items: center; gap: 4px; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.label { font-size: 13px; color: #666; white-space: nowrap; }
.ml-2 { margin-left: 8px; }
.tree-card { height: calc(100vh - 220px); overflow-y: auto; }
.tree-header { display: flex; align-items: center; justify-content: space-between; }
.tree-actions { display: flex; gap: 4px; }
</style>