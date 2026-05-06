<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { VIcon } from 'vuetify/components'
import {
  copyText,
  formatBytes,
  formatDate,
  pluginRequest,
  getFormatLabel,
  uploadFiles,
  validateImageFile,
} from '../utils/zpic'

// ==================== Props & Emits ====================
const props = defineProps({
  api: { type: Object, default: () => ({}) },
  navKey: { type: String, default: 'main' },
  pluginId: { type: String, default: '' },
})
const emit = defineEmits(['action'])

// ==================== 共享状态 ====================
const loading = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })

// 顶部选项卡定义（对齐 MP HeaderTab 风格）
const headerTabs = [
  { key: 'main', title: '上传图片', icon: 'mdi-cloud-upload-outline' },
  { key: 'images', title: '图片列表', icon: 'mdi-image-multiple-outline' },
  { key: 'albums', title: '相册管理', icon: 'mdi-folder-multiple-image' },
]

function showMessage(type, text) {
  message.type = type
  message.text = text
  message.show = true
}

// ==================== 上传视图 (navKey === 'main') ====================
const uploadDragOver = ref(false)
const uploadUploading = ref(false)
const uploadFileInput = ref(null)
const uploadResults = ref([])
const uploadOptions = reactive({ dedup: true, compress: false, watermark: false, albumId: 0 })
const uploadAlbums = ref([])
const uploadSupportedFormats = 'JPG / PNG / GIF / BMP / WebP'

async function loadUploadAlbums() {
  try {
    const result = await pluginRequest(props.api, '/albums')
    if (result?.success) uploadAlbums.value = result.data || []
  } catch (_) {}
}
const uploadLinkTypes = [
  { value: 'url', label: 'URL' },
  { value: 'markdown', label: 'Markdown' },
  { value: 'html', label: 'HTML' },
  { value: 'bbcode', label: 'BBCode' },
]
const uploadLinkColors = { url: 'primary', markdown: 'green', html: 'orange', bbcode: 'purple' }

function handlePaste(e) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) handleUpload([file])
    }
  }
}

function handleDragEnter(e) { e.preventDefault(); uploadDragOver.value = true }
function handleDragOver(e) { e.preventDefault(); uploadDragOver.value = true }
function handleDragLeave(e) { e.preventDefault(); uploadDragOver.value = false }
function handleDrop(e) {
  e.preventDefault()
  uploadDragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length > 0) handleUpload(files)
}

function handleClickUpload() { uploadFileInput.value?.click() }

function handleFileInputChange(e) {
  const files = Array.from(e.target.files || [])
  if (files.length > 0) handleUpload(files)
  e.target.value = ''
}

async function handleUpload(files) {
  if (uploadUploading.value) return
  const validFiles = []
  for (const file of files) {
    const result = validateImageFile(file)
    if (!result.valid) { showMessage('error', result.message); return }
    validFiles.push(file)
  }
  if (validFiles.length === 0) return
  uploadUploading.value = true
  for (const file of validFiles) {
    const uploadItem = reactive({
      file, status: 'uploading', progress: 0, result: null, error: '', linkType: 'url',
    })
    uploadResults.value.unshift(uploadItem)
    try {
      const response = await uploadFiles(props.api, [file], {
        albumId: uploadOptions.albumId,
        dedup: uploadOptions.dedup,
        compress: uploadOptions.compress,
        watermark: uploadOptions.watermark,
      })
      if (response.success) {
        uploadItem.status = 'success'
        uploadItem.result = response.data
        uploadItem.progress = 100
        showMessage('success', `上传成功: ${file.name}`)
      } else {
        uploadItem.status = 'error'
        uploadItem.error = response.message || '上传失败'
        showMessage('error', `上传失败: ${uploadItem.error}`)
      }
    } catch (err) {
      uploadItem.status = 'error'
      uploadItem.error = err.message || '上传失败'
      showMessage('error', `上传失败: ${uploadItem.error}`)
    }
  }
  uploadUploading.value = false
}

async function copyUploadLink(item, type) {
  const linkType = type || item.linkType
  let text = ''
  const data = item.result
  switch (linkType) {
    case 'url': text = data.url || ''; break
    case 'markdown': text = `![${item.file.name}](${data.url || ''})`; break
    case 'html': text = `<img src="${data.url || ''}" alt="${item.file.name}" />`; break
    case 'bbcode': text = `[img]${data.url || ''}[/img]`; break
  }
  const success = await copyText(text)
  showMessage(success ? 'success' : 'error', success ? '链接已复制' : '复制失败')
}

function copyUploadLinkByType(item, type) {
  copyUploadLink(item, type)
}

async function copyAllUploadLinks() {
  const successItems = uploadResults.value.filter(i => i.status === 'success')
  if (successItems.length === 0) { showMessage('info', '没有可复制的上传结果'); return }
  const urls = successItems.map(i => i.result?.url || '').filter(Boolean)
  const text = urls.join('\n')
  const success = await copyText(text)
  showMessage(success ? 'success' : 'error', success ? `已复制 ${urls.length} 个链接` : '复制失败')
}

function removeResult(index) { uploadResults.value.splice(index, 1) }
function clearResults() { uploadResults.value = [] }

const uploadStats = computed(() => {
  const total = uploadResults.value.length
  const success = uploadResults.value.filter(i => i.status === 'success').length
  const failed = uploadResults.value.filter(i => i.status === 'error').length
  const totalSize = uploadResults.value.filter(i => i.status === 'success').reduce((s, i) => s + (i.file?.size || 0), 0)
  return { total, success, failed, totalSize }
})

function getUploadThumbnailUrl(item) {
  return item.result?.thumbnail_url || item.result?.url || ''
}

function goToSettings() {
  emit('action', { action: 'navigate', navKey: 'config' })
}

