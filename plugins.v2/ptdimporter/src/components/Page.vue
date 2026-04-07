<template>
  <div class="pi-page">
    <div class="pi-topbar">
      <div class="pi-topbar__left">
        <div class="pi-topbar__icon">
          <v-icon icon="mdi-database-import-outline" size="24" />
        </div>
        <div>
          <div class="pi-topbar__title">PTD 备份导入</div>
          <div class="pi-topbar__sub">先分析备份，再按需选择导入MP</div>
        </div>
      </div>
      <div class="pi-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="refreshPreview" size="small" min-width="40" class="px-0 px-sm-3">
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

    <div class="pi-hero">
      <div class="pi-hero__main pi-card">
        <div class="pi-card__header">
          <span class="pi-card__title d-flex align-center">
            <v-icon icon="mdi-zip-box-outline" size="18" color="#8b5cf6" class="mr-1" />
            上传并分析备份
          </span>
        </div>

        <div class="pi-hero__desc">
          仅支持上传 PTD 备份压缩包（.zip 格式），且压缩包内须包含 metadata.json。
        </div>

        <v-file-input
          v-model="selectedFile"
          accept="application/zip,.zip"
          label="选择 PTD 备份 ZIP"
          prepend-icon="mdi-zip-box"
          variant="outlined"
          show-size
          class="pi-input"
          :disabled="uploading"
          @update:model-value="uploadFile"
        >
          <template #selection>
            <div v-if="selectedFile" class="pi-file-selection" :title="selectedFile.name">
              <span class="pi-file-selection__name">{{ selectedFile.name }}</span>
              <span class="pi-file-selection__size">{{ formatFileSize(selectedFile.size) }}</span>
            </div>
          </template>
        </v-file-input>

        <div class="pi-action-row">
          <v-btn color="success" prepend-icon="mdi-database-import-outline" size="small" class="pi-import-btn" :disabled="!lastPreviewId || selectedKeys.length === 0" :loading="importing" @click="importMatched">选定导入</v-btn>
        </div>
      </div>

      <div class="pi-card pi-hero__result">
        <div class="pi-card__header">
          <span class="pi-card__title d-flex align-center">
            <v-icon icon="mdi-poll" size="18" color="#10b981" class="mr-1" />
            分析概览
          </span>
          <v-chip v-if="lastPreviewAt" size="x-small" color="primary" variant="tonal">上次分析：{{ lastPreviewAt }}</v-chip>
        </div>

        <div class="pi-results pi-results--summary">
          <div v-for="item in summaryItems" :key="item.label" class="pi-stat-card" :class="item.color">
            <div class="pi-stat-card__label">{{ item.label }}</div>
            <div class="pi-stat-card__value">{{ item.value }}</div>
          </div>
        </div>

        <div class="pi-empty-note pi-summary-note">
          PTD 备份中部分字段可能缺失，如RSS地址、API请求头等，导入后需手动编辑站点配置补全。
        </div>
      </div>
    </div>

    <div class="pi-workspace">
      <div class="pi-workspace__main pi-card pi-card--scrollable" :class="{ 'pi-card--mobile-scroll': previewItems.length }">
        <div class="pi-card__header pi-card__header--wrap">
          <span class="pi-card__title d-flex align-center">
            <v-icon icon="mdi-view-list-outline" size="18" color="#06b6d4" class="mr-1" />
            已导入的站点
          </span>
          <div class="d-flex ga-2 align-center flex-wrap">
            <v-chip size="small" color="primary">共 {{ summary.total || 0 }} 个 · 已选 {{ selectedKeys.length }} 个</v-chip>
            <v-checkbox
              :model-value="allSelected"
              label="全选"
              hide-details
              density="compact"
              :disabled="!selectablePreviewItems.length"
              @update:model-value="toggleAll"
            />
          </div>
        </div>

        <div v-if="previewItems.length" class="pi-table-wrap">
          <div class="pi-table-header" :style="{ paddingRight: overflowPadding }">
            <v-table density="comfortable">
              <colgroup>
                <col style="width: 8%" />
                <col style="width: 22%" />
                <col style="width: 12%" />
                <col style="width: 24%" />
                <col style="width: 20%" />
                <col style="width: 14%" />
              </colgroup>
              <thead>
                <tr>
                  <th class="text-center px-1">选择</th>
                  <th class="text-left">源站点</th>
                  <th class="text-center pi-col-match">解析结果</th>
                  <th class="text-left">标准配对</th>
                  <th class="text-left">状态说明</th>
                  <th class="text-left pl-5">默认动作</th>
                </tr>
              </thead>
            </v-table>
          </div>

          <div class="pi-table-body" ref="tableBodyRef">
            <v-table density="comfortable">
              <colgroup>
                <col style="width: 8%" />
                <col style="width: 22%" />
                <col style="width: 12%" />
                <col style="width: 24%" />
                <col style="width: 20%" />
                <col style="width: 14%" />
              </colgroup>
              <tbody>
              <tr v-for="row in previewItems" :key="row.source.site_key">
                <td class="text-center px-1">
                  <div class="d-flex justify-center align-center">
                    <v-checkbox
                      :model-value="selectedKeys.includes(row.source.site_key)"
                      :disabled="!isSelectable(row)"
                      hide-details
                      density="compact"
                      @update:model-value="(val) => updateSiteSelection(row.source.site_key, val)"
                    />
                  </div>
                </td>
                <td>
                  <div class="font-weight-medium" style="font-size: 13px">{{ row.source.name || row.source.site_key }}</div>
                  <div class="text-caption text-grey">{{ row.source.url || row.source.domain || '-' }}</div>
                </td>
                <td class="text-center pi-col-match">
                  <v-chip size="x-small" :color="matchTypeColor(row.match_type)" variant="tonal">
                    {{ matchTypeLabel(row.match_type) }}
                  </v-chip>
                </td>
                <td>
                  <div style="font-size: 13px">{{ row.standard?.name || '-' }}</div>
                  <div class="text-caption text-grey" style="max-width: 35ch; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :title="row.standard?.url">
                    {{ row.standard?.url || '-' }}
                  </div>
                </td>
                <td>
                  <v-chip size="x-small" class="pi-chip pi-chip--status" :color="statusColor(row.status)" variant="tonal">
                    {{ statusLabel(row.status) }}
                  </v-chip>
                  <div class="text-caption text-grey mt-1" style="font-size: 10px">{{ row.message }}</div>
                </td>
                <td>
                  <v-chip size="x-small" class="pi-chip pi-chip--action" :color="actionColor(row)" variant="tonal">
                    {{ actionLabel(row) }}
                  </v-chip>
                </td>
              </tr>
            </tbody>
            </v-table>
          </div>
        </div>

        <div v-if="previewItems.length" class="pi-mobile-list">
          <div v-for="row in previewItems" :key="`mobile-${row.source.site_key}`" class="pi-mobile-card">
            <div class="pi-mobile-card__top">
              <div class="pi-mobile-card__title-wrap">
                <div class="pi-mobile-card__title-row">
                  <div class="pi-mobile-card__title">{{ row.source.name || row.source.site_key }}</div>
                  <div class="pi-mobile-card__domain pi-mobile-field__value--truncate" :title="row.source.url || row.source.domain || '-'">
                    {{ row.source.url || row.source.domain || '-' }}
                  </div>
                </div>
              </div>
              <v-checkbox
                :model-value="selectedKeys.includes(row.source.site_key)"
                :disabled="!isSelectable(row)"
                hide-details
                density="compact"
                @update:model-value="(val) => updateSiteSelection(row.source.site_key, val)"
              />
            </div>

            <div class="pi-mobile-card__grid">
              <div class="pi-mobile-field">
                <div class="pi-mobile-field__head">
                  <div class="pi-mobile-field__label">标准配对</div>
                  <div class="pi-mobile-field__badges">
                    <v-chip size="x-small" :color="matchTypeColor(row.match_type)" variant="tonal">
                      {{ matchTypeLabel(row.match_type) }}
                    </v-chip>
                    <v-chip size="x-small" class="pi-chip pi-chip--status" :color="statusColor(row.status)" variant="tonal">
                      {{ statusLabel(row.status) }}
                    </v-chip>
                    <v-chip size="x-small" class="pi-chip pi-chip--action" :color="actionColor(row)" variant="tonal">
                      {{ actionLabel(row) }}
                    </v-chip>
                  </div>
                </div>
                <div class="pi-mobile-field__value-row">
                  <div class="pi-mobile-field__value pi-mobile-field__value--strong pi-mobile-field__value--truncate" :title="row.standard?.name || '-'">
                    {{ row.standard?.name || '-' }}
                  </div>
                  <div class="pi-mobile-field__sub pi-mobile-field__value--truncate" :title="row.standard?.url || '-'">
                    {{ row.standard?.url || '-' }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="pi-empty-state">
          <div class="pi-empty-state__icon">
            <v-icon icon="mdi-database-off-outline" size="42" />
          </div>
          <div class="pi-empty-state__title">暂无备份站点数据</div>
          <div class="pi-empty-state__sub">请先上传 PTD 备份压缩包（.zip），解析完成后站点清单将显示在此处。</div>
          <div class="pi-empty-state__steps">
            <div class="pi-empty-step">
              <div class="pi-empty-step__num">1</div>
              <div>
                <div class="pi-empty-step__label">上传 ZIP 备份文件</div>
                <div class="pi-empty-step__desc">点击上方文件选择框，选择 PTD 导出的 .zip 压缩包</div>
              </div>
            </div>
            <v-icon icon="mdi-chevron-right" size="18" color="rgba(var(--v-theme-on-surface), 0.3)" class="pi-empty-step__arrow" />
            <div class="pi-empty-step">
              <div class="pi-empty-step__num">2</div>
              <div>
                <div class="pi-empty-step__label">等待自动解析</div>
                <div class="pi-empty-step__desc">系统会自动识别备份内容并匹配 MP 站点</div>
              </div>
            </div>
            <v-icon icon="mdi-chevron-right" size="18" color="rgba(var(--v-theme-on-surface), 0.3)" class="pi-empty-step__arrow" />
            <div class="pi-empty-step">
              <div class="pi-empty-step__num">3</div>
              <div>
                <div class="pi-empty-step__label">选择并导入站点</div>
                <div class="pi-empty-step__desc">勾选需要的站点后点击「选定导入」完成</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <v-snackbar v-model="message.show" :color="message.type" :timeout="3000" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { computed, ref, reactive, onMounted } from 'vue'

const props = defineProps({
  api: {
    type: Object,
    required: false,
    default: null,
  },
})

const emit = defineEmits(['close', 'switch'])
const PLUGIN_ID = 'PtdImporter'

const createDefaultApi = () => ({
  get: async (url) => {
    const res = await fetch(url)
    return res.json()
  },
  post: async (url, data, options = {}) => {
    const body = data instanceof FormData ? data : options.body || JSON.stringify(data)
    const isFormData = body instanceof FormData
    const res = await fetch(url, {
      method: 'POST',
      headers: options.headers || (isFormData ? {} : { 'Content-Type': 'application/json' }),
      body,
    })
    return res.json()
  },
})

const apiClient = props.api || createDefaultApi()

const selectedFile = ref(null)
const uploading = ref(false)
const importing = ref(false)
const preview = ref({})
const selectedKeys = ref([])
const message = reactive({ show: false, type: 'info', text: '' })

const summary = computed(() => preview.value.summary || {})
const previewItems = computed(() => preview.value.items || [])
const lastPreviewAt = computed(() => preview.value.generated_at || '')
const lastPreviewId = computed(() => previewItems.value.length > 0)

const tableBodyRef = ref(null)
const overflowPadding = ref('0px')

const updateScrollbarPadding = () => {
  if (tableBodyRef.value) {
    const width = tableBodyRef.value.offsetWidth - tableBodyRef.value.clientWidth
    overflowPadding.value = width > 0 ? `${width}px` : '0px'
  }
}


const isSelectable = (item) => ['matched', 'need_confirm', 'exists'].includes(item.status)
const selectablePreviewItems = computed(() => previewItems.value.filter(isSelectable))
const allSelected = computed(() => !!selectablePreviewItems.value.length && selectedKeys.value.length === selectablePreviewItems.value.length)

const summaryItems = computed(() => [
  { label: '导入总数', value: summary.value.total || 0, color: 'pi-stat-card--primary' },
  { label: '可导入', value: summary.value.matched || 0, color: 'pi-stat-card--success' },
  { label: '待确认', value: summary.value.need_confirm || 0, color: 'pi-stat-card--info' },
  { label: '可更新', value: summary.value.exists || 0, color: 'pi-stat-card--warning' },
  { label: '暂未适配', value: summary.value.unmatched || 0, color: 'pi-stat-card--error' },
])

const clearMessage = () => {
  message.text = ''
  message.show = false
}

const setMessage = (type, text) => {
  message.type = type
  message.text = text
  message.show = true
}

const formatFileSize = (size) => {
  if (!Number.isFinite(size) || size < 0) return ''
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  return `${(size / 1024 / 1024 / 1024).toFixed(2)} GB`
}

const updateSiteSelection = (siteKey, checked) => {
  const exists = selectedKeys.value.includes(siteKey)
  if (checked && !exists) {
    selectedKeys.value = [...selectedKeys.value, siteKey]
  } else if (!checked && exists) {
    selectedKeys.value = selectedKeys.value.filter((k) => k !== siteKey)
  }
}

const toggleAll = (val) => {
  if (!selectablePreviewItems.value.length) {
    selectedKeys.value = []
    return
  }
  selectedKeys.value = val ? selectablePreviewItems.value.map(item => item.source.site_key) : []
}

const refreshPreview = async () => {
  const res = await apiClient.get(`/plugin/${PLUGIN_ID}/preview`)
  if (res?.success) {
    preview.value = res.data || {}
    selectedKeys.value = selectablePreviewItems.value.map(item => item.source.site_key)
  }
}

const uploadFile = async () => {
  if (!selectedFile.value) return
  uploading.value = true
  clearMessage()
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const res = await apiClient.post(`/plugin/${PLUGIN_ID}/analyze`, formData)
    if (res?.success) {
      preview.value = res.data || {}
      selectedKeys.value = selectablePreviewItems.value.map(item => item.source.site_key)
      setMessage('success', res.message || '解析成功')
    } else {
      setMessage('error', res?.message || '解析失败')
    }
  } catch (error) {
    setMessage('error', String(error))
  } finally {
    uploading.value = false
  }
}

