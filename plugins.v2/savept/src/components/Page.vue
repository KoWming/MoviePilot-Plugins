<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { buildNoticeSections, pluginRequest, tokenizeNoticeText } from '../utils/savept'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  initialConfig: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['switch', 'close'])

const loading = reactive({ overview: false })
const message = reactive({ show: false, type: 'info', text: '' })
const summary = reactive({ total: 0, healthy: 0, critical: 0, closed: 0, internal: 0, external: 0, today_anniv: 0, years: 0, mp_owned: 0 })
const alerts = ref([])
const sites = ref([])
const fetchedAt = ref('')
const warning = ref('')

const noticeSections = computed(() => buildNoticeSections(alerts.value))
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

function pushMessage(text, type = 'info') {
  message.text = text
  message.type = type
  message.show = true
  scheduleMessageClose(type)
}

async function fetchOverview(showSuccess = false) {
  loading.overview = true
  try {
    const result = await pluginRequest(props.api, '/sites', { method: 'GET' })
    if (!result?.success) {
      throw new Error(result?.message || '加载页面数据失败')
    }

    const data = result.data || {}
    Object.assign(summary, data.summary || {})
    alerts.value = data.alerts || []
    sites.value = data.sites || []
    fetchedAt.value = data.fetched_at || ''
    warning.value = data.warning || ''

    if (showSuccess) {
      pushMessage('页面数据已刷新', 'success')
    }
  } catch (error) {
    pushMessage(error.message || '加载页面数据失败', 'error')
  } finally {
    loading.overview = false
  }
}

onMounted(() => {
  fetchOverview()
})

onBeforeUnmount(() => {
  clearMessageTimer()
})
</script>

<template>
  <div class="spg-page">
    <div class="spg-topbar">
      <div class="spg-topbar__left">
        <div class="spg-topbar__icon">
          <v-icon icon="mdi-heart-pulse" size="24" />
        </div>
        <div class="spg-topbar__meta">
          <div class="spg-topbar__title">PT 监护室</div>
          <div class="spg-topbar__sub">实时统计、关键公告与站点运行概览</div>
        </div>
      </div>
      <div class="spg-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="spg-btn-group elevation-0">
          <v-btn color="primary" @click="fetchOverview(true)" :loading="loading.overview" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-refresh" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">刷新</span>
          </v-btn>
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-cog" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">设置</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18" />
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <Transition name="spg-slide">
      <div v-if="message.show" class="spg-toast" :class="`spg-toast--${message.type}`">
        <v-icon :icon="message.type === 'success' ? 'mdi-check-circle' : message.type === 'error' ? 'mdi-alert-circle' : 'mdi-information'" size="18" />
        <span>{{ message.text }}</span>
        <button class="spg-toast__close" @click="message.show = false">
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </Transition>

    <div class="spg-summary">
      <div class="spg-vitals">
        <div class="spg-vital spg-vital--total">
          <div class="spg-vital__head">
            <span class="spg-vital__icon"><v-icon icon="mdi-monitor-dashboard" size="16" /></span>
            <span class="spg-vital__label">监护中</span>
          </div>
          <div class="spg-vital__value">{{ summary.total }}</div>
        </div>
        <div class="spg-vital spg-vital--healthy">
          <div class="spg-vital__head">
            <span class="spg-vital__icon"><v-icon icon="mdi-heart-pulse" size="16" /></span>
            <span class="spg-vital__label">健康站点</span>
          </div>
          <div class="spg-vital__value">{{ summary.healthy }}</div>
        </div>
        <div class="spg-vital spg-vital--critical">
          <div class="spg-vital__head">
            <span class="spg-vital__icon"><v-icon icon="mdi-alert-circle" size="16" /></span>
            <span class="spg-vital__label">病危站点</span>
          </div>
          <div class="spg-vital__value">{{ summary.critical }}</div>
        </div>
        <div class="spg-vital spg-vital--closed">
          <div class="spg-vital__head">
            <span class="spg-vital__icon"><v-icon icon="mdi-skull-outline" size="16" /></span>
            <span class="spg-vital__label">已关站</span>
          </div>
          <div class="spg-vital__value">{{ summary.closed }}</div>
        </div>
      </div>

      <div class="spg-summary-pills">
        <div class="spg-summary-pill spg-summary-pill--anniv">
          <v-icon icon="mdi-party-popper" size="15" />
          <span class="spg-summary-pill__text">今日站庆</span>
          <span class="spg-summary-pill__value">{{ summary.today_anniv }}</span>
        </div>
        <div class="spg-summary-pill spg-summary-pill--internal">
          <v-icon icon="mdi-home-city-outline" size="15" />
          <span class="spg-summary-pill__text">内站</span>
          <span class="spg-summary-pill__value">{{ summary.internal }}</span>
        </div>
        <div class="spg-summary-pill spg-summary-pill--external">
          <v-icon icon="mdi-earth" size="15" />
          <span class="spg-summary-pill__text">外站</span>
          <span class="spg-summary-pill__value">{{ summary.external }}</span>
        </div>
        <div class="spg-summary-pill spg-summary-pill--years">
          <v-icon icon="mdi-check-decagram" size="15" />
          <span class="spg-summary-pill__text">已拥有站点</span>
          <span class="spg-summary-pill__value">{{ summary.mp_owned }}</span>
        </div>
      </div>
    </div>

    <div v-if="warning" class="spg-warning">
      <v-icon icon="mdi-alert-outline" size="18" />
      <span>{{ warning }}</span>
    </div>

    <div class="spg-card spg-card--panel">
      <div class="spg-card__header">
        <span class="spg-card__title d-flex align-center">
          <v-icon icon="mdi-bullhorn-outline" size="18" color="info" class="mr-1" />
          站点公告
        </span>
        <span v-if="fetchedAt" class="spg-card__badge d-flex align-center">
          <v-icon icon="mdi-clock-outline" size="14" class="mr-1" />
          {{ fetchedAt }}
        </span>
      </div>

      <div class="spg-notices">
        <div v-for="section in noticeSections" :key="section.key" class="spg-notice-card" :class="`spg-notice-card--${section.key}`">
          <div class="spg-notice-card__title">{{ section.title }}</div>
          <div v-if="section.items.length" class="spg-notice-card__content">
            <div v-for="(item, index) in section.items" :key="`${section.key}-${index}`" class="spg-notice-card__item">
              <template v-for="(token, tokenIndex) in tokenizeNoticeText(item, sites)" :key="`${section.key}-${index}-${tokenIndex}`">
                <span v-if="token.type === 'site'" class="spg-notice-tag" :class="`spg-notice-tag--${section.key}`">{{ token.text }}</span>
                <span v-else>{{ token.text }}</span>
              </template>
            </div>
          </div>
          <div v-else class="spg-notice-card__empty">暂无公告</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.spg-page {
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

.spg-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.spg-topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.spg-topbar__meta {
  min-width: 0;
  flex: 1;
}

.spg-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.spg-topbar__icon {
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

.spg-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.spg-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spg-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.05), rgba(var(--v-theme-primary), 0.015));
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.04);
}

