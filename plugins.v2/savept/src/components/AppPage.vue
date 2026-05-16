<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { buildNoticeSections, buildSiteKeywords, getMpStatusMeta, getStatusMeta, pluginRequest, tokenizeNoticeText } from '../utils/savept'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  navKey: { type: String, default: 'main' },
  pluginId: { type: String, default: '' },
})
const emit = defineEmits([])

const loading = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })
const summary = reactive({ total: 0, healthy: 0, critical: 0, closed: 0, internal: 0, external: 0, today_anniv: 0, years: 0, mp_owned: 0, mp_available: 0, mp_unsupported: 0 })
const alerts = ref([])
const sites = ref([])
const yearGroups = ref([])
const fetchedAt = ref('')
const warning = ref('')
const showBackToTop = ref(false)
const backTopStyle = ref({})

const statusOptions = [
  { label: '全部', value: '全部' },
  { label: '健康', value: '健康' },
  { label: '病危', value: '病危' },
  { label: '死亡', value: '死亡' },
]
const typeOptions = [
  { label: '全部', value: '全部' },
  { label: '内站', value: '内站' },
  { label: '外站', value: '外站' },
]
const mpFilterOptions = [
  { label: '全部', value: '全部' },
  { label: '已拥有', value: 'owned' },
  { label: '可添加', value: 'available' },
  { label: '未收录', value: 'unsupported' },
]

const filters = reactive({
  keyword: '',
  year: '全部',
  mpStatus: '全部',
  status: '全部',
  type: '全部',
  anniversaryOnly: false,
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

function pushMessage(text, type = 'info') {
  message.text = text
  message.type = type
  message.show = true
  scheduleMessageClose(type)
}

async function loadData(showSuccess = false) {
  loading.value = true
  try {
    const result = await pluginRequest(props.api, '/sites', { method: 'GET' })
    if (!result?.success) {
      throw new Error(result?.message || '加载站点数据失败')
    }
    const data = result.data || {}
    Object.assign(summary, data.summary || {})
    alerts.value = data.alerts || []
    sites.value = data.sites || []
    yearGroups.value = data.year_groups || []
    fetchedAt.value = data.fetched_at || ''
    warning.value = data.warning || ''
    if (data.default_internal_only) {
      filters.type = '内站'
    }
    if (showSuccess) {
      pushMessage('数据已刷新', 'success')
    }
  } catch (error) {
    pushMessage(error.message || '加载站点数据失败', 'error')
  } finally {
    loading.value = false
  }
}

async function refreshData() {
  loading.value = true
  try {
    const result = await pluginRequest(props.api, '/refresh', { method: 'POST', body: {} })
    if (!result?.success) {
      throw new Error(result?.message || '刷新失败')
    }
    const data = result.data || {}
    Object.assign(summary, data.summary || {})
    alerts.value = data.alerts || []
    sites.value = data.sites || []
    yearGroups.value = data.year_groups || []
    fetchedAt.value = data.fetched_at || ''
    warning.value = data.warning || ''
    pushMessage(result.message || '刷新成功', 'success')
  } catch (error) {
    pushMessage(error.message || '刷新失败', 'error')
  } finally {
    loading.value = false
  }
}

const anniversarySites = computed(() => {
  return sites.value.filter(site => site.anniversary_flag === 'yes' && site.status !== 'closed')
})

const noticeSections = computed(() => buildNoticeSections(alerts.value))

const yearOptions = computed(() => {
  const years = Array.from(new Set(yearGroups.value.map(item => item.year)))
  const hasUnknownYear = sites.value.some(site => !site.year || site.year === '0000')
  if (hasUnknownYear && !years.includes('0000')) {
    years.push('0000')
  }
  return ['全部', ...years]
})

const yearMenuOpen = ref(false)
const yearMenuRef = ref(null)
const mpStatusMenuOpen = ref(false)
const mpStatusMenuRef = ref(null)
const rootRef = ref(null)
let scrollTarget = null
let restoreScrollTargetPosition = ''

const filteredSites = computed(() => {
  return sites.value.filter(site => {
    if (filters.keyword) {
      const keywords = buildSiteKeywords(site)
      if (!keywords.includes(filters.keyword.trim().toLowerCase())) {
        return false
      }
    }
    if (filters.year !== '全部' && site.year !== filters.year) {
      return false
    }
    if (filters.mpStatus !== '全部') {
      const status = site.mp_status || 'unsupported'
      if (status !== filters.mpStatus) {
        return false
      }
    }
    if (filters.status !== '全部') {
      const label = getStatusMeta(site.status).label
      if (label !== filters.status) {
        return false
      }
    }
    if (filters.type !== '全部' && site.site_type !== filters.type) {
      return false
    }
    if (filters.anniversaryOnly && !(site.anniversary_flag === 'yes' && site.status !== 'closed')) {
      return false
    }
    return true
  })
})

const groupedSites = computed(() => {
  const groups = new Map()
  for (const site of filteredSites.value) {
    if (!groups.has(site.year)) {
      groups.set(site.year, [])
    }
    groups.get(site.year).push(site)
  }
  return Array.from(groups.entries()).map(([year, items]) => ({ year, items }))
})

const collapsedYears = reactive({})

function isYearGroupCollapsed(year) {
  return !!collapsedYears[year]
}

function toggleYearGroup(year) {
  collapsedYears[year] = !collapsedYears[year]
}

function toggleYearMenu() {
  yearMenuOpen.value = !yearMenuOpen.value
}

function selectYear(year) {
  filters.year = year
  yearMenuOpen.value = false
}

function mpStatusOptionLabel(value) {
  const option = mpFilterOptions.find(item => item.value === value)
  return option ? option.label : '全部'
}

function toggleMpStatusMenu() {
  mpStatusMenuOpen.value = !mpStatusMenuOpen.value
}

function selectMpStatus(value) {
  filters.mpStatus = value
  mpStatusMenuOpen.value = false
}

function handleDocumentClick(event) {
  if (!yearMenuRef.value?.contains(event.target)) {
    yearMenuOpen.value = false
  }
  if (!mpStatusMenuRef.value?.contains(event.target)) {
    mpStatusMenuOpen.value = false
  }
}

function findScrollParent(element) {
  let current = element?.parentElement
  while (current) {
    const style = window.getComputedStyle(current)
    const overflowY = style.overflowY
    if ((overflowY === 'auto' || overflowY === 'scroll') && current.scrollHeight > current.clientHeight) {
      return current
    }
    current = current.parentElement
  }
  return window
}

function handleScroll() {
  const scrollTop = scrollTarget === window
    ? window.scrollY || document.documentElement.scrollTop || document.body.scrollTop || 0
    : scrollTarget?.scrollTop || 0
  showBackToTop.value = scrollTop > 10

  if (scrollTarget && scrollTarget !== window) {
    const rect = scrollTarget.getBoundingClientRect()
    const rightInset = Math.max(window.innerWidth - rect.right, 0) + 24
    const bottomInset = Math.max(window.innerHeight - rect.bottom, 0) + 24
    backTopStyle.value = {
      right: `${rightInset}px`,
      bottom: `${bottomInset}px`,
    }
  } else {
    backTopStyle.value = {
      right: '24px',
      bottom: '24px',
    }
  }
}

function scrollToTop() {
  if (scrollTarget === window) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    return
  }
  scrollTarget?.scrollTo({ top: 0, behavior: 'smooth' })
}

function formatYearLabel(year) {
  if (!year || year === '0000') {
    return '未知'
  }
  return year
}

function isUnknownYear(year) {
  return formatYearLabel(year) === '未知'
}

function yearOptionLabel(year) {
  if (year === '全部') {
    return '全部年份'
  }
  return isUnknownYear(year) ? '未知年份' : `${formatYearLabel(year)} 年`
}

function statusMeta(site) {
  return getStatusMeta(site.status)
}

function mpStatusMeta(site) {
  return getMpStatusMeta(site.mp_status)
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  scrollTarget = findScrollParent(rootRef.value)
  if (scrollTarget !== window && scrollTarget) {
    restoreScrollTargetPosition = scrollTarget.style.position || ''
    const computedPosition = window.getComputedStyle(scrollTarget).position
    if (!computedPosition || computedPosition === 'static') {
      scrollTarget.style.position = 'relative'
    }
  }
  window.addEventListener('resize', handleScroll, { passive: true })
  if (scrollTarget === window) {
    window.addEventListener('scroll', handleScroll, { passive: true })
  } else {
    scrollTarget?.addEventListener('scroll', handleScroll, { passive: true })
  }
  handleScroll()
  loadData()
})

