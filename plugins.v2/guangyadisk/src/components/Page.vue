<template>
  <div class="gy-page">
    <!-- 顶栏 -->
    <div class="gy-topbar">
      <div class="gy-topbar__left">
        <div class="gy-topbar__icon">
          <v-icon icon="mdi-cloud-outline" size="24" />
        </div>
        <div>
          <div class="gy-topbar__title">光鸭云盘</div>
          <div class="gy-topbar__sub">管理光鸭云盘文件同步与访问</div>
        </div>
      </div>
      <div class="gy-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="refreshStatus" size="small" min-width="40" class="px-0 px-sm-3" :loading="loading">
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

    <v-row class="gy-panel-row">
      <!-- 左侧：状态信息 -->
      <v-col cols="12" md="7" class="gy-panel-col">
        <div class="gy-left-col">
          <!-- 统计卡片 -->
          <div class="gy-card gy-card--status">
            <div class="gy-card__header">
              <span class="gy-card__title d-flex align-center">
                <v-icon icon="mdi-connection" size="18" color="#10b981" class="mr-1" />
                连接状态
              </span>
            </div>
            <div class="gy-results gy-results--summary">
              <div class="gy-stat-card" :class="status.logged_in ? 'gy-stat-card--success' : 'gy-stat-card--warning'">
                <div class="gy-stat-card__label">登录状态</div>
                <div class="gy-stat-card__value">{{ status.logged_in ? '在线' : '离线' }}</div>
              </div>
              <div class="gy-stat-card" :class="status.enabled ? 'gy-stat-card--primary' : 'gy-stat-card--muted'">
                <div class="gy-stat-card__label">插件状态</div>
                <div class="gy-stat-card__value">{{ status.enabled ? '启用' : '禁用' }}</div>
              </div>
              <div class="gy-stat-card gy-stat-card--info">
                <div class="gy-stat-card__label">轮询间隔</div>
                <div class="gy-stat-card__value">{{ status.poll_interval || 5 }}s</div>
              </div>
              <div class="gy-stat-card gy-stat-card--primary">
                <div class="gy-stat-card__label">分页大小</div>
                <div class="gy-stat-card__value">{{ status.page_size || 100 }}</div>
              </div>
            </div>
            <div class="gy-status-note">
              <v-icon icon="mdi-information-outline" size="16" class="gy-status-note__icon" />
              <div class="gy-status-note__content">
                <div class="gy-status-note__title">状态说明</div>
                <div class="gy-status-note__text">页面会自动拉取最新登录状态与空间信息，二维码失效后也会自动刷新。</div>
              </div>
            </div>
          </div>

          <!-- 空间统计卡片 -->
          <div class="gy-card gy-card--space gy-desktop-only-space">
            <div class="gy-card__header">
              <span class="gy-card__title d-flex align-center">
                <v-icon icon="mdi-database-outline" size="18" color="#0ea5e9" class="mr-1" />
                空间统计
              </span>
            </div>
            <template v-if="status.total_space">
              <div class="gy-space-bar">
                <div class="gy-space-text">
                  <span>已用 {{ formatSize(status.used_space) }}</span>
                  <span>/ {{ formatSize(status.total_space) }}</span>
                </div>
                <div class="gy-progress-bar">
                  <div class="gy-progress-fill" :style="{ width: spacePercent + '%' }"></div>
                </div>
                <div class="gy-space-percent">{{ spacePercent }}%</div>
              </div>
              <div class="gy-info-grid">
                <div class="gy-info-item">
                  <div class="gy-info-item__label">总空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.total_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">已用空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.used_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">剩余空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.free_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">文件数量</div>
                  <div class="gy-info-item__value">{{ status.file_count || '-' }}</div>
                </div>
              </div>
            </template>
            <div v-else class="gy-empty-state">
              <div class="gy-empty-state__icon">
                <v-icon icon="mdi-database-off-outline" size="40" />
              </div>
              <div class="gy-empty-state__title">暂无空间统计数据</div>
              <div class="gy-empty-state__sub">完成扫码登录后，将自动展示总空间、已用空间、剩余空间。</div>
              <div class="gy-empty-state__steps">
                <div class="gy-empty-step">
                  <div class="gy-empty-step__num">1</div>
                  <div>
                    <div class="gy-empty-step__label">扫码登录</div>
                    <div class="gy-empty-step__desc">使用右侧二维码完成授权登录</div>
                  </div>
                </div>
                <v-icon icon="mdi-chevron-right" size="18" color="rgba(var(--v-theme-on-surface), 0.3)" class="gy-empty-step__arrow" />
                <div class="gy-empty-step">
                  <div class="gy-empty-step__num">2</div>
                  <div>
                    <div class="gy-empty-step__label">自动同步</div>
                    <div class="gy-empty-step__desc">系统会自动拉取空间与用户信息</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </v-col>

      <!-- 右侧：扫码登录 + 用户信息 -->
      <v-col cols="12" md="5" class="gy-panel-col">
        <div class="gy-right-col">
          <!-- 扫码登录卡片 -->
          <div class="gy-card gy-card--qrcode">
            <div class="gy-card__header">
              <span class="gy-card__title d-flex align-center">
                <v-icon icon="mdi-qrcode-scan" size="18" color="#10b981" class="mr-1"></v-icon>
                扫码登录
              </span>
              <v-chip :color="status.logged_in ? 'success' : 'warning'" size="x-small" variant="tonal">
                {{ status.logged_in ? '已登录' : '未登录' }}
              </v-chip>
            </div>

            <div class="gy-qrcode-box">
              <template v-if="status.logged_in">
                <div class="gy-qrcode-placeholder gy-qrcode-placeholder--success">
                  <v-icon icon="mdi-check-decagram" size="64" color="success"></v-icon>
                  <div class="text-success mt-2">当前已登录</div>
                  <div class="text-medium-emphasis mt-1">如需重新扫码，请先退出登录</div>
                </div>
              </template>
              <template v-else-if="qrCodeSrc">
                <img :src="qrCodeSrc" alt="光鸭云盘二维码" :class="['gy-qrcode-image', { 'gy-qrcode-image--dark': isDarkMode }]" />
              </template>
              <template v-else>
                <div class="gy-qrcode-placeholder">
                  <v-icon icon="mdi-qrcode" size="72" color="grey"></v-icon>
                  <div class="text-medium-emphasis mt-2">{{ qrLoading || qrRendering ? '正在准备二维码...' : '二维码加载中...' }}</div>
                </div>
              </template>
            </div>

            <div class="gy-qrcode-meta" v-if="shouldShowQrMeta && !qrRendering">
              <div class="gy-qrcode-meta__item">
                <span class="gy-qrcode-meta__label">用户码</span>
                <span class="gy-qrcode-meta__value gy-info-item__value--mono">{{ userCode || '-' }}</span>
              </div>
              <div class="gy-qrcode-meta__item">
                <span class="gy-qrcode-meta__label">二维码有效期</span>
                <span class="gy-qrcode-meta__value" :class="qrCountdown <= 30 ? 'gy-qrcode-meta__value--warning' : ''">
                  {{ countdownText }}
                </span>
              </div>
            </div>

          </div>

          <!-- 用户信息卡片 -->
          <div class="gy-card gy-card--user">
            <div class="gy-card__header">
              <span class="gy-card__title d-flex align-center">
                <v-icon icon="mdi-account-circle-outline" size="18" color="#8b5cf6" class="mr-1" />
                用户信息
                <v-btn
                  variant="text"
                  density="comfortable"
                  size="x-small"
                  class="gy-privacy-btn ml-1"
                  :icon="privacyMode ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
                  @click="privacyMode = !privacyMode"
                />
              </span>
              <v-btn v-if="status.logged_in" color="error" variant="tonal" prepend-icon="mdi-logout" @click="logout" :disabled="saving" size="small">
                退出
              </v-btn>
            </div>
            <div class="gy-info-grid">
              <div class="gy-info-item">
                <div class="gy-info-item__label">用户名</div>
                <div class="gy-info-item__value">{{ maskPrivacyValue(status.user_name) }}</div>
              </div>
              <div class="gy-info-item">
                <div class="gy-info-item__label">用户 ID</div>
                <div class="gy-info-item__value" :class="status.user_id ? 'gy-info-item__value--mono' : ''">{{ maskPrivacyValue(status.user_id) }}</div>
              </div>
              <div class="gy-info-item">
                <div class="gy-info-item__label">会员有效期</div>
                <div class="gy-info-item__value">{{ maskPrivacyValue(formatMemberExpireTime(status.member_expire_time)) }}</div>
              </div>
              <div class="gy-info-item">
                <div class="gy-info-item__label">设备 ID</div>
                <div class="gy-info-item__value gy-info-item__value--mono">{{ maskPrivacyValue(status.device_id) }}</div>
              </div>
            </div>
          </div>

          <div class="gy-card gy-card--space gy-mobile-only-space">
            <div class="gy-card__header">
              <span class="gy-card__title d-flex align-center">
                <v-icon icon="mdi-database-outline" size="18" color="#0ea5e9" class="mr-1" />
                空间统计
              </span>
            </div>
            <template v-if="status.total_space">
              <div class="gy-space-bar">
                <div class="gy-space-text">
                  <span>已用 {{ formatSize(status.used_space) }}</span>
                  <span>/ {{ formatSize(status.total_space) }}</span>
                </div>
                <div class="gy-progress-bar">
                  <div class="gy-progress-fill" :style="{ width: spacePercent + '%' }"></div>
                </div>
                <div class="gy-space-percent">{{ spacePercent }}%</div>
              </div>
              <div class="gy-info-grid">
                <div class="gy-info-item">
                  <div class="gy-info-item__label">总空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.total_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">已用空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.used_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">剩余空间</div>
                  <div class="gy-info-item__value">{{ formatSize(status.free_space) || '-' }}</div>
                </div>
                <div class="gy-info-item">
                  <div class="gy-info-item__label">文件数量</div>
                  <div class="gy-info-item__value">{{ status.file_count || '-' }}</div>
                </div>
              </div>
            </template>
            <div v-else class="gy-empty-state">
              <div class="gy-empty-state__icon">
                <v-icon icon="mdi-database-off-outline" size="40" />
              </div>
              <div class="gy-empty-state__title">暂无空间统计数据</div>
              <div class="gy-empty-state__sub">完成扫码登录后，将自动展示总空间、已用空间、剩余空间。</div>
              <div class="gy-empty-state__steps">
                <div class="gy-empty-step">
                  <div class="gy-empty-step__num">1</div>
                  <div>
                    <div class="gy-empty-step__label">扫码登录</div>
                    <div class="gy-empty-step__desc">使用右侧二维码完成授权登录</div>
                  </div>
                </div>
                <v-icon icon="mdi-chevron-right" size="18" color="rgba(var(--v-theme-on-surface), 0.3)" class="gy-empty-step__arrow" />
                <div class="gy-empty-step">
                  <div class="gy-empty-step__num">2</div>
                  <div>
                    <div class="gy-empty-step__label">自动同步</div>
                    <div class="gy-empty-step__desc">系统会自动拉取空间与用户信息</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- 消息提示 -->
    <v-snackbar v-model="message.show" :color="message.type" :timeout="3000" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import QRCode from 'qrcode'

