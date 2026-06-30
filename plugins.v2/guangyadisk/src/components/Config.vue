<template>
  <div class="gy-page">
    <!-- 顶栏 -->
    <div class="gy-topbar">
      <div class="gy-topbar__left">
        <div class="gy-topbar__icon">
          <v-icon icon="mdi-cog-outline" size="24" />
        </div>
        <div class="gy-topbar__meta">
          <div class="gy-topbar__title">光鸭云盘 · 配置</div>
          <div class="gy-topbar__sub">插件参数配置</div>
        </div>
      </div>
      <div class="gy-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="primary" @click="saveConfig" :loading="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18" />
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <!-- Toast 消息 -->
    <Transition name="gy-slide">
      <div v-if="message.show" class="gy-toast" :class="`gy-toast--${message.type}`">
        <v-icon :icon="message.type === 'success' ? 'mdi-check-circle' : message.type === 'error' ? 'mdi-alert-circle' : 'mdi-information'" size="18" />
        <span>{{ message.text }}</span>
        <button class="gy-toast__close" @click="message.show = false">
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </Transition>

    <!-- 基础配置 -->
    <div class="gy-card">
      <div class="gy-card__header">
        <span class="gy-card__title d-flex align-center">
          <v-icon icon="mdi-tune-vertical" size="18" color="#8b5cf6" class="mr-1" />
          基础设置
        </span>
      </div>

      <div class="gy-switch-grid">
        <div
          class="gy-switch-item"
          :class="{ 'gy-switch-item--active': config.enabled }"
          style="--gy-accent: #8b5cf6"
        >
          <div class="gy-switch-item__main">
            <div class="gy-switch-item__icon">
              <v-icon icon="mdi-power-plug" size="18" />
            </div>
            <div class="gy-switch-item__text">
              <span class="gy-switch-item__label">启用插件</span>
            </div>
          </div>
          <label class="gy-switch" style="--switch-checked-bg: #8b5cf6;">
            <input v-model="config.enabled" type="checkbox" />
            <div class="gy-switch__slider">
              <div class="gy-switch__circle">
                <svg class="gy-switch__cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                <svg class="gy-switch__checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
              </div>
            </div>
          </label>
        </div>

        <div
          class="gy-switch-item"
          :class="{ 'gy-switch-item--active': config.permanently_delete }"
          style="--gy-accent: #ef4444"
        >
          <div class="gy-switch-item__main">
            <div class="gy-switch-item__icon" style="--gy-accent: #ef4444">
              <v-icon icon="mdi-delete-alert-outline" size="18" />
            </div>
            <div class="gy-switch-item__text">
              <span class="gy-switch-item__label">彻底删除</span>
              <span class="gy-switch-item__hint">开启后二次删除回收站内容</span>
            </div>
          </div>
          <label class="gy-switch" style="--switch-checked-bg: #ef4444;">
            <input v-model="config.permanently_delete" type="checkbox" />
            <div class="gy-switch__slider">
              <div class="gy-switch__circle">
                <svg class="gy-switch__cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                <svg class="gy-switch__checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
              </div>
            </div>
          </label>
        </div>
      </div>

      <div class="gy-divider" />

      <div class="gy-field">
        <div class="gy-field__header">
          <div class="gy-field__title-main">
            <v-icon icon="mdi-key-outline" size="18" color="#f59e0b" class="gy-field__title-icon" />
            <div class="gy-field__title-text">
              <label class="gy-field__label">鉴权信息</label>
              <span class="gy-field__hint">登录后自动填充，无需手动输入</span>
            </div>
          </div>
        </div>

        <div class="gy-form-grid">
          <div class="gy-form-item">
            <v-text-field
              v-model="config.client_id"
              label="Client ID"
              density="compact"
              variant="outlined"
              hide-details
              class="gy-input"
              placeholder="留空使用默认值"
            />
            <div class="gy-field-hint">可选，用于自定义客户端标识</div>
          </div>
          <div class="gy-form-item">
            <v-text-field
              v-model="config.device_id"
              label="设备 ID"
              density="compact"
              variant="outlined"
              hide-details
              class="gy-input"
              placeholder="自动生成"
            />
            <div class="gy-field-hint">留空将自动生成随机设备 ID</div>
          </div>
          <div class="gy-form-item">
            <v-text-field
              v-model="config.access_token"
              label="Access Token"
              :type="showAccessToken ? 'text' : 'password'"
              :append-inner-icon="showAccessToken ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
              variant="outlined"
              density="compact"
              class="gy-input"
              hide-details
              autocomplete="off"
              @click:append-inner="showAccessToken = !showAccessToken"
            />
          </div>
          <div class="gy-form-item">
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
      </div>
    </div>

    <!-- 查询参数 -->
    <div class="gy-card">
      <div class="gy-card__header">
        <span class="gy-card__title d-flex align-center">
          <v-icon icon="mdi-tune-variant" size="18" color="#0ea5e9" class="mr-1" />
          查询参数
        </span>
      </div>

      <div class="gy-form-grid">
        <div class="gy-form-item">
          <v-text-field
            v-model.number="config.poll_interval"
            label="轮询间隔（秒）"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            class="gy-input"
            min="1"
            max="60"
          />
          <div class="gy-field-hint">建议 5~10 秒，避免请求过于频繁</div>
        </div>
        <div class="gy-form-item">
          <v-text-field
            v-model.number="config.page_size"
            label="分页大小"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            class="gy-input"
            min="10"
            max="500"
          />
          <div class="gy-field-hint">建议 50~200，过大可能影响响应速度</div>
        </div>
        <div class="gy-form-item">
          <v-text-field
            v-model.number="config.order_by"
            label="排序字段"
            type="number"
            density="compact"
            variant="outlined"
            hide-details
            class="gy-input"
          />
          <div class="gy-field-hint">数值对应不同的排序维度</div>
        </div>
        <div class="gy-form-item">
          <v-select
            v-model.number="config.sort_type"
            :items="sortTypeOptions"
            item-title="title"
            item-value="value"
            label="排序方向"
            density="compact"
            variant="outlined"
            hide-details
            class="gy-input"
          />
          <div class="gy-field-hint">升序从小到大，降序从大到小</div>
        </div>
      </div>
    </div>

    <!-- 使用说明 -->
    <div class="gy-card">
      <div class="gy-card__header">
        <span class="gy-card__title d-flex align-center">
          <v-icon icon="mdi-book-information-variant" size="18" color="#6366f1" class="mr-1" />
          使用说明
        </span>
      </div>
      <div class="gy-guide">
        <div class="gy-guide__section">
          <div class="gy-guide__item">
            <v-icon icon="mdi-numeric-1-circle-outline" size="16" color="primary" class="mr-2" />
            <span><strong>扫码登录：</strong>请在状态页使用二维码扫码登录光鸭云盘 App 完成授权</span>
          </div>
          <div class="gy-guide__item">
            <v-icon icon="mdi-numeric-2-circle-outline" size="16" color="primary" class="mr-2" />
            <span><strong>令牌管理：</strong>登录成功后令牌会自动保存，刷新页面后无需重新登录</span>
          </div>
          <div class="gy-guide__item">
            <v-icon icon="mdi-numeric-3-circle-outline" size="16" color="primary" class="mr-2" />
            <span><strong>参数说明：</strong>轮询间隔建议 5-10 秒，分页大小建议 50-200，排序字段和方向可根据需要调整</span>
          </div>
          <div class="gy-guide__item">
            <v-icon icon="mdi-numeric-4-circle-outline" size="16" color="primary" class="mr-2" />
            <span><strong>彻底删除：</strong>开启后会先执行普通删除，再到回收站中匹配同项目并二次删除</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'

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