onBeforeUnmount(() => {
  clearMessageTimer()
  document.removeEventListener('click', handleDocumentClick)
  window.removeEventListener('resize', handleScroll)
  if (scrollTarget === window) {
    window.removeEventListener('scroll', handleScroll)
  } else {
    scrollTarget?.removeEventListener('scroll', handleScroll)
    if (scrollTarget && restoreScrollTargetPosition !== undefined) {
      scrollTarget.style.position = restoreScrollTargetPosition
    }
  }
})
</script>

<template>
  <div ref="rootRef" class="spt-root">
    <!-- ═══ 融合头部：品牌 + 统计 + 筛选 ═══ -->
    <div class="spt-header">
      <!-- 上半：品牌 + 统计 + 操作 -->
      <div class="spt-header__top">
        <div class="spt-header__brand">
          <div class="spt-pulse-icon">
            <v-icon icon="mdi-heart-pulse" size="22" />
          </div>
          <div>
            <h1 class="spt-header__title">PT 监护室</h1>
            <p class="spt-header__desc">站点运行状态实时监护</p>
          </div>
        </div>

        <div class="spt-vitals">
          <div class="spt-vital spt-vital--total">
            <span class="spt-vital__value">{{ summary.total }}</span>
            <span class="spt-vital__label">监护中</span>
          </div>
          <div class="spt-vital__divider" />
          <div class="spt-vital spt-vital--healthy">
            <span class="spt-vital__value">{{ summary.healthy }}</span>
            <span class="spt-vital__label">健康</span>
          </div>
          <div class="spt-vital__divider" />
          <div class="spt-vital spt-vital--owned">
            <span class="spt-vital__value">{{ summary.mp_owned }}</span>
            <span class="spt-vital__label">已拥有</span>
          </div>
          <div class="spt-vital__divider" />
          <div class="spt-vital spt-vital--critical">
            <span class="spt-vital__value">{{ summary.critical }}</span>
            <span class="spt-vital__label">病危</span>
          </div>
          <div class="spt-vital__divider" />
          <div class="spt-vital spt-vital--closed">
            <span class="spt-vital__value">{{ summary.closed }}</span>
            <span class="spt-vital__label">已关站</span>
          </div>
          <div class="spt-vital__divider" />
          <div class="spt-vital spt-vital--anniv">
            <span class="spt-vital__value">{{ summary.today_anniv }}</span>
            <span class="spt-vital__label">站庆</span>
          </div>
        </div>

        <div class="spt-header__actions">
          <span class="spt-meta-pill">
            <v-icon icon="mdi-web" size="14" />
            {{ summary.internal }}/{{ summary.external }} 内外站
          </span>
          <button class="spt-refresh-btn" @click="refreshData" :disabled="loading">
            <v-progress-circular v-if="loading" size="16" width="2" indeterminate color="inherit" />
            <v-icon v-else icon="mdi-refresh" size="18" />
            <span>刷新数据</span>
          </button>
        </div>
      </div>

      <!-- 下半：筛选栏 -->
      <div class="spt-header__filters">
        <div class="spt-filters__search">
          <v-icon icon="mdi-magnify" size="18" class="spt-filters__search-icon" />
          <input
            v-model="filters.keyword"
            type="text"
            placeholder="搜索站点名称..."
            class="spt-filters__input"
          />
          <button v-if="filters.keyword" class="spt-filters__clear" @click="filters.keyword = ''">
            <v-icon icon="mdi-close-circle" size="16" />
          </button>
        </div>

        <div class="spt-filters__divider" />

        <div class="spt-filters__group spt-year-select" ref="yearMenuRef">
          <button class="spt-filters__select-btn" :class="{ 'spt-filters__select-btn--open': yearMenuOpen }" @click.stop="toggleYearMenu">
            <v-icon icon="mdi-calendar" size="16" class="spt-filters__group-icon" />
            <span class="spt-filters__select-label">{{ yearOptionLabel(filters.year) }}</span>
            <v-icon icon="mdi-chevron-down" size="16" class="spt-filters__select-chevron" :class="{ 'spt-filters__select-chevron--open': yearMenuOpen }" />
          </button>

          <div v-if="yearMenuOpen" class="spt-filters__dropdown">
            <button
              v-for="y in yearOptions"
              :key="y"
              class="spt-filters__dropdown-item"
              :class="{ 'spt-filters__dropdown-item--active': filters.year === y }"
              @click.stop="selectYear(y)"
            >
              {{ yearOptionLabel(y) }}
            </button>
          </div>
        </div>

        <div class="spt-filters__divider" />

        <div class="spt-filters__group spt-year-select" ref="mpStatusMenuRef">
          <button class="spt-filters__select-btn" :class="{ 'spt-filters__select-btn--open': mpStatusMenuOpen }" @click.stop="toggleMpStatusMenu">
            <v-icon icon="mdi-check-decagram" size="16" class="spt-filters__group-icon" />
            <span class="spt-filters__select-label">{{ mpStatusOptionLabel(filters.mpStatus) }}</span>
            <v-icon icon="mdi-chevron-down" size="16" class="spt-filters__select-chevron" :class="{ 'spt-filters__select-chevron--open': mpStatusMenuOpen }" />
          </button>

          <div v-if="mpStatusMenuOpen" class="spt-filters__dropdown">
            <button
              v-for="opt in mpFilterOptions"
              :key="opt.value"
              class="spt-filters__dropdown-item"
              :class="{ 'spt-filters__dropdown-item--active': filters.mpStatus === opt.value }"
              @click.stop="selectMpStatus(opt.value)"
            >
              {{ mpStatusOptionLabel(opt.value) }}
            </button>
          </div>
        </div>

        <div class="spt-filters__divider" />

        <div class="spt-filters__pills">
          <button
            v-for="opt in statusOptions"
            :key="opt.value"
            class="spt-pill"
            :class="{
              'spt-pill--active': filters.status === opt.value,
              'spt-pill--healthy': filters.status === '健康' && opt.value === '健康',
              'spt-pill--critical': filters.status === '病危' && opt.value === '病危',
              'spt-pill--closed': filters.status === '死亡' && opt.value === '死亡',
            }"
            @click="filters.status = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>

        <div class="spt-filters__divider" />

        <div class="spt-filters__pills">
          <button
            v-for="opt in typeOptions"
            :key="opt.value"
            class="spt-pill"
            :class="{ 'spt-pill--active': filters.type === opt.value }"
            @click="filters.type = opt.value"
          >
            {{ opt.label }}
          </button>

          <button
            class="spt-pill spt-pill--anniv-toggle"
            :class="{ 'spt-pill--anniv-active': filters.anniversaryOnly }"
            @click="filters.anniversaryOnly = !filters.anniversaryOnly"
          >
            <v-icon icon="mdi-party-popper" size="14" />
            近期站庆
          </button>
        </div>

        <div class="spt-filters__spacer" />

        <div class="spt-filters__meta">
          <span v-if="fetchedAt" class="spt-filters__meta-time">
            <v-icon icon="mdi-clock-outline" size="14" />
            {{ fetchedAt }}
          </span>
          <span class="spt-filters__meta-count">
            显示 <b>{{ filteredSites.length }}</b> / {{ sites.length }} 个站点
          </span>
        </div>
      </div>
    </div>

    <div class="spt-notices">
      <div v-for="section in noticeSections" :key="section.key" class="spt-notice-card" :class="`spt-notice-card--${section.key}`">
        <div class="spt-notice-card__title">{{ section.title }}</div>
        <div v-if="section.items.length" class="spt-notice-card__content">
          <div v-for="(item, index) in section.items" :key="`${section.key}-${index}`" class="spt-notice-card__item">
            <template v-for="(token, tokenIndex) in tokenizeNoticeText(item, sites)" :key="`${section.key}-${index}-${tokenIndex}`">
              <span v-if="token.type === 'site'" class="spt-notice-tag" :class="`spt-notice-tag--${section.key}`">{{ token.text }}</span>
              <span v-else>{{ token.text }}</span>
            </template>
          </div>
        </div>
        <div v-else class="spt-notice-card__empty">暂无公告</div>
      </div>
    </div>

    <!-- ═══ 消息 & 告警 ═══ -->
    <Transition name="spt-slide">
      <div v-if="message.show" class="spt-toast" :class="`spt-toast--${message.type}`">
        <v-icon :icon="message.type === 'success' ? 'mdi-check-circle' : message.type === 'error' ? 'mdi-alert-circle' : 'mdi-information'" size="18" />
        <span>{{ message.text }}</span>
        <button class="spt-toast__close" @click="message.show = false">
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </Transition>

    <div v-if="warning" class="spt-warning">
      <v-icon icon="mdi-alert-outline" size="18" />
      <span>{{ warning }}</span>
    </div>

    <!-- ═══ 站点列表（年份分组） ═══ -->
    <div v-for="group in groupedSites" :key="group.year" class="spt-year-group">
      <div class="spt-year-group__header">
        <button
          type="button"
          class="spt-year-group__toggle"
          :class="{ 'spt-year-group__toggle--collapsed': isYearGroupCollapsed(group.year) }"
          @click="toggleYearGroup(group.year)"
        >
          <div class="spt-year-group__badge">{{ formatYearLabel(group.year) }}</div>
          <span class="spt-year-group__suffix">{{ isUnknownYear(group.year) ? '年份建站' : '年建站' }}</span>
          <span class="spt-year-group__count">{{ group.items.length }} 个站点</span>
        </button>

        <button
          type="button"
          class="spt-year-group__chevron-btn"
          :class="{ 'spt-year-group__chevron-btn--collapsed': isYearGroupCollapsed(group.year) }"
          @click="toggleYearGroup(group.year)"
          :aria-label="isYearGroupCollapsed(group.year) ? `展开 ${formatYearLabel(group.year)} 年分组` : `收起 ${formatYearLabel(group.year)} 年分组`"
        >
          <v-icon
            class="spt-year-group__chevron"
            :class="{ 'spt-year-group__chevron--collapsed': isYearGroupCollapsed(group.year) }"
            icon="mdi-chevron-down"
            size="18"
          />
        </button>
      </div>

      <div v-show="!isYearGroupCollapsed(group.year)" class="spt-grid">
        <a
          v-for="site in group.items"
          :key="`${group.year}-${site.name}`"
          :href="site.url"
          target="_blank"
          rel="noreferrer noopener"
          class="spt-card"
          :class="`spt-card--${site.status || 'unknown'}`"
        >
          <div class="spt-card__body">
            <!-- 顶部标签行 -->
            <div class="spt-card__badges">
              <div class="spt-card__badges-left">
                <span class="spt-tag spt-tag--type">{{ site.site_type }}</span>
                <span v-if="site.duration_text" class="spt-tag spt-tag--duration">
                  <v-icon icon="mdi-clock-fast" size="12" />
                  {{ site.duration_text }}
                </span>
                <span v-if="site.anniversary_text" class="spt-tag spt-tag--anniversary">
                  <v-icon icon="mdi-party-popper" size="12" />
                  {{ site.anniversary_text }}
                </span>
              </div>
            </div>

            <!-- 主内容 -->
            <div class="spt-card__main">
              <img class="spt-card__icon" :src="site.icon" :alt="site.name" loading="lazy" />
              <div class="spt-card__info">
                <div class="spt-card__name-row">
                  <span class="spt-card__name-dot" :style="{ backgroundColor: statusMeta(site).color }" />
                  <div class="spt-card__name">{{ site.name }}</div>
                </div>
                <div class="spt-card__sub">开站 {{ site.open_time || '未知' }}<template v-if="site.close_time && site.close_time !== '未知'"> · 关站 {{ site.close_time }}</template></div>
                <div v-if="site.mp_status || site.mp_site_name || site.mp_site_domain" class="spt-card__sub spt-card__sub--mp">
                  <span v-if="site.mp_site_name || site.mp_site_domain" class="spt-card__mp-text">
                    <span>{{ site.mp_site_name || site.name }}</span>
                    <template v-if="site.mp_site_domain"> · {{ site.mp_site_domain }}</template>
                  </span>
                  <span v-if="site.mp_status" class="spt-tag spt-tag--mp" :class="`spt-tag--mp-${mpStatusMeta(site).chipClass}`">
                    <v-icon :icon="mpStatusMeta(site).icon" size="12" />
                    {{ site.mp_status_text || mpStatusMeta(site).label }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- 状态图标（卡片右侧） -->
          <div v-if="statusMeta(site).icon" class="spt-card__status-icon" :style="{ color: statusMeta(site).color }">
            <v-icon :icon="statusMeta(site).icon" size="18" />
          </div>
        </a>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="!loading && filteredSites.length === 0" class="spt-empty">
      <v-icon icon="mdi-monitor-eye" size="48" color="grey-lighten-1" />
      <p>没有匹配的站点</p>
      <button class="spt-pill" @click="Object.assign(filters, { keyword: '', year: '全部', mpStatus: '全部', status: '全部', type: '全部', anniversaryOnly: false })">
        清除筛选
      </button>
    </div>

    <Teleport to="body">
      <Transition name="spt-fab">
        <button v-if="showBackToTop" class="spt-back-top" :style="backTopStyle" @click="scrollToTop" aria-label="返回顶部">
          <v-icon icon="mdi-chevron-up" size="20" />
        </button>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════
   PT 监护室 — 自定义设计 v2
   ═══════════════════════════════════════════ */

.spt-root {
  --spt-radius: 10px;
  --spt-radius-sm: 6px;
  --spt-radius-pill: 999px;
  --spt-gap: 14px;
  --spt-gap-sm: 10px;
  --spt-color-healthy: #22c55e;
  --spt-color-critical: #ef4444;
  --spt-color-closed: #94a3b8;
  --spt-color-anniv: #f59e0b;
  --spt-color-info: #3b82f6;
  --spt-transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);

  display: flex;
  flex-direction: column;
  gap: var(--spt-gap);
}