const importMatched = async () => {
  importing.value = true
  clearMessage()
  try {
    const res = await apiClient.post(`/plugin/${PLUGIN_ID}/import`, {
      site_keys: selectedKeys.value,
    })
    if (res?.success) {
      const result = res.data || {}
      setMessage('success', res.message || `导入完成：成功 ${result.success || 0}，跳过 ${result.skipped || 0}，失败 ${result.failed || 0}`)
      // 仅刷新站点数据，保留用户的勾选状态
      const refreshRes = await apiClient.get(`/plugin/${PLUGIN_ID}/preview`)
      if (refreshRes?.success) {
        preview.value = refreshRes.data || {}
        // 过滤掉已不在列表中的 key（避免残留），但不重置为全选
        const validKeys = new Set(selectablePreviewItems.value.map(item => item.source.site_key))
        selectedKeys.value = selectedKeys.value.filter(k => validKeys.has(k))
      }
    } else {
      setMessage('error', res?.message || '导入失败')
    }
  } catch (error) {
    setMessage('error', String(error))
  } finally {
    importing.value = false
  }
}

const matchTypeLabel = (type) => ({
  url: 'URL 匹配',
  name: '名称匹配',
  domain: '域名兜底',
  unmatched: '未匹配',
}[type] || '未知')

