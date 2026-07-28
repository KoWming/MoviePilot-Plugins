<template>
  <div class="siqi-config">
    <div class="siqi-topbar">
      <div class="siqi-topbar__left">
        <div class="siqi-topbar__icon">
          <v-icon icon="mdi-cog-outline" size="24" />
        </div>
        <div>
          <div class="siqi-topbar__title">思齐农场 · 配置</div>
          <div class="siqi-topbar__sub">管理定时任务、自动化策略与站点 Cookie</div>
        </div>
      </div>
      <div class="siqi-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="emit('switch', 'page')">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="saveConfig" :loading="saving">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="success" size="small" min-width="40" class="px-0 px-sm-3" @click="emit('close')">
            <v-icon icon="mdi-close" size="18" class="mr-sm-1" />
            <span class="d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <v-alert v-if="message" :type="messageType" density="compact" class="siqi-toast" closable @click:close="message=''">{{ message }}</v-alert>

    <div class="siqi-config-col">
      <div class="siqi-card">
        <div class="siqi-card__header">
          <span class="siqi-card__title d-flex align-center">
            <v-icon icon="mdi-toggle-switch-outline" size="18" color="#22c55e" class="mr-1" />基础设置
          </span>
        </div>
        <div class="siqi-switch-grid">
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.enabled}" style="--siqi-accent:34,197,94">
            <div class="siqi-switch-main"><v-icon icon="mdi-power-plug" size="18" /><div><div class="siqi-switch-label">启用插件</div><div class="siqi-switch-desc">开启定时任务与页面功能</div></div></div>
            <v-switch v-model="config.enabled" color="green" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.notify}" style="--siqi-accent:59,130,246">
            <div class="siqi-switch-main"><v-icon icon="mdi-bell-outline" size="18" /><div><div class="siqi-switch-label">开启通知</div><div class="siqi-switch-desc">任务完成后发送站内通知</div></div></div>
            <v-switch v-model="config.notify" color="blue" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.use_proxy}" style="--siqi-accent:139,92,246">
            <div class="siqi-switch-main"><v-icon icon="mdi-lan-connect" size="18" /><div><div class="siqi-switch-label">使用代理</div><div class="siqi-switch-desc">请求站点时使用系统代理</div></div></div>
            <v-switch v-model="config.use_proxy" color="purple" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.use_ai_captcha && aiAvailable}" style="--siqi-accent:99,102,241">
            <div class="siqi-switch-main"><v-icon icon="mdi-robot" size="18" /><div><div class="siqi-switch-label">AI辅助验证码识别</div><div class="siqi-switch-desc">{{ aiAvailable ? '基础识别失败后使用AI智能助手识别验证码重试一键收获' : '未检测到AI智能助手配置（需启用MP智能助手）' }}</div></div></div>
            <v-switch v-model="config.use_ai_captcha" color="indigo" hide-details density="compact" :disabled="!aiAvailable" />
          </div>
          <div class="siqi-schedule-card siqi-schedule-card--delay">
            <div class="siqi-schedule-card__head">
              <v-icon icon="mdi-timer-outline" size="17" />
              <span>收获执行延迟（分钟）(0-30，默认 2)</span>
            </div>
            <v-text-field
              v-model.number="config.harvest_delay_minutes"
              type="number"
              min="0"
              max="30"
              density="compact"
              variant="outlined"
              class="siqi-input siqi-harvest-delay-field"
            />
          </div>
          <div class="siqi-schedule-card siqi-schedule-card--cron">
            <div class="siqi-schedule-card__head">
              <v-icon icon="mdi-calendar-clock-outline" size="17" />
              <span>Cron 兜底巡检 (例如：5 */4 * * *)</span>
            </div>
            <VCronField
              v-model="config.cron"
              density="compact"
              class="siqi-input siqi-cron-field"
            />
          </div>
        </div>
      </div>

      <div class="siqi-card">
        <div class="siqi-card__header">
          <span class="siqi-card__title d-flex align-center">
            <v-icon icon="mdi-robot-outline" size="18" color="#f59e0b" class="mr-1" />自动化策略
          </span>
        </div>
        <div class="siqi-switch-grid">
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.auto_harvest}" style="--siqi-accent:245,158,11">
            <div class="siqi-switch-main"><v-icon icon="mdi-basket-fill" size="18" /><div><div class="siqi-switch-label">自动收获</div><div class="siqi-switch-desc">收获成熟作物</div></div></div>
            <v-switch v-model="config.auto_harvest" color="orange" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.auto_plant}" style="--siqi-accent:34,197,94">
            <div class="siqi-switch-main"><v-icon icon="mdi-seed" size="18" /><div><div class="siqi-switch-label">自动补种</div><div class="siqi-switch-desc">为空地补种默认种子</div></div></div>
            <v-switch v-model="config.auto_plant" color="green" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.auto_steal}" style="--siqi-accent:239,68,68">
            <div class="siqi-switch-main"><v-icon icon="mdi-incognito" size="18" /><div><div class="siqi-switch-label">自动偷菜</div><div class="siqi-switch-desc">每日尝试偷取一次</div></div></div>
            <v-switch v-model="config.auto_steal" color="red" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.auto_like}" style="--siqi-accent:236,72,153">
            <div class="siqi-switch-main"><v-icon icon="mdi-thumb-up-outline" size="18" /><div><div class="siqi-switch-label">自动点赞</div><div class="siqi-switch-desc">随机批量点赞农场</div></div></div>
            <v-switch v-model="config.auto_like" color="pink" hide-details density="compact" />
          </div>
          <div class="siqi-switch-item" :class="{'siqi-switch-item--active': config.auto_sell}" style="--siqi-accent:14,165,233">
            <div class="siqi-switch-main"><v-icon icon="mdi-cash-sync" size="18" /><div><div class="siqi-switch-label">自动出售</div><div class="siqi-switch-desc">出售收获背包库存</div></div></div>
            <v-switch v-model="config.auto_sell" color="info" hide-details density="compact" />
          </div>
        </div>
      </div>

      <div class="siqi-card">
        <div class="siqi-card__header">
          <span class="siqi-card__title d-flex align-center">
            <v-icon icon="mdi-tune-variant" size="18" color="#0ea5e9" class="mr-1" />参数设置
          </span>
        </div>
        <div class="siqi-form-grid">
          <v-select v-model="config.seed_id" :items="seedOptions" label="默认种子" density="compact" variant="outlined" hide-details class="siqi-input seed-select" prepend-inner-icon="mdi-sprout" :loading="seedLoading">
            <template #item="{ props: itemProps, item }">
              <v-list-item v-bind="itemProps">
                <template #subtitle>
                  <span v-if="item.raw.locked" class="text-error">未解锁：需总收获 {{ item.raw.unlockHarvest }}</span>
                  <span v-else class="text-medium-emphasis">已解锁</span>
                </template>
              </v-list-item>
            </template>
          </v-select>
          <v-text-field v-model.number="config.retry_count" label="重试次数" type="number" density="compact" variant="outlined" hide-details class="siqi-input" prepend-inner-icon="mdi-reload" />
          <v-text-field v-model.number="config.retry_interval" label="重试间隔（秒）" type="number" density="compact" variant="outlined" hide-details class="siqi-input" prepend-inner-icon="mdi-timer-sand" />
        </div>
        <div class="siqi-field-hint">默认种子用于自动补种空地；下拉列表来自站点种子商店，建议选择已解锁种子。</div>
        <v-textarea v-model="config.cookie" label="Cookie（留空时尝试读取站点cookie）" rows="2" auto-grow variant="outlined" class="siqi-input mt-3" :class="{'siqi-secret-input': !showCookie}" prepend-inner-icon="mdi-cookie" autocomplete="off">
          <template #append-inner>
            <v-btn variant="text" density="comfortable" size="x-small" icon class="siqi-secret-toggle" @click.stop="showCookie = !showCookie">
              <v-icon :icon="showCookie ? 'mdi-eye-off-outline' : 'mdi-eye-outline'" size="18" />
            </v-btn>
          </template>
        </v-textarea>
      </div>

    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'

