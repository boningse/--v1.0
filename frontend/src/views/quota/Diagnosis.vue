<template>
  <div class="quota-diagnosis">
    <el-card shadow="hover">
      <div class="toolbar">
        <div class="filter-group">
          <span class="label"><el-icon><Clock /></el-icon></span>
          <el-date-picker v-model="queryYear" type="year" value-format="YYYY" size="small" style="width:140px" />
          <el-button type="primary" size="small" :icon="Search" @click="loadData" :loading="loading">诊断</el-button>
          <span v-if="buildingInfo.name" style="font-size:13px;color:#666;margin-left:8px">{{ buildingInfo.name }} · {{ buildingInfo.type }} · {{ fmtNum(buildingInfo.area) }} m²</span>
        </div>
        <div style="font-size:12px;color:#999">基于山东省公共机构用电定额标准 · 多维度节能诊断</div>
      </div>
    </el-card>

    <!-- 维度一：能耗概况 -->
    <el-row :gutter="12" style="margin-top:12px">
      <el-col :span="6">
        <div class="grade-card">
          <div class="grade-score">{{ gradeData.grade }}</div>
          <div class="grade-label">{{ gradeData.label }}</div>
          <div class="grade-desc">{{ gradeData.desc }}</div>
          <div class="grade-items">
            <div v-for="g in gradeData.items" :key="g.name" class="grade-item">
              <span class="gi-name">{{ g.name }}</span>
              <span class="gi-score" :style="{ color: g.color }">{{ g.val }}</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" style="height:100%">
          <template #header><span class="card-title">能耗概览</span></template>
          <div class="overview-stats">
            <div class="os-item"><span class="os-label">年度总能耗</span><span class="os-value">{{ fmtNum(energyData.total, 2) }} <small>tce</small></span></div>
            <div class="os-item"><span class="os-label">单位面积能耗</span><span class="os-value">{{ fmtNum(energyData.perArea, 2) }} <small>kgce/m²</small></span></div>
            <div class="os-item"><span class="os-label">年用电量</span><span class="os-value">{{ fmtNum(energyData.total / SD_EF * 1000, 0) }} <small>kWh</small></span></div>
            <div class="os-item"><span class="os-label">碳足迹估算</span><span class="os-value">{{ fmtNum(energyData.total * 2.6, 2) }} <small>tCO₂</small></span></div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" style="height:100%">
          <template #header><span class="card-title">月度能耗趋势 vs 定额标准</span></template>
          <div ref="chartTrendRef" style="width:100%;height:240px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 维度二：分项定额对标 -->
    <el-row :gutter="12" style="margin-top:12px">
      <el-col :span="16">
        <el-card shadow="hover" style="height:100%">
          <template #header><span class="card-title">分项定额对标分析</span></template>
          <el-table :data="quotaCompareRows" stripe size="small" style="width:100%">
            <el-table-column prop="name" label="分项" width="80" />
            <el-table-column prop="actual" label="实际(tce)" width="100" />
            <el-table-column prop="quota" label="定额(tce)" width="100" />
            <el-table-column prop="pct" label="占比" width="80" />
            <el-table-column prop="diff" label="偏差" width="100" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.over ? 'danger' : 'success'" size="small">{{ row.over ? '超标' : '达标' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="建议">
              <template #default="{ row }">
                <span style="font-size:12px;color:#999">{{ row.advice }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" style="height:100%">
          <template #header><span class="card-title">分项占比</span></template>
          <div ref="chartPieRef" style="width:100%;height:260px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 维度三：诊断建议 -->
    <el-card shadow="hover" style="margin-top:12px">
      <template #header><span class="card-title">诊断建议</span></template>
      <div class="diag-grid">
        <div v-for="(item, idx) in diagnosisItems" :key="idx" class="diag-item" :class="'sev-' + item.severity" style="margin-bottom:0">
          <div class="diag-left">
            <div class="diag-icon" :style="{ background: item.bg }">{{ item.icon }}</div>
            <div class="diag-info">
              <div class="diag-title">{{ item.title }}</div>
              <div class="diag-desc">{{ item.desc }}</div>
            </div>
          </div>
          <div class="diag-right">
            <el-tag :type="item.tagType" size="small">{{ item.tag }}</el-tag>
          </div>
        </div>
      </div>
    </el-card>

    <div v-if="pageError" style="padding:40px;text-align:center;color:#ff4d4f">
      <h3>页面加载异常</h3><p style="font-size:12px;margin-top:8px">{{ pageError }}</p>
      <el-button size="small" style="margin-top:12px" @click="pageError='';loadData()">重试</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, onErrorCaptured } from 'vue'
