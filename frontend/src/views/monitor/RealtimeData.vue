<template>
  <div class="realtime-data">
    <el-row :gutter="16">
      <el-col :xs="24" :md="5">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="tree-header">
              <span>支路列表</span>
              <div class="tree-actions">
                <el-button link size="small" @click="checkAll">全选</el-button>
                <el-button link size="small" @click="uncheckAll">取消</el-button>
              </div>
            </div>
          </template>
          <el-tree
            ref="treeRef"
            :data="treeData"
            :props="{ children: 'children', label: 'name' }"
            node-key="id"
            show-checkbox
            default-expand-all
            highlight-current
            @check="onTreeCheck"
          />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="19">
        <el-card shadow="hover">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <span style="font-size:14px;font-weight:600">仪表数据</span>
              <span style="font-size:12px;color:#999">
                <el-button link size="small" :icon="Search" :loading="loading" @click="refreshData">刷新</el-button>
              </span>
            </div>
          </template>
          <div style="min-height:200px">
            <el-row :gutter="12" v-if="meterData.length">
              <el-col :span="6" v-for="item in meterData" :key="item.id" style="margin-bottom:12px">
                <el-card shadow="never" class="meter-card" :class="{ 'no-data': !item.has_data }" :body-style="{padding:'14px'}">
                  <div class="meter-name">
                    <span :class="['status-dot', item.has_data ? 'online' : 'offline']"></span>
                    {{ item.name }}
                  </div>
                  <div class="meter-value">
                    {{ item.value !== null && item.value !== undefined ? Number(item.value).toFixed(2) : '--' }}
                  </div>
                  <div class="meter-time">
                    {{ item.has_data ? ('更新时间: ' + (item.update_time || '--')) : '无数据' }}
                  </div>
                </el-card>
              </el-col>
            </el-row>
            <el-empty v-if="!meterData.length && !loading" description="请勾选支路查看实时数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getServiceTree, getMeterData } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref<any[]>([])
const treeRef = ref<any>(null)
const meterData = ref<any[]>([])
let refreshTimer: any = null

async function loadTree() {
  try {
    const r = await getServiceTree(app.buildingSign)
    if (r.success) treeData.value = r.data || []
  } catch {
    ElMessage.error('加载支路列表失败')
  }
}

function onTreeCheck() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (checked.length) loadMeterData(checked)
  else meterData.value = []
}

function checkAll() {
  treeRef.value?.setCheckedKeys(treeData.value.map((n: any) => n.id))
}

function uncheckAll() {
  treeRef.value?.setCheckedKeys([])
  meterData.value = []
}

async function loadMeterData(ids: number[]) {
  if (!ids.length) { meterData.value = []; return }
  loading.value = true
  try {
    const r = await getMeterData({ sign: app.buildingSign, selectedids: ids.join(',') })
    if (r.success) meterData.value = r.data || []
  } catch {
    ElMessage.error('加载仪表数据失败')
  } finally {
    loading.value = false
  }
}

function refreshData() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (checked.length) loadMeterData(checked)
}

onMounted(() => {
  loadTree()
  refreshTimer = setInterval(refreshData, 30000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})

watch(() => app.buildingSign, () => {
  meterData.value = []
  loadTree()
})
</script>

<style scoped>
.tree-card {
  height: calc(100vh - 140px);
  overflow-y: auto;
}
.tree-card .el-card__header {
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 16px;
}
.tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
  color: #1a1a2e;
}
.tree-actions {
  display: flex;
  gap: 4px;
}
.tree-actions .el-button {
  font-size: 12px;
}

/* 仪表卡片 - 全新设计 */
.meter-card {
  margin-bottom: 12px;
  border-radius: 10px;
  border-left: 4px solid #d9d9d9;
  transition: transform .2s, box-shadow .2s;
}
.meter-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,.08);
}
.meter-card:nth-child(4n+1) { border-left-color: #13c785; }
.meter-card:nth-child(4n+2) { border-left-color: #1890ff; }
.meter-card:nth-child(4n+3) { border-left-color: #fa8c16; }
.meter-card:nth-child(4n+4) { border-left-color: #722ed1; }
.meter-card.offline { border-left-color: #d9d9d9; }
.meter-card .meter-name {
  font-size: 13px;
  color: #595959;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-weight: 500;
}
.meter-card .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.meter-card .status-dot.online { background: #52c41a; }
.meter-card .status-dot.offline { background: #ff4d4f; }
.meter-card.no-data .meter-time { color: #ff4d4f; font-weight: 500; }
.meter-card.no-data .meter-value { color: #ff4d4f; }
.meter-card .meter-value {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 4px 0;
  line-height: 1.2;
}
.meter-card .meter-time {
  font-size: 11px;
  color: #bfbfbf;
}
</style>