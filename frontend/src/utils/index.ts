import dayjs from 'dayjs'
import * as XLSX from 'xlsx'
export const fmtNum = (v: any, d = 2) => v != null ? Number(v).toFixed(d) : '0'
export const today = () => dayjs().format('YYYY-MM-DD')
export const monthStart = () => dayjs().startOf('month').format('YYYY-MM-DD')
export const curMonth = () => dayjs().format('YYYYMM')
export function exportTableToExcel(
  data: { name: string; total: number; prev_total: number | null; change: number | null; pct: string }[],
  title: string,
  dateRange: string[],
  summary: any,
  conversionInfo: any,
) {
  const wsData: any[][] = [
    [title],
    [`${dateRange[0] || ''} ~ ${dateRange[1] || ''}`],
    [],
    ['序号', '名称', '本期能耗', '上期能耗', '能耗对比(%)', '占比(%)'],
  ]
  data.forEach((row, i) => {
    wsData.push([
      i + 1,
      row.name,
      Number(row.total).toFixed(3),
      row.prev_total !== null ? Number(row.prev_total).toFixed(3) : '--',
      row.change !== null ? (row.change > 0 ? '+' : '') + row.change + '%' : '--',
      row.pct + '%',
    ])
  })
  if (summary) {
    wsData.push([])
    wsData.push(['', '合计', Number(summary.total_energy).toFixed(3), '', '', ''])
    wsData.push(['', '单位面积能耗', Number(summary.per_area_energy).toFixed(3) + ' ' + (conversionInfo?.unit || '') + '/m²', '', '', ''])
    wsData.push(['', '参考价值', Number(summary.reference_value).toFixed(2) + ' 元', '', '', ''])
    wsData.push(['', '趋势', (summary.trend || 0) + '%', '', '', ''])
  }
  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.aoa_to_sheet(wsData)
  ws['!cols'] = [{ wch: 6 }, { wch: 30 }, { wch: 14 }, { wch: 14 }, { wch: 14 }, { wch: 10 }]
  XLSX.utils.book_append_sheet(wb, ws, '报表')
  XLSX.writeFile(wb, `${title}_${dateRange[0] || ''}_${dateRange[1] || ''}.xlsx`)
}
