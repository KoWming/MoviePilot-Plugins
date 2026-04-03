<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'


const props = defineProps({
  api: {
    type: Object,
    default: () => {}
  }
})

const emit = defineEmits(['action', 'switch', 'close'])

interface Medal {
  medal_id?: string | number
  name: string
  description: string
  imageSmall: string
  saleBeginTime: string
  saleEndTime: string
  price: string | number
  site: string
  purchase_status: string
  gift_status: string
  bonus_rate?: string
  stock?: string
  stock_status?: string
  validity?: string
  purchase_type?: string
  currency?: string
  gift_fee?: string
  group?: string
  new_time?: string
  wear_status?: string
}

const medals = ref<Medal[]>([])
const loading = ref(false)
const refreshing = ref(false)
const clearingCache = ref(false)
const successMessage = ref('')
const errorMessage = ref('')
const purchaseDialog = ref(false)
const purchaseFeedbackDialog = ref(false)
const purchaseLoading = ref(false)
const purchaseFeedbackType = ref<'success' | 'error'>('success')
const purchaseFeedbackTitle = ref('')
const purchaseFeedbackMessage = ref('')
const selectedMedal = ref<Medal | null>(null)
const wearLoading = ref(false)
const wearDialog = ref(false)
const wearAction = ref<'wear' | 'unwear'>('wear')

// Computed stats
const totalMedals = computed(() => medals.value.length)
const siteCount = computed(() => {
  const sites = new Set(medals.value.map(m => m.site))
  return sites.size
})
const ownedMedals = computed(() => {
  return medals.value.filter(m => (m.purchase_status || '').trim() === '已拥有').length
})
const availableMedals = computed(() => {
  return medals.value.filter(m => {
    const status = (m.purchase_status || '').trim()
    if (status === '购买' || status === '赠送') {
      return checkTimeValidity(m.saleBeginTime, m.saleEndTime)
    }
    return false
  }).length
})


const refreshingSites = ref<Record<string, boolean>>({})
const config = ref<any>(null)
const allSites = ref<any[]>([])

const expandedSite = ref<string | null>(null)
const activeTab = ref<string | null>(null)

onMounted(async () => {
  await Promise.all([fetchMedals(), fetchConfig(), fetchSites()])
})

// 检查当前时间是否在范围内 (对齐后端 is_current_time_in_range 逻辑)
function checkTimeValidity(startTime: string, endTime: string): boolean {
  if (!startTime || !endTime) return false
  if (startTime.includes('不限') || endTime.includes('不限')) return true
  if (startTime.includes('长期') || endTime.includes('长期')) return true
  
  // 处理可能存在的波浪号
  const start = startTime.split('~')[0].trim()
  const end = endTime.split('~')[0].trim()
  
  const now = new Date()
  
  // 尝试解析时间
  const startDate = new Date(start)
  const endDate = new Date(end)
  
  if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
    return false
  }
  
  return now >= startDate && now <= endDate
}

async function fetchMedals() {
  loading.value = true
  try {
    const data = await props.api.get('plugin/MedalWallPro/medals')
    if (data) {
      medals.value = data
      // Check for forced refresh result
      if (data.length === 0) {
          // If empty, maybe try to fetch again if it was a cold start? 
          // keeping it simple for now.    
      }
    }
  } catch (e) {
    console.error('Failed to fetch medals', e)
    showNotification('获取勋章数据失败', 'error')
  } finally {
    loading.value = false
  }
}

async function fetchConfig() {
  try {
    config.value = await props.api.get('plugin/MedalWallPro/config')
  } catch (e) {
    console.error('Failed to fetch config', e)
  }
}

async function fetchSites() {
  try {
    allSites.value = await props.api.get('plugin/MedalWallPro/sites')
  } catch (e) {
    console.error('Failed to fetch sites', e)
  }
}

// 根据站点名称获取站点ID
function getSiteIdByName(siteName: string): string | null {
  const site = allSites.value.find(s => s.title === siteName)
  return site ? site.value : null
}

