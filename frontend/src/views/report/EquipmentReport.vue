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
        <el-table-column label="设备名称" min-width="160">
          <template #default="{ row }">
            <span :style="{ paddingLeft: row.level * 20 + 'px', fontWeight: row.level === 0 ? 600 : 400, color: row.level === 0 ? '#1a1a2e' : '#595959' }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="本期能耗" width="140" align="right">
          <template #default="{row}">{{ Number(row.total).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="上期能耗" width="140" align="right">
          <template #default="{row}">
            <span v-if="row.prev_total !== null">{{ Number(row.prev_total).toFixed(3) }}</span>
            <span v-else style="color:var(--text-secondary)">--</span>
          </template>
        </el-table-column>
        <el-table-column label="能耗对比" width="130" align="center">
          <template #default="{row}">
            <span v-if="row.change !== null" :style="{ color: row.change > 0 ? '#ff4d4f' : row.change < 0 ? '#52c41a' : '#8c8c8c', fontWeight: 500 }">
              <span v-if="row.change > 0">↑</span><span v-else-if="row.change < 0">↓</span>
              {{ row.change }}%
            </span>
            <span v-else style="color:var(--text-secondary)">--</span>
          </template>
        </el-table-column>
        <el-table-column label="占比(%)" width="100" align="right">
          <template #default="{row}">{{ row.pct }}%</template>
        </el-table-column>
      </el-table>
      <div v-if="summary" class="report-summary">
        <span>合计: <strong>{{ Number(summary.total_energy).toFixed(3) }}</strong> {{ conversionInfo?.unit }}</span>
        <span style="margin-left:20px">单位面积: <strong>{{ Number(summary.per_area_energy).toFixed(3) }}</strong> {{ conversionInfo?.unit }}/m²</span>
        <span style="margin-left:20px">参考价值: <strong>{{ Number(summary.reference_value).toFixed(2) }}</strong> 元</span>
        <span style="margin-left:20px">趋势: <strong>{{ summary.trend }}%</strong></span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getEquipmentTree, getEquipmentAnalysis } from '@/api/index'
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
    // 1. 获取设备树结构
    const treeR = await getEquipmentTree(app.buildingSign)
    const treeTree = treeR?.tree || []
    const hasTree = treeTree.length > 0

    // 2. 当前期能耗数据
    const params = { sign: app.buildingSign, item_ids: '', start_date: dateRange.value[0], end_date: dateRange.value[1], xdate: 'range', conversion_type: conversionType.value || 3 }
    const curR = await getEquipmentAnalysis(params)
    if (!curR?.success) { ElMessage.error('查询失败：API返回失败'); return }
    conversionInfo.value = curR.conversion || null
    summary.value = curR.summary || null
    const curItems = curR.data || []

    // 3. 建立 sign → total 映射
    const signMap: Record<string, number> = {}
    for (const item of curItems) {
      signMap[item.sign] = item.total || 0
    }

    // 4. 上期能耗（与本期等长的前一个时间段）
    const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    const sd = new Date(dateRange.value[0])
    const ed = new Date(dateRange.value[1])
    const periodDays = Math.round((ed - sd) / (24 * 60 * 60 * 1000)) + 1
    const prevEd = new Date(sd.getTime() - 24 * 60 * 60 * 1000)
    const prevSd = new Date(prevEd.getTime() - (periodDays - 1) * 24 * 60 * 60 * 1000)
    const signMapPrev: Record<string, number> = {}
    try {
      const prevR = await getEquipmentAnalysis({ ...params, start_date: fmt(prevSd), end_date: fmt(prevEd) })
      if (prevR?.success && prevR.data) {
        for (const item of prevR.data) {
          signMapPrev[item.sign] = item.total || 0
        }
      }
    } catch {}

    // 5. 生成表格数据：有树则展示层级，无树则平铺
    if (hasTree) {
      const flatNodes: { name: string; sign: string; level: number }[] = []
      const flattenTree = (nodes: any[], level: number) => {
        if (!nodes) return
        for (const n of nodes) {
          flatNodes.push({ name: n.name, sign: n.sign, level })
          if (n.children?.length) flattenTree(n.children, level + 1)
        }
      }
      flattenTree(treeTree, 0)

      // grandTotal = 只取第一级节点（level 0）的数据
      const grandTotal = flatNodes.filter(n => n.level === 0).reduce((s: number, n) => s + (signMap[n.sign] || 0), 0) || 1

      // 同步更新 summary 为只包含一级节点的合计
      if (summary.value && summary.value.total_energy > 0) {
        const ratio = grandTotal / summary.value.total_energy
        summary.value.total_energy = grandTotal
        summary.value.per_area_energy = Number((summary.value.per_area_energy * ratio).toFixed(3))
        summary.value.reference_value = Number((summary.value.reference_value * ratio).toFixed(2))
      }

      tableData.value = flatNodes.map(n => {
        const total = signMap[n.sign] || 0
        const prev = signMapPrev[n.sign]
        return { name: n.name, level: n.level, total, prev_total: prev != null ? prev : null, change: prev ? Number(((total - prev) / prev * 100).toFixed(1)) : null, pct: (total / grandTotal * 100).toFixed(1) }
      })
    } else {
      const grandTotal = curItems.reduce((s: number, t: any) => s + (t.total || 0), 0) || 1
      tableData.value = curItems.map((t: any, i: number) => {
        const prev = signMapPrev[t.sign]
        return { name: t.name, level: 0, total: t.total || 0, prev_total: prev != null ? prev : null, change: prev ? Number(((t.total - prev) / prev * 100).toFixed(1)) : null, pct: (t.total / grandTotal * 100).toFixed(1) }
      })
    }
  } catch (e) {
    console.error('报表查询错误:', e)
    ElMessage.error('查询失败: ' + (e?.message || e?.toString() || '未知错误'))
  }
  finally { loading.value = false }
}
function doPrint() { window.print() }
</script>
<style scoped>
.toolbar { display:flex;align-items:center;gap:12px;flex-wrap:wrap }
.label { font-size:13px;color:var(--text-secondary);white-space:nowrap }
.report-content { background:var(--card-bg);padding:36px;border-radius:8px }
.report-title { font-size:22px;font-weight:700;text-align:center;margin-bottom:6px;color:var(--text-primary) }
.report-date { font-size:13px;text-align:center;color:var(--text-secondary);margin-bottom:24px }
.report-summary { margin-top:12px;padding:24px 20px;background:var(--main-bg);border-radius:6px;font-size:15px;color:var(--text-secondary) }
@media print { .toolbar { display:none } .report-content { padding:0 } }


.energy-analysis, .tenement-analysis, .equipment-analysis, .report-page {
  position: relative;
}
.energy-analysis::before, .tenement-analysis::before, .equipment-analysis::before, .report-page::before {
  content: ''; position: absolute; top: 200px; left: -5%; width: 110%; height: 400px;
  background:
    radial-gradient(ellipse at 30% 30%, rgba(19,199,133,.04) 0%, transparent 60%),
    radial-gradient(ellipse at 70% 50%, rgba(24,144,255,.04) 0%, transparent 50%);
  pointer-events: none; z-index: 0;
}
.energy-analysis > *, .tenement-analysis > *, .equipment-analysis > *, .report-page::before + * { position: relative; z-index: 1; }
.energy-analysis > *, .tenement-analysis > *, .equipment-analysis > * { position: relative; z-index: 1; }



/* 卡片装饰条 */
.el-card { position: relative; overflow: visible; }
.el-card:not(.is-always-shadow) { overflow: hidden; }

</style>