/* ═══ 融合头部卡片 ═══ */
.spt-header {
  border-radius: var(--spt-radius);
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.06), rgba(var(--v-theme-primary), 0.02));
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  overflow: visible;
}

.spt-header__top {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 18px;
  flex-wrap: wrap;
}

/* 品牌 */
.spt-header__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.spt-pulse-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.12);
  position: relative;
}

.spt-pulse-icon::after {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 14px;
  border: 2px solid rgba(var(--v-theme-primary), 0.25);
  animation: spt-pulse 2s ease-in-out infinite;
}

@keyframes spt-pulse {
  0%, 100% { opacity: 0; transform: scale(0.95); }
  50% { opacity: 1; transform: scale(1.05); }
}

.spt-header__title {
  font-size: 1.05rem;
  font-weight: 700;
  color: rgb(var(--v-theme-on-surface));
  margin: 0;
  letter-spacing: -0.01em;
}

.spt-header__desc {
  font-size: 0.78rem;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin: 2px 0 0;
}

/* 生命体征 */
.spt-vitals {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
  min-width: 0;
}

.spt-vital {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 0 16px;
}

.spt-vital__value {
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1;
}

.spt-vital__label {
  font-size: 0.7rem;
  color: rgba(var(--v-theme-on-surface), 0.45);
  white-space: nowrap;
}