let messageTimer = null

function clearMessageTimer() {
  if (messageTimer) {
    clearTimeout(messageTimer)
    messageTimer = null
  }
}

function scheduleMessageClose(type = 'info') {
  clearMessageTimer()
  const timeout = type === 'error' ? 5000 : 3000
  messageTimer = setTimeout(() => {
    message.show = false
    messageTimer = null
  }, timeout)
}

function setMessage(type, text) {
  message.text = text
  message.type = type
  message.show = true
  scheduleMessageClose(type)
}

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

onBeforeUnmount(() => {
  clearMessageTimer()
})
</script>

<style scoped>
.gy-page {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 400px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  color: rgba(var(--v-theme-on-surface), 0.85);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}

/* ── Topbar ── */
.gy-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.gy-topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.gy-topbar__meta {
  min-width: 0;
  flex: 1;
}

.gy-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.gy-topbar__icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: rgba(139, 92, 246, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b5cf6;
  flex-shrink: 0;
}

.gy-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.gy-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Toast ── */
.gy-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 0.82rem;
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.gy-toast--success {
  background: rgba(34, 197, 94, 0.08);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.15);
}

.gy-toast--error {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.15);
}

.gy-toast--info {
  background: rgba(var(--v-theme-info, 59, 130, 246), 0.08);
  color: rgb(var(--v-theme-info, 59, 130, 246));
  border-color: rgba(var(--v-theme-info, 59, 130, 246), 0.15);
}

.gy-toast__close {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  display: flex;
  transition: opacity 0.2s ease;
}

.gy-toast__close:hover {
  opacity: 1;
}

