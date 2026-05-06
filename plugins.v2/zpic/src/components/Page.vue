<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { calcPercent, formatBytes, pluginRequest } from '../utils/zpic'

const PRIVACY_MODE_STORAGE_KEY = 'zpic-page-privacy-mode'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  initialConfig: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['switch', 'close', 'action'])

const loading = ref(false)
const loginLoading = ref(false)
const dialogLoading = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })
const status = ref({
  enabled: false,
  logged_in: false,
  email: '',
  uid: '',
  role: '',
  tier: '',
  user: {},
  subscription: {},
})
const captcha = ref({ captcha_key: '', image: '' })
const privacyMode = ref(false)
const loginForm = reactive({
  email: '',
  password: '',
  captcha_key: '',
  captcha_value: '',
})

const storagePercent = computed(() => {
  const subscription = status.value.subscription || {}
  return calcPercent(subscription.used_storage_bytes, (subscription.storage_limit_mb || 0) * 1024 * 1024)
})

function pushMessage(text, type = 'info') {
  message.text = text
  message.type = type
  message.show = true
}

function maskPrivacyValue(value) {
  const text = value == null || value === '' ? '-' : String(value)
  if (!privacyMode.value || text === '-') {
    return text
  }
  if (text.length <= 2) {
    return '*'.repeat(text.length)
  }
  if (text.length <= 4) {
    return `${text.slice(0, 1)}${'*'.repeat(text.length - 2)}${text.slice(-1)}`
  }
  const keep = Math.min(2, Math.floor(text.length / 4))
  const maskedLength = Math.max(text.length - keep * 2, 1)
  return `${text.slice(0, keep)}${'*'.repeat(maskedLength)}${text.slice(-keep)}`
}

async function loadStatus(showSuccess = false) {
  loading.value = true
  try {
    const result = await pluginRequest(props.api, '/status')
    if (!result?.success) {
      throw new Error(result?.message || '获取状态失败')
    }
    status.value = result.data || status.value
    loginForm.email = status.value.email || props.initialConfig?.email || ''
    if (showSuccess) {
      pushMessage('状态已刷新', 'success')
    }
  } catch (error) {
    pushMessage(error.message || '获取状态失败', 'error')
  } finally {
    loading.value = false
  }
}

async function loadCaptcha(showMessage = false) {
  try {
    const result = await pluginRequest(props.api, '/captcha')
    if (!result?.success) {
      throw new Error(result?.message || '获取验证码失败')
    }
    captcha.value = result.data || { captcha_key: '', image: '' }
    loginForm.captcha_key = captcha.value.captcha_key || ''
    loginForm.captcha_value = ''
    if (showMessage) {
      pushMessage('验证码已刷新', 'success')
    }
  } catch (error) {
    pushMessage(error.message || '获取验证码失败', 'error')
  }
}

async function doLogin() {
  if (!loginForm.email || !loginForm.password || !loginForm.captcha_value) {
    pushMessage('请完整填写邮箱、密码和验证码', 'warning')
    return
  }
  loginLoading.value = true
  try {
    const result = await pluginRequest(props.api, '/login', {
      method: 'POST',
      body: { ...loginForm },
    })
    if (!result?.success) {
      throw new Error(result?.message || '登录失败')
    }
    pushMessage(result.message || '登录成功', 'success')
    await loadStatus()
    emit('action')
  } catch (error) {
    pushMessage(error.message || '登录失败', 'error')
    await loadCaptcha()
  } finally {
    loginLoading.value = false
  }
}

async function doLogout() {
  dialogLoading.value = true
  try {
    const result = await pluginRequest(props.api, '/logout', { method: 'POST', body: {} })
    if (!result?.success) {
      throw new Error(result?.message || '退出失败')
    }
    status.value = { enabled: status.value.enabled, logged_in: false, user: {}, subscription: {} }
    loginForm.password = ''
    pushMessage('已退出登录', 'success')
    await loadCaptcha()
  } catch (error) {
    pushMessage(error.message || '退出失败', 'error')
  } finally {
    dialogLoading.value = false
  }
}

