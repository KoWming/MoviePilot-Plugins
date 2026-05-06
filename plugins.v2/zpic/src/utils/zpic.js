export const PLUGIN_ID = 'Zpic'

export function pluginPath(path = '') {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `/api/v1/plugin/${PLUGIN_ID}${normalized}`
}

export async function pluginRequest(api, path, options = {}) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  const apiPath = `plugin/${PLUGIN_ID}${normalized}`
  const method = (options.method || 'GET').toUpperCase()
  const payload = options.body ?? options.payload ?? undefined

  if (method === 'POST' && api?.post) {
    return api.post(apiPath, payload || {}, options)
  }
  if (method === 'GET' && api?.get) {
    return api.get(apiPath, options)
  }

  const response = await fetch(pluginPath(normalized), {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    body: method === 'POST' ? JSON.stringify(payload || {}) : undefined,
  })
  return response.json()
}

export function formatBytes(value) {
  const size = Number(value || 0)
  if (!size) {
    return '0 B'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const index = Math.min(Math.floor(Math.log(size) / Math.log(1024)), units.length - 1)
  const num = size / Math.pow(1024, index)
  return `${num.toFixed(num >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

export function formatDate(value) {
  if (!value) {
    return '-'
  }
  return String(value).replace('T', ' ').replace(/\.\d+Z?$/, '')
}

export function calcPercent(used, total) {
  const totalNum = Number(total || 0)
  const usedNum = Number(used || 0)
  if (!totalNum) {
    return 0
  }
  return Math.min(100, Math.max(0, Math.round((usedNum / totalNum) * 100)))
}

export async function copyText(text) {
  if (!text) {
    return false
  }
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']
const MAX_SIZE = 10 * 1024 * 1024 // 10MB

export function validateImageFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return { valid: false, message: `不支持的格式: ${file.type || '未知'}` }
  }
  if (file.size > MAX_SIZE) {
    return { valid: false, message: `文件过大: ${file.name}（最大 10MB）` }
  }
  return { valid: true }
}

export function getFormatLabel(type) {
  const map = {
    'image/jpeg': 'JPG',
    'image/png': 'PNG',
    'image/gif': 'GIF',
    'image/bmp': 'BMP',
    'image/webp': 'WebP',
  }
  return map[type] || type?.split('/')[1]?.toUpperCase() || '?'
}

export async function uploadFiles(api, files, options = {}) {
  const apiPath = `plugin/${PLUGIN_ID}/upload`
  const formData = new FormData()

  // 逐个添加文件（FastAPI UploadFile 参数名是 'file'）
  for (const file of files) {
    formData.append('file', file)
  }

  // 直接作为 FormData 字段传递（FastAPI Form 参数会从 form 中读取）
  if (options.albumId !== undefined) formData.append('album_id', String(options.albumId))
  if (options.compress !== undefined) formData.append('compress', String(options.compress))
  if (options.watermark !== undefined) formData.append('watermark', String(options.watermark))
  if (options.dedup !== undefined) formData.append('dedup', String(options.dedup))

  // 使用 api.post() 发送请求（自动携带 MP 鉴权 token）
  if (api?.post) {
    const res = await api.post(apiPath, formData)
    // api.post 响应拦截器已解包 response.data，res 即为 { success, data, ... }
    return res
  }

  // 降级方案：使用 fetch
  const response = await fetch(pluginPath('/upload'), {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    return { success: false, message: `HTTP ${response.status}` }
  }
  return response.json()
}
