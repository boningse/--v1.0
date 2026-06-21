import dayjs from 'dayjs'
export const fmtNum = (v: any, d = 2) => v != null ? Number(v).toFixed(d) : '0'
export const today = () => dayjs().format('YYYY-MM-DD')
export const monthStart = () => dayjs().startOf('month').format('YYYY-MM-DD')
export const curMonth = () => dayjs().format('YYYYMM')