async function refreshAll() {
  await loadStatus(true)
  if (!status.value.logged_in) {
    await loadCaptcha(true)
  }
}

onMounted(async () => {
  try {
    privacyMode.value = localStorage.getItem(PRIVACY_MODE_STORAGE_KEY) === '1'
  } catch (_) {
    privacyMode.value = false
  }
  loginForm.email = props.initialConfig?.email || ''
  await loadStatus()
  if (!status.value.logged_in) {
    await loadCaptcha()
  }
})

watch(privacyMode, value => {
  try {
    localStorage.setItem(PRIVACY_MODE_STORAGE_KEY, value ? '1' : '0')
  } catch (_) {
    // ignore storage failures
  }
})
</script>

<template>
  <div class="zp-page">
    <!-- 顶栏 -->
    <div class="zp-topbar">
      <div class="zp-topbar__left">
        <div class="zp-topbar__icon">
          <v-icon icon="mdi-image-multiple-outline" size="24" />
        </div>
        <div>
          <div class="zp-topbar__title">Zpic 图库</div>
          <div class="zp-topbar__sub">连接 Zpic 图床，完成登录并查看当前用户信息</div>
        </div>
      </div>
      <div class="zp-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="refreshAll" size="small" min-width="40" class="px-0 px-sm-3" :loading="loading">
            <v-icon icon="mdi-refresh" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">刷新</span>
          </v-btn>
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-cog" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">配置</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <v-row class="zp-panel-row">
      <!-- 左侧：连接状态 + 配额信息 -->
      <v-col cols="12" md="7" class="zp-panel-col">
        <div class="zp-left-col">
          <!-- 连接状态卡片 -->
          <div class="zp-card zp-card--status">
            <div class="zp-card__header">
              <span class="zp-card__title d-flex align-center">
                <v-icon icon="mdi-connection" size="18" color="#10b981" class="mr-1" />
                连接状态
              </span>
            </div>
            <div class="zp-results zp-results--summary">
              <div class="zp-stat-card" :class="status.logged_in ? 'zp-stat-card--success' : 'zp-stat-card--warning'">
                <div class="zp-stat-card__label">登录状态</div>
                <div class="zp-stat-card__value">{{ status.logged_in ? '在线' : '离线' }}</div>
              </div>
              <div class="zp-stat-card" :class="status.enabled ? 'zp-stat-card--primary' : 'zp-stat-card--muted'">
                <div class="zp-stat-card__label">插件状态</div>
                <div class="zp-stat-card__value">{{ status.enabled ? '启用' : '禁用' }}</div>
              </div>
              <div class="zp-stat-card zp-stat-card--info">
                <div class="zp-stat-card__label">当前角色</div>
                <div class="zp-stat-card__value">{{ status.user?.role || status.role || '-' }}</div>
              </div>
              <div class="zp-stat-card zp-stat-card--primary">
                <div class="zp-stat-card__label">当前套餐</div>
                <div class="zp-stat-card__value">{{ status.subscription?.tier || status.tier || '-' }}</div>
              </div>
            </div>
            <div class="zp-status-note">
              <v-icon icon="mdi-information-outline" size="16" class="zp-status-note__icon" />
              <div class="zp-status-note__content">
                <div class="zp-status-note__title">状态说明</div>
                <div class="zp-status-note__text">登录成功后会自动同步用户信息与订阅额度，验证码失效后可直接点击图片刷新。</div>
              </div>
            </div>
          </div>

          <!-- 配额信息卡片 -->
          <div class="zp-card zp-card--space zp-desktop-only-space">
            <div class="zp-card__header">
              <span class="zp-card__title d-flex align-center">
                <v-icon icon="mdi-database-outline" size="18" color="#0ea5e9" class="mr-1" />
                配额信息
              </span>
            </div>
            <template v-if="status.logged_in">
              <div class="zp-space-bar">
                <div class="zp-space-text">
                  <span>已用 {{ formatBytes(status.subscription?.used_storage_bytes) }}</span>
                  <span>/ {{ status.subscription?.storage_limit_mb ? `${status.subscription.storage_limit_mb} MB` : '-' }}</span>
                </div>
                <div class="zp-progress-bar">
                  <div class="zp-progress-fill" :style="{ width: storagePercent + '%' }"></div>
                </div>
                <div class="zp-space-percent">{{ storagePercent }}%</div>
              </div>
              <div class="zp-info-grid">
                <div class="zp-info-item">
                  <div class="zp-info-item__label">今日上传</div>
                  <div class="zp-info-item__value">{{ status.subscription?.daily_used || 0 }} / {{ status.subscription?.daily_limit || 0 }}</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">每月限制</div>
                  <div class="zp-info-item__value">{{ status.subscription?.monthly_used || 0 }} / {{ status.subscription?.monthly_limit || 0 }}</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">单文件限制</div>
                  <div class="zp-info-item__value">{{ status.subscription?.size_limit_mb || 0 }} MB</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">存储总额</div>
                  <div class="zp-info-item__value">{{ status.subscription?.storage_limit_mb || 0 }} MB</div>
                </div>
              </div>
            </template>
            <div v-else class="zp-empty-state">
              <div class="zp-empty-state__icon">
                <v-icon icon="mdi-account-lock-open-outline" size="40" />
              </div>
              <div class="zp-empty-state__title">尚未登录 Zpic</div>
              <div class="zp-empty-state__sub">登录后这里会展示套餐、存储用量和上传额度信息。</div>
              <div class="zp-empty-state__steps">
                <div class="zp-empty-step">
                  <div class="zp-empty-step__num">1</div>
                  <div>
                    <div class="zp-empty-step__label">账号登录</div>
                    <div class="zp-empty-step__desc">使用右侧表单填写账号与验证码</div>
                  </div>
                </div>
                <v-icon icon="mdi-chevron-right" size="18" color="rgba(var(--v-theme-on-surface), 0.3)" class="zp-empty-step__arrow" />
                <div class="zp-empty-step">
                  <div class="zp-empty-step__num">2</div>
                  <div>
                    <div class="zp-empty-step__label">自动同步</div>
                    <div class="zp-empty-step__desc">系统会自动拉取配额与用户信息</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </v-col>

      <!-- 右侧：账号登录 + 用户信息 -->
      <v-col cols="12" md="5" class="zp-panel-col">
        <div class="zp-right-col">
          <!-- 账号登录卡片 -->
          <div class="zp-card zp-card--login">
            <div class="zp-card__header">
              <span class="zp-card__title d-flex align-center">
                <v-icon icon="mdi-login-variant" size="18" color="#10b981" class="mr-1"></v-icon>
                {{ status.logged_in ? '登录完成' : '账号登录' }}
              </span>
              <v-chip :color="status.logged_in ? 'success' : 'warning'" size="x-small" variant="tonal">
                {{ status.logged_in ? '已登录' : '未登录' }}
              </v-chip>
            </div>

            <template v-if="status.logged_in">
              <div class="zp-login-success">
                <v-icon icon="mdi-check-decagram" size="64" color="success"></v-icon>
                <div class="text-success mt-2">当前账号已登录</div>
                <div class="text-medium-emphasis mt-1">如需切换账号，请先退出登录后重新执行登录操作。</div>
              </div>
            </template>
            <template v-else>
              <v-text-field
                v-model="loginForm.email"
                label="邮箱"
                variant="outlined"
                density="comfortable"
                class="mb-2"
                prepend-inner-icon="mdi-email-outline"
                hide-details
              />
              <v-text-field
                v-model="loginForm.password"
                label="密码"
                type="password"
                variant="outlined"
                density="comfortable"
                class="mb-2"
                prepend-inner-icon="mdi-lock-outline"
                hide-details
              />
              <div class="zp-captcha-box mb-3">
                <div class="zp-captcha-wrap" @click="loadCaptcha(true)">
                  <v-img v-if="captcha.image" :src="captcha.image" class="zp-captcha-image" />
                  <div v-else class="zp-captcha-placeholder">
                    <v-icon icon="mdi-refresh" size="18" class="mr-1" />
                    验证码加载中
                  </div>
                </div>
                <v-text-field
                  v-model="loginForm.captcha_value"
                  label="验证码"
                  variant="outlined"
                  density="comfortable"
                  hide-details
                />
              </div>
              <v-btn block color="primary" :loading="loginLoading" @click="doLogin" prepend-icon="mdi-login">
                登录 Zpic
              </v-btn>
            </template>
          </div>

          <!-- 用户信息卡片 -->
          <div class="zp-card zp-card--user">
            <div class="zp-card__header">
              <span class="zp-card__title d-flex align-center">
                <v-icon icon="mdi-account-circle-outline" size="18" color="#8b5cf6" class="mr-1" />
                用户信息
                <v-btn
                  variant="text"
                  density="comfortable"
                  size="x-small"
                  class="zp-privacy-btn ml-1"
                  :icon="privacyMode ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
                  @click="privacyMode = !privacyMode"
                />
              </span>
              <v-btn
                v-if="status.logged_in"
                variant="text"
                icon
                @click="doLogout"
                :loading="dialogLoading"
                size="small"
                class="zp-logout-btn"
              >
                <v-icon icon="mdi-logout" size="18"></v-icon>
              </v-btn>
            </div>
            <div class="zp-info-grid">
              <div class="zp-info-item">
                <div class="zp-info-item__label">邮箱</div>
                <div class="zp-info-item__value">{{ maskPrivacyValue(status.user?.email || status.email) }}</div>
              </div>
              <div class="zp-info-item">
                <div class="zp-info-item__label">用户 ID</div>
                <div class="zp-info-item__value zp-info-item__value--mono">{{ maskPrivacyValue(status.user?.uid || status.uid) }}</div>
              </div>
              <div class="zp-info-item">
                <div class="zp-info-item__label">角色</div>
                <div class="zp-info-item__value">{{ maskPrivacyValue(status.user?.role || status.role) }}</div>
              </div>
              <div class="zp-info-item">
                <div class="zp-info-item__label">套餐</div>
                <div class="zp-info-item__value">{{ maskPrivacyValue(status.subscription?.tier || status.tier) }}</div>
              </div>
            </div>
          </div>

          <!-- 配额信息（移动端） -->
          <div class="zp-card zp-card--space zp-mobile-only-space">
            <div class="zp-card__header">
              <span class="zp-card__title d-flex align-center">
                <v-icon icon="mdi-database-outline" size="18" color="#0ea5e9" class="mr-1" />
                配额信息
              </span>
            </div>
            <template v-if="status.logged_in">
              <div class="zp-space-bar">
                <div class="zp-space-text">
                  <span>已用 {{ formatBytes(status.subscription?.used_storage_bytes) }}</span>
                  <span>/ {{ status.subscription?.storage_limit_mb ? `${status.subscription.storage_limit_mb} MB` : '-' }}</span>
                </div>
                <div class="zp-progress-bar">
                  <div class="zp-progress-fill" :style="{ width: storagePercent + '%' }"></div>
                </div>
                <div class="zp-space-percent">{{ storagePercent }}%</div>
              </div>
              <div class="zp-info-grid">
                <div class="zp-info-item">
                  <div class="zp-info-item__label">今日上传</div>
                  <div class="zp-info-item__value">{{ status.subscription?.daily_used || 0 }} / {{ status.subscription?.daily_limit || 0 }}</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">每月限制</div>
                  <div class="zp-info-item__value">{{ status.subscription?.monthly_used || 0 }} / {{ status.subscription?.monthly_limit || 0 }}</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">单文件限制</div>
                  <div class="zp-info-item__value">{{ status.subscription?.size_limit_mb || 0 }} MB</div>
                </div>
                <div class="zp-info-item">
                  <div class="zp-info-item__label">存储总额</div>
                  <div class="zp-info-item__value">{{ status.subscription?.storage_limit_mb || 0 }} MB</div>
                </div>
              </div>
            </template>
            <div v-else class="zp-empty-state">
              <div class="zp-empty-state__icon">
                <v-icon icon="mdi-account-lock-open-outline" size="40" />
              </div>
              <div class="zp-empty-state__title">尚未登录 Zpic</div>
              <div class="zp-empty-state__sub">登录后这里会展示套餐、存储用量和上传额度信息。</div>
            </div>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- 消息提示 -->
    <v-snackbar v-model="message.show" :color="message.type" :timeout="2400" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<style scoped>
