<script setup lang="ts">
import { ref, reactive, watch } from 'vue'

// ── Props & Emits ─────────────────────────────────────────────────────────────
const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['save', 'close', 'switch'])

// ── 本地配置状态 ───────────────────────────────────────────────────────────────
const config = reactive({
  enabled: false,
  notify: true,
  cron: '0 */6 * * *',
  mode: 'closest',
  server_id: '',
  retry_count: 2,
  history_limit: 31,
  ...props.initialConfig,
})

// 当 initialConfig 变化时同步
watch(
  () => props.initialConfig,
  (val) => Object.assign(config, val),
  { deep: true },
)

// ── 模式选项 ───────────────────────────────────────────────────────────────────
const modeOptions = [
  { title: '最近节点（自动）', value: 'closest', icon: 'mdi-earth', color: 'primary' },
  { title: '中国电信', value: 'telecom', icon: 'mdi-lan-connect', color: 'blue-darken-2' },
  { title: '中国联通', value: 'unicom', icon: 'mdi-web', color: 'deep-orange' },
  { title: '中国移动', value: 'mobile', icon: 'mdi-signal-5g', color: 'light-blue-darken-1' },
  { title: '固定节点', value: 'fixed', icon: 'mdi-pin', color: 'grey' },
]

// ── 固定节点列表 ───────────────────────────────────────────────────────────────
const servers = ref<Array<{ id: string; name: string; location: string; country: string; host: string }>>([]
)
const serversLoading = ref(false)
const serversLoaded = ref(false)

/** 节点下拉选项（id → title, subtitle, value） */
const serverOptions = ref<Array<{ title: string; subtitle: string; value: string }>>([])

async function loadServers() {
  if (serversLoading.value) return
  serversLoading.value = true
  try {
    const res = await props.api.get('plugin/AutoSpeed/servers')
    const list = res?.servers ?? []
    servers.value = list
    serverOptions.value = list.map((s: any) => ({
      title: `${s.name} — ${s.location}, ${s.country}`,
      subtitle: `ID: ${s.id}  |  ${s.host}`,
      value: String(s.id),
    }))
    serversLoaded.value = true
    if (config.mode === 'fixed' && !config.server_id && serverOptions.value.length > 0) {
      config.server_id = serverOptions.value[0].value
    }
  } catch (e) {
    console.warn('[AutoSpeed] 获取节点列表失败', e)
  } finally {
    serversLoading.value = false
  }
}

// 切换到 fixed 模式时自动加载节点列表
watch(
  () => config.mode,
  (val) => {
    if (val === 'fixed') {
      if (!serversLoaded.value) {
        loadServers()
      } else if (!config.server_id && serverOptions.value.length > 0) {
        config.server_id = serverOptions.value[0].value
      }
    }
  },
  { immediate: true },
)

// ── 保存 ──────────────────────────────────────────────────────────────────────
const saving = ref(false)
const snackbar = reactive({ show: false, text: '', color: 'success' })