// ==================== 图片列表视图 (navKey === 'images') ====================
const images = ref([])
const imagesTotal = ref(0)
const imagesPage = ref(1)
const imagesViewMode = ref('grid')
const imagesLimit = computed(() => imagesViewMode.value === 'grid' ? 12 : 10)
const imagesKeyword = ref('')
const imagesSelectedAlbumId = ref(null)
const imagesAlbums = ref([])
const imagesLinkType = reactive({ value: 'url' })
const imagesLinkTypes = [
  { value: 'url', label: 'URL' },
  { value: 'markdown', label: 'MD' },
  { value: 'html', label: 'HTML' },
  { value: 'bbcode', label: 'BBCode' },
]
const imagesPreviewDialog = ref(false)
const imagesPreviewImage = ref(null)
const imagesDeleteDialog = ref(false)
const imagesDeleteTarget = ref(null) // 单个图片对象或图片对象数组
const imagesDeleting = ref(false)
const imagesSelectionMode = ref(false)
const imagesSelectedIds = ref([])
const selectedImages = computed(() => images.value.filter(img => imagesSelectedIds.value.includes(getImageId(img))))
const isAllCurrentPageSelected = computed(() => images.value.length > 0 && images.value.every(img => imagesSelectedIds.value.includes(getImageId(img))))
let imagesSearchTimer = null

async function loadAlbumsForFilter() {
  try {
    const result = await pluginRequest(props.api, '/albums')
    if (result?.success) imagesAlbums.value = result.data || []
  } catch (_) {}
}

async function loadImages() {
  loading.value = true
  try {
    const result = await pluginRequest(props.api, '/images', {
      method: 'POST',
      body: {
        page: imagesPage.value,
        limit: imagesLimit.value,
        album_id: imagesSelectedAlbumId.value || 0,
        keyword: imagesKeyword.value,
      },
    })
    if (result?.success) {
      const data = result.data || {}
      images.value = data.items || []
      imagesTotal.value = data.total || 0
    } else {
      showMessage('error', result?.message || '加载图片失败')
    }
  } catch (err) {
    showMessage('error', err.message || '加载图片失败')
  } finally {
    loading.value = false
  }
}

function onImagesSearchInput() {
  clearTimeout(imagesSearchTimer)
  imagesSearchTimer = setTimeout(() => { imagesPage.value = 1; clearImagesSelection(); loadImages() }, 400)
}

function clearImagesSearch() { imagesKeyword.value = ''; imagesPage.value = 1; clearImagesSelection(); loadImages() }
function onImagesAlbumFilter(albumId) { imagesSelectedAlbumId.value = albumId; imagesPage.value = 1; clearImagesSelection(); loadImages() }
function goToImagesPage(p) { imagesPage.value = p; clearImagesSelection(); loadImages() }
function setImagesViewMode(mode) {
  if (imagesViewMode.value === mode) return
  imagesViewMode.value = mode
  imagesPage.value = 1
  clearImagesSelection()
  loadImages()
}
function getImageId(img) { return img.imgid || img.id || img.key }
function isImageSelected(img) { return imagesSelectedIds.value.includes(getImageId(img)) }
function toggleImageSelection(img) {
  const id = getImageId(img)
  if (!id) return
  if (imagesSelectedIds.value.includes(id)) imagesSelectedIds.value = imagesSelectedIds.value.filter(item => item !== id)
  else imagesSelectedIds.value = [...imagesSelectedIds.value, id]
}
function clearImagesSelection() { imagesSelectedIds.value = [] }
function toggleImagesSelectionMode() {
  imagesSelectionMode.value = !imagesSelectionMode.value
  if (!imagesSelectionMode.value) clearImagesSelection()
}
function toggleSelectCurrentPage() {
  const ids = images.value.map(img => getImageId(img)).filter(Boolean)
  if (isAllCurrentPageSelected.value) imagesSelectedIds.value = imagesSelectedIds.value.filter(id => !ids.includes(id))
  else imagesSelectedIds.value = Array.from(new Set([...imagesSelectedIds.value, ...ids]))
}
function openDeleteSelectedImagesDialog() {
  if (selectedImages.value.length === 0) { showMessage('info', '请先选择要删除的图片'); return }
  openDeleteMultiImageDialog(selectedImages.value)
}
const imagesTotalPages = computed(() => Math.ceil(imagesTotal.value / imagesLimit.value) || 1)

async function copyImageLink(img, type) {
  const linkTypeVal = type || imagesLinkType.value
  let text = ''
  const url = img.origin_url || img.url || img.thumbnail_url || ''
  switch (linkTypeVal) {
    case 'url': text = url; break
    case 'markdown': text = `![${img.filename || 'image'}](${url})`; break
    case 'html': text = `<img src="${url}" alt="${img.filename || 'image'}" />`; break
    case 'bbcode': text = `[img]${url}[/img]`; break
  }
  const success = await copyText(text)
  showMessage(success ? 'success' : 'error', success ? '链接已复制' : '复制失败')
}

async function copyAllImageLinks() {
  const urls = images.value.map(img => img.origin_url || img.url || '').filter(Boolean)
  if (urls.length === 0) { showMessage('info', '没有可复制的图片'); return }
  const text = urls.join('\n')
  const success = await copyText(text)
  showMessage(success ? 'success' : 'error', success ? `已复制 ${urls.length} 个链接` : '复制失败')
}

function openImagePreview(img) { imagesPreviewImage.value = img; imagesPreviewDialog.value = true }
function closeImagePreview() { imagesPreviewDialog.value = false; imagesPreviewImage.value = null }
function getGridImageSrc(img) { return img.origin_url || img.url || img.thumbnail_url || '' }
function getListImageThumb(img) { return img.thumbnail_url || img.origin_url || img.url || '' }
function getImageSizeText(img) {
  if (img.width && img.height) return `${img.width} x ${img.height}`
  return ''
}

function openDeleteImageDialog(img) {
  imagesDeleteTarget.value = img
  imagesDeleteDialog.value = true
}

function openDeleteMultiImageDialog(imgs) {
  imagesDeleteTarget.value = imgs
  imagesDeleteDialog.value = true
}

async function confirmDeleteImages() {
  if (!imagesDeleteTarget.value) return
  const targets = Array.isArray(imagesDeleteTarget.value) ? imagesDeleteTarget.value : [imagesDeleteTarget.value]
  const imageIds = targets.map(img => img.imgid).filter(Boolean)
  if (imageIds.length === 0) { showMessage('error', '图片 ID 为空，无法删除'); return }

  imagesDeleting.value = true
  try {
    const result = await pluginRequest(props.api, '/images/delete', {
      method: 'POST',
      body: { image_ids: imageIds },
    })
    if (result?.success) {
      showMessage('success', result.message || '删除成功')
      imagesDeleteDialog.value = false
      imagesDeleteTarget.value = null
      clearImagesSelection()
      // 如果预览中的图片被删除，关闭预览
      if (imagesPreviewDialog.value && imageIds.includes(imagesPreviewImage.value?.imgid)) {
        closeImagePreview()
      }
      await loadImages()
    } else {
      showMessage('error', result?.message || '删除失败')
    }
  } catch (err) {
    showMessage('error', err.message || '删除失败')
  } finally {
    imagesDeleting.value = false
  }
}