.spt-vital--total .spt-vital__value { color: rgb(var(--v-theme-primary)); }
.spt-vital--healthy .spt-vital__value { color: var(--spt-color-healthy); }
.spt-vital--owned .spt-vital__value { color: #16a34a; }
.spt-vital--critical .spt-vital__value { color: var(--spt-color-critical); }
.spt-vital--closed .spt-vital__value { color: var(--spt-color-closed); }
.spt-vital--anniv .spt-vital__value { color: var(--spt-color-anniv); }

.spt-vital__divider {
  width: 1px;
  height: 28px;
  background: rgba(var(--v-border-color), var(--v-border-opacity));
  flex-shrink: 0;
}

/* 头部右侧操作 */
.spt-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.spt-meta-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 32px;
  padding: 5px 10px;
  border-radius: var(--spt-radius-pill);
  background: rgba(var(--v-theme-on-surface), 0.05);
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.5);
  white-space: nowrap;
  box-sizing: border-box;
}

.spt-refresh-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 32px;
  padding: 5px 14px;
  border-radius: var(--spt-radius-pill);
  border: 1px solid rgba(var(--v-theme-primary), 0.3);
  background: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-primary));
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--spt-transition);
  white-space: nowrap;
}

.spt-refresh-btn:hover:not(:disabled) {
  background: rgba(var(--v-theme-primary), 0.16);
  border-color: rgba(var(--v-theme-primary), 0.5);
}

