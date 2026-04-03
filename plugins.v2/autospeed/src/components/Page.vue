<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

// ── Props & Emits ──────────────────────────────────────────────────────────────
const props = defineProps({
  api: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['action', 'switch', 'close'])

// ── 状态 ───────────────────────────────────────────────────────────────────────
const status = reactive({ enabled: false, running: false, latest: null as any, last_run: null as string | null })
const latest = ref<any>(null)
const history = ref<any[]>([])
const historyTotal = ref(0)
const historyDays = ref(7)
const loading = reactive({ status: false, run: false, history: false })
const snackbar = reactive({ show: false, text: '', color: 'success' })
const chartContainer = ref<HTMLElement | null>(null)
let chartInstance: any = null
let pollingTimer: ReturnType<typeof setTimeout> | null = null

// ── 时间范围选项 ────────────────────────────────────────────────────────────────
const dayOptions = [
  { label: '7天', value: 7 },
  { label: '30天', value: 30 },
  { label: '全部', value: 0 },
]

// ── 历史列表分页 ────────────────────────────────────────────────────────────────
const page = ref(1)
const pageSize = 10
const pagedHistory = computed(() => {
  const start = (page.value - 1) * pageSize
  return [...history.value].reverse().slice(start, start + pageSize)
})
const totalPages = computed(() => Math.ceil(history.value.length / pageSize))

// ── API 调用 ───────────────────────────────────────────────────────────────────
async function fetchStatus() {
  loading.status = true
  try {
    const res = await props.api.get('plugin/AutoSpeed/status')
    Object.assign(status, res)
    if (res.latest) latest.value = res.latest
  } catch (e) {
    console.warn('fetchStatus error', e)
  } finally {
    loading.status = false
  }
}

async function fetchHistory() {
  loading.history = true
  try {
    const res = await props.api.get(`plugin/AutoSpeed/history?days=${historyDays.value}`)
    history.value = res.records || []
    historyTotal.value = res.total || 0
    page.value = 1
    await nextTick()
    renderChart()
  } catch (e) {
    console.warn('fetchHistory error', e)
  } finally {
    loading.history = false
  }
}

async function fetchLatest() {
  try {
    const res = await props.api.get('plugin/AutoSpeed/latest')
    if (res.has_data) latest.value = res.record
  } catch (e) {
    console.warn('fetchLatest error', e)
  }
}

async function runSpeedtest() {
  if (loading.run) return
  loading.run = true
  try {
    const res = await props.api.post('plugin/AutoSpeed/run', {})
    showSnack(res.msg || '测速已开始', 'success')
    // 开始轮询，等测速完成后刷新
    startPolling()
  } catch (e) {
    showSnack('触发测速失败', 'error')
  } finally {
    loading.run = false
  }
}

// ── 轮询（测速运行时每 5s 刷新一次状态） ───────────────────────────────────────
function startPolling() {
  stopPolling()
  let maxPolls = 30 // 最多轮询 2.5 分钟
  pollingTimer = setInterval(async () => {
    await fetchStatus()
    maxPolls--
    if (!status.running || maxPolls <= 0) {
      stopPolling()
      await fetchLatest()
      await fetchHistory()
      emit('action')
    }
  }, 5000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

// ── ECharts 趋势图 ─────────────────────────────────────────────────────────────
async function renderChart() {
  if (!chartContainer.value || history.value.length === 0) return
  try {
    const echarts = await import('echarts')
    if (!chartInstance) {
      chartInstance = echarts.init(chartContainer.value)
    }
    const sorted = [...history.value].sort((a, b) =>
      a.timestamp.localeCompare(b.timestamp)
    )
    const timestamps = sorted.map((r) => r.timestamp.slice(5, 16)) // MM-DD HH:mm
    const downloads = sorted.map((r) => r.download)
    const uploads = sorted.map((r) => r.upload)
    const pings = sorted.map((r) => r.ping)

    const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
                   document.documentElement.classList.contains('v-theme--dark') ||
                   (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
    
    const textColor = isDark ? '#aaaaaa' : '#666666'
    const splitLineColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'
    const tooltipBg = isDark ? 'rgba(30,30,40,0.85)' : 'rgba(255,255,255,0.95)'
    const tooltipBorder = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
    const tooltipText = isDark ? '#ffffff' : '#333333'

    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        textStyle: { color: tooltipText, fontSize: 12 },
        formatter: (params: any[]) => {
          const t = params[0].axisValue
          const lines = params.map(
            (p: any) => {
              const unit = p.seriesName === '延迟' ? 'ms' : 'Mbps'
              return `<span style="color:${p.color}">●</span> <span style="color:${tooltipText}">${p.seriesName}: <b>${p.value} ${unit}</b></span>`
            }
          )
          return `<div style="font-size:11px;color:${textColor};margin-bottom:4px;">${t}</div>${lines.join('<br/>')}`
        },
      },
      legend: {
        data: ['下行', '上行', '延迟'],
        textStyle: { color: textColor, fontSize: 10 },
        itemWidth: 12,
        itemHeight: 8,
        itemGap: 8,
        top: 2,
        right: 8,
      },
      grid: { left: '1%', right: '3%', bottom: '4%', top: '60px', containLabel: true },
      xAxis: {
        type: 'category',
        data: timestamps,
        axisLabel: {
          color: textColor,
          fontSize: 10,
          rotate: 30,
          interval: Math.floor(timestamps.length / 6),
        },
        axisLine: { lineStyle: { color: splitLineColor } },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: 'value',
          name: 'Mbps',
          nameTextStyle: { color: textColor, fontSize: 10 },
          axisLabel: { color: textColor, fontSize: 10 },
          splitLine: { lineStyle: { color: splitLineColor, type: 'dashed' } },
        },
        {
          type: 'value',
          name: 'ms',
          nameTextStyle: { color: textColor, fontSize: 10 },
          axisLabel: { color: textColor, fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '下行',
          type: 'line',
          data: downloads,
          smooth: true,
          yAxisIndex: 0,
          lineStyle: { color: '#a78bfa', width: 2 },
          itemStyle: { color: '#a78bfa' },
          areaStyle: {
            color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(167,139,250,0.25)' }, { offset: 1, color: 'rgba(167,139,250,0)' }] },
          },
          showSymbol: false,
        },
        {
          name: '上行',
          type: 'line',
          data: uploads,
          smooth: true,
          yAxisIndex: 0,
          lineStyle: { color: '#34d399', width: 2 },
          itemStyle: { color: '#34d399' },
          areaStyle: {
            color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [{ offset: 0, color: 'rgba(52,211,153,0.2)' }, { offset: 1, color: 'rgba(52,211,153,0)' }] },
          },
          showSymbol: false,
        },
        {
          name: '延迟',
          type: 'line',
          data: pings,
          smooth: true,
          yAxisIndex: 1,
          lineStyle: { color: '#fbbf24', width: 1.5, type: 'dashed' },
          itemStyle: { color: '#fbbf24' },
          showSymbol: false,
        },
      ],
    }
    chartInstance.setOption(option, true)
  } catch (e) {
    console.warn('ECharts error', e)
  }
}

function showSnack(text: string, color = 'success') {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

// ── 时间范围切换 ────────────────────────────────────────────────────────────────
async function selectDays(days: number) {
  historyDays.value = days
  await fetchHistory()
}

// ── 生命周期 ───────────────────────────────────────────────────────────────────
onMounted(async () => {
  await fetchStatus()
  await fetchLatest()
  await fetchHistory()
})

onBeforeUnmount(() => {
  stopPolling()
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<template>
  <div class="as-page">
    <!-- 顶部操作栏 -->
    <div class="as-topbar">
      <div class="as-topbar__left">
        <div class="as-topbar__icon">
          <v-icon icon="mdi-speedometer" size="24"></v-icon>
        </div>
        <div>
          <div class="as-topbar__title">网络测速</div>
          <div class="as-topbar__sub" v-if="status.last_run">
            上次测速：{{ status.last_run }}
          </div>
          <div class="as-topbar__sub" v-else>从未运行</div>
        </div>
      </div>
      <div class="as-topbar__right" style="padding: 2px;">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="runSpeedtest" :loading="loading.run || status.running" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-play" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">测速</span>
          </v-btn>
          <v-btn color="primary" @click="emit('switch', 'Config')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-cog" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">设置</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <!-- 最近测速结果 -->
    <div class="as-results" v-if="latest">
      <div class="as-result-card as-result-card--down">
        <div class="as-result-card__label">下行速度</div>
        <div class="as-result-card__value">{{ latest.download }}</div>
        <div class="as-result-card__unit">Mbps</div>
      </div>
      <div class="as-result-card as-result-card--up">
        <div class="as-result-card__label">上行速度</div>
        <div class="as-result-card__value">{{ latest.upload }}</div>
        <div class="as-result-card__unit">Mbps</div>
      </div>
      <div class="as-result-card as-result-card--ping">
        <div class="as-result-card__label">网络延迟</div>
        <div class="as-result-card__value">{{ latest.ping }}</div>
        <div class="as-result-card__unit">ms</div>
      </div>
    </div>
    <div class="as-no-data" v-else>
      <span>暂无测速数据，点击"立即测速"开始</span>
    </div>

    <!-- 节点信息 -->
    <div class="as-server-tag" v-if="latest?.server_name">
      📡 {{ latest.server_name }} &nbsp;·&nbsp; {{ latest.timestamp }}
    </div>

    <!-- 趋势图区域 -->
    <div class="as-card" v-if="history.length > 0">
      <div style="position: relative;">
        <!-- 时间范围 下拉选择 -->
        <div class="as-chart-select" style="position: absolute; left: 8px; top: -2px; z-index: 10;">
          <v-menu location="bottom start" :offset="4">
            <template v-slot:activator="{ props }">
              <div class="as-chart-select-btn" v-bind="props">
                {{ dayOptions.find(opt => opt.value === historyDays)?.label }}
                <v-icon icon="mdi-chevron-down" size="14" class="ml-1 opacity-70"></v-icon>
              </div>
            </template>
            <v-list density="compact" class="py-1" bg-color="surface" elevation="4">
              <v-list-item
                v-for="opt in dayOptions"
                :key="opt.value"
                @click="selectDays(opt.value)"
                :active="historyDays === opt.value"
                color="primary"
                min-height="32"
              >
                <v-list-item-title style="font-size: 13px; font-weight: 500;">{{ opt.label }}</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>
        </div>

        <!-- ECharts 图表 -->
        <div ref="chartContainer" class="as-chart" />
      </div>
    </div>

    <!-- 历史记录列表 -->
    <div class="as-card" v-if="history.length > 0">
      <div class="as-card__header">
        <span class="as-card__title">📋 历史记录</span>
        <span class="as-card__badge">{{ historyTotal }} 条</span>
      </div>

      <div class="as-table-wrap">
        <table class="as-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>下行</th>
              <th>上行</th>
              <th>延迟</th>
              <th>节点名称</th>
              <th>节点 ID</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in pagedHistory"
              :key="row.timestamp"
              :class="{ 'as-table__row--alt': idx % 2 === 1 }"
            >
              <td class="as-table__time">{{ row.timestamp }}</td>
              <td class="as-table__down">{{ row.download }} <span>Mbps</span></td>
              <td class="as-table__up">{{ row.upload }} <span>Mbps</span></td>
              <td class="as-table__ping">{{ row.ping }} <span>ms</span></td>
              <td class="as-table__server">{{ row.server_name }}</td>
              <td class="as-table__server" style="color: grey; font-size: 11px;">#{{ row.server_id }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="as-pagination" v-if="totalPages > 1">
        <button
          class="as-pg-btn"
          :disabled="page <= 1"
          @click="page--"
        >‹</button>
        <span class="as-pg-info">{{ page }} / {{ totalPages }}</span>
        <button
          class="as-pg-btn"
          :disabled="page >= totalPages"
          @click="page++"
        >›</button>
      </div>
    </div>

    <!-- 反馈 snackbar -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000" location="top">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<style scoped>
/* ── 工具字体 ─────────────────────────────────────────────────────────────────── */
.as-page {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", sans-serif;
  -webkit-font-smoothing: antialiased;
  color: rgba(var(--v-theme-on-surface), 0.85);
  min-height: 400px;
}

/* ── 顶部操作栏 ───────────────────────────────────────────────────────────────── */
.as-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
}
.as-topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.as-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.as-topbar__icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: rgba(var(--v-theme-primary), 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: rgb(var(--v-theme-primary));
  flex-shrink: 0;
}
.as-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}
.as-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
}



/* ── 按钮 & 卡片主题替换 ───────────────────────────────────────────────────────── */
.as-results {
  display: flex;
  align-items: stretch;
  gap: 12px;
  width: 100%;
}
.as-result-card {
  flex: 1;
  min-width: 0;
  border-radius: 14px;
  padding: 16px 14px;
  backdrop-filter: blur(20px) saturate(150%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.2),
    0 2px 12px rgba(var(--v-theme-on-surface), 0.1);
}
.as-result-card--down {
  background: rgba(167, 139, 250, 0.12);
  border: 0.5px solid rgba(167, 139, 250, 0.3);
}
.as-result-card--up {
  background: rgba(52, 211, 153, 0.1);
  border: 0.5px solid rgba(52, 211, 153, 0.3);
}
.as-result-card--ping {
  background: rgba(251, 191, 36, 0.1);
  border: 0.5px solid rgba(251, 191, 36, 0.3);
}
.as-result-card__label {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.6);
  letter-spacing: 0.5px;
}
.as-result-card__value {
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
}
.as-result-card--down .as-result-card__value { color: #8b5cf6; }
.as-result-card--up .as-result-card__value { color: #10b981; }
.as-result-card--ping .as-result-card__value { color: #f59e0b; }
.as-result-card__unit {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.as-no-data {
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.4);
  font-size: 13px;
  padding: 28px 0;
  border: 0.5px dashed rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 12px;
}

.as-server-tag {
  text-align: center;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.5);
  margin-top: -4px;
}

.as-card {
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
.as-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.as-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}
.as-card__badge {
  font-size: 11px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  color: rgba(var(--v-theme-on-surface), 0.6);
  padding: 2px 8px;
  border-radius: 20px;
}

/* ── 下拉选择框 ─────────────────────────────────────────────────────────────── */
.as-chart-select {
  align-self: flex-start;
}
.as-chart-select-btn {
  display: flex;
  align-items: center;
  background-color: rgba(var(--v-theme-on-surface), 0.06);
  color: rgba(var(--v-theme-on-surface), 0.85);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 6px;
  padding: 4px 8px 4px 10px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  user-select: none;
}
.as-chart-select-btn:hover {
  background-color: rgba(var(--v-theme-on-surface), 0.08);
}

/* ── ECharts 容器 ─────────────────────────────────────────────────────────────── */
.as-chart {
  width: 100%;
  height: 240px;
}

/* ── 历史记录表格 ─────────────────────────────────────────────────────────────── */
.as-table-wrap {
  overflow-x: auto;
}
.as-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.as-table th {
  text-align: center;
  color: rgba(var(--v-theme-on-surface), 0.55);
  font-weight: 500;
  padding: 8px 8px;
  border-bottom: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  white-space: nowrap;
}
.as-table th:first-child {
  text-align: left;
}
.as-table td {
  text-align: center;
  padding: 8px 8px;
  color: rgba(var(--v-theme-on-surface), 0.85);
  border-bottom: 0.5px solid rgba(var(--v-theme-on-surface), 0.04);
  white-space: nowrap;
}
.as-table td:first-child {
  text-align: left;
}
.as-table td span {
  font-size: 10px;
  color: rgba(var(--v-theme-on-surface), 0.4);
}
.as-table__row--alt td { background: rgba(var(--v-theme-on-surface), 0.02); }
.as-table__time { color: rgba(var(--v-theme-on-surface), 0.6) !important; font-size: 11px !important; }
.as-table__down { color: #8b5cf6 !important; }
.as-table__up { color: #10b981 !important; }
.as-table__ping { color: #f59e0b !important; }
.as-table__server {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  color: rgba(var(--v-theme-on-surface), 0.6) !important;
}

/* ── 分页 ─────────────────────────────────────────────────────────────────────── */
.as-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}
.as-pg-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.12);
  background: rgba(var(--v-theme-on-surface), 0.04);
  color: rgba(var(--v-theme-on-surface), 0.8);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.as-pg-btn:hover:not(:disabled) { background: rgba(var(--v-theme-on-surface), 0.1); }
.as-pg-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.as-pg-info {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.6);
}

/* ── 通用 spinner ─────────────────────────────────────────────────────────────── */
.as-spinner {
  width: 13px;
  height: 13px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 移动端适配 ───────────────────────────────────────────────────────────────── */
@media (max-width: 600px) {
  .as-results {
    gap: 8px;
  }
  .as-result-card {
    padding: 12px 6px;
    border-radius: 10px;
  }
  .as-result-card__value {
    font-size: 22px;
  }
  .as-result-card__label, .as-result-card__unit {
    font-size: 10px;
  }
}
</style>
