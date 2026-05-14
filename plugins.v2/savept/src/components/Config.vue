<script setup>
import { reactive, ref } from 'vue'
import { pluginRequest } from '../utils/savept'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  initialConfig: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['switch', 'close'])

const saving = ref(false)
const message = reactive({ show: false, type: 'info', text: '' })
const form = reactive({
  enabled: true,
  source_url: 'https://savept.icu/',
  request_timeout: 15,
  default_internal_only: false,
  notify: true,
  cron: '0 8 * * *',
  ...props.initialConfig,
})

function pushMessage(text, type = 'info') {
  message.text = text
  message.type = type
  message.show = true
}

async function saveConfig() {
  saving.value = true
  try {
    const result = await pluginRequest(props.api, '/config', {
      method: 'POST',
      body: {
        enabled: !!form.enabled,
        source_url: form.source_url,
        request_timeout: Number(form.request_timeout || 15),
        default_internal_only: !!form.default_internal_only,
        notify: !!form.notify,
        cron: form.cron,
      },
    })
    if (!result?.success) {
      throw new Error(result?.message || '保存失败')
    }
    pushMessage('配置已保存', 'success')
  } catch (error) {
    pushMessage(error.message || '保存失败', 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="scfg-page">
    <div class="scfg-topbar">
      <div class="scfg-topbar__left">
        <div class="scfg-topbar__icon">
          <v-icon icon="mdi-heart-pulse" size="24" />
        </div>
        <div class="scfg-topbar__meta">
          <div class="scfg-topbar__title">PT 监护室配置</div>
          <div class="scfg-topbar__sub">数据源、默认行为与采集参数管理</div>
        </div>
      </div>
      <div class="scfg-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="primary" @click="saveConfig" :loading="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1" />
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="primary" @click="emit('close')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18" />
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </div>
    </div>

    <Transition name="scfg-slide">
      <div v-if="message.show" class="scfg-toast" :class="`scfg-toast--${message.type}`">
        <v-icon :icon="message.type === 'success' ? 'mdi-check-circle' : message.type === 'error' ? 'mdi-alert-circle' : 'mdi-information'" size="18" />
        <span>{{ message.text }}</span>
        <button class="scfg-toast__close" @click="message.show = false">
          <v-icon icon="mdi-close" size="16" />
        </button>
      </div>
    </Transition>

    <div class="scfg-card">
      <div class="scfg-card__header">
        <span class="scfg-card__title d-flex align-center">
          <v-icon icon="mdi-toggle-switch-outline" size="18" color="#8b5cf6" class="mr-1" />
          基础设置
        </span>
      </div>

      <div class="scfg-switch-grid">
        <div
          class="scfg-switch-item"
          :class="{ 'scfg-switch-item--active': form.enabled }"
          style="--scfg-accent: #8b5cf6"
        >
          <div class="scfg-switch-item__main">
            <div class="scfg-switch-item__icon">
              <v-icon icon="mdi-power-plug" size="18" />
            </div>
            <div class="scfg-switch-item__text">
              <span class="scfg-switch-item__label">启用插件</span>
            </div>
          </div>
          <label class="scfg-switch" style="--switch-checked-bg: #8b5cf6;">
            <input v-model="form.enabled" type="checkbox" />
            <div class="scfg-switch__slider">
              <div class="scfg-switch__circle">
                <svg
                  class="scfg-switch__cross"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 365.696 365.696"
                  y="0"
                  x="0"
                  height="6"
                  width="6"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                <svg
                  class="scfg-switch__checkmark"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 24 24"
                  y="0"
                  x="0"
                  height="10"
                  width="10"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
              </div>
            </div>
          </label>
        </div>
        <div
          class="scfg-switch-item"
          :class="{ 'scfg-switch-item--active': form.notify }"
          style="--scfg-accent: #10b981"
        >
          <div class="scfg-switch-item__main">
            <div class="scfg-switch-item__icon">
              <v-icon icon="mdi-bell-ring-outline" size="18" />
            </div>
            <div class="scfg-switch-item__text">
              <span class="scfg-switch-item__label">通知发送</span>
            </div>
          </div>
          <label class="scfg-switch" style="--switch-checked-bg: #10b981;">
            <input v-model="form.notify" type="checkbox" />
            <div class="scfg-switch__slider">
              <div class="scfg-switch__circle">
                <svg
                  class="scfg-switch__cross"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 365.696 365.696"
                  y="0"
                  x="0"
                  height="6"
                  width="6"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                <svg
                  class="scfg-switch__checkmark"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 24 24"
                  y="0"
                  x="0"
                  height="10"
                  width="10"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
              </div>
            </div>
          </label>
        </div>
        <div
          class="scfg-switch-item"
          :class="{ 'scfg-switch-item--active': form.default_internal_only }"
          style="--scfg-accent: #3b82f6"
        >
          <div class="scfg-switch-item__main">
            <div class="scfg-switch-item__icon">
              <v-icon icon="mdi-home-switch-outline" size="18" />
            </div>
            <div class="scfg-switch-item__text">
              <span class="scfg-switch-item__label">默认仅看内站</span>
            </div>
          </div>
          <label class="scfg-switch" style="--switch-checked-bg: #3b82f6;">
            <input v-model="form.default_internal_only" type="checkbox" />
            <div class="scfg-switch__slider">
              <div class="scfg-switch__circle">
                <svg
                  class="scfg-switch__cross"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 365.696 365.696"
                  y="0"
                  x="0"
                  height="6"
                  width="6"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g><path fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0" /></g></svg>
                <svg
                  class="scfg-switch__checkmark"
                  xml:space="preserve"
                  style="enable-background:new 0 0 512 512"
                  viewBox="0 0 24 24"
                  y="0"
                  x="0"
                  height="10"
                  width="10"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  version="1.1"
                  xmlns="http://www.w3.org/2000/svg"
                ><g transform="translate(-0.4, 0.2)"><path fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z" /></g></svg>
              </div>
            </div>
          </label>
        </div>
      </div>

      <div class="scfg-divider" />

      <div class="scfg-field">
        <div class="scfg-field__header">
          <div class="scfg-field__title-main">
            <v-icon icon="mdi-cloud-sync-outline" size="18" color="#3b82f6" class="scfg-field__title-icon" />
            <div class="scfg-field__title-text">
              <label class="scfg-field__label">采集设置</label>
            </div>
          </div>
        </div>

        <div class="scfg-form-grid scfg-form-grid--settings">
          <div class="scfg-form-item">
            <v-text-field
              v-model="form.source_url"
              label="源站地址"
              placeholder="https://savept.icu/"
              density="compact"
              variant="outlined"
              hide-details="auto"
              class="scfg-input"
            />
            <div class="scfg-field-hint">PT 监护数据来源页面地址</div>
          </div>

          <div class="scfg-form-item">
            <v-text-field
              v-model.number="form.request_timeout"
              label="超时时间（秒）"
              type="number"
              density="compact"
              variant="outlined"
              hide-details="auto"
              min="5"
              max="120"
              class="scfg-input"
            />
            <div class="scfg-field-hint">建议范围 10 ~ 30 秒，避免源站响应慢导致抓取失败</div>
          </div>

          <div class="scfg-form-item">
            <VCronField
              v-model="form.cron"
              label="Cron表达式"
              hint="默认每天早 8 点执行，例如：0 8 * * *"
              persistent-hint
              density="compact"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="scfg-card">
      <div class="scfg-card__header">
        <span class="scfg-card__title d-flex align-center">
          <v-icon icon="mdi-book-information-variant" size="18" color="#0ea5e9" class="mr-1" />
          关于 PT 监护室
        </span>
      </div>

      <div class="scfg-guide">
        <div class="scfg-guide__section">
          <p class="scfg-guide__paragraph">🏥 您好！本站点致力于监控 PT 站点的存活状态，记录站点开站、站庆等信息。</p>
          <p class="scfg-guide__paragraph">⚠️ <strong>运行说明：</strong>站点存活状态可能因本网站服务器故障、网络异常等原因产生误差。数据仅供参考，请以实际访问为准。</p>
          <p class="scfg-guide__paragraph">💡 <strong>判断规则：</strong>如站点无关站公告，长时间无法访问，将直接判定为死亡。如站点有关站公告及明确关站时间，将正常发布死亡讣告。</p>
          <p class="scfg-guide__paragraph">📨 <strong>联系方式：</strong>如果您发现数据有误、站点遗漏，或者希望申请收录、寻求技术交流，欢迎通过下方方式联系监护员。</p>
        </div>

        <div class="scfg-divider scfg-divider--guide" />

        <div class="scfg-guide__contact">
          <a
            class="scfg-contact-link scfg-contact-link--email"
            href="https://savept.icu/cdn-cgi/l/email-protection#ec9c98858f99dedcded9acdddadfc28f8381"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>📧</span>
            <span>E-Mail</span>
          </a>
          <a
            class="scfg-contact-link scfg-contact-link--tg"
            href="https://t.me/savept_icu"
            target="_blank"
            rel="noopener noreferrer"
          >
            <span>✈️</span>
            <span>Telegram</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scfg-page {
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

.scfg-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 8px;
}

.scfg-topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.scfg-topbar__meta {
  min-width: 0;
  flex: 1;
}

.scfg-topbar__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.scfg-topbar__icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  background: rgba(139, 92, 246, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8b5cf6;
  flex-shrink: 0;
}

.scfg-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.scfg-topbar__sub {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scfg-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 0.82rem;
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.scfg-toast--success {
  background: rgba(34, 197, 94, 0.08);
  color: #22c55e;
  border-color: rgba(34, 197, 94, 0.15);
}

.scfg-toast--error {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.15);
}

.scfg-toast--info {
  background: rgba(var(--v-theme-info), 0.08);
  color: rgb(var(--v-theme-info));
  border-color: rgba(var(--v-theme-info), 0.15);
}

.scfg-toast__close {
  margin-left: auto;
  background: none;
  border: none;
  cursor: pointer;
  color: inherit;
  opacity: 0.6;
  display: flex;
  transition: opacity 0.2s ease;
}

.scfg-toast__close:hover { opacity: 1; }

.scfg-slide-enter-active,
.scfg-slide-leave-active { transition: all 0.3s ease; }
.scfg-slide-enter-from,
.scfg-slide-leave-to { opacity: 0; transform: translateY(-8px); }

.scfg-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.scfg-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.scfg-card__title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.scfg-divider {
  height: 0.5px;
  background: rgba(var(--v-theme-on-surface), 0.08);
  margin: 0 -4px;
}

.scfg-divider--guide {
  margin: 2px 0;
}

.scfg-field {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.scfg-switch-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.scfg-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.scfg-form-grid--settings .scfg-form-item:first-child {
  grid-column: span 1;
}

.scfg-form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.scfg-guide {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.72);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.scfg-guide__paragraph {
  margin: 0;
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.scfg-guide__contact {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.scfg-contact-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 12px;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  background: rgba(var(--v-theme-surface), 0.72);
  color: rgba(var(--v-theme-on-surface), 0.82);
}

.scfg-contact-link:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
}

.scfg-contact-link--email {
  color: #0f766e;
  border-color: rgba(15, 118, 110, 0.14);
  background: rgba(20, 184, 166, 0.08);
}

.scfg-contact-link--tg {
  color: #2563eb;
  border-color: rgba(37, 99, 235, 0.14);
  background: rgba(59, 130, 246, 0.08);
}

.scfg-guide__item {
  color: rgba(var(--v-theme-on-surface), 0.78);
}

.scfg-guide__section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scfg-guide__section-title {
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.82);
}

.scfg-guide__list {
  margin: 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.scfg-field__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.scfg-field__title-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scfg-field__title-icon {
  flex-shrink: 0;
}

.scfg-field__title-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.scfg-field__label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.72);
}

.scfg-field__hint {
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.45);
}

.scfg-field__hint--compact {
  line-height: 1.3;
}

.scfg-switch-list,
.scfg-form-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.scfg-switch-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 14px;
  background: rgba(var(--v-theme-surface), 0.78);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.scfg-switch-item--active {
  border-color: color-mix(in srgb, var(--scfg-accent) 45%, transparent);
  background: color-mix(in srgb, var(--scfg-accent) 7%, rgba(var(--v-theme-surface), 0.9));
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06), inset 0 0 0 1px color-mix(in srgb, var(--scfg-accent) 18%, transparent);
}