const matchTypeColor = (type) => ({
  url: 'success',
  name: 'warning',
  domain: 'orange',
  unmatched: 'grey',
}[type] || 'grey')

const statusLabel = (status) => ({
  matched: '可导入',
  need_confirm: '待确认',
  exists: '已存在',
  unmatched: '暂未适配',
}[status] || '未知')

const statusColor = (status) => ({
  matched: 'success',
  need_confirm: 'warning',
  exists: 'info',
  unmatched: 'grey',
}[status] || 'grey')

const actionLabel = (row) => {
  if (row.status === 'matched' || row.status === 'need_confirm') return '新增站点'
  if (row.status === 'exists') {
    return {
      update_auth: '更新凭据',
      skip: '跳过',
      update_all: '覆盖配置'
    }[preview.value.import_mode] || '未知'
  }
  return '无动作'
}

const actionColor = (row) => {
  if (row.status === 'matched' || row.status === 'need_confirm') return 'success'
  if (row.status === 'exists') {
    return {
      update_auth: 'primary',
      skip: 'grey',
      update_all: 'error'
    }[preview.value.import_mode] || 'grey'
  }
  return 'transparent'
}

onMounted(() => {
  refreshPreview()
  
  if (window.ResizeObserver) {
    const observer = new ResizeObserver(() => {
      updateScrollbarPadding()
    })
    // In Vue, onMounted guarantees DOM is ready, but ref might be inside v-if
    // which makes it unreliable if previewItems.length is 0 initially.
    // Instead we can use a small delay or a watch effect.
  }
})

