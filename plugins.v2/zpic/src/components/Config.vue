<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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

    <!-- 配置列 -->
    <div class="zp-config-col">

      <!-- 基础配置卡片 -->
      <div class="zp-card">
        <div class="zp-card__header">
          <span class="zp-card__title d-flex align-center">
            <v-icon icon="mdi-tune-vertical" size="18" color="#8b5cf6" class="mr-1"></v-icon>
            基础配置
          </span>
        </div>

        <!-- 启用开关 -->
        <div class="zp-switch-row">
          <div class="zp-switch-item">
            <span class="zp-row__text">
              <v-icon icon="mdi-power-plug" size="20" :color="form.enabled ? '#a78bfa' : 'grey'" class="mr-2"></v-icon>
              启用插件
            </span>
            <label class="switch" style="--switch-checked-bg: #a78bfa;">
              <input v-model="form.enabled" type="checkbox" />
              <div class="slider">
                <div class="circle">
                  <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                  <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                </div>
              </div>
            </label>
          </div>
        </div>
      </div>

      <!-- 开放令牌卡片 -->
      <div class="zp-card">
        <div class="zp-card__header">
          <span class="zp-card__title d-flex align-center">
            <v-icon icon="mdi-key-chain" size="18" color="#f59e0b" class="mr-1"></v-icon>
            开放令牌
          </span>
        </div>

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

        <div class="zp-token-hint">
          <v-icon icon="mdi-information-outline" size="14" class="zp-token-hint__icon" />
          <span>用于开放 API 接口鉴权（上传图片 V3、获取相册列表、删除图片等），请前往 Zpic 后台获取。</span>
        </div>
      </div>

      <!-- 系统设置卡片 -->
      <div class="zp-card">
        <div class="zp-card__header">
          <span class="zp-card__title d-flex align-center">
            <v-icon icon="mdi-cog-sync-outline" size="18" color="#10b981" class="mr-1"></v-icon>
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
          <!-- 图片压缩 & 水印（同一行各占一半） -->
          <div class="zp-switch-row zp-switch-row--dual">
            <!-- 图片压缩 -->
            <div class="zp-switch-item">
              <span class="zp-row__text">
                <v-icon icon="mdi-image-size-select-large" size="18" :color="sysConfig.compress ? '#10b981' : 'grey'" class="mr-1"></v-icon>
                <span class="zp-setting-label">
                  图片压缩
                  <span class="zp-setting-desc">自动压缩以节省空间</span>
                </span>
              </span>
              <label class="switch" style="--switch-checked-bg: #10b981;">
                <input v-model="sysConfig.compress" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </div>
            <!-- 文字水印 -->
            <div class="zp-switch-item" :class="{ 'zp-switch-item--disabled': !isVipSubscription }">
              <span class="zp-row__text">
                <v-icon icon="mdi-watermark" size="18" :color="isVipSubscription && sysConfig.watermark_enabled ? '#06b6d4' : 'grey'" class="mr-1"></v-icon>
                <span class="zp-setting-label">
                  文字水印
                  <span class="zp-setting-desc">{{ isVipSubscription ? '为上传图片添加文字水印' : 'VIP 订阅可用' }}</span>
                </span>
              </span>
              <label class="switch" style="--switch-checked-bg: #06b6d4;" :class="{ 'switch--disabled': !isVipSubscription }">
                <input v-model="sysConfig.watermark_enabled" type="checkbox" :disabled="!isVipSubscription" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </div>
          </div>

          <div class="zp-system-fields">
            <!-- 水印文字（条件显示） -->
            <v-expand-transition>
              <v-text-field
                v-if="isVipSubscription && sysConfig.watermark_enabled"
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
            </v-expand-transition>

            <!-- 存储域名 -->
            <v-select
              v-model="sysConfig.storage_domain"
              :items="sysConfig.storage_domains"
              label="存储域名"
              density="compact"
              variant="outlined"
              hide-details
              class="zp-input"
              prepend-inner-icon="mdi-dns-outline"
              placeholder="选择图片存储 CDN 域名"
              clearable
            >
              <template #item="{ props: itemProps }">
                <v-list-item v-bind="itemProps" density="compact" class="zp-domain-list-item">
                  <template #prepend>
                    <v-icon icon="mdi-link-variant" size="16" />
                  </template>
                  <template #title>
                    <span class="zp-domain-item">{{ itemProps.title }}</span>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </div>

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
              <v-icon icon="mdi-content-save-check-outline" size="16" class="mr-1"></v-icon>
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
          <v-icon icon="mdi-book-open-page-variant-outline" size="18" color="#6366f1" class="mr-1"></v-icon>
          使用说明
        </span>
      </div>
      <div class="zp-desc-content">
        <div class="zp-desc-item">
          <v-icon icon="mdi-numeric-1-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>登录方式：</strong>在状态页通过验证码完成登录，登录后站点地址与邮箱自动缓存。</span>
        </div>
        <div class="zp-desc-item">
          <v-icon icon="mdi-numeric-2-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>登录令牌：</strong>登录成功后自动获取并缓存，失效时插件会自动清空。</span>
        </div>
        <div class="zp-desc-item">
          <v-icon icon="mdi-numeric-3-circle-outline" size="16" color="primary" class="mr-2" />
          <span><strong>开放令牌：</strong>用于调用开放 API（上传图片、相册管理），需在 Zpic 后台生成。</span>
        </div>
      </div>
    </div>

    <!-- 消息提示 -->
    <v-snackbar v-model="message.show" :color="message.type" :timeout="2400" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<style scoped>
