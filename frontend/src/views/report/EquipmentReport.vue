<template>
  <div class="report-page">
    <el-card shadow="hover">
      <div class="toolbar">
        <span class="label">时间范围</span>
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" size="small" style="width:240px" range-separator=" - " />
        <el-select v-model="conversionType" size="small" style="width:100px">
          <el-option label="原始数据" :value="3" /><el-option label="标准煤" :value="1" /><el-option label="碳排量" :value="2" />
        </el-select>
        <el-button type="primary" size="small" :loading="loading" @click="doQuery">查询</el-button>
        <el-button size="small" @click="doPrint">打印</el-button>
      </div>
    </el-card>
    <div id="printArea" class="report-content" style="margin-top:12px">
      <div class="report-title">设备能耗报表</div>
      <div class="report-date">{{ dateRange?.[0] }} ~ {{ dateRange?.[1] }}</div>
      <el-table :data="tableData" border stripe size="small" v-loading="loading" style="width:100%">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="name" label="设备名称" min-width="180" />
        <el-table-column label="能耗值" width="140" align="right">
          <template #default="{row}">{{ Number(row.total).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="占比(%)" width="100" align="right">
          <template #default="{row}">{{ row.pct }}%</template>
        </el-table-column>
      </el-table>
      <div v-if="summary" class="report-summary">
        <span>合计: <strong>{{ Number(summary.total_energy).toFixed(3) }}</strong> {{ conversionInfo?.unit }}</span>
        <span style="margin-left:20px">单位面积: <strong>{{ Number(summary.per_area_energy).toFixed(3) }}</strong> {{ conversionInfo?.unit }}/m²</span>
        <span style="margin-left:20px">参考价值: <strong>{{ Number(summary.reference_value).toFixed(2) }}</strong> 元</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getEquipmentAnalysis } from '@/api/index'
const app = useAppStore()
const loading = ref(false)
const now = new Date()
const dateRange = ref<any[]>([`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-01`, now.toISOString().slice(0,10)])
const conversionType = ref(3)
const conversionInfo = ref<any>(null)
const summary = ref<any>(null)
const tableData = ref<any[]>([])
async function doQuery() {
  if (!dateRange.value?.[0]) return ElMessage.warning('请选择时间')
  loading.value = true
  try {
    const r = await getEquipmentAnalysis({ sign: app.buildingSign, item_ids: '', start_date: dateRange.value[0], end_date: dateRange.value[1], xdate: 'range', conversion_type: conversionType.value })
    if (r.success) {
      conversionInfo.value = r.conversion
      summary.value = r.summary
      const items = r.data || []
      const total = items.reduce((s: number, t: any) => s + (t.total || 0), 0) || 1
      tableData.value = items.map((t: any) => ({ name: t.name, total: t.total || 0, pct: total > 0 ? (t.total / total * 100).toFixed(1) : '0' }))
    }
  } catch { ElMessage.error('查询失败') }
  finally { loading.value = false }
}
function doPrint() { window.print() }
</script>
<style scoped>
.toolbar { display:flex;align-items:center;gap:12px;flex-wrap:wrap }
.label { font-size:13px;color:#666;white-space:nowrap }
.report-content { background:#fff;padding:20px;border-radius:8px }
.report-title { font-size:18px;font-weight:700;text-align:center;margin-bottom:4px;color:#1a1a2e }
.report-date { font-size:12px;text-align:center;color:#8c8c8c;margin-bottom:16px }
.report-summary { margin-top:12px;padding:12px 16px;background:#fafafa;border-radius:6px;font-size:13px;color:#595959 }
@media print { .toolbar { display:none } .report-content { padding:0 } }
</style>