import { Clock, Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { fmtNum } from '@/utils/index'
import request from '@/api/request'
import * as echarts from 'echarts'

const SD_EF = 0.31

const app = useAppStore()
const loading = ref(false)
const pageError = ref('')
const queryYear = ref(new Date().getFullYear().toString())
const chartTrendRef = ref<HTMLElement|null>(null)
const chartPieRef = ref<HTMLElement|null>(null)
let chartTrend: echarts.ECharts|null = null
let chartPie: echarts.ECharts|null = null

const buildingInfo = reactive({ name: '', type: '', area: 0 })
const energyData = reactive({ total: 0, perArea: 0, monthlyEnergy: [] as number[] })
const subItems = reactive<Record<number, number>>({ 11:0, 12:0, 13:0, 14:0 })

const QUOTA: Record<string, { constraint: number; baseline: number; guidance: number }> = {
  '行政机关': { constraint: 35, baseline: 28, guidance: 20 },
  '高等院校': { constraint: 30, baseline: 24, guidance: 17 },
  '中小学校': { constraint: 18, baseline: 13, guidance: 9 },
  '医疗机构': { constraint: 65, baseline: 50, guidance: 35 },
  '文化场馆': { constraint: 25, baseline: 18, guidance: 12 },
  '体育场馆': { constraint: 40, baseline: 30, guidance: 20 },
  '科研机构': { constraint: 32, baseline: 25, guidance: 18 },
}
const DEF = { constraint: 40, baseline: 30, guidance: 20 }
const stdVal = computed(() => {
  const t = buildingInfo.type
  return QUOTA[t] || (t === 'A' ? QUOTA['行政机关'] : DEF)
})

const SUB_META: Record<number, { name: string }> = { 11: { name: '照明' }, 12: { name: '空调' }, 13: { name: '动力' }, 14: { name: '特殊' } }

// 综合评级
const gradeData = computed(() => {
  const pa = energyData.perArea; const s = stdVal.value
  let grade: string, label: string
  if (pa <= s.guidance) { grade = 'A'; label = '优秀' }
  else if (pa <= s.baseline) { grade = 'B'; label = '良好' }
  else if (pa <= s.constraint) { grade = 'C'; label = '一般' }
  else { grade = 'D'; label = '超标' }
  return {
    grade, label, desc: '实际 ' + fmtNum(pa, 2) + ' kgce/m² · ' + buildingInfo.type,
    items: [
      { name: '约束值', val: s.constraint + ' kgce/m²', color: '#ff4d4f' },
      { name: '基准值', val: s.baseline + ' kgce/m²', color: '#1890ff' },
      { name: '引导值', val: s.guidance + ' kgce/m²', color: '#52c41a' },
      { name: '单位面积', val: fmtNum(pa, 2) + ' kgce/m²', color: '#722ed1' },
    ]
  }
})

// 分项定额对标行
const quotaCompareRows = computed(() => {
  const s = stdVal.value; const area = buildingInfo.area || 1
  const totalActual = [11,12,13,14].reduce((a, id) => a + (subItems[id] || 0), 0) || 1
  const totalQuota = s.baseline * area / 1000
  return [11,12,13,14].map(id => {
    const actual = subItems[id] || 0
    const pct = actual / totalActual
    const quota = totalQuota * pct
    const over = actual > quota
    const diff = actual - quota
    const advice = over ? '超出定额 ' + fmtNum(diff, 2) + ' tce，建议优化' : '在定额范围内，保持良好'
    return { name: SUB_META[id].name, id, actual: +actual.toFixed(2), quota: +quota.toFixed(2), pct: (pct * 100).toFixed(1) + '%', diff: (over ? '+' : '') + diff.toFixed(2), over, advice }
  })
})

// 诊断建议
const diagnosisItems = computed(() => {
  const s = stdVal.value; const pa = energyData.perArea; const area = buildingInfo.area || 1; const rows = quotaCompareRows.value
  const items: any[] = []
  let overCount = 0; let totalAdvice = 0
  rows.forEach(r => { if (r.over) overCount++; totalAdvice += Math.max(0, r.actual - r.quota) })
  if (pa > s.constraint) items.push({ title: '单位面积能耗超出约束值', severity: 'high', icon: '🚨', bg: '#fff1f0', tag: '紧急', tagType: 'danger', desc: '实际 ' + fmtNum(pa, 2) + ' kgce/m² 超过约束值 ' + s.constraint + ' kgce/m²，超标幅度 ' + fmtNum((pa - s.constraint) / s.constraint * 100, 1) + '%，需立即制定节电方案。' })
  if (pa > s.baseline) items.push({ title: '能耗高于基准值，存在优化空间', severity: 'mid', icon: '⚡', bg: '#fff7e6', tag: '关注', tagType: 'warning', desc: '实际 ' + fmtNum(pa, 2) + ' kgce/m² 高于基准值 ' + s.baseline + ' kgce/m²，超出 ' + fmtNum((pa - s.baseline) / s.baseline * 100, 1) + '%，可对标引导值 ' + s.guidance + ' kgce/m² 进行优化。' })
  if (pa <= s.guidance) items.push({ title: '能耗管理优秀，继续保持', severity: 'low', icon: '🎉', bg: '#f6ffed', tag: '优秀', tagType: 'success', desc: '实际能耗 ' + fmtNum(pa, 2) + ' kgce/m² 低于引导值 ' + s.guidance + ' kgce/m²，节能管理工作成效显著。' })
  rows.filter(r => r.over).forEach(r => items.push({ title: r.name + '分项超出定额', severity: 'mid', icon: '📊', bg: '#fff7e6', tag: '超标', tagType: 'warning', desc: r.name + '实际 ' + r.actual + ' tce 超出定额 ' + r.quota + ' tce，超量 ' + r.diff + ' tce，建议重点排查该分项用电设备。' }))
  if (overCount === 0) items.push({ title: '所有分项均在定额范围内', severity: 'low', icon: '✅', bg: '#f6ffed', tag: '达标', tagType: 'success', desc: '照明、空调、动力、特殊四大分项均未超标，节能状态良好。' })
  items.push({ title: '建议实现精细化用电管理', severity: 'low', icon: '🎯', bg: '#e6f7ff', tag: '建议', tagType: 'info', desc: '对照明、空调等主要分项实施分项计量，建立用电统计分析制度，持续跟踪能耗变化趋势。' })
  return items
})

function renderCharts() {
  try {
    // 月度趋势图
    if (chartTrendRef.value) {
      chartTrend?.dispose(); chartTrend = echarts.init(chartTrendRef.value)
      const s = stdVal.value; const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月']
      chartTrend.setOption({
        tooltip: { trigger: 'axis' }, grid: { left: 50, right: 15, top: 30, bottom: 25 },
        xAxis: { type: 'category', data: months, axisLabel: { fontSize: 10 } },
        yAxis: { type: 'value', name: 'tce' },
        series: [{
          type: 'line', smooth: true, data: energyData.monthlyEnergy,
          symbol: 'circle', symbolSize: 6, lineStyle: { color: '#1890ff', width: 2 }, areaStyle: { color: 'rgba(24,144,255,.1)' },
          markLine: {
            symbol: 'none',
            data: [
              { yAxis: s.constraint * buildingInfo.area / 1000 * 0.105, label: { formatter: '约束线', fontSize: 10 }, lineStyle: { color: '#ff4d4f', type: 'dashed' } },
              { yAxis: s.baseline * buildingInfo.area / 1000 * 0.105, label: { formatter: '基准线', fontSize: 10 }, lineStyle: { color: '#fa8c16', type: 'dashed' } },
            ],
          },
        }],
      })
    }
    // 分项占比饼图
    if (chartPieRef.value) {
      chartPie?.dispose(); chartPie = echarts.init(chartPieRef.value)
      const pieData = [11,12,13,14].map(id => ({ name: SUB_META[id].name, value: subItems[id] || 0 })).filter(d => d.value > 0)
      chartPie.setOption({
        tooltip: { trigger: 'item', formatter: '{b}: {c} tce ({d}%)' },
        series: [{ type: 'pie', radius: ['30%', '65%'], center: ['50%', '55%'], data: pieData.length ? pieData : [{ name: '暂无数据', value: 1 }], label: { show: true, formatter: '{b}\n{d}%', fontSize: 11 }, itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 } }],
      })
    }
  } catch (e) { console.warn('Chart error:', e) }
}