const props = defineProps({ api: Object, initialConfig: { type: Object, default: () => ({}) } })
const emit = defineEmits(['switch', 'close', 'config-updated'])
const PLUGIN_ID = 'SiqiFram'
const config = reactive({ enabled: false, notify: true, cron: '5 */4 * * *', cookie: '', seed_id: '1', auto_plant: true, auto_harvest: true, auto_sell: false, auto_steal: false, auto_like: false, use_proxy: false, use_ai_captcha: false, harvest_delay_minutes: 2, retry_count: 2, retry_interval: 3, ...props.initialConfig })
const loading = ref(false)
const saving = ref(false)
const seedLoading = ref(false)
const showCookie = ref(false)
const aiAvailable = ref(false)
const seedOptions = ref([{ title: '🥕 萝卜（ID 1）', value: '1', locked: false, unlockHarvest: 0 }])
const message = ref('')
const messageType = ref('success')
let messageTimer = null

const apiGet = (path) => props.api.get(`/plugin/${PLUGIN_ID}${path}`)
const apiPost = (path, data) => props.api.post(`/plugin/${PLUGIN_ID}${path}`, data)

function show(text, type = 'success') {
  message.value = text
  messageType.value = type
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(() => {
    if (message.value === text) message.value = ''
    messageTimer = null
  }, 3000)
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await apiGet('/config')
    Object.assign(config, res)
    config.seed_id = String(config.seed_id || '1')
    aiAvailable.value = !!res.ai_available
    if (!res.ai_available) config.use_ai_captcha = false
  } catch (e) {
    show(`加载失败：${e.message}`, 'error')
  } finally {
    loading.value = false
  }
}

