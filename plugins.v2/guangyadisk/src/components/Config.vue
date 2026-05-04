<template>
  <div class="gy-config">
    <!-- 顶栏 -->
    <div class="gy-topbar">
      <div class="gy-topbar__left">
        <div class="gy-topbar__icon">
          <v-icon icon="mdi-cog-outline" size="24" />
        </div>
        <div>
          <div class="gy-topbar__title">光鸭云盘 · 配置</div>
          <div class="gy-topbar__sub">插件参数配置</div>
        </div>
      </div>
      <div class="gy-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="primary" :loading="saving" @click="saveConfig" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <!-- 配置项 -->
    <div class="gy-config-col">
      <div class="gy-card">
        <div class="gy-card__header">
          <span class="gy-card__title d-flex align-center">
            <v-icon icon="mdi-tune-vertical" size="18" color="#8b5cf6" class="mr-1"></v-icon>
            基础配置
          </span>
        </div>

        <div class="gy-switch-row">
          <div class="gy-switch-item">
            <span class="gy-row__text">
              <v-icon icon="mdi-power-plug" size="20" :color="config.enabled ? '#a78bfa' : 'grey'" class="mr-2"></v-icon>
              启用插件
            </span>
            <label class="switch" style="--switch-checked-bg: #a78bfa;">
              <input v-model="config.enabled" type="checkbox" />
              <div class="slider">
                <div class="circle">
                  <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                  <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                </div>
              </div>
            </label>
          </div>
          <div class="gy-switch-item">
            <span class="gy-row__text">
              <v-icon icon="mdi-delete-alert-outline" size="20" :color="config.permanently_delete ? '#ef4444' : 'grey'" class="mr-2"></v-icon>
              彻底删除
            </span>
            <label class="switch" style="--switch-checked-bg: #ef4444;">
              <input v-model="config.permanently_delete" type="checkbox" />
              <div class="slider">
                <div class="circle">
                  <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                  <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                </div>
              </div>
            </label>
          </div>
        </div>

        <v-row class="mt-2 mb-0">
          <v-col cols="12" sm="6" class="py-1">
            <v-text-field v-model="config.client_id" label="Client ID" density="compact" variant="outlined" hide-details class="gy-input" placeholder="留空使用默认值" />
          </v-col>
          <v-col cols="12" sm="6" class="py-1">
            <v-text-field v-model="config.device_id" label="设备 ID" density="compact" variant="outlined" hide-details class="gy-input" placeholder="自动生成" />
          </v-col>
        </v-row>
      </div>

      <div class="gy-card">
        <div class="gy-card__header">
          <span class="gy-card__title d-flex align-center">
            <v-icon icon="mdi-tune-variant" size="18" color="#0ea5e9" class="mr-1"></v-icon>
            查询参数
          </span>
        </div>

        <v-row class="mt-1 mb-0">
          <v-col cols="6" sm="6" class="py-1">
            <v-text-field v-model.number="config.poll_interval" label="轮询间隔(秒)" type="number" density="compact" variant="outlined" hide-details class="gy-input" />
          </v-col>
          <v-col cols="6" sm="6" class="py-1">
            <v-text-field v-model.number="config.page_size" label="分页大小" type="number" density="compact" variant="outlined" hide-details class="gy-input" />
          </v-col>
          <v-col cols="6" sm="6" class="py-1">
            <v-text-field v-model.number="config.order_by" label="排序字段" type="number" density="compact" variant="outlined" hide-details class="gy-input" />
          </v-col>
          <v-col cols="6" sm="6" class="py-1">
            <v-select v-model.number="config.sort_type" :items="sortTypeOptions" item-title="title" item-value="value" label="排序方向" density="compact" variant="outlined" hide-details class="gy-input" />
          </v-col>
        </v-row>
      </div>

      <div class="gy-card">
        <div class="gy-card__header">
          <span class="gy-card__title d-flex align-center">
            <v-icon icon="mdi-key-outline" size="18" color="#f59e0b" class="mr-1"></v-icon>
            令牌信息
          </span>
        </div>

        <v-text-field
          v-model="config.access_token"
          label="Access Token"
          :type="showAccessToken ? 'text' : 'password'"
          :append-inner-icon="showAccessToken ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
          variant="outlined"
          density="compact"
          class="gy-input mb-3"
          hide-details
          autocomplete="off"
          @click:append-inner="showAccessToken = !showAccessToken"
        />
        <v-text-field
          v-model="config.refresh_token"
          label="Refresh Token"
          :type="showRefreshToken ? 'text' : 'password'"
          :append-inner-icon="showRefreshToken ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
          variant="outlined"
          density="compact"
          class="gy-input"
          hide-details
          autocomplete="off"
          @click:append-inner="showRefreshToken = !showRefreshToken"
        />
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="gy-card">
      <div class="gy-card__header">
        <span class="gy-card__title d-flex align-center">
          <v-icon icon="mdi-book-open-page-variant-outline" size="18" color="#6366f1" class="mr-1"></v-icon>
          使用说明
        </span>
      </div>
      <div class="gy-desc-content">
        <div class="gy-desc-item">
          <v-icon icon="mdi-numeric-1-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>扫码登录：</strong>请在状态页使用二维码扫码登录光鸭云盘 App 完成授权</span>
        </div>
        <div class="gy-desc-item">
          <v-icon icon="mdi-numeric-2-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>令牌管理：</strong>登录成功后令牌会自动保存，刷新页面后无需重新登录</span>
        </div>
        <div class="gy-desc-item">
          <v-icon icon="mdi-numeric-3-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>参数说明：</strong>轮询间隔建议 5-10 秒，分页大小建议 50-200，排序字段和方向可根据需要调整</span>
        </div>
        <div class="gy-desc-item">
          <v-icon icon="mdi-numeric-4-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>彻底删除：</strong>开启后会先执行普通删除，再到回收站中匹配同项目并二次删除</span>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <v-snackbar v-model="message.show" :color="message.type" :timeout="2500" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'switch'])

