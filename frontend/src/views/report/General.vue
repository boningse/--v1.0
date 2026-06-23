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
      <div class="report-title">分项能耗报表</div>
      <div class="report-date">{{ dateRange?.[0] }} ~ {{ dateRange?.[1] }}</div>
      <el-table :data="tableData" border stripe size="small" v-loading="loading" style="width:100%">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column label="分项名称" min-width="240">
          <template #default="{ row }">
            <span :style="{ paddingLeft: row.level * 20 + 'px', fontWeight: row.level === 0 ? 600 : 400, color: row.level === 0 ? '#1a1a2e' : '#595959' }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="本期能耗" width="120" align="right">
          <template #default="{row}">{{ Number(row.total).toFixed(3) }}</template>
        </el-table-column>
        <el-table-column label="上期能耗" width="120" align="right">
          <template #default="{row}">
            <span v-if="row.prev_total !== null">{{ Number(row.prev_total).toFixed(3) }}</span>
            <span v-else style="color:#bfbfbf">--</span>
          </template>
        </el-table-column>
        <el-table-column label="能耗对比" width="110" align="center">
          <template #default="{row}">
            <span v-if="row.change !== null" :style="{ color: row.change > 0 ? '#ff4d4f' : row.change < 0 ? '#52c41a' : '#8c8c8c', fontWeight: 500 }">
              <span v-if="row.change > 0">↑</span><span v-else-if="row.change < 0">↓</span>
              {{ row.change }}%
            </span>
            <span v-else style="color:#bfbfbf">--</span>
          </template>
        </el-table-column>
        <el-table-column label="占比(%)" width="80" align="right">
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
import { getEnergyItems, getEnergyAnalysis } from '@/api/index'
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
    // 1. 获取分项树
    const treeR = await getEnergyItems(app.buildingSign)
    if (!treeR.success) { ElMessage.error('获取分项树失败'); return }
    const tree = treeR['\u603b\u7528\u7535'] || []
    if (!tree.length) { ElMessage.warning('无分项数据'); return }

    // 2. 收集启用的叶子节点ID
    const enabledIds = []
    const walk = (nodes: any[]) => {
      for (const n of nodes) {
        if (n.children?.length) walk(n.children)
        else if (!n.disabled) enabledIds.push(n.id)
      }
    }
    walk(tree)
    const ids = enabledIds.length ? enabledIds.join(',') : 'total'

    // 3. 查询本期能耗
    const params = { sign: app.buildingSign, item_ids: ids, conversion_type: conversionType.value || 3, xdate: 'range',
      start_date: dateRange.value[0], end_date: dateRange.value[1] }
    const curR = await getEnergyAnalysis(params)
    if (!curR?.success) { ElMessage.error('查询失败：API返回失败'); return }

    conversionInfo.value = curR.conversion || null
    summary.value = curR.summary || null

    // 4. 建立 name→total 映射
    const nameMap = {}
    if (curR.series) {
      for (const s of curR.series) {
        if (s.name === '\u5408\u8ba1' || !s.data) continue
        nameMap[s.name] = s.data.reduce((a, b) => a + b, 0)
      }
    }

    // 5. 查询上期能耗（与本期等长的前一个时间段）
    const fmt = (d) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
    const sd = new Date(dateRange.value[0])
    const ed = new Date(dateRange.value[1])
    const periodDays = Math.round((ed - sd) / (24 * 60 * 60 * 1000)) + 1
    const prevEd = new Date(sd.getTime() - 24 * 60 * 60 * 1000)
    const prevSd = new Date(prevEd.getTime() - (periodDays - 1) * 24 * 60 * 60 * 1000)
    const prevR = await getEnergyAnalysis({ ...params, start_date: fmt(prevSd), end_date: fmt(prevEd) })
    const nameMapPrev = {}
    if (prevR?.success && prevR.series) {
      for (const s of prevR.series) {
        if (s.name === '合计' || !s.data) continue
        nameMapPrev[s.name] = s.data.reduce((a, b) => a + b, 0)
      }
    }

    // 6. 扁平化树，递归计算总值
    const flatNodes = []
    const flattenTree = (nodes, level) => {
      if (!nodes) return
      for (const n of nodes) {
        flatNodes.push({ name: n.name, level, children: n.children || [] })
        if (n.children?.length) flattenTree(n.children, level + 1)
      }
    }
    flattenTree(tree, 0)

    const getTotal = (node, nmap) => {
      if (node.children?.length) {
        return node.children.reduce((s, c) => s + getTotal(c, nmap), 0)
      }
      return nmap[node.name] || 0
    }

    tableData.value = flatNodes.map(n => {
      const total = getTotal(n, nameMap)
      const prev = getTotal(n, nameMapPrev)
      return { name: n.name, level: n.level, total, prev_total: prev || null, change: prev ? Number(((total - prev) / prev * 100).toFixed(1)) : null }
    })
    const grand = tableData.value.reduce((s, r) => s + r.total, 0) || 1
    tableData.value.forEach((r) => r.pct = (r.total / grand * 100).toFixed(1))
  } catch (e) {
    console.error('\u62a5\u8868\u67e5\u8be2\u9519\u8bef:', e)
    ElMessage.error('\u67e5\u8be2\u5931\u8d25: ' + (e?.message || e?.toString() || '\u672a\u77e5\u9519\u8bef'))
  }
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