.scfg-switch-item__main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.scfg-switch-item__icon {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--scfg-accent);
  background: color-mix(in srgb, var(--scfg-accent) 14%, transparent);
}

.scfg-switch-grid .scfg-switch-item {
  padding: 14px 16px;
}

.scfg-switch-grid .scfg-switch-item:last-child {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}

.scfg-switch-item:last-child {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  padding-bottom: 14px;
}

.scfg-switch-item__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.scfg-switch-item__label {
  font-size: 13px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.84);
}

.scfg-switch-item__hint,
.scfg-field-hint {
  font-size: 12px;
  color: rgba(var(--v-theme-on-surface), 0.55);
  line-height: 1.5;
}

.scfg-switch {
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgba(var(--v-theme-on-surface), 0.22);
  --switch-checked-bg: rgb(var(--v-theme-primary));
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-checked-shadow: -1px 1px 2px rgba(0, 0, 0, 0.2);
  --circle-transition: var(--switch-transition);
  --icon-transition: all 0.2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: rgba(0, 0, 0, 0.4);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all 0.2s ease-in-out;
  display: inline-block;
  flex-shrink: 0;
  user-select: none;
}

.scfg-switch input {
  display: none;
}

.scfg-switch svg {
  transition: var(--icon-transition);
  position: absolute;
  height: auto;
}