const config = reactive({
  enabled: false,
  permanently_delete: false,
  access_token: '',
  refresh_token: '',
  client_id: '',
  device_id: '',
  poll_interval: 5,
  page_size: 100,
  order_by: 3,
  sort_type: 1,
  logged_in: false,
  ...props.initialConfig,
})

const loading = ref(false)
const saving = ref(false)
const showAccessToken = ref(false)
const showRefreshToken = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })

const sortTypeOptions = ref([
  { title: '升序', value: 1 },
  { title: '降序', value: 0 },
])

function pluginUrl(path) {
  return `/api/v1/plugin/GuangyaDisk${path}`
}

async function request(path, options = {}) {
  const apiPath = `plugin/GuangyaDisk${path}`
  if (options.method === 'POST') {
    if (props.api?.post) {
      return props.api.post(apiPath, options.body ? JSON.parse(options.body) : {}, options)
    }
  } else if (props.api?.get) {
    return props.api.get(apiPath, options)
  }

  const response = await fetch(pluginUrl(path), {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  return response.json()
}

function applyConfig(data = {}) {
  config.enabled = Boolean(data.enabled)
  config.permanently_delete = Boolean(data.permanently_delete)
  config.access_token = data.access_token || ''
  config.refresh_token = data.refresh_token || ''
  config.client_id = data.client_id || ''
  config.device_id = data.device_id || ''
  config.poll_interval = Number(data.poll_interval || 5)
  config.page_size = Number(data.page_size || 100)
  config.order_by = Number(data.order_by || 3)
  config.sort_type = Number(data.sort_type || 1)
  config.logged_in = Boolean(data.logged_in)
}

function setMessage(type, text) {
  message.type = type
  message.text = text
  message.show = true
}

async function loadConfig() {
  loading.value = true
  try {
    const data = await request('/config')
    applyConfig(data)
  } catch (error) {
    setMessage('error', `加载配置失败：${error}`)
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const result = await request('/config', {
      method: 'POST',
      body: JSON.stringify({ ...config }),
    })
    if (!result.success) {
      throw new Error(result.message || '保存失败')
    }
    applyConfig(result.data || {})
    setMessage('success', result.message || '配置保存成功')
  } catch (error) {
    setMessage('error', `保存配置失败：${error.message || error}`)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.gy-config {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  color: rgba(var(--v-theme-on-surface), 0.85);
  min-height: 400px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}

.gy-topbar,
.gy-card__header,
.gy-switch-row {
  display: flex;
  align-items: center;
}

.gy-topbar,
.gy-card__header {
  justify-content: space-between;
}

.gy-topbar__left,
.gy-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.gy-topbar__right {
  flex-shrink: 0;
}

.gy-topbar__right :deep(.v-btn-group) {
  flex-wrap: nowrap;
}

.gy-topbar__icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: rgba(var(--v-theme-primary), 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgb(var(--v-theme-primary));
  flex-shrink: 0;
}

.gy-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
}

.gy-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.gy-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gy-card__title {
  font-size: 13px;
  font-weight: 600;
}

.gy-config-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.gy-switch-row {
  display: flex;
  gap: 16px;
  flex-wrap: nowrap;
  justify-content: flex-start;
}

.gy-switch-item {
  display: flex;
  flex: 1 1 0;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
}

.gy-row__text {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.gy-input :deep(.v-field) {
  border-radius: 12px;
}

.gy-desc-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.gy-desc-item {
  display: flex;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.gy-desc-item strong {
  font-weight: 600;
}

/* 自定义开关样式 */
.switch {
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgba(var(--v-theme-on-surface), 0.22);
  --switch-checked-bg: rgb(var(--v-theme-primary));
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-checked-shadow: -1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-transition: var(--switch-transition);
  --icon-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: rgba(0, 0, 0, 0.4);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all .2s ease-in-out;
  display: inline-block;
  margin-left: 10px;
  user-select: none;
}
.switch input { display: none; }
.switch svg { transition: var(--icon-transition); position: absolute; height: auto; }
.switch .checkmark { width: var(--icon-checkmark-size); color: var(--icon-checkmark-color); transform: scale(0); }
.switch .cross { width: var(--icon-cross-size); color: var(--icon-cross-color); }
.slider { box-sizing: border-box; width: var(--switch-width); height: var(--switch-height); background: var(--switch-bg); border-radius: 999px; display: flex; align-items: center; position: relative; transition: var(--switch-transition); cursor: pointer; }
.circle { width: var(--circle-diameter); height: var(--circle-diameter); background: var(--circle-bg); border-radius: inherit; box-shadow: var(--circle-shadow); display: flex; align-items: center; justify-content: center; transition: var(--circle-transition); z-index: 1; position: absolute; left: var(--switch-offset); }
.slider::before { content: ""; position: absolute; width: var(--effect-width); height: var(--effect-height); left: calc(var(--switch-offset) + (var(--effect-width) / 2)); background: var(--effect-bg); border-radius: var(--effect-border-radius); transition: var(--effect-transition); }
.switch input:checked+.slider { background: var(--switch-checked-bg); }
.switch input:checked+.slider .checkmark { transform: scale(1); }
.switch input:checked+.slider .cross { transform: scale(0); }
.switch input:checked+.slider::before { left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset)); }
.switch input:checked+.slider .circle { left: calc(100% - var(--circle-diameter) - var(--switch-offset)); box-shadow: var(--circle-checked-shadow); }
.switch input:disabled+.slider { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .gy-config {
    padding: 14px;
  }

  .gy-switch-row {
    flex-wrap: wrap;
  }

  .gy-switch-item {
    flex: 1 1 100%;
  }

  .gy-topbar {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .gy-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .gy-topbar__right {
    justify-content: flex-end;
  }

  .gy-topbar__right :deep(.v-btn-group) {
    gap: 0;
  }

  .gy-topbar__right :deep(.v-btn) {
    min-width: 36px !important;
    padding-inline: 0 !important;
  }
}
</style>