/* ── 页面容器 ── */
.zp-config {
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

/* ── 顶栏 ── */
.zp-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.zp-topbar__left,
.zp-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.zp-topbar__right {
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
}

.zp-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

/* ── 配置列 ── */
.zp-config-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  gap: 12px;
}

.zp-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.zp-card__title {
  font-size: 13px;
  font-weight: 600;
}

/* ── 开关行 ── */
.zp-switch-row {
  display: flex;
  gap: 16px;
  flex-wrap: nowrap;
  justify-content: flex-start;
}

/* 双列并排：图片压缩 & 水印各占一半 */
.zp-switch-row--dual {
  gap: 8px;
}

.zp-switch-row--dual .zp-switch-item {
  flex: 1 1 50%;
  min-width: 0;
}

.zp-switch-row--dual .zp-switch-item .zp-row__text {
  font-size: 12px;
}

.zp-switch-row--dual .zp-switch-item .zp-setting-desc {
  font-size: 10px;
}

.zp-switch-row--dual .switch {
  margin-left: 6px;
  --switch-width: 32px;
  --switch-height: 18px;
  --circle-diameter: 14px;
}

.zp-switch-row--dual .switch svg.checkmark {
  width: 8px;
  height: 8px;
}

.zp-switch-row--dual .switch svg.cross {
  width: 5px;
  height: 5px;
}

.zp-switch-item {
  display: flex;
  flex: 1 1 0;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
}

.zp-switch-item--disabled {
  opacity: 0.72;
}

.zp-row__text {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.85);
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

/* ── 说明列表 ── */
.zp-desc-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.zp-desc-item {
  display: flex;
  align-items: flex-start;
  font-size: 13px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.zp-desc-item strong {
  font-weight: 600;
}

/* ── 自定义开关 ── */
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
.switch input:disabled+.slider,
.switch--disabled .slider {
  opacity: 0.5;
  cursor: not-allowed;
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

/* ── 设置标签 ── */
.zp-setting-label {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.zp-setting-desc {
  font-size: 11px;
  font-weight: 400;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

/* ── 系统设置字段 ── */
.zp-system-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
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

  .zp-topbar__right :deep(.v-btn-group) {
    gap: 0;
  }

  .zp-topbar__right :deep(.v-btn) {
    min-width: 36px !important;
    padding-inline: 0 !important;
  }

  .zp-switch-row {
    flex-wrap: wrap;
  }

  .zp-switch-item {
    flex: 1 1 100%;
  }

  /* 移动端双列还原为单列 */
  .zp-switch-row--dual .zp-switch-item {
    flex: 1 1 100%;
  }

  .zp-switch-row--dual .zp-switch-item .zp-row__text {
    font-size: 13px;
  }

  .zp-switch-row--dual .zp-switch-item .zp-setting-desc {
    font-size: 11px;
  }

  .zp-switch-row--dual .switch {
    --switch-width: 36px;
    --switch-height: 20px;
    --circle-diameter: 16px;
    margin-left: 10px;
  }

  .zp-switch-row--dual .switch svg.checkmark {
    width: var(--icon-checkmark-size);
  }

  .zp-switch-row--dual .switch svg.cross {
    width: var(--icon-cross-size);
  }
}
</style>