.spg-vitals {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.spg-vital {
  min-width: 0;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(var(--v-theme-surface), 0.84);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.06);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.spg-vital--total {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.14), rgba(59, 130, 246, 0.05));
  border-color: rgba(59, 130, 246, 0.22);
}

.spg-vital--healthy {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.14), rgba(16, 185, 129, 0.05));
  border-color: rgba(16, 185, 129, 0.22);
}

.spg-vital--critical {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.14), rgba(239, 68, 68, 0.05));
  border-color: rgba(239, 68, 68, 0.22);
}

.spg-vital--closed {
  background: linear-gradient(135deg, rgba(100, 116, 139, 0.16), rgba(100, 116, 139, 0.06));
  border-color: rgba(100, 116, 139, 0.24);
}

.spg-vital__head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.spg-vital__icon {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.spg-vital--total .spg-vital__icon {
  background: rgba(59, 130, 246, 0.14);
}

.spg-vital--healthy .spg-vital__icon {
  background: rgba(16, 185, 129, 0.14);
}

.spg-vital--critical .spg-vital__icon {
  background: rgba(239, 68, 68, 0.14);
}

.spg-vital--closed .spg-vital__icon {
  background: rgba(100, 116, 139, 0.18);
}

.spg-vital__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.spg-vital__value {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
}

.spg-vital--total .spg-vital__icon,
.spg-vital--total .spg-vital__value {
  color: #3b82f6;
}

.spg-vital--healthy .spg-vital__icon,
.spg-vital--healthy .spg-vital__value {
  color: #10b981;
}

.spg-vital--critical .spg-vital__icon,
.spg-vital--critical .spg-vital__value {
  color: #ef4444;
}

.spg-vital--closed .spg-vital__icon,
.spg-vital--closed .spg-vital__value {
  color: #64748b;
}

.spg-summary-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.spg-summary-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(var(--v-theme-surface), 0.82);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.07);
  color: rgba(var(--v-theme-on-surface), 0.64);
  font-size: 12px;
  line-height: 1;
}

.spg-summary-pill__text {
  font-weight: 500;
}

.spg-summary-pill__value {
  font-size: 13px;
  font-weight: 700;
  color: rgba(var(--v-theme-on-surface), 0.9);
}

.spg-summary-pill--anniv {
  color: #d97706;
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.16);
}

.spg-summary-pill--anniv .spg-summary-pill__value {
  color: #d97706;
}

.spg-summary-pill--internal {
  color: #2563eb;
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.16);
}

.spg-summary-pill--internal .spg-summary-pill__value {
  color: #2563eb;
}

