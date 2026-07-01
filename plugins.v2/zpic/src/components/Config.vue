<script setup>
import { onBeforeUnmount, computed, onMounted, reactive, ref } from 'vue'
import { pluginRequest } from '../utils/zpic'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  initialConfig: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['switch', 'close'])

const saving = ref(false)
const showToken = ref(false)
const sysLoading = ref(false)
const form = reactive({
  enabled: false,
  open_token: '',
  ...props.initialConfig,
})
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

// ── 系统设置（从 Zpic API 实时获取） ──
const sysConfig = reactive({
  compress: true,
  watermark_enabled: false,
  watermark_text: '',
  current_tier: props.initialConfig?.tier || 'free',
  storage_slug: 'default',
  storage_domain: '',
  storage_domains: [],    // 可选域名列表
})
const sysLoaded = ref(false)

const isVipSubscription = computed(() => String(sysConfig.current_tier || '').toLowerCase() !== 'free')

const message = reactive({ show: false, type: 'info', text: '' })

function pushMessage(text, type = 'info') {
  message.text = text
  message.type = type
  message.show = true
  scheduleMessageClose(type)
}

async function fetchSystemConfig() {
  sysLoading.value = true
  try {
    const [configRes, domainsRes] = await Promise.all([
      pluginRequest(props.api, '/system/config', { method: 'GET' }),
      pluginRequest(props.api, '/system/domains', { method: 'GET' }),
    ])

    // 解析 get_own_config
    if (configRes?.data) {
      sysConfig.compress = configRes.data.compress ?? true
      const remoteWatermarkEnabled = configRes.data.watermark_enabled ?? false
      sysConfig.watermark_enabled = isVipSubscription.value ? remoteWatermarkEnabled : false
      sysConfig.watermark_text = configRes.data.watermark_text || ''
      // 从返回数据中提取当前存储域名
      if (configRes.data.storage_domain) {
        sysConfig.storage_domain = configRes.data.storage_domain
      }
    }

    // 解析 storage_domains
    if (domainsRes?.data) {
      sysConfig.storage_slug = domainsRes.data.storage_slug || 'default'
      sysConfig.storage_domains = domainsRes.data.domains || []
    }

    sysLoaded.value = true
  } catch (error) {
    // 未登录或接口不可用时静默失败
    sysLoaded.value = false
  } finally {
    sysLoading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const result = await pluginRequest(props.api, '/config', {
      method: 'POST',
      body: { ...form },
    })
    if (!result?.success) {
      throw new Error(result?.message || '保存失败')
    }
    pushMessage('配置已保存', 'success')
  } catch (error) {
    pushMessage(error.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function saveSystemConfig() {
  sysLoading.value = true
  try {
    const payload = {
      compress: sysConfig.compress,
      watermark_enabled: isVipSubscription.value ? sysConfig.watermark_enabled : false,
      watermark_text: isVipSubscription.value ? sysConfig.watermark_text : '',
      storage_slug: sysConfig.storage_slug,
      storage_domain: sysConfig.storage_domain,
    }
    const result = await pluginRequest(props.api, '/system/config', {
      method: 'POST',
      body: payload,
    })
    if (!result?.success) {
      throw new Error(result?.message || '保存系统设置失败')
    }
    pushMessage('系统设置已保存', 'success')
  } catch (error) {
    pushMessage(error.message || '保存系统设置失败', 'error')
  } finally {
    sysLoading.value = false
  }
}

onMounted(() => {
  fetchSystemConfig()
})

onBeforeUnmount(() => {
  clearMessageTimer()
})
</script>

<template>
  <div class="zp-config">
    <!-- 顶栏 -->
    <div class="zp-topbar">
      <div class="zp-topbar__left">
        <div class="zp-topbar__icon">
          <v-icon icon="mdi-cog-outline" size="24" />
        </div>
        <div>
          <div class="zp-topbar__title">Zpic 图库 · 配置</div>
          <div class="zp-topbar__sub">管理插件配置、开放令牌与 Zpic 系统设置</div>
        </div>
      </div>
      <div class="zp-topbar__right">
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

    <!-- 消息提示 -->
    <Transition name="zp-toast-slide">
      <div v-if="message.show" class="zp-toast" :class="`zp-toast--${message.type}`">
        <v-icon :icon="message.type === 'success' ? 'mdi-check-circle' : message.type === 'error' ? 'mdi-alert-circle' : 'mdi-information'" size="18" />
        <span>{{ message.text }}</span>
        <button class="zp-toast__close" @click="message.show = false">
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </Transition>

    <!-- 配置列 -->
    <div class="zp-config-col">

      <!-- 基础配置卡片 -->
      <div class="zp-card">
        <div class="zp-card__header">
          <span class="zp-card__title d-flex align-center">
            <v-icon icon="mdi-toggle-switch-outline" size="18" color="#8b5cf6" class="mr-1" />
            基础设置
          </span>
        </div>
<div class="zp-row">
          <div class="zp-row__col">
            <div class="zp-switch-grid">
              <div
                class="zp-switch-item"
                :class="{ 'zp-switch-item--active': form.enabled }"
                style="--zp-accent: 139, 92, 246"
              >
                <div class="zp-switch-item__main">
                  <div class="zp-switch-item__icon">
                    <v-icon icon="mdi-power-plug" size="18" />
                  </div>
                  <div class="zp-switch-item__text">
                    <span class="zp-switch-item__label">启用插件</span>
                  </div>
                </div>
                <label class="zp-toggle" style="--switch-checked-bg: #8b5cf6;">
                  <input v-model="form.enabled" type="checkbox" />
                  <div class="zp-toggle__slider">
                    <div class="zp-toggle__circle">
                      <svg class="zp-toggle__cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                      <svg class="zp-toggle__checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
                    </div>
                  </div>
                </label>
              </div>
            </div>
          </div>
          <div class="zp-row__col">
            <v-text-field
              v-model="form.open_token"
              label="开放令牌（Open Token）"
              :type="showToken ? 'text' : 'password'"
              variant="outlined"
              density="compact"
              class="zp-input"
              hide-details
              autocomplete="off"
              prepend-inner-icon="mdi-key-variant"
            >
              <template #append-inner>
                <v-btn
                  variant="text"
                  density="comfortable"
                  size="x-small"
                  icon
                  class="zp-token-eye-btn"
                  @click.stop="showToken = !showToken"
                >
                  <v-icon :icon="showToken ? 'mdi-eye-off-outline' : 'mdi-eye-outline'" size="18" />
                </v-btn>
              </template>
            </v-text-field>
          </div>
        </div>

        <div class="zp-token-hint">
          <v-icon icon="mdi-information-outline" size="14" class="zp-token-hint__icon" />
          <span>用于开放 API 接口鉴权（上传图片 V3、获取相册列表、删除图片等），请前往 Zpic 后台获取。</span>
        </div>
      </div>

      <!-- 系统设置卡片 -->
      <div class="zp-card">
        <div class="zp-card__header">
          <span class="zp-card__title d-flex align-center">
            <v-icon icon="mdi-cog-sync-outline" size="18" color="#10b981" class="mr-1" />
            系统设置
          </span>
          <v-btn
            variant="text"
            density="comfortable"
            size="x-small"
            :loading="sysLoading"
            :icon="sysLoaded ? 'mdi-refresh' : 'mdi-loading mdi-spin'"
            :disabled="sysLoading"
            class="zp-refresh-btn"
            @click="fetchSystemConfig"
          />
        </div>

        <!-- 未登录提示 -->
        <div v-if="!sysLoaded && !sysLoading" class="zp-sys-placeholder">
          <v-icon icon="mdi-login-variant" size="20" color="grey" />
          <span>请先在状态页登录后查看系统设置</span>
        </div>

        <!-- 加载中 -->
        <div v-else-if="sysLoading && !sysLoaded" class="zp-sys-placeholder">
          <v-progress-circular size="20" width="2" indeterminate color="primary" />
          <span>正在加载系统设置…</span>
        </div>

        <!-- 设置内容 -->
        <template v-else-if="sysLoaded">
          <div class="zp-switch-grid">
            <!-- 图片压缩 -->
            <div
              class="zp-switch-item"
              :class="{ 'zp-switch-item--active': sysConfig.compress }"
              style="--zp-accent: 16, 185, 129"
            >
              <div class="zp-switch-item__main">
                <div class="zp-switch-item__icon">
                  <v-icon icon="mdi-image-size-select-large" size="18" />
                </div>
                <div class="zp-switch-item__text">
                  <span class="zp-switch-item__label">图片压缩</span>
                  <span class="zp-switch-item__desc">自动压缩以节省空间</span>
                </div>
              </div>
              <label class="zp-toggle" style="--switch-checked-bg: #10b981;">
                <input v-model="sysConfig.compress" type="checkbox" />
                <div class="zp-toggle__slider">
                  <div class="zp-toggle__circle">
                    <svg class="zp-toggle__cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                    <svg class="zp-toggle__checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
                  </div>
                </div>
              </label>
            </div>
            <!-- 文字水印 -->
            <div
              class="zp-switch-item"
              :class="{ 'zp-switch-item--active': isVipSubscription && sysConfig.watermark_enabled, 'zp-switch-item--disabled': !isVipSubscription }"
              style="--zp-accent: 6, 182, 212"
            >
              <div class="zp-switch-item__main">
                <div class="zp-switch-item__icon">
                  <v-icon icon="mdi-watermark" size="18" />
                </div>
                <div class="zp-switch-item__text">
                  <span class="zp-switch-item__label">文字水印</span>
                  <span class="zp-switch-item__desc">{{ isVipSubscription ? '为上传图片添加文字水印' : 'VIP 订阅可用' }}</span>
                </div>
              </div>
              <label class="zp-toggle" style="--switch-checked-bg: #06b6d4;" :class="{ 'zp-toggle--disabled': !isVipSubscription }">
                <input v-model="sysConfig.watermark_enabled" type="checkbox" :disabled="!isVipSubscription" />
                <div class="zp-toggle__slider">
                  <div class="zp-toggle__circle">
                    <svg class="zp-toggle__cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                    <svg class="zp-toggle__checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
                  </div>
                </div>
              </label>
            </div>
          <!-- 存储域名 -->
            <div class="zp-switch-item" style="--zp-accent: 59, 130, 246">
              <div class="zp-switch-item__main">
                <div class="zp-switch-item__icon">
                  <v-icon icon="mdi-dns-outline" size="18" />
                </div>
                <div class="zp-storage-select-wrap">
                  <v-select
                    v-model="sysConfig.storage_domain"
                    :items="sysConfig.storage_domains"
                    label="存储域名"
                    density="compact"
                    variant="outlined"
                    hide-details
                    class="zp-storage-select"
                    clearable
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 水印文字 -->
          <v-expand-transition>
            <div v-if="isVipSubscription && sysConfig.watermark_enabled" class="zp-sys-watermark-field">
              <v-text-field
                v-model="sysConfig.watermark_text"
                label="文字水印"
                density="compact"
                variant="outlined"
                hide-details
                class="zp-input"
                prepend-inner-icon="mdi-format-text"
                placeholder="请输入水印文字内容"
                clearable
              />
              <div class="zp-field-hint">仅 VIP 订阅可用，开启水印后显示此字段</div>
            </div>
          </v-expand-transition>

          <!-- 保存系统设置按钮 -->
          <div class="zp-sys-save-actions">
            <v-btn
              variant="tonal"
              color="#10b981"
              size="small"
              :loading="sysLoading"
              @click="saveSystemConfig"
              class="zp-sys-save-btn"
            >
              <v-icon icon="mdi-content-save-check-outline" size="16" class="mr-1" />
              保存系统设置
            </v-btn>
          </div>
        </template>
      </div>

    </div>

    <!-- 使用说明 -->
    <div class="zp-card">
      <div class="zp-card__header">
        <span class="zp-card__title d-flex align-center">
          <v-icon icon="mdi-book-information-variant" size="18" color="#0ea5e9" class="mr-1" />
          关于 Zpic
        </span>
      </div>

      <div class="zp-guide">
        <div class="zp-guide__section">
          <p class="zp-guide__paragraph">📷 使用 Zpic 图床插件，轻松管理您的图片上传与存储。</p>
          <p class="zp-guide__paragraph">🔑 <strong>登录方式：</strong>在状态页通过验证码完成登录，登录后站点地址与邮箱自动缓存。</p>
          <p class="zp-guide__paragraph">🔐 <strong>登录令牌：</strong>登录成功后自动获取并缓存，失效时插件会自动清空。</p>
          <p class="zp-guide__paragraph">🔓 <strong>开放令牌：</strong>用于调用开放 API（上传图片、相册管理），需在 Zpic 后台生成。</p>
        </div>

        <div class="zp-guide__divider" />

        <div class="zp-guide__contact">
          <a
            class="zp-contact-link"
            href="https://www.imgurl.org/user/register"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>📝</span>
            <span>注册 Zpic</span>
          </a>
          <a
            class="zp-contact-link"
            href="https://www.imgurl.org/"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>🌐</span>
            <span>访问官网</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ── 页面容器 ── */
.zp-config {
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

/* ── 顶栏 ── */
.zp-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.zp-topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.zp-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.zp-topbar__right :deep(.v-btn-group) {
  flex-wrap: nowrap;
}

.zp-topbar__icon {
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

.zp-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.zp-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 配置列 ── */
.zp-config-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Toast ── */
.zp-toast {
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

.zp-toast--success {
  background: rgba(34, 197, 94, 0.08);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.15);
}

.zp-toast--error {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.15);
}

.zp-toast--info {
  background: rgba(var(--v-theme-info), 0.08);
  color: rgb(var(--v-theme-info));
  border-color: rgba(var(--v-theme-info), 0.15);
}

.zp-toast__close {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  display: flex;
  transition: opacity 0.2s ease;
}

.zp-toast__close:hover { opacity: 1; }

.zp-toast-slide-enter-active,
.zp-toast-slide-leave-active { transition: all 0.3s ease; }
.zp-toast-slide-enter-from,
.zp-toast-slide-leave-to { opacity: 0; transform: translateY(-8px); }

/* ── 行布局 ── */
.zp-row {
  display: flex;
  gap: 16px;
  align-items: stretch;
}

.zp-row__col {
  flex: 1;
  min-width: 0;
}

/* 行布局内开关网格占满整列 */
.zp-row__col .zp-switch-grid {
  grid-template-columns: 1fr;
}

/* 行布局内输入框匹配开关卡片高度 */
.zp-row :deep(.v-field) {
  min-height: 58px;
  align-items: center;
}

.zp-row :deep(.v-field__input) {
  align-items: center;
  padding-block: 8px;
}

/* ── 卡片 ── */
.zp-card {
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

.zp-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.zp-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

/* ── 分隔线 ── */
.zp-divider {
  height: 0.5px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  margin: 0 -4px;
}

/* ── 开关网格 ── */
.zp-switch-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.zp-switch-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
  transition: background 0.2s ease, border-color 0.2s ease;
}

.zp-switch-item--active {
  background: rgba(var(--zp-accent, 139, 92, 246), 0.06);
  border-color: rgba(var(--zp-accent, 139, 92, 246), 0.12);
}

.zp-switch-item--disabled {
  opacity: 0.55;
}

.zp-switch-item__main {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.zp-switch-item__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface), 0.55);
  background: rgba(var(--v-theme-on-surface), 0.04);
  transition: background 0.2s ease, color 0.2s ease;
}

.zp-switch-item--active .zp-switch-item__icon {
  background: rgba(var(--zp-accent, 139, 92, 246), 0.12);
  color: rgb(var(--zp-accent, 139, 92, 246));
}

.zp-switch-item__text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.zp-switch-item__label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.zp-switch-item__desc {
  font-size: 11px;
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

/* ── 自定义开关 (.zp-toggle) ── */
.zp-toggle {
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
  flex-shrink: 0;
  user-select: none;
}
.zp-toggle input { display: none; }
.zp-toggle svg { transition: var(--icon-transition); position: absolute; height: auto; }
.zp-toggle__checkmark { width: var(--icon-checkmark-size); color: var(--icon-checkmark-color); transform: scale(0); }
.zp-toggle__cross { width: var(--icon-cross-size); color: var(--icon-cross-color); }
.zp-toggle__slider { box-sizing: border-box; width: var(--switch-width); height: var(--switch-height); background: var(--switch-bg); border-radius: 999px; display: flex; align-items: center; position: relative; transition: var(--switch-transition); cursor: pointer; }
.zp-toggle__circle { width: var(--circle-diameter); height: var(--circle-diameter); background: var(--circle-bg); border-radius: inherit; box-shadow: var(--circle-shadow); display: flex; align-items: center; justify-content: center; transition: var(--circle-transition); z-index: 1; position: absolute; left: var(--switch-offset); }
.zp-toggle__slider::before { content: ""; position: absolute; width: calc(var(--circle-diameter) / 2); height: calc(var(--circle-diameter) / 4 - 1px); left: calc(var(--switch-offset) + (var(--circle-diameter) / 4)); background: var(--circle-bg); border-radius: 1px; transition: all .2s ease-in-out; }
.zp-toggle input:checked + .zp-toggle__slider { background: var(--switch-checked-bg); }
.zp-toggle input:checked + .zp-toggle__slider .zp-toggle__checkmark { transform: scale(1); }
.zp-toggle input:checked + .zp-toggle__slider .zp-toggle__cross { transform: scale(0); }
.zp-toggle input:checked + .zp-toggle__slider::before { left: calc(100% - var(--circle-diameter) / 2 - (var(--circle-diameter) / 4) - var(--switch-offset)); }
.zp-toggle input:checked + .zp-toggle__slider .zp-toggle__circle { left: calc(100% - var(--circle-diameter) - var(--switch-offset)); box-shadow: var(--circle-checked-shadow); }
.zp-toggle input:disabled + .zp-toggle__slider,
.zp-toggle--disabled .zp-toggle__slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── 输入框 ── */
.zp-input :deep(.v-field) {
  border-radius: 12px;
}

/* ── Token 输入 ── */
.zp-token-eye-btn {
  min-width: 28px;
  width: 28px;
  height: 28px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.zp-token-eye-btn :deep(.v-btn__overlay),
.zp-token-eye-btn :deep(.v-btn__underlay) {
  display: none;
}

/* ── Token 提示 ── */
.zp-token-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 11px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.5);
  padding: 8px 10px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.07);
  border-radius: 10px;
}

.zp-token-hint__icon {
  margin-top: 2px;
  flex-shrink: 0;
  color: rgba(var(--v-theme-on-surface), 0.4);
}

/* ── 字段区块 ── */
.zp-field {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.zp-field__header {
  display: flex;
  align-items: center;
}

.zp-field__title-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.zp-field__title-icon {
  flex-shrink: 0;
}

.zp-field__title-text {
  display: flex;
  flex-direction: column;
}

.zp-field__label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(var(--v-theme-on-surface), 0.82);
}

.zp-field-hint {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.42);
  line-height: 1.5;
}

