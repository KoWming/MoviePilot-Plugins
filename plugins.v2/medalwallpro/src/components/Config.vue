<script setup lang="ts">
import { ref, onMounted, reactive, watch, computed } from 'vue'

const props = defineProps({
  initialConfig: {
    type: Object,
    default: () => ({})
  },
  api: {
    type: Object,
    default: () => {}
  }
})

const emit = defineEmits(['save', 'close', 'switch'])

// Config state
const config = reactive({
  enabled: false,
  cron: "0 9 * * *",
  notify: false,
  chat_sites: [] as string[],
  use_proxy: true,
  retry_times: 3,
  retry_interval: 5
})

// Cache for reset
const originalConfig = reactive({})

// Options state
const siteOptions = ref<{title: string, value: string}[]>([])
const saving = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

// Init
onMounted(async () => {
  if (props.initialConfig && Object.keys(props.initialConfig).length > 0) {
    Object.assign(config, props.initialConfig)
    Object.assign(originalConfig, JSON.parse(JSON.stringify(config)))
  }
  await fetchSites()
})

watch(() => props.initialConfig, (newVal) => {
  if (newVal && Object.keys(newVal).length > 0) {
    Object.assign(config, newVal)
    // Only set original if empty to allow reset to server state
    if (Object.keys(originalConfig).length === 0) {
      Object.assign(originalConfig, JSON.parse(JSON.stringify(newVal)))
    }
  }
}, { deep: true })