async function loadData() {
  loading.value = true; pageError.value = ''
  try {
    const br = await request.get('/dashboard/homepage', { params: { sign: app.buildingSign, energy_type: 1 } })
    if (br.success) { const b = br.data.building; buildingInfo.name = b.name || ''; buildingInfo.type = b.type || ''; buildingInfo.area = Number(b.area) || 0 }
    const [sd, ed] = [queryYear.value + '-01-01', queryYear.value + '-12-31']
    const er = await request.get('/energy/analysis', { params: { sign: app.buildingSign, item_ids: 'total', start_date: sd, end_date: ed, xdate: 'year', conversion_type: 3 } })
    if (er.success) {
      const rawT = Number(er.summary?.total_energy) || 0
      energyData.total = rawT * SD_EF / 1000
      energyData.perArea = buildingInfo.area > 0 ? rawT * SD_EF / buildingInfo.area : 0
      const ts = (er.series || []).find((s: any) => s.name === '合计' || s.name === '总用电合计')
      energyData.monthlyEnergy = ts?.data?.map((v: any) => Number(v) * SD_EF / 1000 || 0) || []
    }
    const subEr = await request.get('/energy/analysis', { params: { sign: app.buildingSign, item_ids: '11,12,13,14', start_date: sd, end_date: ed, xdate: 'year', conversion_type: 3 } })
    if (subEr.success) {
      Object.entries(subEr.summary?.item_totals || {}).forEach(([id, val]) => {
        subItems[Number(id)] = Number(val) * SD_EF / 1000
      })
    }
    await nextTick(); renderCharts()
  } catch (e: any) { pageError.value = String(e); console.error(e) }
  finally { loading.value = false }
}