.scfg-switch__checkmark {
  width: var(--icon-checkmark-size);
  color: var(--icon-checkmark-color);
  transform: scale(0);
}

.scfg-switch__cross {
  width: var(--icon-cross-size);
  color: var(--icon-cross-color);
}

.scfg-switch__slider {
  box-sizing: border-box;
  width: var(--switch-width);
  height: var(--switch-height);
  background: var(--switch-bg);
  border-radius: 999px;
  display: flex;
  align-items: center;
  position: relative;
  transition: var(--switch-transition);
  cursor: pointer;
}

.scfg-switch__circle {
  width: var(--circle-diameter);
  height: var(--circle-diameter);
  background: var(--circle-bg);
  border-radius: inherit;
  box-shadow: var(--circle-shadow);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--circle-transition);
  z-index: 1;
  position: absolute;
  left: var(--switch-offset);
}

.scfg-switch__slider::before {
  content: "";
  position: absolute;
  width: var(--effect-width);
  height: var(--effect-height);
  left: calc(var(--switch-offset) + (var(--effect-width) / 2));
  background: var(--effect-bg);
  border-radius: var(--effect-border-radius);
  transition: var(--effect-transition);
}

.scfg-switch input:checked + .scfg-switch__slider {
  background: var(--switch-checked-bg);
}