async function runTask() {
  refreshing.value = true
  try {
    const res = await props.api.post('plugin/MedalWallPro/run')
    if (res && res.success) {
      showNotification('刷新请求已发送,请稍候...', 'success')
      // Poll for updates or just wait a bit
      setTimeout(fetchMedals, 3000)
    } else {
      showNotification(res?.message || '刷新失败', 'error')
    }
  } catch (e: any) {
    console.error('Task run failed', e)
    showNotification('刷新失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    refreshing.value = false
  }
}

// 单站点刷新方法
async function refreshSingleSite(siteName: string, siteId: string) {
  refreshingSites.value[siteName] = true
  
  try {
    const res = await props.api.post('plugin/MedalWallPro/refresh_site', { site_id: siteId })
    
    if (res && res.success) {
      showNotification(`${siteName} 刷新成功`, 'success')
      // 重新加载数据
      await fetchMedals()
    } else {
      throw new Error(res?.message || '刷新失败')
    }
  } catch (e: any) {
    console.error('Single site refresh failed', e)
    showNotification(`${siteName} 刷新失败: ${e.message || '未知错误'}`, 'error')
  } finally {
    refreshingSites.value[siteName] = false
  }
}

// 清理缓存方法
async function clearCache() {
  clearingCache.value = true
  try {
    const res = await props.api.post('plugin/MedalWallPro/clear_cache')
    if (res && res.success) {
      showNotification('缓存已清理', 'success')
      // 清理缓存后自动刷新数据
      await fetchMedals()
    } else {
      showNotification(res?.message || '清理缓存失败', 'error')
    }
  } catch (e: any) {
    console.error('Clear cache failed', e)
    showNotification('清理缓存失败: ' + (e.message || '未知错误'), 'error')
  } finally {
    clearingCache.value = false
  }
}

function showNotification(message: string, type: 'success' | 'error' = 'success') {
  if (type === 'success') {
    successMessage.value = message
    setTimeout(() => successMessage.value = '', 3000)
  } else {
    errorMessage.value = message
    setTimeout(() => errorMessage.value = '', 3000)
  }
}

function canPurchase(medal: Medal) {
  const status = (medal.purchase_status || '').trim()
  return status === '购买' && checkTimeValidity(medal.saleBeginTime, medal.saleEndTime) && !!medal.medal_id
}

function canToggleWear(medal: Medal) {
  return isOwned(medal) && !!medal.medal_id
}

function isWorn(medal: Medal) {
  return (medal.wear_status || '').trim() === '已佩戴'
}

function openPurchaseDialog(medal: Medal) {
  selectedMedal.value = medal
  purchaseDialog.value = true
}

function closePurchaseDialog() {
  purchaseDialog.value = false
  selectedMedal.value = null
}

function openWearDialog(medal: Medal, action: 'wear' | 'unwear') {
  selectedMedal.value = medal
  wearAction.value = action
  wearDialog.value = true
}

function closeWearDialog() {
  wearDialog.value = false
  selectedMedal.value = null
}

function showPurchaseFeedback(title: string, message: string, type: 'success' | 'error') {
  purchaseFeedbackTitle.value = title
  purchaseFeedbackMessage.value = message
  purchaseFeedbackType.value = type
  purchaseFeedbackDialog.value = true
}

async function confirmPurchase() {
  if (!selectedMedal.value) return
  const siteId = getSiteIdByName(selectedMedal.value.site)
  if (!siteId) {
    showPurchaseFeedback('购买失败', '未找到对应站点ID', 'error')
    return
  }

  purchaseLoading.value = true
  try {
    const res = await props.api.post('plugin/MedalWallPro/purchase_medal', {
      site_id: siteId,
      medal: selectedMedal.value
    })

    purchaseDialog.value = false

    if (res && res.success) {
      showPurchaseFeedback(
        '购买成功',
        res.message || `已成功购买 ${selectedMedal.value.name}`,
        'success'
      )
      showNotification(res.message || `已成功购买 ${selectedMedal.value.name}`, 'success')
      await fetchMedals()
    } else {
      showPurchaseFeedback(
        '购买失败',
        res?.message || `购买 ${selectedMedal.value.name} 失败`,
        'error'
      )
      showNotification(res?.message || `购买 ${selectedMedal.value.name} 失败`, 'error')
    }
  } catch (e: any) {
    purchaseDialog.value = false
    showPurchaseFeedback('购买失败', e?.message || '未知错误', 'error')
    showNotification(`购买失败: ${e?.message || '未知错误'}`, 'error')
  } finally {
    purchaseLoading.value = false
  }
}

async function confirmWearAction() {
  if (!selectedMedal.value) return
  const targetMedal = selectedMedal.value
  const siteId = getSiteIdByName(selectedMedal.value.site)
  if (!siteId) {
    showPurchaseFeedback('操作失败', '未找到对应站点ID', 'error')
    return
  }

  wearLoading.value = true
  const isWear = wearAction.value === 'wear'
  const actionTitle = isWear ? '佩戴' : '取下'
  const apiPath = isWear ? 'plugin/MedalWallPro/wear_medal' : 'plugin/MedalWallPro/unwear_medal'

  try {
    const res = await props.api.post(apiPath, {
      site_id: siteId,
      medal: selectedMedal.value
    })

    wearDialog.value = false

    if (res && res.success) {
      targetMedal.wear_status = isWear ? '已佩戴' : '未佩戴'
      showPurchaseFeedback(
        `${actionTitle}成功`,
        res.message || `${targetMedal.name}${actionTitle}成功`,
        'success'
      )
      showNotification(res.message || `${targetMedal.name}${actionTitle}成功`, 'success')
      await fetchMedals()
    } else {
      showPurchaseFeedback(
        `${actionTitle}失败`,
        res?.message || `${targetMedal.name}${actionTitle}失败`,
        'error'
      )
      showNotification(res?.message || `${targetMedal.name}${actionTitle}失败`, 'error')
    }
  } catch (e: any) {
    wearDialog.value = false
    showPurchaseFeedback(`${actionTitle}失败`, e?.message || '未知错误', 'error')
    showNotification(`${actionTitle}失败: ${e?.message || '未知错误'}`, 'error')
  } finally {
    wearLoading.value = false
  }
}

function notifySwitch() {
  emit('switch', 'config')
}

function notifyClose() {
  emit('close')
}

const groupedMedals = computed(() => {
  const groups: Record<string, Medal[]> = {}
  
  // 获取配置中已启用的站点名称集合
  const enabledSiteNames = new Set<string>()
  if (config.value && config.value.chat_sites) {
    config.value.chat_sites.forEach((siteId: string) => {
      const site = allSites.value.find(s => s.value === siteId)
      if (site) {
        enabledSiteNames.add(site.title)
      }
    })
  } else if (allSites.value.length > 0) {
  }

  // 先将已有勋章按站点分组
  medals.value.forEach(medal => {
    // 只有在配置中启用的站点才显示
    if (config.value && config.value.chat_sites && !enabledSiteNames.has(medal.site)) {
        return
    }
    
    if (!groups[medal.site]) {
      groups[medal.site] = []
    }
    groups[medal.site].push(medal)
  })

  // 添加配置中的站点(即使没有勋章数据)
  if (config.value && config.value.chat_sites) {
    config.value.chat_sites.forEach((siteId: string) => {
      // 根据siteId查找站点名称
      const site = allSites.value.find(s => s.value === siteId)
      const siteName = site ? site.title : siteId
      
      // 如果这个站点还没有数据,添加空数组占位
      if (!groups[siteName]) {
        groups[siteName] = []
      }
    })
  }

  return Object.keys(groups).map(site => {
    const siteMedals = groups[site]
    const ownedCount = siteMedals.filter(m => isOwned(m)).length
    const totalCount = siteMedals.length
    const progress = totalCount > 0 ? Math.round((ownedCount / totalCount) * 100) : 0
    
    // Sort medals: owned first, then purchasable, then others
    siteMedals.sort((a, b) => {
      const ownedA = isOwned(a)
      const ownedB = isOwned(b)
      if (ownedA && !ownedB) return -1
      if (!ownedB && ownedA) return 1
      if (ownedA === ownedB) {
         // If same ownership status, check purchase status
         const statusA = (a.purchase_status || '')
         const statusB = (b.purchase_status || '')
         const buyA = statusA.includes('购买') || statusA.includes('赠送')
         const buyB = statusB.includes('购买') || statusB.includes('赠送')
         if (buyA && !buyB) return -1
         if (!buyA && buyB) return 1
      }
      return 0
    })
    
    return {
      site,
      medals: siteMedals,
      ownedCount,
      totalCount,
      progress
    }
  }).sort((a, b) => b.ownedCount - a.ownedCount) // Sort sites by owned count descending
})

function isOwned(medal: Medal) {
  // 严格匹配已拥有状态，对齐后端
  const status = (medal.purchase_status || '').trim()
  return status === '已拥有'
}

const toggleDetails = (siteName: string) => {
  if (expandedSite.value === siteName) {
    expandedSite.value = null;
    activeTab.value = null; // 重置选中标签
  } else {
    expandedSite.value = siteName;
    // 重置选中标签为第一个分组（如果有）
    const site = groupedMedals.value.find(s => s.site === siteName); // Use groupedMedals here
    if (site && hasGroups(site.medals)) {
        const groups = getGroupNames(site.medals);
        if (groups.length > 0) {
            activeTab.value = groups[0];
        }
    } else {
        activeTab.value = null;
    }
  }
};

// 检查是否有分组数据
const hasGroups = (medals: Medal[]) => {
  return medals.some(medal => !!medal.group);
};

// 获取所有唯一的分组名称
const getGroupNames = (medals: Medal[]) => {
  const groups = new Set<string>();
  medals.forEach(medal => {
    if (medal.group) {
      groups.add(medal.group);
    }
  });
  return Array.from(groups);
};

// 根据当前选中的 tab 获取要显示的勋章
const getDisplayMedals = (medals: Medal[]) => {
  if (!hasGroups(medals) || !activeTab.value) {
    return medals;
  }
  return medals.filter(medal => medal.group === activeTab.value);
};


function getCurrency(medal: Medal) {
  return medal.currency || '魔力'
}

// 后端已将 UBits 图片转换为 Base64 Data URI，直接返回即可
function getProxiedImageUrl(imageUrl: string) {
  return imageUrl || ''
}

function formatPrice(price: string | number) {
  if (!price) return '0'
  return price.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")
}

// 根据勋章描述判断显示尺寸
function getMedalSize(medal: Medal): { stack: number, detail: number } {
  const desc = medal.description || ''
  const name = medal.name || ''
  const site = medal.site || ''
  
  // 只有 OurBits（我堡）站点需要区分大小勋章
  const isOurBits = site.toLowerCase().includes('ourbits') || site.includes('我堡')
  
  if (isOurBits) {
    // 检查是否为大徽章
    if (desc.includes('大徽章') || desc.includes('大') || name.includes('（大）')) {
      return { stack: 100, detail: 90 }  // 大徽章：顶部轮播100px，详情90px
    }
    // 检查是否为小徽章
    else if (desc.includes('小徽章') || desc.includes('小') || name.includes('（小）')) {
      return { stack: 60, detail: 50 }   // 小徽章：顶部轮播60px，详情50px
    }
  }
  
  // 其他站点使用固定默认尺寸
  return { stack: 80, detail: 70 }     // 默认：顶部轮播80px，详情70px
}

// 判断是否需要圆形遮罩（针对 LongPT 站点的 MP 勋章）
function needsCircleMask(medal: Medal): boolean {
  const site = medal.site || ''
  const name = medal.name || ''
  // LongPT 站点的 MP 勋章是方形的，需要圆形遮罩
  return site.toLowerCase().includes('longpt') && name.toUpperCase() === 'MP'
}

// 判断是否需要移除黑色背景（针对藏宝阁站点的勋章）
function needsRemoveBlackBg(medal: Medal): boolean {
  const site = medal.site || ''
  // 藏宝阁站点的勋章有黑色背景，需要透明化处理
  return site.includes('藏宝阁') || site.toLowerCase().includes('cangbaoge')
}


// Get background style for stack item
function getStackItemStyle() {
  // 所有卡片使用统一的容器尺寸，确保轮播区域整齐一致
  // 图片大小通过 getMedalSize 动态控制
  // 背景色交由CSS控制,以支持深色模式
  return {
    border: '1px solid rgba(0,0,0,0.05)',
    boxShadow: '0 2px 6px rgba(0,0,0,0.05)',
    width: '110px',      // 固定宽度
    height: '140px'      // 固定高度
  }
}

// Get background style for dialog card
function getCardStyle() {
  return {
    // 还原旧版样式：移除自定义背景，使用CSS类定义的背景色
    // Revert to old style: Remove custom background, use CSS class
    border: 'thin solid rgba(255, 255, 255, 0.1)',
    transition: 'transform 0.2s, box-shadow 0.2s',
    boxShadow: '0 2px 8px rgba(22,177,255,0.08)' // Old version shadow
  }
}


function getStatusColor(medal: Medal) {
  if (isOwned(medal)) return 'light-green-accent-4'
  const status = medal.purchase_status || ''
  if (status.includes('已过') || status.includes('未到')) return 'light-blue-accent-4'
  if (status.includes('库存不足')) return 'orange-darken-1'
  if (status.includes('购买') || status.includes('赠送')) return 'light-green-accent-4'
  return 'grey'
}
</script>

<template>
  <div class="plugin-page" id="medalwall-pro-page">
    
    <!-- SVG Filters Definition -->
    <svg style="position: absolute; width: 0; height: 0; pointer-events: none;" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="remove-black-bg" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">
          <!-- 1. Map luminance to Alpha channel: bright=opaque, dark=transparent -->
          <feColorMatrix type="luminanceToAlpha" in="SourceGraphic" result="luma"/>
          
          <!-- 2. Sharpen the Alpha mask: Cut off dark greys near black -->
          <feComponentTransfer in="luma" result="mask">
             <!-- slope=7, intercept=-0.5
                  Input < 0.07 (dark) -> Alpha 0
                  Input > 0.21 (mid-bright) -> Alpha 1
                  This ensures deep blacks/dark greys become fully transparent -->
             <feFuncA type="linear" slope="7" intercept="-0.5"/>
          </feComponentTransfer>
          
          <!-- 3. Composite original image with the generated mask -->
          <feComposite in="SourceGraphic" in2="mask" operator="in" />
        </filter>
      </defs>
    </svg>

    <v-card flat class="rounded border">
      <!-- Header -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary">
        <v-icon icon="mdi-medal-outline" class="mr-2" color="white" size="small"></v-icon>
        <span class="text-white">勋章墙 Pro</span>
        <v-spacer></v-spacer>
        
        <v-btn-group variant="outlined" density="compact" class="mr-1">
          <v-btn color="white" @click="runTask" :loading="refreshing" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-refresh" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">刷新</span>
            <v-tooltip activator="parent" location="bottom">全局刷新</v-tooltip>
          </v-btn>
          <v-btn color="white" @click="clearCache" :loading="clearingCache" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-delete-sweep" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">清缓存</span>
            <v-tooltip activator="parent" location="bottom">清理缓存</v-tooltip>
          </v-btn>
          <v-btn color="white" @click="notifySwitch" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-cog" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">设置</span>
          </v-btn>
          <v-btn color="white" @click="notifyClose" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </v-card-title>
      
      <v-card-text class="px-0 py-2" style="position: relative;">
        <!-- Notification Area -->
        <div style="position: absolute; top: 0; left: 0; right: 0; z-index: 50; padding: 0 10px 10px 10px;">
          <transition name="slide-fade">
            <v-alert v-if="successMessage" type="success" density="compact" class="mb-2 text-caption" variant="elevated" closable @click:close="successMessage = ''">
              {{ successMessage }}
            </v-alert>
          </transition>
          <transition name="slide-fade">
            <v-alert v-if="errorMessage" type="error" density="compact" class="mb-2 text-caption" variant="elevated" closable @click:close="errorMessage = ''">
              {{ errorMessage }}
            </v-alert>
          </transition>
        </div>

        <!-- Statistics Cards -->
        <div class="px-3 mb-3">
            <v-row dense>
              <v-col cols="6" sm="4" md>
                <v-card variant="tonal" color="info" class="pa-3 d-flex align-center rounded-lg">
                  <v-avatar color="info" variant="flat" class="mr-3" size="40">
                    <v-icon color="white" icon="mdi-web"></v-icon>
                  </v-avatar>
                  <div>
                    <div class="text-caption text-medium-emphasis">站点数量</div>
                    <div class="text-h6 font-weight-bold" style="line-height: 1.2">{{ siteCount }}</div>
                  </div>
                </v-card>
              </v-col>
              <v-col cols="6" sm="4" md>
                <v-card variant="tonal" color="primary" class="pa-3 d-flex align-center rounded-lg">
                  <v-avatar color="primary" variant="flat" class="mr-3" size="40">
                    <v-icon color="white" icon="mdi-medal"></v-icon>
                  </v-avatar>
                  <div>
                    <div class="text-caption text-medium-emphasis">勋章总数</div>
                    <div class="text-h6 font-weight-bold" style="line-height: 1.2">{{ totalMedals }}</div>
                  </div>
                </v-card>
              </v-col>
              <v-col cols="6" sm="4" md>
                <v-card variant="tonal" color="success" class="pa-3 d-flex align-center rounded-lg">
                  <v-avatar color="success" variant="flat" class="mr-3" size="40">
                    <v-icon color="white" icon="mdi-check-circle"></v-icon>
                  </v-avatar>
                  <div>
                    <div class="text-caption text-medium-emphasis">已拥有</div>
                    <div class="text-h6 font-weight-bold" style="line-height: 1.2">{{ ownedMedals }}</div>
                  </div>
                </v-card>
              </v-col>
              <v-col cols="6" sm="4" md>
                <v-card variant="tonal" color="green" class="pa-3 d-flex align-center rounded-lg">
                  <v-avatar color="green" variant="flat" class="mr-3" size="40">
                    <v-icon color="white" icon="mdi-cart"></v-icon>
                  </v-avatar>
                  <div>
                    <div class="text-caption text-medium-emphasis">可购买</div>
                    <div class="text-h6 font-weight-bold" style="line-height: 1.2">{{ availableMedals }}</div>
                  </div>
                </v-card>
              </v-col>
            </v-row>
        </div>
        
        <!-- Loading State -->
         <div v-if="loading && medals.length === 0" class="d-flex justify-center align-center py-10">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
            <span class="ml-3 text-grey">正在加载勋章数据...</span>
         </div>

        <!-- Empty State -->
        <v-empty-state
          v-if="!loading && medals.length === 0"
          icon="mdi-medal-off-outline"
          title="暂无勋章数据"
          text="请点击上方刷新按钮获取数据，或检查设置中的站点配置。"
          class="py-10"
        ></v-empty-state>

        <!-- Grouped Medals List -->
        <div v-if="groupedMedals.length > 0" class="pb-10">
          <div v-for="group in groupedMedals" :key="group.site" class="mb-6">
            <!-- Header -->
            <div class="d-flex align-center justify-space-between px-4 mb-2 cursor-pointer">
               <div class="d-flex align-center" @click="toggleDetails(group.site)">
                  <span class="text-h6 font-weight-bold mr-1">{{ group.site }}</span>
                  <v-chip v-if="group.progress === 100" color="success" size="x-small" variant="flat" class="font-weight-bold">全收集</v-chip>
                  <!-- 单站点刷新按钮 -->
                  <v-btn 
                    icon="mdi-refresh" 
                    size="x-small" 
                    variant="text" 
                    color="primary"
                    :loading="refreshingSites[group.site]"
                    @click.stop="refreshSingleSite(group.site, getSiteIdByName(group.site) || '')"
                    class="ml-1"
                  >
                    <v-icon>mdi-refresh</v-icon>
                    <v-tooltip activator="parent" location="bottom">单站刷新</v-tooltip>
                  </v-btn>
               </div>
               <div class="d-flex align-center text-caption text-grey">
                  <span class="mr-2">数量 {{ group.ownedCount }}/{{ group.totalCount }}</span>
                  <span class="mr-2">拥有率 {{ group.progress }}%</span>
                  <v-icon icon="mdi-chevron-right" class="ml-1 transition-transform" :class="{'rotate-90': expandedSite === group.site}" @click="toggleDetails(group.site)"></v-icon>
               </div>
            </div>

            <!-- Slide Group Stack -->
            <v-slide-group
              class="px-2"
              show-arrows="desktop"
              selected-class=""
              :key="group.medals.length"
            >
              <v-slide-group-item
                v-for="(medal, index) in group.medals"
                :key="index"
                :value="`medal-${index}`"
              >
                  <div 
                    class="medal-stack-item" 
                    style="margin: 0 4px;"
                    :style="getStackItemStyle()"
                  >
                    <!-- Corner ribbon -->
                    <div v-if="isOwned(medal)" class="medal-corner-ribbon medal-corner-ribbon-owned">
                      已拥有
                    </div>
                    <div v-else class="medal-corner-ribbon">
                      未拥有
                    </div>
                    
                     <div class="d-flex justify-center align-center pt-2 px-2" style="height: 100px;" @click="toggleDetails(group.site)">
                         <v-img 
                              :src="getProxiedImageUrl(medal.imageSmall)" 
                               :class="['medal-stack-image', { 'circle-mask': needsCircleMask(medal), 'remove-black-bg': needsRemoveBlackBg(medal) }]"
                               contain
                               :max-height="getMedalSize(medal).stack"
                               :max-width="getMedalSize(medal).stack"
                               loading="lazy"
                          >
                              <template v-slot:placeholder>
                                 <div class="d-flex align-center justify-center fill-height bg-transparent">
                                     <v-progress-circular indeterminate color="grey-lighten-2" size="20"></v-progress-circular>
                                 </div>
                             </template>
                        </v-img>
                    </div>
                    
                    
                    <div class="medal-stack-info" @click="toggleDetails(group.site)">
                        <div class="text-truncate text-caption text-center px-1 font-weight-bold text-grey-darken-1">
                            {{ medal.name }}
                        </div>
                    </div>
                  </div>
              </v-slide-group-item>
            </v-slide-group>
            
            <style>
              /* 强制隐藏小屏幕下的轮播按钮 */
              @media (max-width: 960px) {
                .v-slide-group__prev,
                .v-slide-group__next {
                  display: none !important;
                }
              }
            </style>
            <v-expand-transition>
               <div v-if="expandedSite === group.site" class="px-2 pt-4 pb-2 bg-grey-lighten-5 rounded-lg mt-2 mx-2">
                 
                 <!-- Group Tabs -->
                 <v-tabs
                   v-if="hasGroups(group.medals)"
                   v-model="activeTab"
                   color="primary"
                   align-tabs="start"
                   density="compact"
                   class="mb-4"
                 >
                   <v-tab
                     v-for="groupName in getGroupNames(group.medals)"
                     :key="groupName"
                     :value="groupName"
                     class="text-grey"
                   >
                     {{ groupName }}
                   </v-tab>
                 </v-tabs>

                 <v-row dense>
                  <v-col 
                    v-for="(medal, index) in getDisplayMedals(group.medals)" 
                    :key="index" 
                    cols="12" sm="6" md="4" xl="3"
                  >
                    <v-card 
                        class="mx-auto medal-card medal-item-card h-100 d-flex flex-row pa-2 align-center" 
                        hover 
                        variant="flat" 
                        elevation="2" 
                        density="compact"
                        :style="getCardStyle()"
                    >
                       <!-- Image Section (Left) -->
                       <div class="d-flex justify-center align-center mr-3 flex-shrink-0" :style="{ width: getMedalSize(medal).detail + 'px', minWidth: getMedalSize(medal).detail + 'px' }">
                          <v-img :src="getProxiedImageUrl(medal.imageSmall)" :max-height="getMedalSize(medal).detail" :max-width="getMedalSize(medal).detail" contain :class="['medal-image', { 'circle-mask': needsCircleMask(medal), 'remove-black-bg': needsRemoveBlackBg(medal) }]" loading="lazy"></v-img>
                       </div>
                       
                       <!-- Content Section (Right) -->
                       <div class="d-flex flex-column justify-center flex-grow-1 overflow-hidden" style="min-width: 0;">
                          
                          <!-- Name & Badges -->
                          <div class="d-flex align-center justify-space-between mb-1">
                              <div class="d-flex align-center overflow-hidden flex-grow-1 mr-2">
                                <div class="text-subtitle-2 font-weight-bold text-truncate flex-shrink-1 text-grey-darken-1" :title="medal.name">
                                   {{ medal.name }}
                                </div>
                             </div>
                             <div class="d-flex flex-shrink-0 align-center">
                                <v-chip 
                                  v-if="medal.bonus_rate" 
                                  size="x-small" 
                                  color="purple-lighten-5" 
                                  variant="flat" 
                                  class="px-2 mr-1 font-weight-bold text-purple-darken-2 rounded-pill" 
                                  style="height: 20px; font-size: 11px;"
                                >
                                   <v-icon start icon="mdi-star-four-points-outline" size="10" class="mr-1"></v-icon>
                                   {{ medal.bonus_rate }}
                                </v-chip>
                                <v-chip 
                                  v-if="medal.purchase_status" 
                                  size="x-small" 
                                  :color="getStatusColor(medal)" 
                                  variant="flat" 
                                  class="px-2 font-weight-bold text-white rounded-pill"
                                  style="height: 20px; font-size: 11px;"
                                >
                                   {{ isOwned(medal) ? '已拥有' : (medal.purchase_status || '未拥有') }}
                                </v-chip>
                             </div>
                          </div>
        
                          <!-- Price -->
                          <div class="d-flex align-center mb-1">
                             <div class="text-primary font-weight-bold text-caption">
                               {{ formatPrice(medal.price) }} <span style="font-size: 0.65rem;">{{ getCurrency(medal) }}</span>
                             </div>
                          </div>
        
                           <!-- Description -->
                          <div class="text-caption text-grey-darken-1 text-truncate mb-1" style="font-size: 0.65rem !important; max-width: 100%;" :title="medal.description">
                             {{ medal.description }}
                          </div>
                          
                           <!-- Times / Validity / Stock -->
                           <div class="text-caption text-grey-darken-1 d-flex flex-column mt-1" style="font-size: 0.7rem !important; line-height: 1.4;">
                              <div v-if="medal.saleBeginTime" class="d-flex align-center">
                                <span class="mr-1 font-weight-bold">开售:</span>
                                <span>{{ medal.saleBeginTime }}</span>
                              </div>
                              <div v-if="medal.saleEndTime" class="d-flex align-center">
                                <span class="mr-1 font-weight-bold">截止:</span>
                                <span>{{ medal.saleEndTime }}</span>
                              </div>
                              <div v-if="medal.validity" class="d-flex align-center">
                               <span class="mr-1 font-weight-bold">有效期:</span>
                               <span>{{ medal.validity }}</span>
                             </div>
                             <div v-if="medal.new_time" class="d-flex align-center">
                               <span class="mr-1 font-weight-bold">上新时间:</span>
                               <span>{{ medal.new_time }}</span>
                             </div>
                              <div v-if="medal.stock" class="d-flex align-center">
                                <v-icon icon="mdi-package-variant-closed" size="10" class="mr-1"></v-icon>
                                <span>库存: {{ medal.stock }}</span>
                              </div>
                              <div v-if="medal.stock_status" class="mt-1">
                                <v-chip
                                  size="x-small"
                                  color="orange-lighten-4"
                                  variant="flat"
                                  class="px-2 font-weight-bold text-orange-darken-4 rounded-pill"
                                  style="height: 18px; font-size: 10px;"
                                >
                                  {{ medal.stock_status }}
                                </v-chip>
                              </div>
                           </div>

                           <div v-if="canPurchase(medal)" class="mt-2 d-flex justify-end">
                             <v-btn
                               size="small"
                               color="primary"
                               variant="flat"
                               prepend-icon="mdi-cart"
                               class="medal-action-btn"
                               @click="openPurchaseDialog(medal)"
                             >
                               购买
                             </v-btn>
                           </div>

                           <div v-if="canToggleWear(medal)" class="mt-2 d-flex justify-end">
                             <v-btn
                               size="small"
                               :color="isWorn(medal) ? 'warning' : 'primary'"
                               variant="flat"
                               :prepend-icon="isWorn(medal) ? 'mdi-minus-circle-outline' : 'mdi-check-circle-outline'"
                               class="medal-action-btn"
                               @click="openWearDialog(medal, isWorn(medal) ? 'unwear' : 'wear')"
                             >
                               {{ isWorn(medal) ? '取下' : '佩戴' }}
                             </v-btn>
                           </div>


        
                       </div>
                    </v-card>
                  </v-col>
                </v-row>
               </div>
            </v-expand-transition>
          </div>
        </div>

      </v-card-text>
    </v-card>

    <v-dialog v-model="purchaseDialog" max-width="440">
      <v-card v-if="selectedMedal" class="neo-dialog-card">
        <v-card-title class="neo-dialog-title d-flex align-center">
          <div class="neo-dialog-icon neo-dialog-icon-primary">
            <v-icon icon="mdi-cart-outline" size="18"></v-icon>
          </div>
          <div>
            <div class="text-subtitle-1 font-weight-bold">确认购买</div>
            <div class="neo-dialog-subtitle">请确认本次勋章购买信息</div>
          </div>
        </v-card-title>
        <v-card-text class="neo-dialog-content">
          <div class="neo-dialog-highlight">
            <span class="neo-dialog-label">支付金额</span>
            <span class="neo-dialog-price">{{ formatPrice(selectedMedal.price) }} {{ getCurrency(selectedMedal) }}</span>
          </div>
          <div class="neo-dialog-message">
            即将购买勋章
            <span class="font-weight-bold">《{{ selectedMedal.name }}》</span>
          </div>
        </v-card-text>
        <v-card-actions class="neo-dialog-actions">
          <v-spacer />
          <v-btn variant="text" class="neo-dialog-btn neo-dialog-btn-ghost" @click="closePurchaseDialog" :disabled="purchaseLoading">取消</v-btn>
          <v-btn color="primary" variant="flat" class="neo-dialog-btn neo-dialog-btn-primary" @click="confirmPurchase" :loading="purchaseLoading">立即购买</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="purchaseFeedbackDialog" max-width="440">
      <v-card class="neo-dialog-card neo-dialog-card-flat">
        <v-card-title class="neo-dialog-title d-flex align-center">
          <div class="neo-dialog-icon" :class="purchaseFeedbackType === 'success' ? 'neo-dialog-icon-success' : 'neo-dialog-icon-error'">
            <v-icon :icon="purchaseFeedbackType === 'success' ? 'mdi-check-circle-outline' : 'mdi-alert-circle-outline'" size="18"></v-icon>
          </div>
          <div>
            <div class="text-subtitle-1 font-weight-bold" :class="purchaseFeedbackType === 'success' ? 'text-success' : 'text-error'">
              {{ purchaseFeedbackTitle }}
            </div>
            <div class="neo-dialog-subtitle">操作结果提示</div>
          </div>
        </v-card-title>
        <v-card-text class="neo-dialog-content">
          <div class="neo-dialog-highlight neo-dialog-highlight-flat">
            <span class="neo-dialog-label">反馈信息</span>
            <span class="neo-dialog-feedback-message">{{ purchaseFeedbackMessage }}</span>
          </div>
        </v-card-text>
        <v-card-actions class="neo-dialog-actions">
          <v-spacer />
          <v-btn color="primary" variant="flat" class="neo-dialog-btn neo-dialog-btn-primary" @click="purchaseFeedbackDialog = false">知道了</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="wearDialog" max-width="440">
      <v-card v-if="selectedMedal" class="neo-dialog-card">
        <v-card-title class="neo-dialog-title d-flex align-center">
          <div class="neo-dialog-icon" :class="wearAction === 'wear' ? 'neo-dialog-icon-primary' : 'neo-dialog-icon-warning'">
            <v-icon :icon="wearAction === 'wear' ? 'mdi-check-circle-outline' : 'mdi-minus-circle-outline'" size="18"></v-icon>
          </div>
          <div>
            <div class="text-subtitle-1 font-weight-bold">确认{{ wearAction === 'wear' ? '佩戴' : '取下' }}</div>
            <div class="neo-dialog-subtitle">请确认本次勋章状态变更</div>
          </div>
        </v-card-title>
        <v-card-text class="neo-dialog-content">
          <div class="neo-dialog-highlight">
            <span class="neo-dialog-label">目标勋章</span>
            <span class="neo-dialog-name">《{{ selectedMedal.name }}》</span>
          </div>
          <div class="neo-dialog-message">
            即将{{ wearAction === 'wear' ? '佩戴' : '取下' }}该勋章
          </div>
        </v-card-text>
        <v-card-actions class="neo-dialog-actions">
          <v-spacer />
          <v-btn variant="text" class="neo-dialog-btn neo-dialog-btn-ghost" @click="closeWearDialog" :disabled="wearLoading">取消</v-btn>
          <v-btn color="primary" variant="flat" class="neo-dialog-btn" :class="wearAction === 'wear' ? 'neo-dialog-btn-primary' : 'neo-dialog-btn-warning'" @click="confirmWearAction" :loading="wearLoading">
            立即{{ wearAction === 'wear' ? '佩戴' : '取下' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<style scoped>
.plugin-page {
  padding: 0.5rem;
}

.bg-gradient-primary {
  background-color: #328df5ff;
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.text-subtitle-1 {
  font-size: 1.1rem !important;
  font-weight: 500;
}

.medal-card {
  transition: transform 0.2s, box-shadow 0.2s;
  border-radius: 8px;
  overflow: hidden;
}

.medal-action-btn {
  min-width: 66px;
  height: 28px;
  padding: 0 10px !important;
  border-radius: 12px !important;
  font-size: 0.74rem !important;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
}

.medal-action-btn :deep(.v-btn__prepend) {
  margin-inline-end: 4px;
}

.medal-action-btn :deep(.v-icon) {
  font-size: 14px;
}

.neo-dialog-card {
  border-radius: 22px !important;
  background: #f6f7fb !important;
  box-shadow: 0 10px 28px rgba(51, 65, 85, 0.12) !important;
  padding: 8px;
  border: 1px solid rgba(226, 232, 240, 0.95);
}

.neo-dialog-card-flat {
  background: #f7f8fc !important;
}

.neo-dialog-title {
  padding: 18px 18px 8px 18px;
  gap: 12px;
}

.neo-dialog-subtitle {
  margin-top: 2px;
  font-size: 0.77rem;
  color: #8a90a2;
}

.neo-dialog-content {
  padding: 10px 18px 8px 18px;
}

.neo-dialog-highlight {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border-radius: 18px;
  background: #ffffff;
  border: 1px solid #e8ecf4;
}

.neo-dialog-highlight-flat {
  background: #fdfdff;
}

.neo-dialog-label {
  font-size: 0.74rem;
  color: #8e94a8;
  font-weight: 600;
}

.neo-dialog-price,
.neo-dialog-name {
  font-size: 1rem;
  font-weight: 700;
  color: #5f63f2;
}

.neo-dialog-message {
  margin-top: 14px;
  font-size: 0.9rem;
  color: #666c80;
  line-height: 1.7;
}

.neo-dialog-feedback-message {
  font-size: 0.95rem;
  font-weight: 600;
  color: #4b5563;
  line-height: 1.7;
}

.neo-dialog-actions {
  padding: 12px 18px 18px 18px;
  gap: 10px;
}

.neo-dialog-btn {
  min-width: 88px;
  height: 36px;
  border-radius: 14px !important;
  font-size: 0.8rem !important;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.neo-dialog-btn-ghost {
  color: #7c82a0 !important;
}

.neo-dialog-btn-primary {
  box-shadow: none !important;
}

.neo-dialog-btn-warning {
  background: #ffb74d !important;
  color: #fff !important;
  box-shadow: none !important;
}

.neo-dialog-icon {
  width: 38px;
  height: 38px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.neo-dialog-icon-primary {
  background: #5f63f2;
}

.neo-dialog-icon-warning {
  background: #ffb74d;
}

.neo-dialog-icon-success {
  background: #66bb6a;
}

.neo-dialog-icon-error {
  background: #ef5350;
}

#medalwall-pro-page .medal-item-card {
  background-color: #ffffff;
}

@media (min-width: 1280px) {
  .v-col-lg-one-fifth {
    flex: 0 0 20%;
    max-width: 20%;
  }
}

.medal-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.medal-image {
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
  transition: transform 0.3s;
}

/* Circle mask for square medals (e.g., LongPT MP medal) */
.circle-mask {
  border-radius: 50% !important;
  overflow: hidden;
}

/* Remove black background for medals (e.g., 藏宝阁 site) */
.remove-black-bg {
  /* filter: url(#remove-black-bg); Remove aggressive filter */
  border-radius: 50% !important; /* Crop to circle to remove black corners */
}

/* For dark mode, adjust differently */
@media (prefers-color-scheme: dark) {
  .remove-black-bg {
    filter: brightness(1.1) contrast(1.02);
  }
}

.medal-card:hover .medal-image {
  transform: scale(1.1);
}

.bg-grey-lighten-4 {
  background-color: #f5f5f5 !important;
}

.bg-grey-lighten-5 {
  background-color: #fafafa !important;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  .bg-grey-lighten-4 {
    background-color: rgba(255, 255, 255, 0.05) !important;
  }
  
  .bg-grey-lighten-5 {
    background-color: rgba(255, 255, 255, 0.02) !important;
  }
  
  /* 深色模式下勋章卡片背景 */
  .medal-item-card {
    background-color: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
  }
  
  /* 深色模式下卡片悬停效果 */
  .medal-card:hover {
    box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15) !important;
  }
  
  /* 深色模式下轮播卡片 */
  .medal-stack-item {
    background-color: rgba(255, 255, 255, 0.08) !important;
    border-color: rgba(255, 255, 255, 0.12) !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2) !important;
  }
  
  /* 深色模式下轮播卡片底部渐变 */
  .medal-stack-info {
    background: linear-gradient(to top, rgba(30,30,30,1) 20%, rgba(30,30,30,0.9) 50%, rgba(30,30,30,0) 100%) !important;
  }
  
  /* 深色模式下文字颜色调整 */
  .text-grey-darken-1 {
    color: rgba(255, 255, 255, 0.85) !important;
  }
  
  /* 深色模式下价格颜色 */
  .text-primary {
    color: #64b5f6 !important;
  }
  
  /* 深色模式下图片边框和阴影 */
  .medal-image {
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
  }
  
  /* 深色模式下移除黑色背景的勋章 */
  .remove-black-bg {
    filter: brightness(1.2) contrast(1.1);
  }

  .neo-dialog-card,
  .neo-dialog-card-flat {
    background: linear-gradient(180deg, #1f2330 0%, #191d28 100%) !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38) !important;
  }

  .neo-dialog-subtitle,
  .neo-dialog-label {
    color: #98a2b3 !important;
  }

  .neo-dialog-highlight,
  .neo-dialog-highlight-flat {
    background: linear-gradient(180deg, #2a3142 0%, #222838 100%) !important;
    border-color: rgba(255, 255, 255, 0.08) !important;
  }

  .neo-dialog-price,
  .neo-dialog-name {
    color: #8ea2ff !important;
  }

  .neo-dialog-message,
  .neo-dialog-feedback-message {
    color: #c2c9d6 !important;
  }

  .neo-dialog-btn-ghost {
    color: #7fd0ff !important;
  }

  .neo-dialog-btn-primary {
    background: #ffb84d !important;
    color: #fff !important;
  }

  .neo-dialog-btn-warning {
    background: #ffb84d !important;
    color: #fff !important;
  }

  .neo-dialog-icon-primary {
    background: #6c72ff;
  }

  .neo-dialog-icon-warning {
    background: #ffb84d;
  }

  .neo-dialog-icon-success {
    background: #4caf50;
  }

  .neo-dialog-icon-error {
    background: #ef5350;
  }
}

/* Vuetify深色主题支持 - 使用data-theme属性选择器 */
[data-theme="dark"] .bg-grey-lighten-4,
[data-theme="purple"] .bg-grey-lighten-4,
[data-theme="transparent"] .bg-grey-lighten-4 {
  background-color: rgba(255, 255, 255, 0.05) !important;
}

[data-theme="dark"] .bg-grey-lighten-5,
[data-theme="purple"] .bg-grey-lighten-5,
[data-theme="transparent"] .bg-grey-lighten-5 {
  background-color: rgba(255, 255, 255, 0.02) !important;
}

[data-theme="dark"] #medalwall-pro-page .medal-item-card,
[data-theme="purple"] #medalwall-pro-page .medal-item-card,
[data-theme="transparent"] #medalwall-pro-page .medal-item-card {
  background-color: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
}

[data-theme="dark"] .medal-card:hover,
[data-theme="purple"] .medal-card:hover,
[data-theme="transparent"] .medal-card:hover {
  box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15) !important;
}

[data-theme="dark"] .medal-stack-item,
[data-theme="purple"] .medal-stack-item,
[data-theme="transparent"] .medal-stack-item {
  background-color: rgba(255, 255, 255, 0.08) !important;
  border-color: rgba(255, 255, 255, 0.12) !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2) !important;
}

[data-theme="dark"] .medal-stack-info,
[data-theme="purple"] .medal-stack-info,
[data-theme="transparent"] .medal-stack-info {
  background: linear-gradient(to top, rgba(30,30,30,1) 20%, rgba(30,30,30,0.9) 50%, rgba(30,30,30,0) 100%) !important;
}

[data-theme="dark"] .text-grey-darken-1,
[data-theme="purple"] .text-grey-darken-1,
[data-theme="transparent"] .text-grey-darken-1 {
  color: rgba(255, 255, 255, 0.85) !important;
}

[data-theme="dark"] .text-primary,
[data-theme="purple"] .text-primary,
[data-theme="transparent"] .text-primary {
  color: #64b5f6 !important;
}

[data-theme="dark"] .neo-dialog-card,
[data-theme="dark"] .neo-dialog-card-flat,
[data-theme="purple"] .neo-dialog-card,
[data-theme="purple"] .neo-dialog-card-flat,
[data-theme="transparent"] .neo-dialog-card,
[data-theme="transparent"] .neo-dialog-card-flat {
  background: linear-gradient(180deg, #1f2330 0%, #191d28 100%) !important;
  border-color: rgba(255, 255, 255, 0.1) !important;
  box-shadow: 0 14px 34px rgba(0, 0, 0, 0.38) !important;
}

[data-theme="dark"] .neo-dialog-subtitle,
[data-theme="dark"] .neo-dialog-label,
[data-theme="purple"] .neo-dialog-subtitle,
[data-theme="purple"] .neo-dialog-label,
[data-theme="transparent"] .neo-dialog-subtitle,
[data-theme="transparent"] .neo-dialog-label {
  color: #98a2b3 !important;
}

[data-theme="dark"] .neo-dialog-highlight,
[data-theme="dark"] .neo-dialog-highlight-flat,
[data-theme="purple"] .neo-dialog-highlight,
[data-theme="purple"] .neo-dialog-highlight-flat,
[data-theme="transparent"] .neo-dialog-highlight,
[data-theme="transparent"] .neo-dialog-highlight-flat {
  background: linear-gradient(180deg, #2a3142 0%, #222838 100%) !important;
  border-color: rgba(255, 255, 255, 0.08) !important;
}

[data-theme="dark"] .neo-dialog-price,
[data-theme="dark"] .neo-dialog-name,
[data-theme="purple"] .neo-dialog-price,
[data-theme="purple"] .neo-dialog-name,
[data-theme="transparent"] .neo-dialog-price,
[data-theme="transparent"] .neo-dialog-name {
  color: #8ea2ff !important;
}

[data-theme="dark"] .neo-dialog-message,
[data-theme="dark"] .neo-dialog-feedback-message,
[data-theme="purple"] .neo-dialog-message,
[data-theme="purple"] .neo-dialog-feedback-message,
[data-theme="transparent"] .neo-dialog-message,
[data-theme="transparent"] .neo-dialog-feedback-message {
  color: #c2c9d6 !important;
}

[data-theme="dark"] .neo-dialog-btn-ghost,
[data-theme="purple"] .neo-dialog-btn-ghost,
[data-theme="transparent"] .neo-dialog-btn-ghost {
  color: #7fd0ff !important;
}

[data-theme="dark"] .neo-dialog-btn-primary,
[data-theme="purple"] .neo-dialog-btn-primary,
[data-theme="transparent"] .neo-dialog-btn-primary,
[data-theme="dark"] .neo-dialog-btn-warning,
[data-theme="purple"] .neo-dialog-btn-warning,
[data-theme="transparent"] .neo-dialog-btn-warning {
  background: #ffb84d !important;
  color: #fff !important;
}

[data-theme="dark"] .medal-image,
[data-theme="purple"] .medal-image,
[data-theme="transparent"] .medal-image {
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
}

[data-theme="dark"] .remove-black-bg,
[data-theme="purple"] .remove-black-bg,
[data-theme="transparent"] .remove-black-bg {
  filter: brightness(1.2) contrast(1.1);
  box-shadow: 0 0 0 1px rgba(255,255,255,0.2);
}



.medal-stack-item {
  position: relative;
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
}

.medal-stack-item:active {
  transform: scale(0.95);
}

.medal-stack-info {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 4px;
  background: linear-gradient(to top, rgba(255,255,255,1) 20%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
  z-index: 2;
}

/* Corner ribbon for medals */
.medal-corner-ribbon {
  position: absolute;
  top: 0;
  right: 0;
  background: #f15e5e;
  color: white;
  font-size: 9px;
  font-weight: bold;
  padding: 2px 7px;
  z-index: 3;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transform-origin: top right;
  transform: rotate(0deg) translate(0, 0);
  border-bottom-left-radius: 8px;
  white-space: nowrap;
  letter-spacing: 0.5px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}

.medal-corner-ribbon-owned {
  background: #4edb55;
}

.medal-corner-ribbon::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 0 8px 8px;
  border-color: transparent transparent #d96565 transparent;
  transform: translate(0, -8px);
}

.medal-corner-ribbon-owned::before {
  border-color: transparent transparent #1f5a24 transparent;
}

.medal-stack-image {
  transition: transform 0.3s;
}



.cursor-pointer {
  cursor: pointer;
}

.transition-transform {
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.rotate-90 {
  transform: rotate(90deg);
}

/* 禁用状态的箭头保持半透明，视觉上表示不可点击 */
.v-slide-group__prev--disabled,
.v-slide-group__next--disabled {
  opacity: 0.3 !important;
  cursor: not-allowed !important;
  pointer-events: none !important;
}

/* 启用状态的箭头强制显示 */
.v-slide-group__prev:not(.v-slide-group__prev--disabled),
.v-slide-group__next:not(.v-slide-group__next--disabled) {
  opacity: 1 !important;
  pointer-events: auto !important;
  cursor: pointer !important;
}

/* 小屏幕隐藏轮播箭头 - 使用滑动浏览 */
@media (max-width: 960px) {
  :deep(.v-slide-group__prev),
  :deep(.v-slide-group__next) {
    display: none !important;
  }
}

</style>