onErrorCaptured((err) => { pageError.value = String(err); console.error(err); return false })
onMounted(() => { loadData() })
onUnmounted(() => { try { chartTrend?.dispose(); chartPie?.dispose() } catch(e) {} })
</script>

<style scoped>
.quota-diagnosis { position: relative; }
.toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; justify-content: space-between; }
.filter-group { display: flex; align-items: center; gap: 6px; }
.card-title { font-size: 14px; font-weight: 600; color: #1a1a2e; }
.grade-card { background: linear-gradient(135deg,#1a1a2e,#16213e); border-radius: 12px; padding: 20px; color: #fff; height: 100%; }
.grade-score { font-size: 48px; font-weight: 700; line-height: 1; margin-bottom: 4px; }
.grade-label { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
.grade-desc { font-size: 11px; opacity: .7; margin-bottom: 16px; }
.grade-items { display: flex; flex-wrap: wrap; gap: 6px; }
.grade-item { background: rgba(255,255,255,.08); border-radius: 6px; padding: 6px 10px; display: flex; align-items: center; justify-content: space-between; width: calc(50% - 3px); }
.gi-name { font-size: 10px; opacity: .8; } .gi-score { font-size: 12px; font-weight: 700; }
.overview-stats { padding: 4px 0; }
.os-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f5f5f5; }
.os-item:last-child { border-bottom: none; }
.os-label { font-size: 13px; color: #666; }
.os-value { font-size: 16px; font-weight: 700; color: #1a1a2e; }
.os-value small { font-size: 11px; font-weight: 400; color: #999; }
.diag-grid { display: grid; gap: 0; }
.diag-item { display: flex; align-items: flex-start; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid #f5f5f5; gap: 12px; }
.diag-item:last-child { border-bottom: none; }
.diag-left { display: flex; gap: 12px; flex: 1; }
.diag-icon { width: 36px; height: 36px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.diag-info { flex: 1; }
.diag-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 2px; }
.diag-desc { font-size: 12px; color: #999; line-height: 1.5; }
.diag-right { text-align: right; flex-shrink: 0; }
.el-tag { margin-top: 2px; }
</style>