// Since the table element is rendered inside v-if="previewItems.length",
// tableBodyRef might not be available immediately on mounted.
import { watch, nextTick } from 'vue'

watch(previewItems, () => {
  nextTick(() => {
    if (tableBodyRef.value) {
      updateScrollbarPadding()
      // Setup observer once when available
      if (!tableBodyRef.value._hasObserver && window.ResizeObserver) {
        const obs = new ResizeObserver(updateScrollbarPadding)
        obs.observe(tableBodyRef.value)
        tableBodyRef.value._hasObserver = true
      }
    }
  })
}, { deep: true, immediate: true })
</script>

<style scoped>
.pi-page {
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

.pi-topbar,
.pi-card__header,
.pi-results,
.pi-action-row {
  display: flex;
  align-items: center;
}

.pi-topbar,
.pi-card__header {
  justify-content: space-between;
}

.pi-topbar__left,
.pi-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pi-topbar__right {
  flex-shrink: 0;
}

.pi-topbar__right :deep(.v-btn-group) {
  flex-wrap: nowrap;
}

.pi-topbar__icon {
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

.pi-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
}

.pi-topbar__sub,
.pi-stat-card__label,
.pi-stat-card__hint {
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.pi-topbar__sub,
.pi-stat-card__label,
.pi-stat-card__hint {
  font-size: 11px;
}

.pi-card {
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

.pi-card--scrollable {
  height: 55vh;
  overflow: hidden;
}

.pi-card--mobile-scroll {
  min-height: 0;
}

.pi-hero,
.pi-workspace {
  display: grid;
  gap: 16px;
}

.pi-hero {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
}

.pi-workspace {
  grid-template-columns: minmax(0, 1fr);
  align-items: stretch;
}

.pi-hero__desc {
  font-size: 11px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.pi-hero__main {
  min-height: 0;
}

.pi-hero__result {
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.pi-results--summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pi-stat-card {
  flex: 1;
  min-width: 0;
  border-radius: 14px;
  padding: 10px 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 2px 12px rgba(var(--v-theme-on-surface), 0.1);
}

.pi-stat-card__value {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -1px;
  line-height: 1;
  text-align: center;
}

.pi-stat-card__label {
  text-align: center;
}

.pi-stat-card--primary {
  background: rgba(139, 92, 246, 0.12);
  border: 0.5px solid rgba(139, 92, 246, 0.3);
}
.pi-stat-card--primary .pi-stat-card__value { color: #8b5cf6; }

.pi-stat-card--success {
  background: rgba(16, 185, 129, 0.12);
  border: 0.5px solid rgba(16, 185, 129, 0.3);
}
.pi-stat-card--success .pi-stat-card__value { color: #10b981; }

.pi-stat-card--info {
  background: rgba(59, 130, 246, 0.12);
  border: 0.5px solid rgba(59, 130, 246, 0.3);
}
.pi-stat-card--info .pi-stat-card__value { color: #3b82f6; }

.pi-stat-card--warning {
  background: rgba(245, 158, 11, 0.12);
  border: 0.5px solid rgba(245, 158, 11, 0.3);
}
.pi-stat-card--warning .pi-stat-card__value { color: #f59e0b; }

.pi-stat-card--error {
  background: rgba(239, 68, 68, 0.12);
  border: 0.5px solid rgba(239, 68, 68, 0.3);
}
.pi-stat-card--error .pi-stat-card__value { color: #ef4444; }

.pi-table-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.pi-mobile-list {
  display: none;
}

.pi-table-header {
  flex-shrink: 0;
  overflow: hidden;
}

.pi-table-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.pi-table-header :deep(.v-table__wrapper),
.pi-table-body :deep(.v-table__wrapper) {
  overflow: hidden !important;
}

.pi-table-header :deep(.v-table),
.pi-table-body :deep(.v-table) {
  width: 100%;
  table-layout: fixed;
}

.pi-table-header :deep(thead th) {
  background: transparent !important;
  white-space: nowrap;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.pi-col-match {
  vertical-align: middle;
}

.pi-col-match :deep(.v-chip) {
  vertical-align: middle;
}

.pi-action-row {
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.pi-import-btn {
  height: 38px;
  border-radius: 12px;
}

.pi-import-btn :deep(.v-btn__prepend) {
  margin-inline-end: 0;
}

.pi-card__title {
  font-size: 13px;
  font-weight: 600;
}

.pi-input :deep(.v-field) {
  border-radius: 12px;
}

.pi-input :deep(.v-input__prepend) {
  margin-inline-end: 8px;
}

.pi-file-selection {
  min-width: 0;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.pi-file-selection__name {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pi-file-selection__size {
  flex-shrink: 0;
}

.pi-empty-note {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.65);
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.24);
  border-radius: 10px;
  padding: 10px 12px;
}

.pi-empty-state {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  text-align: center;
  gap: 12px;
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.24);
  border-radius: 14px;
}

.pi-empty-state__icon {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  border: 1px dashed rgba(var(--v-theme-on-surface), 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(var(--v-theme-on-surface), 0.3);
  margin-bottom: 4px;
}

.pi-empty-state__title {
  font-size: 15px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.7);
  letter-spacing: -0.2px;
}

.pi-empty-state__sub {
  font-size: 12px;
  line-height: 1.6;
  color: rgba(var(--v-theme-on-surface), 0.45);
  white-space: nowrap;
}

.pi-empty-state__steps {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 8px;
}

.pi-empty-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 12px;
  padding: 10px 14px;
  text-align: left;
  max-width: 160px;
}

.pi-empty-step__num {
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

.pi-empty-step__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.75);
  margin-bottom: 3px;
}

.pi-empty-step__desc {
  font-size: 11px;
  line-height: 1.5;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.pi-empty-step__arrow {
  flex-shrink: 0;
}

.pi-chip {
  font-weight: 600;
  letter-spacing: 0.1px;
}

.pi-chip--status,
.pi-chip--action {
  min-width: auto;
  justify-content: center;
}

.pi-chip--status :deep(.v-chip__content),
.pi-chip--action :deep(.v-chip__content) {
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}

.pi-chip--status:deep(.v-chip),
.pi-chip--action:deep(.v-chip) {
  border-radius: 999px;
}

.pi-mobile-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 14px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.pi-mobile-card__top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.pi-mobile-card__title-wrap {
  min-width: 0;
  flex: 1;
}

.pi-mobile-card__title-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  min-width: 0;
}

.pi-mobile-card__title {
  font-size: 14px;
  font-weight: 700;
  color: rgba(var(--v-theme-on-surface), 0.85);
  flex-shrink: 0;
}

.pi-mobile-card__domain {
  min-width: 0;
  flex: 1;
  font-size: 11px;
  line-height: 1.4;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.pi-mobile-card__sub,
.pi-mobile-field__sub {
  font-size: 11px;
  line-height: 1.5;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

.pi-mobile-card__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.pi-mobile-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(var(--v-theme-on-surface), 0.025);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.06);
}

.pi-mobile-field__label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.pi-mobile-field__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.pi-mobile-field__badges {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  flex-wrap: wrap;
}

.pi-mobile-field__value {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.82);
}

.pi-mobile-field__value-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  min-width: 0;
}

.pi-mobile-field__value--strong {
  font-weight: 700;
  flex-shrink: 0;
}

.pi-mobile-field__value--truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 768px) {
  .pi-page {
    padding: 14px;
  }

  .pi-topbar {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .pi-results {
    flex-direction: column;
    align-items: stretch;
  }

  .pi-results--summary {
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

  .pi-stat-card {
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

  .pi-stat-card__label {
    font-size: 10px;
    white-space: nowrap;
  }

  .pi-stat-card__value {
    font-size: 18px;
    letter-spacing: -0.4px;
    text-align: center;
  }

  .pi-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .pi-topbar__right {
    justify-content: flex-end;
  }

  .pi-topbar__right :deep(.v-btn-group) {
    gap: 0;
  }

  .pi-topbar__right :deep(.v-btn) {
    min-width: 36px !important;
    padding-inline: 0 !important;
  }

  .pi-hero,
  .pi-workspace {
    grid-template-columns: 1fr;
  }

  .pi-workspace__main {
    min-width: 0;
  }

  .pi-card--scrollable {
    height: auto;
    min-height: 70vh;
    overflow: visible;
  }

  .pi-card--mobile-scroll {
    height: 70vh;
    min-height: 0;
    overflow: hidden;
  }

  .pi-card__header--wrap {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .pi-card__header--wrap > :last-child {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    flex-wrap: wrap;
    min-width: 0;
  }

  .pi-card__header--wrap > :last-child :deep(.v-selection-control) {
    margin-inline-start: auto;
  }

  .pi-card__header--wrap :deep(.v-selection-control) {
    margin-inline-start: 0;
    flex-direction: row-reverse;
    justify-content: flex-end;
    gap: 6px;
  }

  .pi-card__header--wrap :deep(.v-selection-control .v-label) {
    margin-inline: 0;
  }

  .pi-table-wrap {
    display: none;
  }

  .pi-mobile-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    padding-right: 2px;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .pi-mobile-list::-webkit-scrollbar {
    display: none;
  }

  .pi-mobile-card :deep(.v-selection-control) {
    flex-shrink: 0;
    margin-inline-start: 0;
  }

  .pi-mobile-card__grid {
    grid-template-columns: 1fr;
  }

  .pi-mobile-field__head {
    flex-direction: row;
    align-items: flex-start;
  }

  .pi-mobile-field__badges {
    flex-wrap: nowrap;
    max-width: 70%;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .pi-mobile-field__badges::-webkit-scrollbar {
    display: none;
  }

  .pi-mobile-field__badges :deep(.v-chip) {
    flex-shrink: 0;
    width: auto;
  }

  .pi-table-wrap {
    overflow-x: auto;
    overflow-y: visible;
  }

  .pi-table-header,
  .pi-table-body {
    min-width: 720px;
  }

  .pi-table-body {
    overflow-y: visible;
  }

  .pi-table-header :deep(.v-table),
  .pi-table-body :deep(.v-table) {
    min-width: 720px;
  }

  .pi-empty-state {
    padding: 18px 12px;
    overflow: hidden;
  }

  .pi-empty-state__sub {
    white-space: normal;
    word-break: break-word;
  }

  .pi-empty-state__steps {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }

  .pi-empty-step {
    max-width: none;
    width: 100%;
    padding: 10px 12px;
  }

  .pi-empty-step__arrow {
    display: none;
  }
}
</style>