.spt-refresh-btn:disabled { opacity: 0.6; cursor: wait; }

/* ═══ 筛选栏（头部内嵌） ═══ */
.spt-header__filters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px 14px;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  flex-wrap: wrap;
}

/* 搜索框 */
.spt-filters__search {
  display: flex;
  align-items: center;
  position: relative;
  flex-shrink: 0;
}

.spt-filters__search-icon {
  position: absolute;
  left: 10px;
  color: rgba(var(--v-theme-on-surface), 0.35);
  pointer-events: none;
}

.spt-filters__input {
  min-height: 32px;
  padding: 5px 32px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: var(--spt-radius-pill);
  background: rgba(var(--v-theme-on-surface), 0.03);
  font-size: 0.82rem;
  color: rgb(var(--v-theme-on-surface));
  outline: none;
  width: 180px;
  transition: all var(--spt-transition);
  box-sizing: border-box;
}

.spt-filters__input::placeholder { color: rgba(var(--v-theme-on-surface), 0.35); }
.spt-filters__input:focus {
  border-color: rgba(var(--v-theme-primary), 0.4);
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.08);
}

.spt-filters__clear {
  position: absolute;
  right: 4px;
  background: none;
  border: none;
  cursor: pointer;
  color: rgba(var(--v-theme-on-surface), 0.35);
  padding: 2px;
  display: flex;
  align-items: center;
  transition: color var(--spt-transition);
}
.spt-filters__clear:hover { color: rgba(var(--v-theme-on-surface), 0.7); }

/* 分割线 */
.spt-filters__divider {
  width: 1px;
  height: 24px;
  background: rgba(var(--v-border-color), var(--v-border-opacity));
  flex-shrink: 0;
}

/* 年份选择器 */
.spt-filters__group {
  display: flex;
  align-items: center;
  position: relative;
  flex-shrink: 0;
}

.spt-year-select {
  position: relative;
}

.spt-filters__group-icon {
  position: absolute;
  left: 10px;
  color: rgba(var(--v-theme-on-surface), 0.35);
  pointer-events: none;
  z-index: 1;
}

.spt-filters__select-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 118px;
  min-height: 32px;
  padding: 5px 34px 5px 34px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: var(--spt-radius-pill);
  background: rgba(var(--v-theme-on-surface), 0.03);
  font-size: 0.82rem;
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  outline: none;
  transition: all var(--spt-transition);
  box-sizing: border-box;
  white-space: nowrap;
  text-align: center;
}

.spt-filters__select-label {
  display: block;
  width: 100%;
  text-align: center;
}

.spt-filters__select-btn:hover,
.spt-filters__select-btn--open {
  border-color: rgba(var(--v-theme-primary), 0.4);
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 0 0 3px rgba(var(--v-theme-primary), 0.08);
}

.spt-filters__select-chevron {
  position: absolute;
  right: 10px;
  color: rgba(var(--v-theme-on-surface), 0.35);
  transition: transform var(--spt-transition);
}

.spt-filters__select-chevron--open {
  transform: rotate(180deg);
}

.spt-filters__dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 100%;
  max-height: 240px;
  padding: 6px;
  border-radius: 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
  box-shadow: 0 10px 30px rgba(var(--v-theme-on-surface), 0.12);
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
  z-index: 200;
  scrollbar-width: thin;
  scrollbar-color: rgba(var(--v-theme-on-surface), 0.22) transparent;
}

.spt-filters__dropdown::-webkit-scrollbar {
  width: 6px;
}

.spt-filters__dropdown::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.18);
}

.spt-filters__dropdown::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-on-surface), 0.28);
}