/* ── 页面变量 ── */
.zp-page {
  --zp-panel-gap: 12px;
  --zp-panel-min-height: 548px;
  --zp-status-card-min-height: 168px;
  --zp-login-card-min-height: 308px;
}

/* ── 页面容器 ── */
.zp-page {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif;
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

/* ── 面板布局 ── */
.zp-panel-row {
  margin: -6px;
  align-items: stretch;
}

.zp-panel-col {
  display: flex;
  padding: 6px;
}

.zp-panel-col > div {
  width: 100%;
}

.zp-left-col {
  display: flex;
  flex-direction: column;
  gap: var(--zp-panel-gap);
  height: 100%;
  min-height: var(--zp-panel-min-height);
}

.zp-right-col {
  display: flex;
  flex-direction: column;
  gap: var(--zp-panel-gap);
  height: 100%;
  min-height: var(--zp-panel-min-height);
}

/* ── 卡片基础 ── */
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

.zp-privacy-btn {
  min-width: 24px;
  width: 24px;
  height: 24px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.zp-logout-btn {
  min-width: 32px;
  width: 32px;
  height: 32px;
  color: rgb(var(--v-theme-error));
}

.zp-logout-btn :deep(.v-btn__overlay),
.zp-logout-btn :deep(.v-btn__underlay) {
  display: none;
}

/* ── 卡片尺寸修饰 ── */
.zp-card--status {
  flex: 0 0 auto;
  min-height: var(--zp-status-card-min-height);
}

.zp-card--space {
  flex: 1 1 0;
  min-height: 0;
}

.zp-card--login {
  flex: 0 0 auto;
  min-height: var(--zp-login-card-min-height);
}

.zp-card--user {
  flex: 1 1 0;
  min-height: 0;
}

.zp-card--space .zp-info-grid,
.zp-card--user .zp-info-grid {
  align-content: start;
}

/* ── 响应式：配额卡片 ── */
.zp-mobile-only-space {
  display: none;
}

/* ── 状态统计行 ── */
.zp-results--summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.zp-stat-card {
  flex: 1;
  min-width: 0;
  border-radius: 14px;
  padding: 8px 10px 7px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 2px 12px rgba(var(--v-theme-on-surface), 0.1);
}

.zp-stat-card__label {
  font-size: 11px;
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.zp-stat-card__value {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
  text-align: center;
}

.zp-stat-card--primary {
  background: rgba(139, 92, 246, 0.12);
  border: 0.5px solid rgba(139, 92, 246, 0.3);
}
.zp-stat-card--primary .zp-stat-card__value { color: #8b5cf6; }

.zp-stat-card--success {
  background: rgba(16, 185, 129, 0.12);
  border: 0.5px solid rgba(16, 185, 129, 0.3);
}
.zp-stat-card--success .zp-stat-card__value { color: #10b981; }

.zp-stat-card--warning {
  background: rgba(245, 158, 11, 0.12);
  border: 0.5px solid rgba(245, 158, 11, 0.3);
}
.zp-stat-card--warning .zp-stat-card__value { color: #f59e0b; }

.zp-stat-card--info {
  background: rgba(59, 130, 246, 0.12);
  border: 0.5px solid rgba(59, 130, 246, 0.3);
}
.zp-stat-card--info .zp-stat-card__value { color: #3b82f6; }

.zp-stat-card--muted {
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.12);
}
.zp-stat-card--muted .zp-stat-card__value { color: rgba(var(--v-theme-on-surface), 0.55); }

/* ── 状态说明提示 ── */
.zp-status-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.22);
}

.zp-status-note__icon {
  margin-top: 1px;
  color: rgb(var(--v-theme-info));
  flex-shrink: 0;
}

.zp-status-note__content {
  min-width: 0;
}

.zp-status-note__title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.75);
  margin-bottom: 2px;
}

.zp-status-note__text {
  font-size: 11px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

/* ── 配额进度条 ── */
.zp-space-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 10px;
}

.zp-space-text {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.zp-progress-bar {
  height: 8px;
  background: rgba(var(--v-theme-on-surface), 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.zp-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #8b5cf6, #38bdf8);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.zp-space-percent {
  font-size: 14px;
  font-weight: 700;
  color: #8b5cf6;
  text-align: right;
}

/* ── 信息网格 ── */
.zp-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.zp-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 10px;
}

.zp-info-item__label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.zp-info-item__value {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.zp-info-item__value--mono {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', Consolas, monospace;
  font-size: 12px;
}

/* ── 空状态 ── */
.zp-empty-state {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 19px 15px 24px;
  text-align: center;
  gap: 10px;
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.24);
  border-radius: 14px;
}

.zp-empty-state__icon {
  width: 62px;
  height: 62px;
  border-radius: 18px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.3);
  margin-bottom: 3px;
}

.zp-empty-state__title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.7);
  letter-spacing: -0.2px;
}

