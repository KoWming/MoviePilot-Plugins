<template>
  <div class="mr-config">
    <div class="mr-topbar">
      <div class="mr-topbar__left">
        <div class="mr-topbar__icon">
          <v-icon icon="mdi-tune-variant" size="24" />
        </div>
        <div>
          <div class="mr-topbar__title">PTD 导入 · 配置中心</div>
          <div class="mr-topbar__sub">导入策略、字段映射与兼容行为配置</div>
        </div>
      </div>
      <div class="mr-topbar__right">
        <v-btn-group variant="tonal" density="compact" class="elevation-0">
          <v-btn color="primary" @click="emit('switch')" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="primary" :loading="saving" @click="saveConfig" size="small" min-width="40" class="px-0 px-sm-3">
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

    <v-row class="mr-panel-row">
      <v-col cols="12">
        <div class="mr-card">
          <div class="mr-card__header">
            <span class="mr-card__title d-flex align-center">
              <v-icon icon="mdi-tune-vertical" size="18" color="#8b5cf6" class="mr-1"></v-icon>
              基础设置
            </span>
          </div>

          <v-row class="mt-1 mb-1">
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-power-plug" size="20" :color="config.enabled ? '#a78bfa' : 'grey'" class="mr-2"></v-icon>
                启用站点导入
              </span>
              <label class="switch" style="--switch-checked-bg: #a78bfa;">
                <input v-model="config.enabled" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-shield-check" size="20" :color="config.only_supported ? '#3b82f6' : 'grey'" class="mr-2"></v-icon>
                仅导入支持站点
              </span>
              <label class="switch" style="--switch-checked-bg: #3b82f6;">
                <input v-model="config.only_supported" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-history" size="20" :color="config.only_active ? '#10b981' : 'grey'" class="mr-2"></v-icon>
                仅处理活跃站点
              </span>
              <label class="switch" style="--switch-checked-bg: #10b981;">
                <input v-model="config.only_active" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
          </v-row>

          <div class="mr-card__header mt-3">
            <span class="mr-card__title d-flex align-center">
              <v-icon icon="mdi-database-import-outline" size="18" color="#0ea5e9" class="mr-1"></v-icon>
              导入字段控制
            </span>
          </div>

          <v-row class="mt-1 mb-1">
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-cookie-outline" size="20" :color="config.import_cookie ? '#f59e0b' : 'grey'" class="mr-2"></v-icon>
                导入 Cookie
              </span>
              <label class="switch" style="--switch-checked-bg: #f59e0b;">
                <input v-model="config.import_cookie" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-key-outline" size="20" :color="config.import_token ? '#14b8a6' : 'grey'" class="mr-2"></v-icon>
                导入 Token
              </span>
              <label class="switch" style="--switch-checked-bg: #14b8a6;">
                <input v-model="config.import_token" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
            <v-col cols="12" sm="6" md="4" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-api" size="20" :color="config.import_apikey ? '#ec4899' : 'grey'" class="mr-2"></v-icon>
                导入 ApiKey
              </span>
              <label class="switch" style="--switch-checked-bg: #ec4899;">
                <input v-model="config.import_apikey" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
          </v-row>
        </div>
      </v-col>

      <v-col cols="12" md="12">
        <div class="mr-card mr-card--panel">
          <div class="mr-card__header">
            <span class="mr-card__title d-flex align-center">
              <v-icon icon="mdi-shuffle-variant" size="18" color="#6366f1" class="mr-1"></v-icon>
              导入逻辑
            </span>
          </div>

          <v-select
            v-model="config.import_mode"
            :items="importModeOptions"
            item-title="title"
            item-value="value"
            label="已存在站点处理方式"
            variant="outlined"
            density="comfortable"
            class="mr-input mt-2"
          />

          <div class="mr-card__header mt-1">
            <span class="mr-card__title d-flex align-center">
              <v-icon icon="mdi-transit-connection-variant" size="16" color="#f59e0b" class="mr-1"></v-icon>
              缺失字段补全（PTD 备份通常不含以下信息）
            </span>
          </div>

          <div class="d-flex align-center" style="gap: 8px;">
            <v-text-field
              v-model="config.default_ua"
              label="站点 User-Agent"
              variant="outlined"
              density="comfortable"
              class="mr-input flex-grow-1"
              clearable
              hide-details
              placeholder="站点User-Agent"
            />
            <v-btn
              variant="tonal"
              color="primary"
              size="small"
              style="height: 40px; flex-shrink: 0;"
              class="mr-ua-btn"
              @click="fillBrowserUA"
            >
              <v-icon icon="mdi-cellphone-arrow-down" size="16" class="mr-ua-btn__icon"></v-icon>
              <span class="mr-ua-btn__text">获取当前 UA</span>
            </v-btn>
          </div>

          <v-row class="mt-0 mb-0">
            <v-col cols="12" sm="6" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-vpn" size="20" :color="config.default_proxy ? '#6366f1' : 'grey'" class="mr-2"></v-icon>
                使用代理访问
                <v-tooltip location="top" text="导入时为缺少代理配置的站点统一启用代理">
                  <template #activator="{ props: tp }"><v-icon v-bind="tp" icon="mdi-help-circle-outline" size="14" class="ml-1" style="opacity:0.5"></v-icon></template>
                </v-tooltip>
              </span>
              <label class="switch" style="--switch-checked-bg: #6366f1;">
                <input v-model="config.default_proxy" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
            <v-col cols="12" sm="6" class="d-flex align-center justify-space-between py-1">
              <span class="mr-row__text">
                <v-icon icon="mdi-google-chrome" size="20" :color="config.default_render ? '#f59e0b' : 'grey'" class="mr-2"></v-icon>
                浏览器仿真
                <v-tooltip location="top" text="导入时为缺少仿真配置的站点启用浏览器渲染模式（JS渲染站点使用）">
                  <template #activator="{ props: tp }"><v-icon v-bind="tp" icon="mdi-help-circle-outline" size="14" class="ml-1" style="opacity:0.5"></v-icon></template>
                </v-tooltip>
              </span>
              <label class="switch" style="--switch-checked-bg: #f59e0b;">
                <input v-model="config.default_render" type="checkbox" />
                <div class="slider">
                  <div class="circle">
                    <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                    <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g transform="translate(-0.4, 0.2)"><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                  </div>
                </div>
              </label>
            </v-col>
          </v-row>

          <div class="mr-empty-state">
            <v-icon icon="mdi-lightbulb-on-outline" size="16" color="info" class="mr-1"></v-icon>
            建议使用"仅更新 Cookie/凭据"。UA 仅作为 PTD 缺失时的统一填充值；代理和仿真默认关闭，仅在需要时开启。
          </div>
        </div>
      </v-col>
    </v-row>

    <div class="mr-card">
      <div class="mr-card__header">
        <span class="mr-card__title d-flex align-center">
          <v-icon icon="mdi-book-open-page-variant-outline" size="18" color="#0ea5e9" class="mr-1"></v-icon>
          使用说明
        </span>
      </div>

      <div class="mr-desc-content">
        <div class="mb-2"><strong>导入模式：</strong>支持跳过、更新凭据、整站覆盖三种策略，适用于不同的站点同步场景。</div>
        <div class="mb-2"><strong>字段导入：</strong>可以独立控制 Cookie、Token、ApiKey 是否写入，避免误覆盖现有配置。</div>
        <div class="mb-2"><strong>兼容控制：</strong>开启“仅导入 MP 支持站点”后，可提前过滤暂未适配的站点，降低界面中冗余项的出现。</div>
      </div>
    </div>

    <v-snackbar v-model="message.show" :color="message.type" :timeout="2500" location="top">
      {{ message.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'

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
  post: async (url, data) => {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    return res.json()
  },
})