async function handleSave() {
  saving.value = true
  try {
    emit('save', { ...config })
    await props.api.post('plugin/AutoSpeed/config', { ...config }).catch(() => {})
    snackbar.text = '配置已保存'
    snackbar.color = 'success'
    snackbar.show = true
  } catch (e) {
    snackbar.text = '保存失败'
    snackbar.color = 'error'
    snackbar.show = true
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="as-config">
    <!-- 顶部标题栏 -->
    <div class="as-topbar">
      <div class="as-topbar__left">
        <div class="as-topbar__icon">
          <v-icon icon="mdi-cog" size="24"></v-icon>
        </div>
        <div>
          <div class="as-topbar__title">网络测速 · 配置</div>
          <div class="as-topbar__sub">AutoSpeed Plugin</div>
        </div>
      </div>
      <div class="as-topbar__right" style="padding: 2px;">
        <!-- 操作按钮组 -->
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="emit('switch', 'page')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="primary" @click="handleSave" :loading="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <!-- 基础设置卡片 -->
    <div class="as-card">
      <div class="as-card__header">
        <span class="as-card__title"><v-icon icon="mdi-tune-vertical" size="18" class="mr-1"></v-icon>基础设置</span>
      </div>

      <v-row class="mt-1 mb-1">
        <v-col cols="12" sm="6" class="d-flex align-center justify-space-between py-1">
          <span class="as-row__text">
            <v-icon icon="mdi-power-plug" size="20" :color="config.enabled ? '#a78bfa' : 'grey'" class="mr-2"></v-icon>启用插件
          </span>
          <label class="switch" style="--switch-checked-bg: #a78bfa;">
            <input v-model="config.enabled" type="checkbox">
            <div class="slider">
              <div class="circle">
                <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
              </div>
            </div>
          </label>
        </v-col>
        <v-col cols="12" sm="6" class="d-flex align-center justify-space-between py-1">
          <span class="as-row__text">
            <v-icon icon="mdi-bell-ring-outline" size="20" :color="config.notify ? '#34d399' : 'grey'" class="mr-2"></v-icon>推送通知
          </span>
          <label class="switch" style="--switch-checked-bg: #34d399;">
            <input v-model="config.notify" type="checkbox">
            <div class="slider">
              <div class="circle">
                <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
              </div>
            </div>
          </label>
        </v-col>
      </v-row>
      <div class="as-divider" />

      <div class="as-field" style="margin-top: 12px; margin-bottom: 8px;">
        <label class="as-field__label mb-1">
          <v-icon icon="mdi-wan" size="18" color="info" class="mr-1"></v-icon>节点选择模式
        </label>
        <v-row dense>
          <v-col cols="12" :sm="config.mode === 'fixed' ? 6 : 12">
            <v-select
              v-model="config.mode"
              :items="modeOptions"
              item-title="title"
              item-value="value"
              density="compact"
              variant="outlined"
              hide-details="auto"
              class="as-input"
            >
              <template v-slot:selection="{ item }">
                <v-icon :icon="item.raw.icon" :color="item.raw.color" size="18" class="mr-2"></v-icon>
                {{ item.raw.title }}
              </template>
              <template v-slot:item="{ props, item }">
                <v-list-item v-bind="props" :title="item.raw.title">
                  <template v-slot:prepend>
                    <v-icon :icon="item.raw.icon" :color="item.raw.color" size="20" class="mr-3"></v-icon>
                  </template>
                </v-list-item>
              </template>
            </v-select>
          </v-col>

          <v-col cols="12" sm="6" v-if="config.mode === 'fixed'">
            <v-select
                v-model="config.server_id"
                :items="serverOptions"
                item-title="title"
                item-value="value"
                label="固定节点"
                density="compact"
                variant="outlined"
                hide-details="auto"
                color="primary"
                :loading="serversLoading"
                :no-data-text="serversLoaded ? '未找到匹配节点' : '节点列表加载中…'"
                class="as-input"
              >
                <!-- 已选中项展示 -->
                <template v-slot:selection="{ item }">
                  <span class="as-server-selected">
                    <v-icon icon="mdi-server" size="15" color="primary" class="mr-1" />
                    {{ item.raw.title }}
                  </span>
                </template>
                <!-- 下拉列表项 -->
                <template v-slot:item="{ props: itemProps, item }">
                  <v-list-item v-bind="itemProps" :title="item.raw.title" :subtitle="item.raw.subtitle">
                    <template v-slot:prepend>
                      <v-icon icon="mdi-server-network" size="18" color="grey" class="mr-2" />
                    </template>
                  </v-list-item>
                </template>
                <!-- 列表底部：刷新按钮 -->
                <template v-slot:append-item>
                  <v-divider class="mt-1 mb-1" />
                  <div class="d-flex justify-center pa-1">
                    <v-btn
                      size="small"
                      variant="text"
                      color="primary"
                      :loading="serversLoading"
                      prepend-icon="mdi-refresh"
                      @click.stop="loadServers"
                    >
                      刷新节点列表
                    </v-btn>
                  </div>
                </template>
              </v-select>
          </v-col>
        </v-row>
      </div>

      <div class="as-divider my-2" />

      <div class="as-field" style="margin-top: 12px; margin-bottom: 8px;">
        <v-row>
          <v-col cols="12" md="4">
            <VCronField
              v-model="config.cron"
              label="Cron表达式"
              hint="周期，例如：0 */6 * * *"
              persistent-hint
              density="compact"
            ></VCronField>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="config.retry_count"
              label="测速重试次数"
              placeholder="2"
              type="number"
              density="compact"
              variant="outlined"
              hide-details="auto"
              color="primary"
              hint="失败时的最大重试次数"
              persistent-hint
              :min="0"
              :max="10"
            ></v-text-field>
          </v-col>
          <v-col cols="12" md="4">
            <v-text-field
              v-model.number="config.history_limit"
              label="历史保留条数"
              placeholder="31"
              type="number"
              density="compact"
              variant="outlined"
              hide-details="auto"
              color="primary"
              hint="最多保留的历史数据条数"
              persistent-hint
              :min="10"
              :max="5000"
            ></v-text-field>
          </v-col>
        </v-row>
      </div>
    </div>

    <!-- 致谢卡片 -->
    <div class="as-card">
      <div class="as-card__header">
        <span class="as-card__title" style="color: rgb(var(--v-theme-info));">
          <v-icon icon="mdi-heart-outline" size="18" class="mr-1"></v-icon>致谢
        </span>
      </div>
      <div style="font-size: 13px; line-height: 1.8; color: rgba(var(--v-theme-on-surface), 0.75); padding: 4px 0;">
        <div class="d-flex align-center gap-2 mb-1">
          <v-icon icon="mdi-star-four-points" size="14" color="warning" class="mr-1"></v-icon>
          <span>本插件测速核心实现参考自 <strong>鱼丸粗面</strong> 大佬的开源项目。</span>
        </div>
        <div class="d-flex align-center" style="margin-left: 4px;">
          <v-icon icon="mdi-github" size="16" class="mr-2" style="opacity: 0.7;"></v-icon>
          <a
            href="https://github.com/yuwancumian2009/Autospeed"
            target="_blank"
            rel="noopener noreferrer"
            class="as-link"
          >
            yuwancumian2009 / Autospeed
          </a>
        </div>
      </div>
    </div>

    <!-- 操作反馈 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="2500" location="top">
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<style scoped>
/* ── 容器 ────────────────────────────────────────────────────────────────────── */
.as-config {
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

/* ── 图标按钮 ─────────────────────────────────────────────────────────────────── */
.as-icon-btn {
  width: 34px;
  height: 34px;
  border-radius: 8px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  background: rgba(var(--v-theme-on-surface), 0.04);
  color: rgb(var(--v-theme-on-surface));
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}
.as-icon-btn:hover { background: rgba(var(--v-theme-on-surface), 0.1); }
.as-icon-btn:active { transform: scale(0.92); }

/* ── 卡片 ────────────────────────────────────────────────────────────────────── */
.as-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
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

/* ── 行（开关类） ─────────────────────────────────────────────────────────────── */
.as-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 36px;
}
.as-row__text {
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.85);
  display: flex;
  align-items: center;
  gap: 6px;
}
.as-row__icon {
  font-size: 16px;
}

/* ── 分割线 ───────────────────────────────────────────────────────────────────── */
.as-divider {
  height: 0.5px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  margin: 0 -4px;
}

/* ── 表单字段 ─────────────────────────────────────────────────────────────────── */
.as-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.as-field__label {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.7);
  display: flex;
  align-items: center;
  gap: 6px;
}
.as-field__hint {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.45);
}
.as-field__hint code {
  background: rgba(var(--v-theme-on-surface), 0.08);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: "SF Mono", "Fira Code", monospace;
  font-size: 11px;
}
.as-input :deep(.v-field) {
  background: rgba(var(--v-theme-on-surface), 0.03) !important;
  border-radius: 8px !important;
}
.as-input :deep(.v-field__outline) {
  --v-field-border-opacity: 0.15;
}