.spt-filters__dropdown-item {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 32px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: rgba(var(--v-theme-on-surface), 0.68);
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
  transition: all var(--spt-transition);
}

.spt-filters__dropdown-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
  color: rgba(var(--v-theme-on-surface), 0.92);
}

.spt-filters__dropdown-item--active {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
}

/* 胶囊按钮组 */
.spt-filters__pills {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.spt-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 32px;
  padding: 5px 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: var(--spt-radius-pill);
  background: transparent;
  color: rgba(var(--v-theme-on-surface), 0.6);
  font-size: 0.78rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--spt-transition);
  white-space: nowrap;
  line-height: 1.4;
  box-sizing: border-box;
}

.spt-pill:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.spt-pill--active {
  background: rgba(var(--v-theme-primary), 0.1);
  color: rgb(var(--v-theme-primary));
  border-color: rgba(var(--v-theme-primary), 0.25);
}

.spt-pill--healthy.spt-pill--active {
  background: rgba(34, 197, 94, 0.1);
  color: var(--spt-color-healthy);
  border-color: rgba(34, 197, 94, 0.25);
}

.spt-pill--critical.spt-pill--active {
  background: rgba(239, 68, 68, 0.1);
  color: var(--spt-color-critical);
  border-color: rgba(239, 68, 68, 0.25);
}

.spt-pill--closed.spt-pill--active {
  background: rgba(148, 163, 184, 0.1);
  color: var(--spt-color-closed);
  border-color: rgba(148, 163, 184, 0.25);
}

.spt-pill--anniv-toggle { border-style: dashed; }

.spt-pill--anniv-active {
  background: rgba(245, 158, 11, 0.1);
  color: var(--spt-color-anniv);
  border-color: rgba(245, 158, 11, 0.3);
  border-style: solid;
}

.spt-filters__spacer { flex: 1; min-width: 8px; }

.spt-filters__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  margin-left: auto;
  font-size: 0.78rem;
  color: rgba(var(--v-theme-on-surface), 0.45);
  white-space: nowrap;
}

.spt-filters__meta-count b {
  color: rgba(var(--v-theme-on-surface), 0.7);
  font-weight: 600;
}

.spt-filters__meta-time {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: rgba(var(--v-theme-on-surface), 0.4);
}

/* ═══ 公告区域 ═══ */
.spt-notices {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spt-gap-sm);
}

.spt-notice-card {
  border-radius: var(--spt-radius);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgb(var(--v-theme-surface));
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.spt-notice-card__title {
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.spt-notice-card__content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.spt-notice-card__item {
  font-size: 0.8rem;
  line-height: 1.55;
  color: rgba(var(--v-theme-on-surface), 0.68);
}

.spt-notice-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  margin: 0 3px;
  border-radius: var(--spt-radius-pill);
  font-size: 0.72rem;
  font-weight: 600;
  line-height: 1.4;
  vertical-align: baseline;
}

.spt-notice-tag--critical {
  background: rgba(239, 68, 68, 0.12);
  color: var(--spt-color-critical);
}

.spt-notice-tag--success {
  background: rgba(34, 197, 94, 0.12);
  color: var(--spt-color-healthy);
}

.spt-notice-tag--info {
  background: rgba(245, 158, 11, 0.14);
  color: #d97706;
}

.spt-notice-tag--error {
  background: rgba(148, 163, 184, 0.16);
  color: rgba(var(--v-theme-on-surface), 0.68);
}

.spt-notice-card__empty {
  font-size: 0.78rem;
  color: rgba(var(--v-theme-on-surface), 0.38);
}

.spt-notice-card--critical {
  background: rgba(239, 68, 68, 0.04);
  border-color: rgba(239, 68, 68, 0.14);
}
.spt-notice-card--critical .spt-notice-card__title {
  color: var(--spt-color-critical);
}

.spt-notice-card--success {
  background: rgba(34, 197, 94, 0.04);
  border-color: rgba(34, 197, 94, 0.14);
}
.spt-notice-card--success .spt-notice-card__title {
  color: var(--spt-color-healthy);
}

.spt-notice-card--info {
  background: rgba(245, 158, 11, 0.05);
  border-color: rgba(245, 158, 11, 0.16);
}
.spt-notice-card--info .spt-notice-card__title {
  color: var(--spt-color-anniv);
}

.spt-notice-card--error {
  background: rgba(148, 163, 184, 0.06);
  border-color: rgba(148, 163, 184, 0.16);
}
.spt-notice-card--error .spt-notice-card__title {
  color: rgba(var(--v-theme-on-surface), 0.58);
}

/* ═══ Toast ═══ */
.spt-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--spt-radius-sm);
  font-size: 0.82rem;
}

.spt-toast--success {
  background: rgba(34, 197, 94, 0.08);
  color: var(--spt-color-healthy);
  border: 1px solid rgba(34, 197, 94, 0.15);
}

.spt-toast--error {
  background: rgba(239, 68, 68, 0.08);
  color: var(--spt-color-critical);
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.spt-toast--info {
  background: rgba(var(--v-theme-info), 0.08);
  color: rgb(var(--v-theme-info));
  border: 1px solid rgba(var(--v-theme-info), 0.15);
}

.spt-toast__close {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  display: flex;
  transition: opacity var(--spt-transition);
}
.spt-toast__close:hover { opacity: 1; }

.spt-slide-enter-active, .spt-slide-leave-active { transition: all 0.3s ease; }
.spt-slide-enter-from, .spt-slide-leave-to { opacity: 0; transform: translateY(-8px); }

/* 警告 */
.spt-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: var(--spt-radius-sm);
  background: rgba(245, 158, 11, 0.08);
  color: var(--spt-color-anniv);
  border: 1px solid rgba(245, 158, 11, 0.15);
  font-size: 0.82rem;
}