.zp-empty-state__sub {
  font-size: 12px;
  line-height: 1.55;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.zp-empty-state__steps {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 6px;
}

.zp-empty-step {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 12px;
  padding: 8px 13px;
  text-align: left;
  max-width: 170px;
}

.zp-empty-step__num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(var(--v-theme-primary), 0.15);
  color: rgb(var(--v-theme-primary));
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.zp-empty-step__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.75);
  margin-bottom: 3px;
}

.zp-empty-step__desc {
  font-size: 11px;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.zp-empty-step__arrow {
  flex-shrink: 0;
}

/* ── 登录表单 ── */
.zp-captcha-box {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  align-items: center;
}

.zp-captcha-wrap {
  height: 56px;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
}

.zp-captcha-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.zp-captcha-image :deep(img) {
  object-fit: contain !important;
  object-position: center center;
  padding: 4px;
}

.zp-captcha-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

/* ── 登录成功状态 ── */
.zp-login-success {
  display: flex;
  min-height: 220px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

/* ── 响应式 ── */
@media (max-width: 768px) {
  .zp-page {
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

  .zp-panel-col {
    display: block;
  }

  .zp-results--summary {
    display: flex;
    flex-direction: row;
    align-items: stretch;
    justify-content: space-between;
    flex-wrap: nowrap;
    gap: 0;
    padding: 8px 6px;
    background: rgba(var(--v-theme-on-surface), 0.03);
    border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
    border-radius: 14px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 2px 10px rgba(0, 0, 0, 0.05);
    overflow-x: auto;
  }

  .zp-stat-card {
    flex: 1 1 20%;
    min-width: 0;
    padding: 6px 4px;
    background: transparent;
    border: none;
    box-shadow: none;
    border-radius: 0;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
  }

  .zp-stat-card__label {
    font-size: 10px;
    white-space: nowrap;
  }

  .zp-stat-card__value {
    font-size: 18px;
    letter-spacing: -0.4px;
    text-align: center;
  }

  .zp-info-grid {
    grid-template-columns: 1fr;
  }

  .zp-captcha-box {
    grid-template-columns: 100px 1fr;
  }

  .zp-desktop-only-space {
    display: none;
  }

  .zp-mobile-only-space {
    display: flex;
  }

  .zp-card--space .zp-empty-state__steps {
    display: none;
  }

  .zp-card--login {
    min-height: auto !important;
  }

  .zp-card--status,
  .zp-card--space,
  .zp-card--user,
  .zp-left-col,
  .zp-right-col {
    min-height: auto;
    height: auto;
  }
}
</style>