.gy-slide-enter-active,
.gy-slide-leave-active {
  transition: all 0.3s ease;
}

.gy-slide-enter-from,
.gy-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── Card ── */
.gy-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.gy-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.gy-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

/* ── Divider ── */
.gy-divider {
  height: 0.5px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  margin: 0 -4px;
}

/* ── Switch Grid ── */
.gy-switch-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.gy-switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 14px;
  background: rgba(var(--v-theme-surface, 255, 255, 255), 0.78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.gy-switch-item--active {
  border-color: color-mix(in srgb, var(--gy-accent) 45%, transparent);
  background: color-mix(in srgb, var(--gy-accent) 7%, rgba(var(--v-theme-surface, 255, 255, 255), 0.9));
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06), inset 0 0 0 1px color-mix(in srgb, var(--gy-accent) 18%, transparent);
}

.gy-switch-item__main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.gy-switch-item__icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--gy-accent, #8b5cf6);
  background: color-mix(in srgb, var(--gy-accent, #8b5cf6) 14%, transparent);
}

.gy-switch-item__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.gy-switch-item__label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.84);
}

.gy-switch-item__hint {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  line-height: 1.5;
}

/* ── Field / Form Grid ── */
.gy-field {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.gy-field__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.gy-field__title-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.gy-field__title-icon {
  flex-shrink: 0;
}

.gy-field__title-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.gy-field__label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.72);
}

.gy-field__hint {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.gy-form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.gy-form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.gy-field-hint {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  line-height: 1.5;
}

/* ── Guide ── */
.gy-guide {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.72);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.gy-guide__section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gy-guide__item {
  display: flex;
  align-items: flex-start;
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.gy-guide__item strong {
  font-weight: 600;
}

/* ── Input ── */
.gy-input :deep(.v-field) {
  border-radius: 12px;
  background: rgba(var(--v-theme-surface, 255, 255, 255), 0.72);
}

/* ── Switch Component ── */
.gy-switch {
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgba(var(--v-theme-on-surface), 0.22);
  --switch-checked-bg: rgb(var(--v-theme-primary));
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-checked-shadow: -1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-transition: var(--switch-transition);
  --icon-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: rgba(0, 0, 0, 0.4);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all 0.2s ease-in-out;
  display: inline-block;
  flex-shrink: 0;
  user-select: none;
}

.gy-switch input {
  display: none;
}

.gy-switch svg {
  transition: var(--icon-transition);
  position: absolute;
  height: auto;
}

.gy-switch__checkmark {
  width: var(--icon-checkmark-size);
  color: var(--icon-checkmark-color);
  transform: scale(0);
}

.gy-switch__cross {
  width: var(--icon-cross-size);
  color: var(--icon-cross-color);
}

.gy-switch__slider {
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

.gy-switch__circle {
  width: var(--circle-diameter);
  height: var(--circle-diameter);
  background: var(--circle-bg);
  border-radius: inherit;
  box-shadow: var(--circle-shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--circle-transition);
  z-index: 1;
  position: absolute;
  left: var(--switch-offset);
}

.gy-switch__slider::before {
  content: "";
  position: absolute;
  width: var(--effect-width);
  height: var(--effect-height);
  left: calc(var(--switch-offset) + (var(--effect-width) / 2));
  background: var(--effect-bg);
  border-radius: var(--effect-border-radius);
  transition: var(--effect-transition);
}

.gy-switch input:checked + .gy-switch__slider {
  background: var(--switch-checked-bg);
}

.gy-switch input:checked + .gy-switch__slider .gy-switch__checkmark {
  transform: scale(1);
}

.gy-switch input:checked + .gy-switch__slider .gy-switch__cross {
  transform: scale(0);
}

.gy-switch input:checked + .gy-switch__slider::before {
  left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset));
}

.gy-switch input:checked + .gy-switch__slider .gy-switch__circle {
  left: calc(100% - var(--circle-diameter) - var(--switch-offset));
  box-shadow: var(--circle-checked-shadow);
}

.gy-switch input:disabled + .gy-switch__slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Responsive ── */
@media (max-width: 960px) {
  .gy-form-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .gy-page {
    padding: 14px;
  }

  .gy-switch-grid {
    grid-template-columns: 1fr;
  }

  .gy-topbar {
    align-items: center;
    flex-wrap: nowrap;
  }

  .gy-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .gy-topbar__meta {
    min-width: 0;
  }

  .gy-topbar__right {
    justify-content: flex-end;
    flex-shrink: 0;
  }

  .gy-switch-item,
  .gy-switch-item__main {
    align-items: flex-start;
  }

  .gy-switch-item {
    padding: 14px;
  }
}
</style>