.scfg-switch input:checked + .scfg-switch__slider .scfg-switch__checkmark {
  transform: scale(1);
}

.scfg-switch input:checked + .scfg-switch__slider .scfg-switch__cross {
  transform: scale(0);
}

.scfg-switch input:checked + .scfg-switch__slider::before {
  left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset));
}

.scfg-switch input:checked + .scfg-switch__slider .scfg-switch__circle {
  left: calc(100% - var(--circle-diameter) - var(--switch-offset));
  box-shadow: var(--circle-checked-shadow);
}

.scfg-switch input:disabled + .scfg-switch__slider {
  opacity: 0.5;
  cursor: not-allowed;
}

.scfg-input :deep(.v-field) {
  border-radius: 12px;
  background: rgba(var(--v-theme-surface), 0.72);
}

@media (max-width: 960px) {
  .scfg-switch-grid,
  .scfg-form-grid {
    grid-template-columns: 1fr;
  }

  .scfg-form-grid--settings .scfg-form-item:first-child {
    grid-column: span 1;
  }
}

@media (max-width: 768px) {
  .scfg-page {
    padding: 14px;
  }

  .scfg-topbar {
    align-items: center;
    flex-wrap: nowrap;
  }

  .scfg-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .scfg-topbar__meta {
    min-width: 0;
  }

  .scfg-topbar__right {
    justify-content: flex-end;
    flex-shrink: 0;
  }

  .scfg-switch-item,
  .scfg-switch-item__main {
    align-items: flex-start;
  }

  .scfg-switch-item {
    padding: 14px;
  }
}
</style>