.spg-summary-pill--external {
  color: #7c3aed;
  background: rgba(139, 92, 246, 0.08);
  border-color: rgba(139, 92, 246, 0.16);
}

.spg-summary-pill--external .spg-summary-pill__value {
  color: #7c3aed;
}

.spg-summary-pill--years {
  color: #16a34a;
  background: rgba(34, 197, 94, 0.08);
  border-color: rgba(34, 197, 94, 0.16);
}

.spg-summary-pill--years .spg-summary-pill__value {
  color: #16a34a;
}

.spg-card,
.spg-warning,
.spg-toast {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.spg-card {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.spg-card--panel {
  min-height: 240px;
}

.spg-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.spg-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.spg-card__badge {
  font-size: 11px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgba(var(--v-theme-on-surface), 0.6);
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.spg-warning,
.spg-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 0.82rem;
}

.spg-warning {
  background: rgba(245, 158, 11, 0.08);
  color: #d97706;
  border-color: rgba(245, 158, 11, 0.15);
}

.spg-toast--success {
  background: rgba(34, 197, 94, 0.08);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.15);
}

.spg-toast--error {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.15);
}

.spg-toast--info {
  background: rgba(var(--v-theme-info), 0.08);
  color: rgb(var(--v-theme-info));
  border-color: rgba(var(--v-theme-info), 0.15);
}

.spg-toast__close {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  display: flex;
  transition: opacity 0.2s ease;
}

.spg-toast__close:hover { opacity: 1; }

.spg-slide-enter-active,
.spg-slide-leave-active { transition: all 0.3s ease; }
.spg-slide-enter-from,
.spg-slide-leave-to { opacity: 0; transform: translateY(-8px); }

.spg-notices {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.spg-notice-card {
  border-radius: 14px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spg-notice-card__title {
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.spg-notice-card__content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.spg-notice-card__item {
  font-size: 0.8rem;
  line-height: 1.55;
  color: rgba(var(--v-theme-on-surface), 0.68);
}

.spg-notice-card__empty {
  font-size: 0.78rem;
  color: rgba(var(--v-theme-on-surface), 0.38);
}

.spg-notice-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  margin: 0 3px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.4;
  vertical-align: baseline;
}

.spg-notice-card--critical {
  background: rgba(239, 68, 68, 0.04);
  border-color: rgba(239, 68, 68, 0.14);
}

.spg-notice-card--critical .spg-notice-card__title,
.spg-notice-tag--critical {
  color: #ef4444;
}

.spg-notice-tag--critical { background: rgba(239, 68, 68, 0.12); }

.spg-notice-card--success {
  background: rgba(34, 197, 94, 0.04);
  border-color: rgba(34, 197, 94, 0.14);
}

.spg-notice-card--success .spg-notice-card__title,
.spg-notice-tag--success {
  color: #22c55e;
}

.spg-notice-tag--success { background: rgba(34, 197, 94, 0.12); }

.spg-notice-card--info {
  background: rgba(245, 158, 11, 0.05);
  border-color: rgba(245, 158, 11, 0.16);
}

.spg-notice-card--info .spg-notice-card__title { color: #f59e0b; }
.spg-notice-tag--info {
  background: rgba(245, 158, 11, 0.14);
  color: #d97706;
}

.spg-notice-card--error {
  background: rgba(148, 163, 184, 0.06);
  border-color: rgba(148, 163, 184, 0.16);
}

.spg-notice-card--error .spg-notice-card__title { color: rgba(var(--v-theme-on-surface), 0.58); }
.spg-notice-tag--error {
  background: rgba(148, 163, 184, 0.16);
  color: rgba(var(--v-theme-on-surface), 0.68);
}

@media (max-width: 960px) {
  .spg-vitals {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .spg-page {
    padding: 14px;
  }

  .spg-topbar {
    align-items: center;
    flex-wrap: nowrap;
  }

  .spg-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .spg-topbar__meta {
    min-width: 0;
  }

  .spg-topbar__right {
    justify-content: flex-end;
    flex-shrink: 0;
  }

  .spg-card__header {
    flex-direction: row;
    align-items: center;
  }

  .spg-card__title {
    min-width: 0;
  }

  .spg-card__badge {
    margin-left: auto;
  }

  .spg-summary {
    padding: 14px;
  }

  .spg-notices {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .spg-vitals {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .spg-summary-pills {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .spg-summary-pill {
    width: auto;
    min-width: 0;
    min-height: 0;
    padding: 8px 4px;
    border-radius: 12px;
    flex-direction: column;
    justify-content: center;
    gap: 4px;
    text-align: center;
  }

  .spg-summary-pill .v-icon {
    display: none;
  }

  .spg-summary-pill__text {
    font-size: 11px;
    line-height: 1.1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .spg-summary-pill__value {
    font-size: 14px;
    line-height: 1;
  }
}
</style>