// ==================== 相册管理视图 (navKey === 'albums') ====================
const albums = ref([])
const defaultAlbumImageCount = ref(0)
const albumGridItems = computed(() => [
  {
    album_id: 0,
    name: '默认相册',
    description: '未归类图片默认存放位置',
    count: defaultAlbumImageCount.value,
    isDefault: true,
  },
  ...albums.value,
])
const albumDialog = ref(false)
const albumDialogMode = ref('create')
const albumDialogTitle = ref('创建相册')
const albumForm = reactive({ album_id: null, name: '', description: '' })
const albumFormErrors = reactive({ name: '' })
const albumDeleteDialog = ref(false)
const albumDeleteTarget = ref(null)
const albumSaving = ref(false)
const albumDeleting = ref(false)

async function loadDefaultAlbumImageCount() {
  try {
    const result = await pluginRequest(props.api, '/images', {
      method: 'POST',
      body: { page: 1, limit: 1, album_id: 0, keyword: '' },
    })
    if (result?.success) defaultAlbumImageCount.value = result.data?.total || 0
  } catch (_) {}
}

async function loadAlbums() {
  loading.value = true
  try {
    const result = await pluginRequest(props.api, '/albums')
    if (result?.success) { albums.value = result.data || [] }
    else { showMessage('error', result?.message || '加载相册失败') }
    await loadDefaultAlbumImageCount()
  } catch (err) { showMessage('error', err.message || '加载相册失败') }
  finally { loading.value = false }
}

function openCreateAlbumDialog() {
  albumDialogMode.value = 'create'
  albumDialogTitle.value = '创建相册'
  albumForm.album_id = null; albumForm.name = ''; albumForm.description = ''
  albumFormErrors.name = ''
  albumDialog.value = true
}

function openEditAlbumDialog(album) {
  albumDialogMode.value = 'edit'
  albumDialogTitle.value = '编辑相册'
  albumForm.album_id = album.album_id
  albumForm.name = album.name || ''
  albumForm.description = album.description || ''
  albumFormErrors.name = ''
  albumDialog.value = true
}

function validateAlbumForm() {
  let valid = true
  albumFormErrors.name = ''
  if (!albumForm.name.trim()) { albumFormErrors.name = '相册名称不能为空'; valid = false }
  else if (albumForm.name.trim().length > 50) { albumFormErrors.name = '名称不能超过 50 个字符'; valid = false }
  return valid
}

async function saveAlbum() {
  if (!validateAlbumForm()) return
  albumSaving.value = true
  try {
    const endpoint = albumDialogMode.value === 'create' ? '/albums/create' : '/albums/update'
    const payload = { name: albumForm.name.trim(), description: albumForm.description.trim() }
    if (albumDialogMode.value === 'edit') payload.album_id = albumForm.album_id
    const result = await pluginRequest(props.api, endpoint, { method: 'POST', body: payload })
    if (result?.success) { showMessage('success', result.message || '操作成功'); albumDialog.value = false; await loadAlbums() }
    else { showMessage('error', result?.message || '操作失败') }
  } catch (err) { showMessage('error', err.message || '操作失败') }
  finally { albumSaving.value = false }
}

function openDeleteAlbumDialog(album) { albumDeleteTarget.value = album; albumDeleteDialog.value = true }

async function confirmDeleteAlbum() {
  if (!albumDeleteTarget.value) return
  albumDeleting.value = true
  try {
    const result = await pluginRequest(props.api, '/albums/delete', {
      method: 'POST', body: { album_id: albumDeleteTarget.value.album_id },
    })
    if (result?.success) {
      showMessage('success', '相册已删除')
      albumDeleteDialog.value = false
      albumDeleteTarget.value = null
      await loadAlbums()
    } else { showMessage('error', result?.message || '删除失败') }
  } catch (err) { showMessage('error', err.message || '删除失败') }
  finally { albumDeleting.value = false }
}

function getAlbumCover(album) {
  if (album.cover_url || album.cover) return album.cover_url || album.cover
  if (album.thumbnail_url) return album.thumbnail_url
  return ''
}
function getAlbumImageCount(album) { return album.image_count || album.count || 0 }

function goToAlbumImages(albumId) {
  imagesSelectedAlbumId.value = albumId
  localNavKey.value = 'images'
}

// ==================== 本地导航状态（内部切换） ====================
const localNavKey = ref(props.navKey)

watch(
  () => props.navKey,
  (newKey) => { localNavKey.value = newKey }
)

function switchView(key) {
  localNavKey.value = key
}

let pasteHandlerAdded = false
let footerContentObserver = null
const hiddenFooterContentElements = new Map()

function hideMpFooterContentContainer() {
  document.querySelectorAll('.footer-content-container').forEach((el) => {
    if (!hiddenFooterContentElements.has(el)) {
      hiddenFooterContentElements.set(el, el.style.display)
    }
    el.style.display = 'none'
  })
}

function restoreMpFooterContentContainer() {
  hiddenFooterContentElements.forEach((display, el) => {
    el.style.display = display
  })
  hiddenFooterContentElements.clear()
}

onMounted(() => {
  hideMpFooterContentContainer()
  footerContentObserver = new MutationObserver(() => hideMpFooterContentContainer())
  footerContentObserver.observe(document.body, { childList: true, subtree: true })
})

watch(
  () => localNavKey.value,
  (newKey) => {
    // paste 事件仅绑定到上传视图
    if (newKey === 'main' && !pasteHandlerAdded) {
      document.addEventListener('paste', handlePaste)
      pasteHandlerAdded = true
    } else if (newKey !== 'main' && pasteHandlerAdded) {
      document.removeEventListener('paste', handlePaste)
      pasteHandlerAdded = false
    }
    // 按需加载数据
    if (newKey === 'main') { loadUploadAlbums() }
    else if (newKey === 'images') { loadAlbumsForFilter(); loadImages() }
    else if (newKey === 'albums') { loadAlbums() }
  },
  { immediate: true }
)

onUnmounted(() => {
  document.removeEventListener('paste', handlePaste)
  if (footerContentObserver) {
    footerContentObserver.disconnect()
    footerContentObserver = null
  }
  restoreMpFooterContentContainer()
})
</script>