/* ═══ 年份分组 ═══ */
.spt-year-group {
  display: flex;
  flex-direction: column;
  gap: var(--spt-gap-sm);
}

.spt-year-group__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  width: 100%;
}

.spt-year-group__toggle,
.spt-year-group__chevron-btn {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 0;
  margin: 0;
}

.spt-year-group__toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-align: left;
}

.spt-year-group__toggle:hover .spt-year-group__badge,
.spt-year-group__toggle:focus-visible .spt-year-group__badge {
  background: rgba(var(--v-theme-primary), 0.12);
}

.spt-year-group__toggle:focus-visible,
.spt-year-group__chevron-btn:focus-visible {
  outline: 2px solid rgba(var(--v-theme-primary), 0.45);
  outline-offset: 4px;
  border-radius: 10px;
}

.spt-year-group__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  padding: 2px 10px;
  border-radius: var(--spt-radius-pill);
  background: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-primary));
  font-size: 0.82rem;
  font-weight: 700;
  transition: background var(--spt-transition);
}

.spt-year-group__suffix {
  font-size: 0.8rem;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.spt-year-group__count {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.4);
}

.spt-year-group__chevron-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  transition: background var(--spt-transition);
}

.spt-year-group__chevron-btn:hover,
.spt-year-group__chevron-btn:focus-visible {
  background: rgba(var(--v-theme-on-surface), 0.05);
}

.spt-year-group__chevron {
  color: rgba(var(--v-theme-on-surface), 0.35);
  transition: transform var(--spt-transition), color var(--spt-transition);
}

.spt-year-group__chevron-btn:hover .spt-year-group__chevron,
.spt-year-group__chevron-btn:focus-visible .spt-year-group__chevron {
  color: rgba(var(--v-theme-on-surface), 0.6);
}

.spt-year-group__chevron--collapsed {
  transform: rotate(-90deg);
}

/* ═══ 站点卡片网格 — 固定四列 ═══ */
.spt-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spt-gap-sm);
}

.spt-card {
  display: flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
  border-radius: var(--spt-radius);
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  overflow: hidden;
  transition: all var(--spt-transition);
  position: relative;
}

.spt-card:hover {
  border-color: rgba(var(--v-theme-on-surface), 0.18);
  box-shadow: 0 4px 16px rgba(var(--v-theme-on-surface), 0.06);
  transform: translateY(-1px);
}

.spt-card--healthy { background: rgba(34, 197, 94, 0.03); }

.spt-card--critical { background: rgba(239, 68, 68, 0.03); }

.spt-card--closed { opacity: 0.7; }
.spt-card--closed:hover { opacity: 0.88; }
.spt-card--closed .spt-card__icon {
  filter: grayscale(1) saturate(0.2);
}
.spt-card--closed .spt-tag {
  background: rgba(148, 163, 184, 0.1);
  color: var(--spt-color-closed);
}
.spt-card--closed .spt-card__status-icon {
  color: var(--spt-color-closed) !important;
}

.spt-card__body {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 标签行 */
.spt-card__badges {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 0;
  min-width: 0;
}

.spt-card__badges-left {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-wrap: wrap;
}

.spt-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  gap: 3px;
  padding: 1px 8px;
  border-radius: var(--spt-radius-pill);
  font-size: 0.68rem;
  font-weight: 500;
  white-space: nowrap;
  line-height: 1.2;
  flex-shrink: 0;
}

.spt-tag :deep(.v-icon),
.spt-tag .v-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  flex-shrink: 0;
}

.spt-tag--type {
  background: rgba(var(--v-theme-on-surface), 0.06);
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.spt-tag--mp {
  width: fit-content;
  max-width: 100%;
  padding-inline: 7px;
  font-size: 0.66rem;
}

.spt-tag--mp-owned {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.spt-tag--mp-available {
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
}

.spt-tag--mp-unsupported {
  background: rgba(148, 163, 184, 0.14);
  color: #64748b;
}

.spt-tag--duration {
  background: rgba(var(--v-theme-primary), 0.08);
  color: rgb(var(--v-theme-primary));
}

.spt-tag--anniversary {
  background: rgba(245, 158, 11, 0.1);
  color: var(--spt-color-anniv);
}

/* 主内容行 */
.spt-card__main {
  display: flex;
  align-items: center;
  gap: 10px;
}

.spt-card__icon {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: 8px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  padding: 4px;
  flex-shrink: 0;
}

.spt-card__info {
  flex: 1;
  min-width: 0;
}

.spt-card__name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.spt-card__name-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(var(--v-theme-on-surface), 0.04);
}

.spt-card__name {
  font-size: 0.88rem;
  font-weight: 600;
  color: rgb(var(--v-theme-on-surface));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.spt-card--closed .spt-card__name {
  color: rgba(var(--v-theme-on-surface), 0.62);
}

.spt-card--closed .spt-card__name-dot {
  background: var(--spt-color-closed) !important;
}

.spt-card__sub {
  font-size: 0.75rem;
  color: rgba(var(--v-theme-on-surface), 0.45);
  margin-top: 2px;
}

.spt-card__sub--mp {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  color: rgba(var(--v-theme-primary), 0.78);
}

.spt-card__mp-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
}

.spt-tag--mp {
  margin-left: auto;
}

.spt-card--closed .spt-card__sub {
  color: rgba(var(--v-theme-on-surface), 0.38);
}

/* 状态图标（卡片右侧） */
.spt-card__status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  position: static;
  width: 20px;
  height: 20px;
  min-width: 20px;
  margin-right: 10px;
  flex-shrink: 0;
  opacity: 0.9;
  transition: all var(--spt-transition);
}

.spt-card:hover .spt-card__status-icon { transform: scale(1.15); }

/* ═══ 空状态 ═══ */
.spt-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 20px;
  color: rgba(var(--v-theme-on-surface), 0.4);
  font-size: 0.9rem;
}