async function loadSeeds() {
  seedLoading.value = true
  try {
    const res = await apiGet('/data')
    const seeds = Array.isArray(res?.seeds) ? res.seeds : []
    const totalHarvest = Number(res?.user_stats?.total_harvest || 0)
    if (seeds.length) {
      seedOptions.value = seeds.map(seed => ({
        title: `${seed.icon || '🌱'} ${seed.name || `种子 ${seed.id}`}（ID ${seed.id}）`,
        value: String(seed.id),
        locked: totalHarvest < Number(seed.unlock_harvest || 0),
        unlockHarvest: Number(seed.unlock_harvest || 0),
        props: {
          disabled: totalHarvest < Number(seed.unlock_harvest || 0)
        }
      }))
    }
  } catch (e) {
    // 保留默认兜底选项
  } finally {
    seedLoading.value = false
  }
}

async function saveConfig() {
  const delay = Number(config.harvest_delay_minutes)
  config.harvest_delay_minutes = Number.isFinite(delay) ? Math.min(30, Math.max(0, Math.trunc(delay))) : 2
  saving.value = true
  try {
    const res = await apiPost('/config', { ...config })
    if (res.success && res.config) emit('config-updated', res.config)
    show(res.message || (res.success ? '保存成功' : '保存失败'), res.success ? 'success' : 'error')
  } catch (e) {
    show(`保存失败：${e.message}`, 'error')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
  loadSeeds()
})
</script>