<template>
  <!-- 内部导航栏（对齐 MP HeaderTab 风格） -->
  <div class="zpic-tab-header">
    <div class="zpic-tab-items">
      <div
        v-for="tab in headerTabs"
        :key="tab.key"
        class="zpic-tab-item"
        :class="{ active: localNavKey === tab.key }"
        @click="switchView(tab.key)"
      >
        <VIcon v-if="tab.icon" :icon="tab.icon" size="small" class="zpic-tab-item-icon" />
        <span>{{ tab.title }}</span>
      </div>
    </div>
  </div>

  <!-- ==================== 上传视图 ==================== -->
  <div v-if="localNavKey === 'main'" class="zpic-upload-page">
    <v-snackbar v-model="message.show" :color="message.type === 'error' ? 'red' : message.type === 'success' ? 'green' : 'info'" timeout="3000" location="top">
      {{ message.text }}
    </v-snackbar>

    <!-- 上传选项栏 -->
    <v-card class="upload-options-card mb-4" variant="flat">
      <v-card-text class="py-3 px-4">
        <div class="upload-options-bar d-flex flex-wrap align-center justify-space-between">
          <div class="d-flex flex-wrap align-center">
            <div class="upload-switch-item mr-8">
              <span class="upload-switch-label">图片去重</span>
              <v-switch v-model="uploadOptions.dedup" color="primary" hide-details density="compact" />
            </div>
            <div class="upload-switch-item mr-8">
              <span class="upload-switch-label">图片压缩</span>
              <v-switch v-model="uploadOptions.compress" color="primary" hide-details density="compact" />
            </div>
            <div class="upload-switch-item">
              <span class="upload-switch-label">文字水印</span>
              <v-switch v-model="uploadOptions.watermark" color="primary" hide-details density="compact" />
            </div>
          </div>
          <v-select
            v-model="uploadOptions.albumId"
            :items="[{ id: 0, name: '默认相册' }, ...uploadAlbums.map(a => ({ id: a.album_id, name: a.name }))]"
            item-title="name"
            item-value="id"
            placeholder="选择相册"
            prepend-inner-icon="mdi-folder-outline"
            variant="outlined"
            density="compact"
            hide-details
            style="max-width: 160px;"
          />
        </div>
      </v-card-text>
    </v-card>

    <v-card class="upload-dropzone-card mb-4" variant="flat">
      <v-card-text class="pa-0">
        <div class="upload-dropzone" :class="{ 'dropzone-active': uploadDragOver, 'dropzone-disabled': uploadUploading }" @dragenter="handleDragEnter" @dragover="handleDragOver" @dragleave="handleDragLeave" @drop="handleDrop" @click="handleClickUpload">
          <input ref="uploadFileInput" type="file" accept=".jpg,.jpeg,.png,.gif,.bmp,.webp" multiple style="display: none" @change="handleFileInputChange" />
          <v-icon :icon="uploadUploading ? 'mdi-loading mdi-spin' : 'mdi-cloud-upload-outline'" size="64" :color="uploadDragOver ? 'primary' : 'grey-lighten-1'" class="mb-4" />
          <div v-if="uploadUploading" class="text-h6 text-grey-darken-1">正在上传...</div>
          <div v-else>
            <div class="text-h6 mb-2">{{ uploadDragOver ? '松开鼠标上传文件' : '拖拽图片到此处，或点击选择' }}</div>
            <div class="text-body-2 text-grey-darken-1">支持 {{ uploadSupportedFormats }} 格式，单个文件最大 5MB</div>
            <v-chip size="small" color="primary" variant="outlined" class="mt-3">支持多文件同时上传</v-chip>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <v-card v-if="uploadResults.length > 0" class="mb-4">
      <v-card-title class="d-flex align-center">
        <span>上传结果</span>
        <v-spacer />
        <v-chip size="small" color="primary" variant="outlined">{{ uploadStats.success }} / {{ uploadStats.total }} 成功</v-chip>
      </v-card-title>
      <v-card-text>
        <div class="d-flex align-center mb-3">
          <v-btn size="small" variant="outlined" color="primary" prepend-icon="mdi-content-copy" :disabled="uploadStats.success === 0" @click="copyAllUploadLinks">批量复制</v-btn>
          <v-spacer />
          <v-btn size="small" variant="text" color="grey" prepend-icon="mdi-delete-sweep-outline" @click="clearResults">清空队列</v-btn>
        </div>
        <v-list lines="two">
          <template v-for="(item, index) in uploadResults" :key="index">
            <v-list-item class="mb-2" :class="`result-${item.status}`">
              <template #prepend>
                <div class="result-thumbnail mr-3">
                  <img v-if="item.status === 'success' && getUploadThumbnailUrl(item)" :src="getUploadThumbnailUrl(item)" :alt="item.file.name" class="thumbnail-img" />
                  <div v-else-if="item.status === 'uploading'" class="thumbnail-placeholder"><v-progress-circular indeterminate size="24" color="primary" /></div>
                  <div v-else-if="item.status === 'error'" class="thumbnail-placeholder"><v-icon icon="mdi-alert-circle" color="red" /></div>
                  <div v-else class="thumbnail-placeholder"><v-icon icon="mdi-file-image-outline" color="grey" /></div>
                </div>
              </template>
              <v-list-item-title class="mb-1">
                <v-chip size="x-small" :color="item.status === 'success' ? 'green' : item.status === 'error' ? 'red' : 'primary'" class="mr-2">{{ item.status === 'uploading' ? '上传中' : item.status === 'success' ? '成功' : '失败' }}</v-chip>
                {{ item.file.name }}
              </v-list-item-title>
              <v-list-item-subtitle>
                <span class="text-caption">{{ getFormatLabel(item.file.type) }} · {{ formatBytes(item.file.size) }}</span>
                <span v-if="item.status === 'success' && item.result" class="text-caption ml-2">{{ item.result.width }} × {{ item.result.height }}</span>
              </v-list-item-subtitle>
              <template v-if="item.status === 'success' && item.result" #append>
                <div class="d-flex flex-column align-end">
                  <div class="d-flex align-center mb-1">
                    <v-chip
                      v-for="lt in uploadLinkTypes" :key="lt.value" size="x-small" variant="tonal"
                      :color="uploadLinkColors[lt.value]"
                      class="mr-1 upload-link-chip"
                      @click="copyUploadLinkByType(item, lt.value)"
                    >{{ lt.label }}</v-chip>
                  </div>
                  <v-btn size="x-small" variant="text" color="grey" icon="mdi-close" @click="removeResult(index)">
                    <v-icon icon="mdi-close" size="small" />
                    <v-tooltip activator="parent" location="top">删除</v-tooltip>
                  </v-btn>
                </div>
              </template>
              <v-list-item-subtitle v-if="item.status === 'error'" class="text-red-darken-2">{{ item.error }}</v-list-item-subtitle>
            </v-list-item>
          </template>
        </v-list>
        <v-divider class="my-3" />
        <div class="d-flex align-center text-caption text-grey-darken-1">
          <span>总计：{{ uploadStats.total }} 张图片</span>
          <v-spacer />
          <span>成功：{{ uploadStats.success }} 张</span>
          <span class="mx-2">|</span>
          <span>失败：{{ uploadStats.failed }} 张</span>
          <span class="mx-2">|</span>
          <span>总大小：{{ formatBytes(uploadStats.totalSize) }}</span>
        </div>
      </v-card-text>
    </v-card>

    <div v-if="uploadResults.length === 0 && !uploadUploading" class="text-center pa-8">
      <v-icon icon="mdi-image-multiple-outline" size="80" color="grey-lighten-2" class="mb-4" />
      <div class="text-h6 text-grey-darken-1 mb-2">暂无上传记录</div>
      <div class="text-body-2 text-grey">支持拖拽上传、点击选择或 Ctrl+V 粘贴图片</div>
    </div>
  </div>

  <!-- ==================== 图片列表视图 ==================== -->
  <div v-else-if="localNavKey === 'images'" class="zpic-images-page">
    <v-snackbar v-model="message.show" :color="message.type === 'error' ? 'red' : message.type === 'success' ? 'green' : 'info'" timeout="3000" location="top">{{ message.text }}</v-snackbar>

    <!-- 筛选栏 -->
    <v-card class="mb-4" variant="flat">
      <v-card-text class="pa-3">
        <v-row align="center" dense>
          <v-col cols="12" sm="2">
            <v-select :model-value="imagesSelectedAlbumId" :items="[{ id: null, name: '全部相册' }, { id: 0, name: '默认相册' }, ...imagesAlbums.map(a => ({ id: a.album_id, name: a.name }))]" item-title="name" item-value="id" placeholder="相册筛选" prepend-inner-icon="mdi-folder-outline" variant="outlined" density="compact" hide-details @update:model-value="onImagesAlbumFilter" />
          </v-col>
          <v-col cols="12" sm="2">
            <v-text-field v-model="imagesKeyword" placeholder="搜索图片..." prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details clearable @update:model-value="onImagesSearchInput" @click:clear="clearImagesSearch" />
          </v-col>
          <v-col cols="12" sm="8" class="d-flex align-center justify-end flex-wrap ga-2">
            <span class="text-caption text-grey-darken-1 mr-1 flex-shrink-0">共 {{ imagesTotal }} 张</span>
            <template v-if="imagesSelectionMode">
              <span class="text-caption text-primary flex-shrink-0">已选 {{ imagesSelectedIds.length }} 张</span>
              <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-checkbox-multiple-marked-outline" @click="toggleSelectCurrentPage">
                {{ isAllCurrentPageSelected ? '取消全选' : '本页全选' }}
              </v-btn>
              <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" :disabled="imagesSelectedIds.length === 0" @click="openDeleteSelectedImagesDialog">批量删除</v-btn>
              <v-btn size="small" variant="text" @click="toggleImagesSelectionMode">退出选择</v-btn>
            </template>
            <v-btn v-else size="small" variant="tonal" color="primary" prepend-icon="mdi-select-multiple" @click="toggleImagesSelectionMode">批量选择</v-btn>
            <div class="view-toggle-group flex-shrink-0">
              <v-btn size="small" variant="tonal" :color="imagesViewMode === 'grid' ? 'primary' : 'default'" icon="mdi-view-grid-outline" @click="setImagesViewMode('grid')" />
              <v-btn size="small" variant="tonal" :color="imagesViewMode === 'list' ? 'primary' : 'default'" icon="mdi-view-list-outline" @click="setImagesViewMode('list')" />
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center pa-8">
      <v-progress-circular indeterminate color="primary" size="40" />
      <div class="text-caption text-grey-darken-1 mt-2">加载中...</div>
    </div>

    <!-- 网格视图 -->
    <div v-else-if="imagesViewMode === 'grid' && images.length > 0" class="image-grid">
      <v-card v-for="img in images" :key="img.key || img.id" class="image-card" :class="{ 'image-card--selected': isImageSelected(img) }" variant="outlined" @click="imagesSelectionMode ? toggleImageSelection(img) : openImagePreview(img)">
        <v-checkbox-btn
          v-if="imagesSelectionMode"
          :model-value="isImageSelected(img)"
          class="image-card__checkbox"
          color="primary"
          @click.stop="toggleImageSelection(img)"
        />
        <div class="image-card__thumb">
          <v-img :src="getGridImageSrc(img)" :alt="img.filename || ''" aspect-ratio="1" cover class="image-card__img">
            <template #placeholder><div class="d-flex align-center justify-center fill-height"><v-progress-circular indeterminate size="20" color="grey" /></div></template>
            <template #error><div class="d-flex align-center justify-center fill-height bg-grey-lighten-4"><v-icon icon="mdi-image-off-outline" size="32" color="grey" /></div></template>
          </v-img>
        </div>
        <div class="image-card__info">
          <div class="image-card__name text-truncate" :title="img.filename || ''">{{ img.filename || '未命名' }}</div>
          <div class="d-flex align-center justify-space-between">
            <div class="image-card__meta text-caption text-grey-darken-1 text-truncate">
              <span v-if="getImageSizeText(img)">{{ getImageSizeText(img) }}</span>
              <span v-if="img.size"> · {{ formatBytes(img.size) }}</span>
            </div>
            <div class="image-card__actions flex-shrink-0" @click.stop>
              <v-btn density="compact" icon size="x-small" variant="tonal" color="primary" @click="copyImageLink(img)">
                <v-icon size="14">mdi-content-copy</v-icon>
                <v-tooltip activator="parent" location="top">复制链接</v-tooltip>
              </v-btn>
              <v-btn density="compact" icon size="x-small" variant="tonal" color="error" @click="openDeleteImageDialog(img)">
                <v-icon size="18">mdi-delete-outline</v-icon>
                <v-tooltip activator="parent" location="top">删除图片</v-tooltip>
              </v-btn>
            </div>
          </div>
        </div>
      </v-card>
    </div>

    <!-- 列表视图 -->
    <v-card v-else-if="imagesViewMode === 'list' && images.length > 0" class="image-list-card" variant="flat">
      <v-list lines="two" density="compact" class="image-list pa-0">
        <template v-for="(img, index) in images" :key="img.key || img.id">
          <v-list-item :class="{ 'image-list-item--selected': isImageSelected(img) }" @click="imagesSelectionMode ? toggleImageSelection(img) : openImagePreview(img)">
            <template #prepend>
              <div class="d-flex align-center">
                <v-checkbox-btn
                  v-if="imagesSelectionMode"
                  :model-value="isImageSelected(img)"
                  color="primary"
                  class="mr-1"
                  @click.stop="toggleImageSelection(img)"
                />
                <v-avatar size="48" rounded variant="tonal" class="mr-2">
                  <v-img :src="getListImageThumb(img)" :alt="img.filename || ''">
                    <template #error><v-icon icon="mdi-image-off-outline" /></template>
                  </v-img>
                </v-avatar>
              </div>
            </template>
            <v-list-item-title class="text-body-2">{{ img.filename || '未命名' }}</v-list-item-title>
            <v-list-item-subtitle class="text-caption">
              <span>{{ getFormatLabel(img.mime_type || img.mimetype || '') || '图片' }}</span>
              <span v-if="getImageSizeText(img)"> · {{ getImageSizeText(img) }}</span>
              <span v-if="img.size"> · {{ formatBytes(img.size) }}</span>
              <span v-if="img.upload_at || img.created_at"> · {{ formatDate(img.upload_at || img.created_at) }}</span>
            </v-list-item-subtitle>
            <template #append>
              <div class="image-card__actions flex-shrink-0" @click.stop>
                <v-btn density="compact" icon size="x-small" variant="tonal" color="primary" @click.stop="copyImageLink(img)">
                  <v-icon size="14">mdi-content-copy</v-icon>
                  <v-tooltip activator="parent" location="top">复制链接</v-tooltip>
                </v-btn>
                <v-btn density="compact" icon size="x-small" variant="tonal" color="error" @click.stop="openDeleteImageDialog(img)">
                  <v-icon size="18">mdi-delete-outline</v-icon>
                  <v-tooltip activator="parent" location="top">删除图片</v-tooltip>
                </v-btn>
              </div>
            </template>
          </v-list-item>
          <v-divider v-if="index < images.length - 1" />
        </template>
      </v-list>
    </v-card>

    <!-- 空状态 -->
    <div v-else class="text-center pa-8">
      <v-icon icon="mdi-image-off-outline" size="80" color="grey-lighten-2" class="mb-4" />
      <div class="text-h6 text-grey-darken-1 mb-2">暂无图片</div>
      <div class="text-body-2 text-grey">{{ imagesKeyword ? '没有找到匹配的图片，请尝试其他关键词' : '去上传页面上传图片吧' }}</div>
    </div>

    <!-- 分页 -->
    <div v-if="imagesTotalPages > 1" class="images-pagination d-flex justify-center mt-2 mb-0">
      <v-pagination v-model="imagesPage" :length="imagesTotalPages" :total-visible="5" density="compact" rounded="circle" @update:model-value="goToImagesPage" />
    </div>

    <!-- 图片预览对话框 -->
    <v-dialog v-model="imagesPreviewDialog" max-width="800">
      <v-card v-if="imagesPreviewImage">
        <v-card-title class="d-flex align-center pa-2">
          <span class="text-body-2 text-truncate ml-2">{{ imagesPreviewImage.filename || '预览' }}</span>
          <span v-if="imagesPreviewImage.imgid" class="text-caption text-medium-emphasis ml-2">ID:{{ imagesPreviewImage.imgid }}</span>
          <v-spacer />
          <div class="d-flex align-center mr-2">
            <v-chip
              v-for="lt in imagesLinkTypes" :key="lt.value" size="x-small" variant="tonal"
              :color="uploadLinkColors[lt.value]"
              class="mr-1 upload-link-chip"
              @click="copyImageLink(imagesPreviewImage, lt.value)"
            >{{ lt.label }}</v-chip>
          </div>
          <v-btn size="small" variant="text" color="error" icon @click="openDeleteImageDialog(imagesPreviewImage)">
            <v-icon icon="mdi-delete-outline" />
            <v-tooltip activator="parent" location="top">删除图片</v-tooltip>
          </v-btn>
          <v-btn size="small" variant="text" icon="mdi-close" @click="closeImagePreview" />
        </v-card-title>
        <v-divider />
        <div class="preview-container pa-4">
          <v-img :src="imagesPreviewImage.origin_url || imagesPreviewImage.url || ''" :alt="imagesPreviewImage.filename || ''" contain max-height="500" class="mx-auto">
            <template #error><div class="d-flex align-center justify-center fill-height"><v-icon icon="mdi-image-broken-variant" size="64" color="grey" /></div></template>
          </v-img>
        </div>
        <v-divider />
        <v-card-text class="text-caption text-grey-darken-1 pa-3">
          <v-row dense>
            <v-col cols="6" sm="3"><span class="text-medium-emphasis">尺寸：</span>{{ getImageSizeText(imagesPreviewImage) || '-' }}</v-col>
            <v-col cols="6" sm="3"><span class="text-medium-emphasis">大小：</span>{{ imagesPreviewImage.size ? formatBytes(imagesPreviewImage.size) : '-' }}</v-col>
            <v-col cols="6" sm="3"><span class="text-medium-emphasis">格式：</span>{{ getFormatLabel(imagesPreviewImage.mime_type || imagesPreviewImage.mimetype || '') || '-' }}</v-col>
            <v-col cols="6" sm="3"><span class="text-medium-emphasis">上传：</span>{{ formatDate(imagesPreviewImage.upload_at || imagesPreviewImage.created_at) || '-' }}</v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- 删除图片确认对话框 -->
    <v-dialog v-model="imagesDeleteDialog" max-width="420" persistent>
      <v-card>
        <v-card-title class="text-h6">确认删除</v-card-title>
        <v-card-text>
          <div class="text-body-2 mb-2">确定要删除以下图片吗？此操作不可恢复。</div>
          <div v-if="imagesDeleteTarget" class="text-caption text-medium-emphasis">
            <template v-if="Array.isArray(imagesDeleteTarget)">
              <div v-for="img in imagesDeleteTarget" :key="img.imgid" class="text-truncate">{{ img.filename || img.imgid }}</div>
            </template>
            <template v-else>
              {{ imagesDeleteTarget.filename || imagesDeleteTarget.imgid }}
            </template>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="imagesDeleting" @click="imagesDeleteDialog = false">取消</v-btn>
          <v-btn color="error" variant="flat" :loading="imagesDeleting" @click="confirmDeleteImages">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
  <div v-else-if="localNavKey === 'albums'" class="zpic-albums-page">
    <v-snackbar v-model="message.show" :color="message.type === 'error' ? 'red' : message.type === 'success' ? 'green' : 'info'" timeout="3000" location="top">{{ message.text }}</v-snackbar>

    <!-- 加载状态 -->
    <div v-if="loading" class="text-center pa-8">
      <v-progress-circular indeterminate color="primary" size="40" />
      <div class="text-caption text-grey-darken-1 mt-2">加载中...</div>
    </div>

    <!-- 相册网格 -->
    <div v-else class="album-grid">
      <v-card v-for="album in albumGridItems" :key="album.album_id" class="album-card" variant="outlined">
        <div class="album-card__cover" @click="goToAlbumImages(album.album_id)">
          <v-img v-if="getAlbumCover(album)" :src="getAlbumCover(album)" :alt="album.name" height="160" cover class="album-card__img">
            <template #error><div class="d-flex align-center justify-center fill-height bg-grey-lighten-4"><v-icon icon="mdi-image-off-outline" size="40" color="grey-lighten-2" /></div></template>
          </v-img>
          <div v-else class="album-card__cover-placeholder"><v-icon :icon="album.isDefault ? 'mdi-image-multiple-outline' : 'mdi-folder-image'" size="48" color="grey-lighten-2" /></div>
          <v-chip size="x-small" color="black" class="album-card__count" label>
            <v-icon icon="mdi-image-outline" size="12" class="mr-1" /> {{ getAlbumImageCount(album) }}
          </v-chip>
        </div>
        <v-card-text class="album-card__body pa-3">
          <div class="album-card__name text-body-2 font-weight-medium text-truncate" :title="album.name">{{ album.name }}</div>
          <div v-if="album.description" class="album-card__desc text-caption text-grey-darken-1 text-truncate mt-1" :title="album.description">{{ album.description }}</div>
          <div v-if="album.created_at" class="text-caption text-grey-darken-1 mt-1">{{ formatDate(album.created_at) }}</div>
        </v-card-text>
        <v-divider />
        <div class="album-card__actions d-flex">
          <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-eye-outline" class="flex-grow-1" @click="goToAlbumImages(album.album_id)">浏览</v-btn>
          <template v-if="!album.isDefault">
            <v-divider vertical />
            <v-btn size="small" variant="text" color="grey-darken-1" icon="mdi-pencil-outline" @click="openEditAlbumDialog(album)">
              <v-icon size="18" /><v-tooltip activator="parent" location="top">编辑</v-tooltip>
            </v-btn>
            <v-btn size="small" variant="text" color="red" icon="mdi-delete-outline" @click="openDeleteAlbumDialog(album)">
              <v-icon size="18" /><v-tooltip activator="parent" location="top">删除</v-tooltip>
            </v-btn>
          </template>
        </div>
      </v-card>

      <v-card class="album-card album-card--create" variant="outlined" @click="openCreateAlbumDialog">
        <div class="album-card__create-content">
          <v-icon icon="mdi-folder-plus-outline" size="48" color="primary" class="mb-3" />
          <div class="text-body-2 font-weight-medium mb-1">创建相册</div>
          <div class="text-caption text-grey-darken-1">新建一个相册来整理图片</div>
        </div>
      </v-card>
    </div>

    <!-- 创建/编辑对话框 -->
    <v-dialog v-model="albumDialog" max-width="480">
      <v-card>
        <v-card-title class="pa-4">
          <v-icon :icon="albumDialogMode === 'create' ? 'mdi-folder-plus-outline' : 'mdi-folder-edit-outline'" class="mr-2" />
          {{ albumDialogTitle }}
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="albumForm.name" label="相册名称" variant="outlined" density="comfortable" :error-messages="albumFormErrors.name" counter="50" maxlength="50" class="mb-3" prepend-inner-icon="mdi-folder-outline" />
          <v-textarea v-model="albumForm.description" label="描述（可选）" variant="outlined" density="comfortable" rows="3" counter="200" maxlength="200" prepend-inner-icon="mdi-text-short" hide-details />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="albumDialog = false">取消</v-btn>
          <v-btn color="primary" :loading="albumSaving" @click="saveAlbum">{{ albumDialogMode === 'create' ? '创建' : '保存' }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 删除确认对话框 -->
    <v-dialog v-model="albumDeleteDialog" max-width="400">
      <v-card>
        <v-card-title class="pa-4">
          <v-icon icon="mdi-delete-alert-outline" color="red" class="mr-2" />
          确认删除
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <div class="text-body-2">确定要删除相册 <strong>{{ albumDeleteTarget?.name }}</strong> 吗？</div>
          <div class="text-caption text-grey-darken-1 mt-2">此操作不可撤销，相册内的图片不会被删除。</div>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-spacer />
          <v-btn variant="text" @click="albumDeleteDialog = false">取消</v-btn>
          <v-btn color="red" variant="flat" :loading="albumDeleting" @click="confirmDeleteAlbum">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
/* 顶部导航栏（对齐 MP HeaderTab 风格） */
.zpic-tab-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  margin: -16px -16px 0 -16px;
  padding: 2px 16px 2px;
  background: rgba(var(--v-theme-background), 0.95);
  backdrop-filter: blur(12px);
}