const PRIVACY_MODE_STORAGE_KEY = 'guangyadisk-page-privacy-mode'

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['close', 'switch'])

const status = reactive({
  enabled: false,
  access_token: '',
  refresh_token: '',
  client_id: '',
  device_id: '',
  poll_interval: 5,
  page_size: 100,
  order_by: 3,
  sort_type: 1,
  logged_in: false,
  // 用户信息
  user_name: '',
  user_id: '',
  vip_level: '',
  member_expire_time: 0,
  // 空间统计
  total_space: 0,
  used_space: 0,
  free_space: 0,
  file_count: 0,
  ...props.initialConfig,
})

const loading = ref(false)
const saving = ref(false)
const qrLoading = ref(false)
const qrRendering = ref(false)
const polling = ref(false)
const qrCodeImage = ref('')
const userCode = ref('')
const verificationUri = ref('')
const verificationUriComplete = ref('')
const qrCountdown = ref(0)
const privacyMode = ref(false)
const isDarkMode = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })
let qrFetchRequestSeq = 0
let qrRenderRequestSeq = 0
let pollSessionSeq = 0
let pollRequestSeq = 0
let statusRefreshRequestSeq = 0

const hasPendingQr = computed(() => Boolean(userCode.value || verificationUri.value || verificationUriComplete.value))
const shouldShowQrMeta = computed(() => !status.logged_in && (hasPendingQr.value || qrLoading.value || qrRendering.value || qrCountdown.value > 0))
const qrCodeSrc = computed(() => {
  if (qrCodeImage.value) {
    return qrCodeImage.value
  }
  return ''
})