/* ═══ 返回顶部按钮 ═══ */

/* ═══ 响应式 ═══ */
@media (max-width: 1200px) {
  .spt-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (max-width: 900px) {
  .spt-grid { grid-template-columns: repeat(2, 1fr); }

  .spt-filters__meta {
    margin-left: 0;
    width: 100%;
    flex: 0 0 100%;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .spt-filters__meta-time {
    order: 2;
    display: inline-flex;
    align-items: center;
    gap: 3px;
    margin-left: auto;
    flex: 0 0 auto;
    text-align: right;
    white-space: nowrap;
  }

  .spt-filters__meta-count {
    order: 1;
    margin-left: 0;
    flex: 0 0 auto;
    text-align: left;
    white-space: nowrap;
  }
}

@media (max-width: 768px) {
  .spt-header__top {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    grid-template-areas:
      'brand actions'
      'vitals actions';
    align-items: center;
    gap: 12px 14px;
  }

  .spt-header__brand {
    grid-area: brand;
    min-width: 0;
  }

  .spt-header__brand > div:last-child {
    min-width: 0;
  }

  .spt-header__title,
  .spt-header__desc {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .spt-vitals {
    grid-area: vitals;
    width: 100%;
    overflow-x: hidden;
    justify-content: space-between;
  }

  .spt-vital {
    flex: 1 1 0;
    min-width: 0;
    padding: 0 8px;
  }

  .spt-vital__value {
    font-size: 1rem;
  }

  .spt-vital__label {
    font-size: 0.62rem;
  }

  .spt-vital__divider {
    height: 22px;
  }

  .spt-header__actions {
    grid-area: actions;
    display: grid;
    grid-auto-rows: min-content;
    justify-items: end;
    align-content: space-between;
    gap: 8px;
    align-self: stretch;
    min-width: max-content;
  }

  .spt-refresh-btn {
    order: 1;
  }

  .spt-meta-pill {
    order: 2;
    justify-self: end;
  }

  .spt-header__filters {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }

  .spt-filters__divider,
  .spt-filters__spacer {
    display: none;
  }

  .spt-filters__search {
    width: 100%;
    min-width: 0;
    grid-column: 1 / -1;
  }

  .spt-year-select {
    width: 100%;
    min-width: 0;
  }

  .spt-filters__group {
    min-width: 0;
  }

  .spt-filters__input,
  .spt-filters__select-btn {
    width: 100%;
  }

  .spt-filters__pills,
  .spt-filters__meta {
    grid-column: 1 / -1;
  }

  .spt-filters__pills {
    flex-wrap: wrap;
  }

  .spt-filters__meta {
    margin-left: 0;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .spt-filters__meta-time {
    order: 2;
    display: inline-flex;
    align-items: center;
    gap: 3px;
    margin-left: auto;
    flex: 0 0 auto;
    text-align: right;
    white-space: nowrap;
  }

  .spt-filters__meta-count {
    order: 1;
    margin-left: 0;
    flex: 0 0 auto;
    text-align: left;
    white-space: nowrap;
  }

  .spt-notices {
    grid-template-columns: 1fr;
  }

  .spt-grid { grid-template-columns: 1fr; }

  .spt-card {
    align-items: stretch;
  }

  .spt-card__body {
    padding: 10px 36px 10px 12px;
    gap: 6px;
  }

  .spt-card__badges {
    padding-right: 4px;
  }

  .spt-card__badges-left {
    gap: 4px;
  }

  .spt-tag {
    padding: 1px 7px;
    font-size: 0.64rem;
  }

  .spt-card__main {
    align-items: flex-start;
    gap: 8px;
  }

  .spt-card__icon {
    width: 32px;
    height: 32px;
    margin-top: 1px;
  }

  .spt-card__name {
    font-size: 0.84rem;
  }

  .spt-card__sub {
    font-size: 0.72rem;
    line-height: 1.35;
  }

  .spt-card__sub--mp {
    gap: 4px;
    margin-top: 4px;
  }

  .spt-card__mp-text {
    flex: 1 1 auto;
  }

  .spt-card__status-icon {
    position: absolute;
    top: 11px;
    right: 10px;
    width: 18px;
    height: 18px;
    min-width: 18px;
    margin-right: 0;
    opacity: 0.82;
  }
}

@media (max-width: 480px) {
  .spt-vitals {
    gap: 0;
  }

  .spt-vital {
    padding: 0 5px;
  }

  .spt-vital__value {
    font-size: 0.92rem;
  }

  .spt-vital__label {
    font-size: 0.56rem;
  }

  .spt-vital__divider {
    height: 18px;
  }

  .spt-card__body {
    padding-right: 34px;
  }

  .spt-card__name {
    font-size: 0.82rem;
  }

  .spt-card__sub {
    font-size: 0.7rem;
  }

  .spt-card__status-icon {
    top: 10px;
    right: 8px;
  }
}
</style>

<!-- 非 scoped：返回顶部按钮样式（Teleport 到外部 DOM，scoped 不生效） -->
<style>
.spt-back-top {
  position: fixed;
  right: 24px;
  bottom: 24px;
  width: 42px;
  height: 42px;
  border: none;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  opacity: 0.56;
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 9999;
}

.spt-back-top:hover,
.spt-back-top:focus-visible,
.spt-back-top:active {
  opacity: 1;
}

.spt-back-top:hover {
  transform: translateY(-2px);
}

.spt-back-top:active {
  transform: translateY(0);
}

@media (max-width: 480px) {
  .spt-back-top {
    right: 16px;
    bottom: 16px;
    width: 40px;
    height: 40px;
  }
}

.spt-fab-enter-active,
.spt-fab-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.spt-fab-enter-from,
.spt-fab-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.92);
}
</style>