.zpic-tab-items {
  position: relative;
  display: flex;
  flex-grow: 1;
  gap: 12px;
  padding: 4px 0;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.zpic-tab-items::-webkit-scrollbar {
  display: none;
}

.zpic-tab-item {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: 20px;
  background-color: transparent;
  color: rgba(var(--v-theme-on-background), 0.7);
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 6px 14px;
  text-shadow: 0 1px 3px rgba(0, 0, 0, 10%);
  transition: all 0.2s ease;
  white-space: nowrap;
  user-select: none;
  flex-shrink: 0;
}

/* 激活态底部下划线（MP 原生风格：3px 粗、70% 宽、底部外侧 4px） */
.zpic-tab-item::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: -4px;
  width: 70%;
  height: 3px;
  border-radius: 3px;
  background-color: rgb(var(--v-theme-primary));
  transform: translateX(-50%) scaleX(0);
  transition: transform 0.2s ease;
}

.zpic-tab-item.active {
  color: rgb(var(--v-theme-primary));
  text-shadow: 0 1px 3px rgba(0, 0, 0, 15%);
}

.zpic-tab-item.active::after {
  transform: translateX(-50%) scaleX(1);
}

.zpic-tab-item-icon {
  color: rgba(var(--v-theme-on-background), 0.6);
  margin-right: 6px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 10%);
  transition: color 0.2s ease;
}

