<template>
  <div class="realtime-data">
    <!-- ====== 主体: 左侧设备树 + 右侧仪表盘 ====== -->
    <el-row :gutter="16">
      <el-col :span="5">
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
            check-strictly
            default-expand-all
            highlight-current
            @check="onTreeCheck"
          />
          </el-card>
      </el-col>
      <el-col :span="19">
        <el-card shadow="hover">
          <template #header><div style="font-size:14px;font-weight:600">仪表数据</div></template>
          <div v-loading="loading" style="min-height:200px">
            <el-row :gutter="12">
              <el-col :span="8" v-for="item in meterData" :key="item.id" style="margin-bottom:12px">
                <el-card shadow="hover" :body-style="{padding:'14px'}">
                  <div style="font-size:12px;color:#8c8c8c">{{ item.name }}</div>
                  <div style="font-size:24px;font-weight:700;color:#1a1a2e;margin:6px 0">{{ item.value }}</div>
                  <div style="font-size:11px;color:#bfbfbf">更新时间: {{ item.time }}</div>
                </el-card>
              </el-col>
            </el-row>
            <el-empty v-if="!meterData.length && !loading" description="暂无数据" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useAppStore } from '@/stores/index'
import { ElMessage } from 'element-plus'
import { getMeterList } from '@/api/index'

const app = useAppStore()
const loading = ref(false)
const treeData = ref([])
const treeRef = ref(null)
const meterData = ref<any[]>([])

async function loadTree() {
  loading.value = true
  try {
    const r = await getMeterList(app.buildingSign)
    if (r.success) treeData.value = r['总用电'] || r.data || []
  } catch { ElMessage.error('加载支路列表失败') }
  finally { loading.value = false }
}

function onTreeCheck() {
  const checked = treeRef.value?.getCheckedKeys() || []
  if (checked.length) loadMeterData(checked)
}

function checkAll() { treeRef.value?.setCheckedKeys(treeData.value.map((n: any) => n.id)) }
function uncheckAll() { treeRef.value?.setCheckedKeys([]) }

async function loadMeterData(ids: number[]) {
  loading.value = true
  try {
    const r = await getMeterList(app.buildingSign)
    if (r.success) {
      const all = r.data || []
      const flat: any[] = []
      function walk(nodes: any[]) {
        for (const n of nodes) {
          if (ids.includes(n.id) && !n.children) flat.push(n)
          if (n.children) walk(n.children)
        }
      }
      walk(all)
      meterData.value = flat
    }
  } catch { ElMessage.error('加载仪表数据失败') }
  finally { loading.value = false }
}

onMounted(() => { loadTree() })
watch(() => app.buildingSign, () => { loadTree() })
</script>
<style scoped>
.tree-card { height: calc(100vh - 140px); overflow-y: auto; }
.tree-header { display: flex; align-items: center; justify-content: space-between; }
.tree-actions { display: flex; gap: 4px; }
</style>