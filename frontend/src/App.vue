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
  --header-text: #c0c0d0;
  --main-bg: #151521;
  --card-bg: #1e1e2d;
  --text-primary: #c0c0d0;
  --text-secondary: #9999b0;
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
</style>
