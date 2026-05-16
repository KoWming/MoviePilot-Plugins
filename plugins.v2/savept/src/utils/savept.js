export const PLUGIN_ID = 'Savept'

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

export function getStatusMeta(status) {
  switch (status) {
    case 'healthy':
      return { label: '健康', color: '#22c55e', chip: 'success', icon: 'mdi-heart-pulse', cardClass: 'savept-site-card--healthy' }
    case 'critical':
      return { label: '病危', color: '#ef4444', chip: 'error', icon: 'mdi-alert-circle', cardClass: 'savept-site-card--critical' }
    case 'closed':
      return { label: '死亡', color: '#94a3b8', chip: 'grey', icon: 'mdi-skull-outline', cardClass: 'savept-site-card--closed' }
    default:
      return { label: '未知', color: '#94a3b8', chip: 'grey', icon: '', cardClass: '' }
  }
}

export function getMpStatusMeta(status) {
  switch (status) {
    case 'owned':
      return { label: 'MP已拥有', color: '#22c55e', icon: 'mdi-check-decagram', chipClass: 'owned' }
    case 'available':
      return { label: 'MP可添加', color: '#3b82f6', icon: 'mdi-plus-circle', chipClass: 'available' }
    default:
      return { label: 'MP未收录', color: '#94a3b8', icon: 'mdi-help-circle', chipClass: 'unsupported' }
  }
}

export function normalizeText(value, fallback = '-') {
  const text = value == null ? '' : String(value).trim()
  return text || fallback
}

export function buildSiteKeywords(site) {
  return [site.name, site.search, site.year, site.status_text, site.site_type].filter(Boolean).join(' ').toLowerCase()
}

export function buildNoticeSections(alerts = []) {
  const grouped = {
    critical: [],
    success: [],
    info: [],
    error: [],
  }

  for (const alert of alerts) {
    const level = alert?.level
    const text = `${alert?.text || ''}`.trim()
    if (grouped[level] && text) {
      grouped[level].push(text)
    }
  }

  return [
    { key: 'critical', title: '⚠️病危通知：', items: grouped.critical },
    { key: 'success', title: '✅恢复公告：', items: grouped.success },
    { key: 'info', title: '🎉站庆预告：', items: grouped.info },
    { key: 'error', title: '🕯️死亡讣告：', items: grouped.error },
  ]
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function appendNoticeTextToken(tokens, text) {
  if (!text) {
    return
  }

  const lastToken = tokens[tokens.length - 1]
  if (lastToken?.type === 'text') {
    lastToken.text += text
    return
  }

  tokens.push({ type: 'text', text })
}

function buildNoticeSiteNames(sites = []) {
  return Array.from(new Set(
    sites
      .map(site => `${site?.name || ''}`.trim())
      .filter(Boolean),
  )).sort((a, b) => b.length - a.length)
}

function detectNoticeSiteName(segmentText, siteNames) {
  const raw = `${segmentText || ''}`
  const trimmed = raw.trim()
  if (!trimmed) {
    return null
  }

  const colonMatch = raw.match(/^(.*?[：:]\s*)(.+)$/)
  const prefix = colonMatch ? colonMatch[1] : ''
  const body = colonMatch ? colonMatch[2] : raw
  const trimmedBody = body.trimStart()
  const bodyLeadingWhitespace = body.slice(0, body.length - trimmedBody.length)

  const knownSite = siteNames.find(name => {
    const sitePattern = new RegExp(`^${escapeRegExp(name)}(?=\s|$)`)
    return sitePattern.test(trimmedBody)
  })

  if (knownSite) {
    return {
      prefix: `${prefix}${bodyLeadingWhitespace}`,
      siteName: knownSite,
      suffix: trimmedBody.slice(knownSite.length),
    }
  }

  const heuristicMatch = trimmedBody.match(/^(.+?)(?=\s(?:已抢救|已|还有|抢救|于))/)
  if (heuristicMatch?.[1]) {
    const siteName = heuristicMatch[1].trim()
    if (siteName) {
      return {
        prefix: `${prefix}${bodyLeadingWhitespace}`,
        siteName,
        suffix: trimmedBody.slice(heuristicMatch[1].length),
      }
    }
  }

  return null
}

function tokenizeNoticeSegment(segmentText, siteNames) {
  const raw = `${segmentText || ''}`
  if (!raw) {
    return []
  }

  const detected = detectNoticeSiteName(raw, siteNames)
  if (!detected) {
    return [{ type: 'text', text: raw }]
  }

  const tokens = []
  appendNoticeTextToken(tokens, detected.prefix)
  tokens.push({ type: 'site', text: detected.siteName })
  appendNoticeTextToken(tokens, detected.suffix)
  return tokens
}

export function tokenizeNoticeText(text, sites = []) {
  const content = `${text || ''}`
  if (!content.trim()) {
    return []
  }

  const siteNames = buildNoticeSiteNames(sites)
  const tokens = []
  const segments = content.split(/(\s*\|\s*)/)

  for (const segment of segments) {
    if (!segment) {
      continue
    }

    if (segment.includes('|')) {
      appendNoticeTextToken(tokens, segment)
      continue
    }

    for (const token of tokenizeNoticeSegment(segment, siteNames)) {
      if (token.type === 'text') {
        appendNoticeTextToken(tokens, token.text)
      } else {
        tokens.push(token)
      }
    }
  }

  return tokens
}