async function fetchSites() {
  try {
    const data = await props.api.get('plugin/MedalWallPro/sites')
    if (data) {
      siteOptions.value = data
    }
  } catch (e) {
    console.error('Failed to fetch sites', e)
    showNotification('获取站点列表失败', 'error')
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await props.api.post('plugin/MedalWallPro/config', config)
    if (res && res.success) {
      showNotification('配置已保存', 'success')
      emit('save', config)
      // Update original config after save
      Object.assign(originalConfig, JSON.parse(JSON.stringify(config)))
    } else {
      showNotification(res?.message || '保存失败', 'error')
    }
  } catch (e: any) {
    console.error('Failed to save config', e)
    showNotification('保存配置失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    saving.value = false
  }
}

function resetConfig() {
  if (Object.keys(originalConfig).length > 0) {
    Object.assign(config, JSON.parse(JSON.stringify(originalConfig)))
    showNotification('配置已重置', 'success')
  }
}

function showNotification(message: string, type: 'success' | 'error' = 'success') {
  if (type === 'success') {
    successMessage.value = message
    setTimeout(() => successMessage.value = '', 3000)
  } else {
    errorMessage.value = message
    setTimeout(() => errorMessage.value = '', 3000)
  }
}

function notifyClose() {
  emit('close')
}

function notifySwitch() {
  emit('switch', 'page')
}

// 计算选择状态
const isAllSelected = computed(() => {
  return siteOptions.value.length > 0 && config.chat_sites.length === siteOptions.value.length
})

const isPartiallySelected = computed(() => {
  return config.chat_sites.length > 0 && config.chat_sites.length < siteOptions.value.length
})

// 根据选择状态返回图标
const selectionIcon = computed(() => {
  if (isAllSelected.value) {
    return 'mdi-checkbox-multiple-marked' // 全选:打钩
  } else if (isPartiallySelected.value) {
    return 'mdi-minus-box-multiple-outline' // 部分选中:横线
  } else {
    return 'mdi-checkbox-multiple-blank-outline' // 未选:空框
  }
})

// 根据选择状态返回按钮文本
const selectionText = computed(() => {
  return '全选'
})

// 全选/取消全选站点
function selectAllSites() {
  if (isAllSelected.value) {
    config.chat_sites = []
  } else {
    config.chat_sites = siteOptions.value.map(site => site.value)
  }
}

function clearAllSites() {
  config.chat_sites = []
}

function invertSelection() {
  const allSiteValues = siteOptions.value.map(site => site.value)
  const currentSelection = new Set(config.chat_sites)
  config.chat_sites = allSiteValues.filter(value => !currentSelection.has(value))
}
</script>

<template>
  <div class="plugin-config">
    <v-card flat class="rounded border">
      <!-- 标题区域 -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary">
        <v-icon icon="mdi-cog" class="mr-2" color="white" size="small"></v-icon>
        <span class="text-white">勋章墙配置</span>
        <v-spacer />

        <!-- 操作按钮组 -->
         <v-btn-group variant="outlined" density="compact" class="mr-1">
          <v-btn color="white" @click="notifySwitch" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="white" @click="resetConfig" :disabled="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-restore" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">重置</span>
          </v-btn>
          <v-btn color="white" @click="saveConfig" :loading="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="white" @click="notifyClose" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </v-card-title>
      
      <v-card-text class="px-3 py-3" style="position: relative;">
        <!-- 通知 Alert -->
        <div style="position: absolute; top: 0; left: 0; right: 0; z-index: 50; padding: 0 10px 10px 10px;">
          <transition name="slide-fade">
            <v-alert v-if="successMessage" type="success" density="compact" class="mb-2 text-caption" variant="elevated" closable @click:close="successMessage = ''">
              {{ successMessage }}
            </v-alert>
          </transition>
          <transition name="slide-fade">
            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-2 text-caption" variant="elevated" closable @click:close="errorMessage = ''">
              {{ errorMessage }}
            </v-alert>
          </transition>
        </div>

        <v-form>
          <!-- 基础设置 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 px-3 py-2 bg-purple-lighten-5 d-flex align-center">
              <v-icon icon="mdi-tune" class="mr-2" color="purple" size="small"></v-icon>
              基础设置
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-play-circle-outline" size="small" :color="config.enabled ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">启用插件</div>
                          <div class="text-caption text-grey">是否启用勋章墙插件</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #bc98fd;">
                          <input v-model="config.enabled" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle"></div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-message-processing-outline" size="small" :color="config.notify ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">开启通知</div>
                          <div class="text-caption text-grey">开启通知发送，首次运行不建议开启</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #73cffe;">
                          <input v-model="config.notify" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle"></div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-earth" size="small" :color="config.use_proxy ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">使用代理</div>
                          <div class="text-caption text-grey">使用系统代理连接站点</div>
                        </div>
                         <label class="switch" style="--switch-checked-bg: #9adf66;">
                          <input v-model="config.use_proxy" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle"></div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 监控设置 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 px-3 py-2 bg-blue-lighten-5 d-flex align-center">
              <v-icon icon="mdi-eye-outline" class="mr-2" color="blue" size="small"></v-icon>
              监控配置
              <v-spacer />
              <span class="text-caption text-grey mr-1 d-none d-sm-inline">已选: {{ config.chat_sites.length }} / {{ siteOptions.length }}</span>
              <v-btn-group variant="outlined" density="compact" class="quick-action-group">
                <v-btn
                  @click="selectAllSites"
                  size="x-small"
                  :color="isAllSelected ? 'grey' : 'primary'"
                  class="px-1 px-sm-2"
                >
                  <v-icon :icon="selectionIcon" size="16" class="mr-sm-1"></v-icon>
                  <span class="d-none d-sm-inline">{{ selectionText }}</span>
                </v-btn>
                <v-btn
                  @click="invertSelection"
                  size="x-small"
                  color="purple"
                  class="px-1 px-sm-2"
                >
                  <v-icon icon="mdi-swap-horizontal-variant" size="16" class="mr-sm-1"></v-icon>
                  <span class="d-none d-sm-inline">反选</span>
                </v-btn>
                <v-btn
                  @click="clearAllSites"
                  size="x-small"
                  color="red-lighten-1"
                  class="px-1 px-sm-2"
                >
                  <v-icon icon="mdi-close-box-multiple" size="16" class="mr-sm-1"></v-icon>
                  <span class="d-none d-sm-inline">清空</span>
                </v-btn>
              </v-btn-group>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12">
                  
                   <v-select
                    v-model="config.chat_sites"
                    :items="siteOptions"
                    label="监控站点"
                    multiple
                    chips
                    item-title="title"
                    item-value="value"
                    variant="outlined"
                    density="compact"
                    hide-details="auto"
                    color="primary"
                    hint="选择需要监控勋章的站点"
                    persistent-hint
                  ></v-select>
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="config.cron"
                    label="CRON表达式"
                    placeholder="0 9 * * *"
                    variant="outlined"
                    density="compact"
                    hide-details="auto"
                    color="primary"
                    prefix="周期间隔"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="4">
                   <v-select
                    v-model="config.retry_times"
                    label="重试次数"
                    :items="[1, 2, 3, 5]"
                    variant="outlined"
                    density="compact"
                    hide-details="auto"
                    color="primary"
                  ></v-select>
                </v-col>
                 <v-col cols="12" md="4">
                   <v-select
                    v-model="config.retry_interval"
                    label="重试间隔(秒)"
                    :items="[3, 5, 10, 15]"
                    variant="outlined"
                    density="compact"
                    hide-details="auto"
                    color="primary"
                  ></v-select>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 底部提示 -->
          <div class="mt-4 pa-3 rounded text-caption d-flex flex-column notice-card">
             <div class="d-flex align-center mb-2">
                <v-icon icon="mdi-bell-off-outline" size="small" class="mr-2" color="primary"></v-icon>
                <span>建议首次运行时不要开启通知，避免因同步历史数据导致通知刷屏。</span>
             </div>
             <div class="d-flex align-center">
                <v-icon icon="mdi-alert-circle-outline" size="small" class="mr-2" color="warning"></v-icon>
                <span>站点图片如果无法显示可能是站点图床失效无法获取！</span>
             </div>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<style scoped>
.plugin-config {
  margin: 0 auto;
  padding: 0.5rem;
}

.bg-gradient-primary {
  background-color: #328df5ff;
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.inner-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.inner-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.bg-purple-lighten-5 {
  background-color: rgba(156, 39, 176, 0.07) !important;
}

.bg-blue-lighten-5 {
  background-color: rgba(33, 150, 243, 0.07) !important;
}


.setting-item {
  background: transparent;
  padding: 0;
}

.text-subtitle-1 {
  font-size: 1.1rem !important;
  font-weight: 500;
}

.text-subtitle-2 {
  font-size: 0.9rem !important;
  font-weight: 500;
}

/* Switch Styles */
.switch {
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgb(131, 131, 131);
  --switch-checked-bg: rgb(0, 218, 80);
  --switch-offset: 2px;
  --switch-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(146, 146, 146, 0.45);
  --switch-checked-shadow: -1px 1px 2px rgba(163, 163, 163, 0.45);
  
  display: inline-block;
  margin-left: 16px; 
}

.switch input {
  display: none;
}

.slider {
  box-sizing: border-box;
  width: var(--switch-width);
  height: var(--switch-height);
  background: var(--switch-bg);
  border-radius: 999px;
  display: flex;
  align-items: center;
  position: relative;
  transition: var(--switch-transition);
  cursor: pointer;
}

.circle {
  width: var(--circle-diameter);
  height: var(--circle-diameter);
  background: var(--circle-bg);
  border-radius: inherit;
  box-shadow: var(--circle-shadow);
  position: absolute;
  left: var(--switch-offset);
  transition: var(--switch-transition);
  z-index: 1;
}

.switch input:checked + .slider {
  background: var(--switch-checked-bg);
}

.switch input:checked + .slider .circle {
  left: calc(100% - var(--circle-diameter) - var(--switch-offset));
  box-shadow: var(--switch-checked-shadow);
}

.switch input:disabled + .slider {
  opacity: 0.5;
  cursor: not-allowed;
}



.notice-card {
  background-color: #f5f5f5;
  color: #616161;
}

@media (prefers-color-scheme: dark) {
  .bg-purple-lighten-5 {
    background-color: rgba(156, 39, 176, 0.2) !important;
  }
  
  .bg-blue-lighten-5 {
    background-color: rgba(33, 150, 243, 0.2) !important;
  }
  
  .text-subtitle-2 {
    color: rgba(255, 255, 255, 0.9) !important;
  }
  
  .notice-card {
    background-color: rgba(255, 255, 255, 0.05); /* 更柔和的深色背景 */
    color: rgba(255, 255, 255, 0.7);
  }
}

/* Vuetify深色主题支持 - 使用data-theme属性选择器 */
[data-theme="dark"] .bg-purple-lighten-5,
[data-theme="purple"] .bg-purple-lighten-5,
[data-theme="transparent"] .bg-purple-lighten-5 {
  background-color: rgba(156, 39, 176, 0.2) !important;
}

[data-theme="dark"] .bg-blue-lighten-5,
[data-theme="purple"] .bg-blue-lighten-5,
[data-theme="transparent"] .bg-blue-lighten-5 {
  background-color: rgba(33, 150, 243, 0.2) !important;
}

[data-theme="dark"] .text-subtitle-2,
[data-theme="purple"] .text-subtitle-2,
[data-theme="transparent"] .text-subtitle-2 {
  color: rgba(255, 255, 255, 0.9) !important;
}

[data-theme="dark"] .notice-card,
[data-theme="purple"] .notice-card,
[data-theme="transparent"] .notice-card {
  background-color: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.7);
}

/* 按钮组样式 */
.action-btn-group {
  background-color: rgba(255, 255, 255, 0.15) !important;
  padding: 2px !important;
  border-radius: 6px !important;
}

/* 快捷操作按钮组样式 */
.quick-action-group {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)) !important;
  border-radius: 6px !important;
  overflow: hidden !important;
}

.quick-action-group .v-btn {
  border: none !important;
  border-radius: 0 !important;
}

.quick-action-group .v-btn:not(:last-child) {
  border-right: 1px solid rgba(var(--v-border-color), 0.2) !important;
}


</style>
