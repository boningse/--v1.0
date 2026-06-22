import { createRouter, createWebHashHistory } from 'vue-router'; import { useAuthStore } from '@/stores/index'
const routes = [
  { path: '/login', component: () => import('@/views/login/Login.vue') },
  { path: '/', component: () => import('@/components/layout/MainLayout.vue'), redirect: '/home', children: [
    { path: 'home', component: () => import('@/views/home/Home.vue'), meta: { title: '首页' } },
    { path: 'energy-analysis', component: () => import('@/views/energy/Analysis.vue'), meta: { title: '分项分析' } },
    { path: 'energy-ratio', component: () => import('@/views/energy/Ratio.vue'), meta: { title: '分项比例' } },
    { path: 'energy-compare', component: () => import('@/views/energy/Compare.vue'), meta: { title: '分项对比' } },
    { path: 'tenement-analysis', component: () => import('@/views/tenement/Analysis.vue'), meta: { title: '分户分析' } },
    { path: 'tenement-compare', component: () => import('@/views/tenement/Compare.vue'), meta: { title: '分户对比' } },
    { path: 'equipment-analysis', component: () => import('@/views/equipment/Analysis.vue'), meta: { title: '设备分析' } },
    { path: 'equipment-compare', component: () => import('@/views/equipment/Compare.vue'), meta: { title: '设备对比' } },
    { path: 'realtime-data', component: () => import('@/views/monitor/RealtimeData.vue'), meta: { title: '实时数据' } },
    { path: 'data-table', component: () => import('@/views/monitor/DataTable.vue'), meta: { title: '原始数据' } },
    { path: 'data-alert', component: () => import('@/views/monitor/AlertTable.vue'), meta: { title: '报警管理' } },
    { path: 'report-general', component: () => import('@/views/report/General.vue'), meta: { title: '通用报表' } },
    { path: 'report-branch', component: () => import('@/views/report/Branch.vue'), meta: { title: '支路报表' } },
    { path: 'report-custom', component: () => import('@/views/report/Custom.vue'), meta: { title: '定制报表' } },
  ]}
]
const router = createRouter({ history: createWebHashHistory(), routes })
router.beforeEach((to, _, next) => { const a = useAuthStore(); if (to.path !== '/login' && !a.token) next('/login'); else next() })
export default router