const apiClient = props.api || createDefaultApi()
const saving = ref(false)
const importModeOptions = ref([
  { title: '仅更新认证信息 (推荐)', value: 'update_auth' },
  { title: '跳过 (保留MP配置)', value: 'skip' },
  { title: '全面覆盖 (危险)', value: 'update_all' },
])

const config = reactive({
  enabled: false,
  only_active: true,
  only_supported: true,
  import_mode: 'update_auth',
  import_cookie: true,
  import_token: true,
  import_apikey: true,
  default_ua: '',
  default_proxy: false,
  default_render: false,
})

const fillBrowserUA = () => {
  config.default_ua = navigator.userAgent
}
const message = reactive({ show: false, type: 'info', text: '' })

const loadConfig = async () => {
  const res = await apiClient.get(`/plugin/${PLUGIN_ID}/config`)
  if (res) {
    Object.assign(config, res)
    if (config.default_ua === undefined) config.default_ua = ''
    if (config.default_proxy === undefined) config.default_proxy = false
    if (config.default_render === undefined) config.default_render = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const res = await apiClient.post(`/plugin/${PLUGIN_ID}/config`, { ...config })
    if (res?.success) {
      message.type = 'success'
      message.text = res.message || '保存成功'
    } else {
      message.type = 'error'
      message.text = res?.message || '保存失败'
    }
  } catch (error) {
    message.type = 'error'
    message.text = String(error)
  } finally {
    message.show = true
    saving.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.mr-config {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Inter', sans-serif;
  -webkit-font-smoothing: antialiased;
  color: rgba(var(--v-theme-on-surface), 0.85);
  min-height: 400px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}

.mr-topbar,
.mr-card__header,
.mr-results,
.mr-row__text {
  display: flex;
  align-items: center;
}

.mr-topbar,
.mr-card__header {
  justify-content: space-between;
}

.mr-topbar__left,
.mr-topbar__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mr-topbar__right {
  flex-shrink: 0;
}

.mr-topbar__right :deep(.v-btn-group) {
  flex-wrap: nowrap;
}

.mr-topbar__icon {
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

.mr-topbar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.3px;
}

.mr-topbar__sub,
.mr-alert-rules {
  color: rgba(var(--v-theme-on-surface), 0.55);
}

.mr-topbar__sub,
.mr-alert-rules {
  font-size: 11px;
}

.mr-panel-row {
  margin: -8px;
}

.mr-card {
  background: rgba(var(--v-theme-on-surface), 0.03);
  backdrop-filter: blur(20px) saturate(150%);
  border-radius: 14px;
  border: 0.5px solid rgba(var(--v-theme-on-surface), 0.08);
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
}

.mr-card__title {
  font-size: 13px;
  font-weight: 600;
}

.mr-row__text {
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.85);
}

.mr-input :deep(.v-field) {
  border-radius: 12px;
}

.mr-ua-btn__icon {
  margin-right: 4px;
}

.mr-empty-state {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(var(--v-theme-on-surface), 0.65);
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px dashed rgba(var(--v-theme-info), 0.22);
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  align-items: center;
}

.mr-desc-content {
  color: rgba(var(--v-theme-on-surface), 0.78);
  font-size: 13px;
  line-height: 1.8;
}

.mr-alert-rules {
  background: rgba(var(--v-theme-warning), 0.08);
  border: 1px dashed rgba(var(--v-theme-warning), 0.24);
  border-radius: 10px;
  padding: 10px 12px;
}

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

@media (max-width: 768px) {
  .mr-config {
    padding: 14px;
  }

  .mr-topbar {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;
  }

  .mr-topbar__left {
    min-width: 0;
    flex: 1;
  }

  .mr-topbar__right {
    justify-content: flex-end;
  }

  .mr-topbar__right :deep(.v-btn-group) {
    gap: 0;
  }

  .mr-topbar__right :deep(.v-btn) {
    min-width: 36px !important;
    padding-inline: 0 !important;
  }

  .mr-ua-btn {
    min-width: 40px !important;
    padding-inline: 0 !important;
  }

  .mr-ua-btn__icon {
    margin-right: 0;
  }

  .mr-ua-btn__text {
    display: none;
  }
}
</style>