/* ── 表单网格 ── */
.zp-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.zp-form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* ── 刷新按钮 ── */
.zp-refresh-btn {
  min-width: 28px;
  width: 28px;
  height: 28px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

/* ── 系统设置占位 ── */
.zp-sys-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 0;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

/* ── 域名下拉 ── */
.zp-domain-list-item {
  min-height: 40px !important;
}

.zp-domain-list-item :deep(.v-list-item__prepend) {
  margin-inline-end: 8px;
}

.zp-domain-list-item :deep(.v-list-item-title) {
  min-width: 0;
}

.zp-domain-item {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  line-height: 1.4;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

/* ── 系统保存按钮 ── */
.zp-sys-save-actions {
  display: flex;
  justify-content: flex-end;
}

.zp-sys-save-btn {
  border-radius: 10px;
  text-transform: none;
  letter-spacing: 0;
  font-size: 13px;
  font-weight: 500;
}

/* ── 系统存储选择器 ── */
.zp-storage-select-wrap {
  flex: 1;
  min-width: 0;
}

.zp-storage-select :deep(.v-field) {
  min-height: unset;
  box-shadow: none;
}

.zp-storage-select :deep(.v-field__outline) {
  --v-field-border-width: 1px;
  color: rgba(var(--v-theme-on-surface), 0.12);
}

.zp-storage-select :deep(.v-field__input) {
  padding-block: 0;
  font-size: 13px;
}

/* 空值时聚焦不上浮，仅选择值后才上浮 */
.zp-storage-select :deep(.v-field--focused:not(.v-field--active) .v-field-label--floating) {
  transform: translateY(0) scale(1) !important;
  opacity: 1 !important;
}
.zp-storage-select :deep(.v-field--focused:not(.v-field--active) .v-field__outline__notch) {
  border-color: transparent !important;
}

/* ── 系统水印文字字段 ── */
.zp-sys-watermark-field {
  margin-top: 16px;
}

/* ── 关于 / 指南 ── */
.zp-guide {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.72);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.zp-guide__section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.zp-guide__paragraph {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.zp-guide__divider {
  height: 0.5px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  margin: 2px 0;
}

.zp-guide__contact {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.zp-contact-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 12px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  background: rgba(var(--v-theme-surface), 0.72);
  color: rgba(var(--v-theme-on-surface), 0.82);
}

.zp-contact-link:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .zp-config {
    padding: 14px;
  }

  .zp-topbar {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .zp-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .zp-topbar__right {
    justify-content: flex-end;
  }

  .zp-row {
    flex-direction: column;
  }


  .zp-topbar__right :deep(.v-btn-group) {
    gap: 0;
  }

  .zp-topbar__right :deep(.v-btn) {
    min-width: 36px !important;
    padding-inline: 0 !important;
  }

  .zp-switch-grid {
    grid-template-columns: 1fr;
  }

  .zp-form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