const spacePercent = computed(() => {
  if (!status.total_space || status.total_space === 0) return 0
  return Math.round((status.used_space / status.total_space) * 100)
})

const countdownText = computed(() => {
  if (!hasPendingQr.value && qrCountdown.value <= 0) {
    return '-'
  }
  if (qrCountdown.value <= 0) {
    return '已过期'
  }
  const minutes = Math.floor(qrCountdown.value / 60)
  const seconds = qrCountdown.value % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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

function formatMemberExpireTime(timestamp) {
  const value = Number(timestamp || 0)
  if (!value) {
    return '-'
  }

  const date = new Date(value * 1000)
  if (Number.isNaN(date.getTime())) {
    return '-'
  }

  const yyyy = date.getFullYear()
  const mm = String(date.getMonth() + 1).padStart(2, '0')
  const dd = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mi = String(date.getMinutes()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

async function buildQrCodeImage(qrTextOverride = '') {
  const qrText = qrTextOverride || verificationUriComplete.value || verificationUri.value || userCode.value
  if (!qrText) {
    qrCodeImage.value = ''
    qrRendering.value = false
    return
  }
  const renderSeq = ++qrRenderRequestSeq
  qrRendering.value = true
  try {
    const renderedImage = await QRCode.toDataURL(qrText, {
      width: 180,
      margin: 2,
      errorCorrectionLevel: 'M',
      color: {
        dark: '#111111',
        light: isDarkMode.value ? '#d1d5db' : '#ffffff',
      },
    })
    if (renderSeq !== qrRenderRequestSeq) {
      return
    }
    qrCodeImage.value = renderedImage
  } catch (error) {
    if (renderSeq === qrRenderRequestSeq) {
      qrCodeImage.value = ''
    }
    console.error('生成二维码失败', error)
  } finally {
    if (renderSeq === qrRenderRequestSeq) {
      qrRendering.value = false
    }
  }
}

function resetQrDisplayState() {
  qrCodeImage.value = ''
  userCode.value = ''
  verificationUri.value = ''
  verificationUriComplete.value = ''
  updateQrCountdown(0)
}

function detectDarkMode() {
  try {
    const root = document.documentElement
    const rootStyle = window.getComputedStyle(root)
    const colorScheme = rootStyle.getPropertyValue('color-scheme') || ''
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    isDarkMode.value = Boolean(
      root.classList.contains('v-theme--dark')
      || root.classList.contains('dark')
      || colorScheme.includes('dark')
      || prefersDark
    )
  } catch (_) {
    isDarkMode.value = false
  }
}

function pluginUrl(path) {
  return `/api/v1/plugin/GuangYaDisk${path}`
}

async function request(path, options = {}) {
  const apiPath = `plugin/GuangYaDisk${path}`
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

const setMessage = (type, text) => {
  message.type = type
  message.text = text
  message.show = true
}

function updateQrCountdown(expiresIn = 0) {
  qrCountdown.value = Math.max(Number(expiresIn || 0), 0)
}

async function syncQrStateFromConfig(data = {}) {
  if (status.logged_in) {
    resetQrDisplayState()
    return
  }

  userCode.value = data.user_code || ''
  verificationUri.value = data.verification_uri || ''
  verificationUriComplete.value = data.verification_uri_complete || ''
  updateQrCountdown(data.qr_expires_in || 0)

  if (verificationUriComplete.value || verificationUri.value || userCode.value) {
    await buildQrCodeImage()
  } else {
    qrCodeImage.value = ''
  }

  if (qrCountdown.value > 0) {
    startQrCountdown()
  } else {
    stopQrCountdown()
  }
}

async function refreshStatus(showToast = true) {
  const requestSeq = ++statusRefreshRequestSeq
  loading.value = true
  try {
    let data
    if (props.api?.get) {
      data = await props.api.get('plugin/GuangYaDisk/config')
    } else {
      const response = await fetch(pluginUrl('/config'))
      data = await response.json()
    }
    if (requestSeq !== statusRefreshRequestSeq) {
      return
    }
    Object.assign(status, {
      enabled: Boolean(data.enabled),
      access_token: data.access_token || '',
      refresh_token: data.refresh_token || '',
      client_id: data.client_id || '',
      device_id: data.device_id || '',
      poll_interval: Number(data.poll_interval || 5),
      page_size: Number(data.page_size || 100),
      order_by: Number(data.order_by || 3),
      sort_type: Number(data.sort_type || 1),
      logged_in: Boolean(data.logged_in),
      // 用户信息
      user_name: data.user_name || '',
      user_id: data.user_id || '',
      vip_level: data.vip_level || '',
      member_expire_time: Number(data.member_expire_time || 0),
      // 空间统计
      total_space: Number(data.total_space || 0),
      used_space: Number(data.used_space || 0),
      free_space: Number(data.free_space || 0),
      file_count: Number(data.file_count || 0),
    })
    await syncQrStateFromConfig(data)
    if (requestSeq !== statusRefreshRequestSeq) {
      return
    }
    if (!status.logged_in && !qrLoading.value) {
      await fetchQrCode({ showSuccessMessage: false })
      if (requestSeq !== statusRefreshRequestSeq) {
        return
      }
    }
    if (showToast) {
      setMessage('success', '状态已刷新')
    }
  } catch (error) {
    if (requestSeq === statusRefreshRequestSeq) {
      setMessage('error', `获取状态失败：${error.message || error}`)
    }
  } finally {
    if (requestSeq === statusRefreshRequestSeq) {
      loading.value = false
    }
  }
}

function stopPolling() {
  pollSessionSeq += 1
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}
let pollTimer = null

function stopQrCountdown() {
  if (qrTimer) {
    clearInterval(qrTimer)
    qrTimer = null
  }
}
let qrTimer = null

function startQrCountdown() {
  stopQrCountdown()
  if (qrCountdown.value <= 0) {
    if (!status.logged_in && !qrLoading.value) {
      fetchQrCode({ showSuccessMessage: false })
    }
    return
  }
  qrTimer = setInterval(() => {
    if (qrCountdown.value > 0) {
      qrCountdown.value -= 1
      return
    }
    stopQrCountdown()
    if (!status.logged_in && !qrLoading.value) {
      fetchQrCode({ showSuccessMessage: false })
    }
  }, 1000)
}

async function fetchQrCode(options = {}) {
  const { showSuccessMessage = true } = options
  const requestSeq = ++qrFetchRequestSeq
  qrLoading.value = true
  try {
    stopPolling()
    stopQrCountdown()
    resetQrDisplayState()
    const result = await request('/login/qrcode')
    if (requestSeq !== qrFetchRequestSeq) {
      return
    }
    if (!result.success) {
      throw new Error(result.message || '获取二维码失败')
    }
    const nextUserCode = result.user_code || ''
    const nextVerificationUriComplete = result.verification_uri_complete || ''
    const nextVerificationUri = result.verification_uri_complete || result.verification_uri || ''
    const nextQrText = nextVerificationUriComplete || nextVerificationUri || nextUserCode

    userCode.value = nextUserCode
    verificationUri.value = nextVerificationUri
    verificationUriComplete.value = nextVerificationUriComplete
    qrCodeImage.value = ''
    updateQrCountdown(result.expires_in || 0)
    await buildQrCodeImage(nextQrText)
    if (requestSeq !== qrFetchRequestSeq) {
      return
    }
    status.device_id = result.device_id || status.device_id
    startQrCountdown()
    if (showSuccessMessage) {
      setMessage('success', '二维码已生成，请使用光鸭云盘客户端扫码')
    }
    startPolling()
  } catch (error) {
    if (requestSeq === qrFetchRequestSeq) {
      qrRendering.value = false
      setMessage('error', `获取二维码失败：${error.message || error}`)
    }
  } finally {
    if (requestSeq === qrFetchRequestSeq) {
      qrLoading.value = false
    }
  }
}

async function pollLoginOnce() {
  if (!hasPendingQr.value || polling.value) {
    return
  }
  const currentPollSessionSeq = pollSessionSeq
  const currentPollRequestSeq = ++pollRequestSeq
  polling.value = true
  try {
    const result = await request('/login/poll')
    if (currentPollSessionSeq !== pollSessionSeq || currentPollRequestSeq !== pollRequestSeq) {
      return
    }
    if (result.success) {
      stopPolling()
      polling.value = false
      // 登录成功后自动启用插件
      status.enabled = true
      await request('/config', {
        method: 'POST',
        body: JSON.stringify({ enabled: true }),
      })
      await refreshStatus(false)
      resetQrDisplayState()
      stopQrCountdown()
      setMessage('success', result.message || '登录成功，插件已自动启用')
      return
    }
    if (!result.waiting) {
      setMessage('error', result.message || '登录失败')
    }
  } catch (error) {
    if (currentPollSessionSeq === pollSessionSeq && currentPollRequestSeq === pollRequestSeq) {
      setMessage('error', `轮询失败：${error.message || error}`)
      stopPolling()
    }
  } finally {
    if (currentPollSessionSeq === pollSessionSeq && currentPollRequestSeq === pollRequestSeq) {
      polling.value = false
    }
  }
}

function startPolling() {
  stopPolling()
  pollSessionSeq += 1
  const interval = Math.max(Number(status.poll_interval || 5), 2) * 1000
  pollTimer = setInterval(() => {
    pollLoginOnce()
  }, interval)
}

async function logout() {
  saving.value = true
  try {
    const result = await request('/login/logout', { method: 'POST' })
    if (!result.success) {
      throw new Error(result.message || '退出失败')
    }
    stopPolling()
    resetQrDisplayState()
    stopQrCountdown()
    await refreshStatus(false)
    setMessage('success', result.message || '已退出登录')
  } catch (error) {
    setMessage('error', `退出失败：${error.message || error}`)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    privacyMode.value = localStorage.getItem(PRIVACY_MODE_STORAGE_KEY) === '1'
  } catch (_) {
    privacyMode.value = false
  }
  detectDarkMode()
  await refreshStatus(false)
})

onBeforeUnmount(() => {
  stopPolling()
  stopQrCountdown()
})

watch(privacyMode, value => {
  try {
    localStorage.setItem(PRIVACY_MODE_STORAGE_KEY, value ? '1' : '0')
  } catch (_) {
    // ignore storage failures
  }
})

watch(
  () => [status.logged_in, verificationUriComplete.value, verificationUri.value, userCode.value].join('|'),
  () => {
    detectDarkMode()
  }
)

watch(isDarkMode, async (value, oldValue) => {
  if (value === oldValue || status.logged_in) {
    return
  }
  if (verificationUriComplete.value || verificationUri.value || userCode.value) {
    await buildQrCodeImage()
  }
})
</script>

<style scoped>
.gy-page {
  --gy-panel-gap: 12px;
  --gy-panel-min-height: 548px;
  --gy-status-card-min-height: 168px;
  --gy-qrcode-card-min-height: 308px;
}

.gy-page {
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

.gy-topbar,
.gy-card__header,
.gy-results,
.gy-action-row {
  display: flex;
  align-items: center;
  gap: 10px;
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

.gy-topbar__sub,
.gy-stat-card__label {
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.gy-topbar__sub,
.gy-stat-card__label {
  font-size: 11px;
}

.gy-panel-row {
  margin: -6px;
  align-items: stretch;
}

.gy-panel-col {
  display: flex;
  padding: 6px;
}

.gy-panel-col > div {
  width: 100%;
}

.gy-qrcode-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 0;
}

.gy-qrcode-meta__item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.04);
}

.gy-qrcode-meta__label {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.gy-qrcode-meta__value {
  font-size: 14px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.9);
}

.gy-qrcode-meta__value--warning {
  color: rgb(var(--v-theme-warning));
}

.gy-action-btn {
  flex: 1 1 0;
  min-width: 0;
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

.gy-privacy-btn {
  min-width: 24px;
  width: 24px;
  height: 24px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.gy-left-col {
  display: flex;
  flex-direction: column;
  gap: var(--gy-panel-gap);
  height: 100%;
  min-height: var(--gy-panel-min-height);
}

.gy-right-col {
  display: flex;
  flex-direction: column;
  gap: var(--gy-panel-gap);
  height: 100%;
  min-height: var(--gy-panel-min-height);
}

.gy-results--summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.gy-stat-card {
  flex: 1;
  min-width: 0;
  border-radius: 14px;
  padding: 8px 10px 7px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 2px 12px rgba(var(--v-theme-on-surface), 0.1);
}

.gy-stat-card__value {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
  text-align: center;
}

.gy-stat-card__label {
  text-align: center;
}

.gy-stat-card--primary {
  background: rgba(139, 92, 246, 0.12);
  border: 0.5px solid rgba(139, 92, 246, 0.3);
}
.gy-stat-card--primary .gy-stat-card__value { color: #8b5cf6; }

.gy-stat-card--success {
  background: rgba(16, 185, 129, 0.12);
  border: 0.5px solid rgba(16, 185, 129, 0.3);
}
.gy-stat-card--success .gy-stat-card__value { color: #10b981; }

.gy-stat-card--warning {
  background: rgba(245, 158, 11, 0.12);
  border: 0.5px solid rgba(245, 158, 11, 0.3);
}
.gy-stat-card--warning .gy-stat-card__value { color: #f59e0b; }

.gy-stat-card--info {
  background: rgba(59, 130, 246, 0.12);
  border: 0.5px solid rgba(59, 130, 246, 0.3);
}
.gy-stat-card--info .gy-stat-card__value { color: #3b82f6; }

.gy-stat-card--muted {
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.12);
}
.gy-stat-card--muted .gy-stat-card__value { color: rgba(var(--v-theme-on-surface), 0.55); }

.gy-status-note {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.22);
}

.gy-status-note__icon {
  margin-top: 1px;
  color: rgb(var(--v-theme-info));
  flex-shrink: 0;
}

.gy-status-note__content {
  min-width: 0;
}

.gy-status-note__title {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.75);
  margin-bottom: 2px;
}

.gy-status-note__text {
  font-size: 11px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.gy-qrcode-box {
  flex: 1 1 auto;
  min-height: 150px;
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.02);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
}

.gy-qrcode-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
}

.gy-qrcode-placeholder--success {
  min-height: 100%;
}

.gy-qrcode-image {
  width: 144px;
  height: 144px;
  object-fit: contain;
  border-radius: 8px;
  background: #fff;
  padding: 6px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.gy-qrcode-image--dark {
  background: #d1d5db;
  border-color: rgba(209, 213, 219, 0.55);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
}

.gy-card--qrcode {
  flex: 0 0 auto;
  min-height: var(--gy-qrcode-card-min-height);
  padding-bottom: 16px;
}

.gy-card--status {
  flex: 0 0 auto;
  min-height: var(--gy-status-card-min-height);
}

.gy-card--space {
  flex: 1 1 0;
  min-height: 0;
}

.gy-mobile-only-space {
  display: none;
}

.gy-card--user {
  flex: 1 1 0;
  min-height: 0;
}

.gy-card--space .gy-info-grid,
.gy-card--user .gy-info-grid {
  align-content: start;
}

.gy-action-row {
  gap: 8px;
  flex-wrap: wrap;
}

.gy-action-btn {
  border-radius: 8px;
}

.gy-action-btn :deep(.v-btn__prepend) {
  margin-inline-end: 0;
}

.gy-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.gy-info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 10px;
}

.gy-info-item__label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.gy-info-item__value {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gy-info-item__value--mono {
  font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
  font-size: 12px;
}

.gy-space-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
  border-radius: 10px;
}

.gy-space-text {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.65);
}

.gy-progress-bar {
  height: 8px;
  background: rgba(var(--v-theme-on-surface), 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.gy-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #3b82f6);
  border-radius: 4px;
  transition: width 0.3s ease;
}

.gy-space-percent {
  font-size: 14px;
  font-weight: 700;
  color: #3b82f6;
  text-align: right;
}

.gy-empty-note {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.65);
  background: rgba(var(--v-theme-success), 0.08);
  border: 1px dashed rgba(var(--v-theme-success), 0.24);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
}

.gy-empty-note--warning {
  background: rgba(var(--v-theme-warning), 0.08);
  border: 1px dashed rgba(var(--v-theme-warning), 0.24);
}

.gy-empty-note--muted {
  background: rgba(var(--v-theme-on-surface), 0.03);
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.12);
}

.gy-empty-state {
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

.gy-empty-state__icon {
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

.gy-empty-state__title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.7);
  letter-spacing: -0.2px;
}

.gy-empty-state__sub {
  font-size: 12px;
  line-height: 1.55;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.gy-empty-state__steps {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 6px;
}

.gy-empty-step {
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

.gy-empty-step__num {
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

.gy-empty-step__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.75);
  margin-bottom: 3px;
}

.gy-empty-step__desc {
  font-size: 11px;
  line-height: 1.45;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.gy-empty-step__arrow {
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .gy-page {
    padding: 14px;
  }

  .gy-topbar {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .gy-panel-col {
    display: block;
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

  .gy-results--summary {
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
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 2px 10px rgba(0,0,0,0.05);
    overflow-x: auto;
  }

  .gy-stat-card {
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

  .gy-stat-card__label {
    font-size: 10px;
    white-space: nowrap;
  }

  .gy-stat-card__value {
    font-size: 18px;
    letter-spacing: -0.4px;
    text-align: center;
  }

  .gy-info-grid {
    grid-template-columns: 1fr;
  }

  .gy-action-row {
    flex-direction: column;
  }

  .gy-action-btn {
    width: 100%;
  }

  .gy-qrcode-box {
    min-height: 180px;
  }

  .gy-desktop-only-space {
    display: none;
  }

  .gy-mobile-only-space {
    display: flex;
  }

  .gy-card--space .gy-empty-state__steps {
    display: none;
  }

  .gy-card--qrcode {
    min-height: auto !important;
  }

  .gy-card--status,
  .gy-card--space,
  .gy-card--user,
  .gy-left-col,
  .gy-right-col {
    min-height: auto;
    height: auto;
  }

  .gy-card--space {
    min-height: auto;
    height: auto;
  }
}
</style>