@keyframes spin {
  to { transform: rotate(360deg); }
}

/* ── 自定义开关 ───────────────────────────────────────────────────────────────── */
.switch {
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgba(var(--v-theme-on-surface), 0.22);
  --switch-checked-bg: rgb(var(--v-theme-primary));
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-checked-shadow: -1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-transition: var(--switch-transition);
  --icon-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: rgba(0, 0, 0, 0.4);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all .2s ease-in-out;
  display: inline-block;
  margin-left: 10px;
  user-select: none;
}
.switch input { display: none; }
.switch svg { transition: var(--icon-transition); position: absolute; height: auto; }
.switch .checkmark { width: var(--icon-checkmark-size); color: var(--icon-checkmark-color); transform: scale(0); }
.switch .cross { width: var(--icon-cross-size); color: var(--icon-cross-color); }
.slider { box-sizing: border-box; width: var(--switch-width); height: var(--switch-height); background: var(--switch-bg); border-radius: 999px; display: flex; align-items: center; position: relative; transition: var(--switch-transition); cursor: pointer; }
.circle { width: var(--circle-diameter); height: var(--circle-diameter); background: var(--circle-bg); border-radius: inherit; box-shadow: var(--circle-shadow); display: flex; align-items: center; justify-content: center; transition: var(--circle-transition); z-index: 1; position: absolute; left: var(--switch-offset); }
.slider::before { content: ""; position: absolute; width: var(--effect-width); height: var(--effect-height); left: calc(var(--switch-offset) + (var(--effect-width) / 2)); background: var(--effect-bg); border-radius: var(--effect-border-radius); transition: var(--effect-transition); }
.switch input:checked+.slider { background: var(--switch-checked-bg); }
.switch input:checked+.slider .checkmark { transform: scale(1); }
.switch input:checked+.slider .cross { transform: scale(0); }
.switch input:checked+.slider::before { left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset)); }
.switch input:checked+.slider .circle { left: calc(100% - var(--circle-diameter) - var(--switch-offset)); box-shadow: var(--circle-checked-shadow); }
.switch input:disabled+.slider { opacity: 0.5; cursor: not-allowed; }

/* ── 超链接 ─────────────────────────────────────────────────────────────────── */
.as-link {
  color: rgb(var(--v-theme-info));
  text-decoration: none;
  font-weight: 500;
  border-bottom: 1px dashed rgba(var(--v-theme-info), 0.5);
  transition: all 0.2s ease;
}
.as-link:hover {
  color: rgb(var(--v-theme-primary));
  border-bottom-color: rgb(var(--v-theme-primary));
  border-bottom-style: solid;
}

/* ── 固定节点已选中项 ────────────────────────────────────────────────────────── */
.as-server-selected {
  display: flex;
  align-items: center;
  font-size: 13px;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