.zpic-tab-item.active .zpic-tab-item-icon {
  color: rgb(var(--v-theme-primary));
  text-shadow: 0 1px 3px rgba(0, 0, 0, 15%);
}

.zpic-tab-item:hover:not(.active) {
  background-color: rgba(var(--v-theme-primary), 0.05);
  color: rgba(var(--v-theme-on-background), 1);
}

.zpic-upload-page { max-width: 100%; padding: 12px 16px; }
.upload-options-card { border-radius: 12px; background-color: rgb(var(--v-theme-surface)); }
.upload-switch-item { display: flex; align-items: center; }
.upload-switch-label { font-size: 0.875rem; margin-right: 16px; white-space: nowrap; user-select: none; color: rgba(var(--v-theme-on-background), 0.85); }
.upload-link-chip { cursor: pointer; transition: transform 0.15s ease, filter 0.15s ease; }
.upload-link-chip:hover { transform: scale(1.08); filter: brightness(1.15); }
.upload-link-chip:active { transform: scale(0.95); }
.upload-dropzone-card { border-radius: 12px; background-color: rgb(var(--v-theme-surface)); }
.upload-dropzone { border: 2px dashed rgba(var(--v-theme-primary), 0.3); border-radius: 12px; cursor: pointer; transition: all 0.3s ease; padding: 24px 16px; text-align: center; }
.upload-dropzone:hover { border-color: rgba(var(--v-theme-primary), 0.6); background-color: rgba(var(--v-theme-primary), 0.05); }
.upload-dropzone.dropzone-active { border-color: rgb(var(--v-theme-primary)); background-color: rgba(var(--v-theme-primary), 0.1); transform: scale(1.01); }
.upload-dropzone.dropzone-disabled { opacity: 0.6; cursor: not-allowed; }
.result-thumbnail { width: 60px; height: 60px; border-radius: 8px; overflow: hidden; flex-shrink: 0; }
.thumbnail-img { width: 100%; height: 100%; object-fit: cover; }
.thumbnail-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background-color: rgba(var(--v-theme-surface-variant), 0.3); border-radius: 8px; }
.result-success { background-color: rgba(76, 175, 80, 0.05); border-radius: 8px; }
.result-error { background-color: rgba(244, 67, 54, 0.05); border-radius: 8px; }
:deep(.v-list-item) { padding: 12px 16px; border-radius: 8px; }
/* 图片列表视图 */
.zpic-images-page { max-width: 100%; padding: 12px 16px 0; }
.image-list-card { border-radius: 12px !important; overflow: hidden; }
.image-list { padding-top: 0 !important; padding-bottom: 0 !important; }
.image-list :deep(.v-list-item) { border-radius: 0 !important; }
.image-list :deep(.v-list-item:hover),
.image-list :deep(.v-list-item--active),
.image-list :deep(.v-list-item--variant-text .v-list-item__overlay) { border-radius: 0 !important; }
.view-toggle-group { display: flex; gap: 6px; }
.image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.image-card { cursor: pointer; transition: all 0.2s ease; overflow: hidden; position: relative; }
.image-card--selected { border-color: rgb(var(--v-theme-primary)) !important; background-color: rgba(var(--v-theme-primary), 0.06); }
.image-card__checkbox { position: absolute; top: 6px; left: 6px; z-index: 2; }
.image-list-item--selected { background-color: rgba(var(--v-theme-primary), 0.06); border-radius: 0 !important; }
.image-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.image-card__thumb { position: relative; overflow: hidden; }
.image-card__img { transition: transform 0.3s ease; }
.image-card:hover .image-card__img { transform: scale(1.05); }
.image-card__info { padding: 8px 10px; }
.image-card__name { font-size: 13px; font-weight: 500; }
.image-card__meta { font-size: 11px; }
.image-card__actions { display: flex; align-items: center; gap: 6px; margin-left: 6px; }
.image-card__actions .v-btn { width: 24px; height: 24px; min-width: 24px; }
.image-card__actions .v-btn .v-icon { font-size: 16px !important; }
.images-pagination { line-height: 1; }
.images-pagination :deep(.v-pagination) { margin-bottom: 0; }
.preview-container { background: rgba(var(--v-theme-surface-variant), 0.3); display: flex; align-items: center; justify-content: center; }
@media (max-width: 600px) {
  .image-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
}

/* 相册管理视图 */
.zpic-albums-page { max-width: 100%; padding: 12px 16px; }
.album-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.album-card { transition: all 0.2s ease; overflow: hidden; }
.album-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.album-card--create { cursor: pointer; border-style: dashed !important; }
.album-card__create-content { min-height: 256px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; text-align: center; background: rgba(var(--v-theme-primary), 0.04); }
.album-card__cover { position: relative; cursor: pointer; overflow: hidden; }
.album-card__img { transition: transform 0.3s ease; }
.album-card:hover .album-card__img { transform: scale(1.05); }
.album-card__cover-placeholder { height: 160px; display: flex; align-items: center; justify-content: center; background: rgba(var(--v-theme-surface-variant), 0.2); }
.album-card__count { position: absolute; bottom: 8px; right: 8px; }
.album-card__body { min-height: 60px; padding: 12px 16px; }
.album-card__name { line-height: 1.4; }
.album-card__desc { line-height: 1.4; font-size: 12px; }
.album-card__actions { border-top: none !important; }
@media (max-width: 600px) {
  .album-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 10px; }
  .album-card__cover-placeholder { height: 120px; }
  .album-card__create-content { min-height: 216px; }
}
</style>