<style scoped>
.siqi-config{padding:16px 20px;display:flex;flex-direction:column;gap:16px;min-height:400px;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Text','Inter',sans-serif;color:rgba(var(--v-theme-on-surface),.85);border:1px solid rgba(var(--v-theme-on-surface),.12);border-radius:8px;background:linear-gradient(180deg,rgba(255,255,255,.02),rgba(76,175,80,.025))}
.siqi-topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-bottom:8px}.siqi-topbar__left{display:flex;align-items:center;gap:12px;min-width:0;flex:1}.siqi-topbar__right{display:flex;align-items:center;gap:10px;flex-shrink:0}.siqi-topbar__right :deep(.v-btn-group){flex-wrap:nowrap}.siqi-topbar__icon{width:42px;height:42px;border-radius:11px;background:rgba(76,175,80,.14);display:flex;align-items:center;justify-content:center;color:#2e7d32;flex-shrink:0}.siqi-topbar__title{font-size:16px;font-weight:700;letter-spacing:-.3px;color:rgba(var(--v-theme-on-surface),.88)}.siqi-topbar__sub{font-size:11px;color:rgba(var(--v-theme-on-surface),.55);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.siqi-toast{position:fixed!important;top:18px!important;left:50%!important;transform:translateX(-50%)!important;z-index:99999!important;width:min(520px,calc(100vw - 32px))!important;margin:0!important;box-shadow:0 12px 36px rgba(15,23,42,.18)!important;border-radius:12px!important}
.siqi-config-col{display:flex;flex-direction:column;gap:16px}.siqi-card{background:rgba(var(--v-theme-on-surface),.03);backdrop-filter:blur(20px) saturate(150%);border-radius:14px;border:.5px solid rgba(var(--v-theme-on-surface),.08);box-shadow:0 2px 10px rgba(0,0,0,.05);padding:14px 16px;display:flex;flex-direction:column;gap:14px}.siqi-card__header{display:flex;align-items:center;justify-content:space-between;gap:12px}.siqi-card__title{font-size:13px;font-weight:700;color:rgba(var(--v-theme-on-surface),.85)}
.siqi-switch-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.siqi-switch-item{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px;border-radius:12px;background:rgba(var(--v-theme-on-surface),.025);border:.5px solid rgba(var(--v-theme-on-surface),.06);transition:background .2s ease,border-color .2s ease,transform .2s ease}.siqi-switch-item:hover{transform:translateY(-1px)}.siqi-switch-item--active{background:rgba(var(--siqi-accent,34,197,94),.07);border-color:rgba(var(--siqi-accent,34,197,94),.18)}.siqi-switch-main{display:flex;align-items:center;gap:10px;min-width:0;flex:1;color:rgba(var(--v-theme-on-surface),.58)}.siqi-switch-item--active .siqi-switch-main{color:rgb(var(--siqi-accent,34,197,94))}.siqi-switch-label{font-size:13px;font-weight:600;color:rgba(var(--v-theme-on-surface),.86)}.siqi-switch-desc{font-size:11px;color:rgba(var(--v-theme-on-surface),.46);line-height:1.35;margin-top:1px}.siqi-switch-item :deep(.v-switch){flex:0 0 auto}.siqi-switch-item :deep(.v-selection-control){min-height:unset}.siqi-switch-item :deep(.v-input__details){display:none}
.siqi-schedule-card{min-width:0;padding:9px 12px 6px;border-radius:12px;border:.5px solid rgba(var(--v-theme-on-surface),.08);background:rgba(var(--v-theme-on-surface),.025);box-shadow:inset 0 1px 0 rgba(255,255,255,.04);transition:transform .2s ease,border-color .2s ease,background .2s ease}.siqi-schedule-card:hover{transform:translateY(-1px);border-color:rgba(34,197,94,.2);background:rgba(34,197,94,.035)}.siqi-schedule-card__head{display:flex;align-items:center;gap:7px;margin-bottom:6px;font-size:12px;font-weight:700;color:rgba(var(--v-theme-on-surface),.72)}.siqi-schedule-card__head .v-icon{color:#22c55e}.siqi-schedule-card :deep(.v-input__details){display:none}.siqi-schedule-card :deep(.v-field){background:rgba(var(--v-theme-surface),.36);transition:border-color .2s ease,box-shadow .2s ease}.siqi-schedule-card :deep(.v-field--focused){box-shadow:0 0 0 3px rgba(34,197,94,.1)}.siqi-cron-field,.siqi-harvest-delay-field{min-width:0}.siqi-form-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.siqi-input :deep(.v-field){border-radius:12px}.siqi-input :deep(.v-field__loader){left:1px;right:1px;width:auto;border-radius:12px 12px 0 0;overflow:hidden}.seed-select :deep(.v-input__control){border-radius:12px;clip-path:inset(-10px 0 0 0 round 12px)}.seed-select :deep(.v-input__loader){left:1px!important;right:1px!important;width:auto!important;margin:0!important;overflow:hidden!important;border-radius:12px 12px 0 0!important}.seed-select :deep(.v-progress-linear){border-radius:12px 12px 0 0;overflow:hidden}.siqi-secret-input :deep(textarea){-webkit-text-security:disc}.siqi-secret-toggle{min-width:28px;width:28px;height:28px;color:rgba(var(--v-theme-on-surface),.55)}.siqi-secret-toggle :deep(.v-btn__overlay),.siqi-secret-toggle :deep(.v-btn__underlay){display:none}.siqi-field-hint{font-size:11px;line-height:1.5;color:rgba(var(--v-theme-on-surface),.48);margin-top:-6px}
@media(max-width:900px){.siqi-switch-grid,.siqi-form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.siqi-config{padding:14px}.siqi-topbar{align-items:flex-start;gap:10px}.siqi-topbar__left{min-width:0}.siqi-topbar__right :deep(.v-btn){min-width:36px!important;padding-inline:0!important}.siqi-switch-grid,.siqi-form-grid{grid-template-columns:1fr}.siqi-switch-item{align-items:center}}
</style>
