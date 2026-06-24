<template><router-view/></template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/index'
import 'element-plus/theme-chalk/dark/css-vars.css'
const app = useAppStore()
onMounted(() => { app.applyDark(app.darkMode) })
</script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
html,body,#app{height:100%;font-family:'PingFang SC',Helvetica,Arial,sans-serif}
:root {
  --sidebar-bg: #001529;
  --sidebar-menu-text: #ffffffb3;
  --sidebar-menu-active: #1890ff;
  --header-bg: #fff;
  --header-border: #e8e8e8;
  --header-text: #333;
  --main-bg: #f5f5f5;
  --card-bg: #fff;
  --text-primary: #333;
  --text-secondary: #666;
  --border-color: #e8e8e8;
  --section-gap: 16px;
}
.dark {
  --header-bg: #1e1e2d;
  --header-border: #2d2d3f;
  --header-text: #e0e0f0;
  --main-bg: #151521;
  --card-bg: #1e1e2d;
  --text-primary: #e0e0f0;
  --text-secondary: #b8b8d0;
  --border-color: #2d2d3f;
  --section-gap: 16px;
}
/* 全局卡片/表格微调 */
.el-card { border-radius: 10px; }
.el-card.is-hover-shadow:hover { box-shadow: 0 4px 16px rgba(0,0,0,.08); }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: #d0d0d0; border-radius: 3px; }
::-webkit-scrollbar-track { background: transparent; }
.dark ::-webkit-scrollbar-thumb { background: #404050; }

/* 暗色模式全局修正 - 覆盖 Element Plus 暗色变量提升对比度 */
.dark {
  --el-bg-color: var(--card-bg);
  --el-bg-color-overlay: var(--card-bg);
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-secondary);
  --el-text-color-placeholder: var(--text-secondary);
  --el-border-color: var(--border-color);
  --el-border-color-light: var(--border-color);
  --el-fill-color: rgba(255,255,255,.05);
  --el-fill-color-light: rgba(255,255,255,.03);
  --el-bg-color-page: var(--main-bg);
}
.dark .el-table { --el-table-text-color: var(--text-primary); --el-table-header-text-color: var(--text-primary); --el-table-border-color: var(--border-color); background: var(--card-bg); }
.dark .el-table th, .dark .el-table td { background: var(--card-bg) !important; border-bottom-color: var(--border-color); }
.dark .el-table tr { background: var(--card-bg); }
.dark .el-table--striped .el-table__body tr.el-table__row--striped td { background: rgba(255,255,255,.04) !important; }
.dark .el-table .el-table__body tr:hover > td { background: rgba(255,255,255,.06) !important; }
.dark .el-picker-panel { background: var(--card-bg); }
.dark .el-popper { --el-popper-bg-color: var(--card-bg); }
.dark .el-empty__description p { color: var(--text-secondary); }
.dark .el-tag { border-color: var(--border-color); }
.dark .el-card .el-card__header { border-bottom-color: var(--border-color); }
.dark .el-button--text { color: var(--text-primary); }
.dark .el-progress__text { color: var(--text-primary); }

/* 暗色模式 - 全局低对比度文字兜底 */
.dark .el-table__body .cell,
.dark .el-table .cell > span,
.dark .el-table .cell span { color: var(--text-primary) !important; }
.dark .el-table .cell span[style*="bfbfbf"],
.dark .el-table .cell span[style*="8c8c8c"] { color: var(--text-secondary) !important; }
.dark .el-table .cell span[style*="1890ff"],
.dark .el-table .cell strong[style*="1890ff"] { color: #4da6ff !important; }
.dark .el-table .cell span[style*="666"] { color: var(--text-secondary) !important; }
</style>
