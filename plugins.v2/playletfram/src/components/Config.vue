<template>
  <div class="plugin-config">
    <v-card flat class="rounded border">
      <!-- 标题区域 -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary">
        <v-icon icon="mdi-cog" class="mr-2" color="white" size="small"></v-icon>
        <span class="text-white">开心农场配置</span>
        <v-spacer />

        <!-- 操作按钮组 -->
         <v-btn-group variant="outlined" density="compact" class="mr-1">
          <v-btn color="white" @click="switchToPage" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-view-dashboard" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">状态页</span>
          </v-btn>
          <v-btn color="white" @click="resetConfig" :disabled="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-restore" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">重置</span>
          </v-btn>
          <v-btn color="white" @click="saveConfig" :loading="saving" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-content-save" size="18" class="mr-sm-1"></v-icon>
            <span class="btn-text d-none d-sm-inline">保存</span>
          </v-btn>
          <v-btn color="white" @click="closePlugin" size="small" min-width="40" class="px-0 px-sm-3">
            <v-icon icon="mdi-close" size="18"></v-icon>
            <span class="btn-text d-none d-sm-inline">关闭</span>
          </v-btn>
        </v-btn-group>
      </v-card-title>
      
      <v-card-text class="px-3 py-3" style="position: relative;">
        <div style="position: absolute; top: 0; left: 0; right: 0; z-index: 50; padding: 0 10px 10px 10px;">
          <transition name="slide-fade">
            <v-alert
              v-if="successMessage"
              type="success"
              density="compact"
              class="mb-2 text-caption"
              variant="elevated"
              closable
              @click:close="successMessage = ''"
            >
              {{ successMessage }}
            </v-alert>
          </transition>
          <transition name="slide-fade">
            <v-alert
              v-if="errorMessage"
              type="error"
              density="compact"
              class="mb-2 text-caption"
              variant="elevated"
              closable
              @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>
          </transition>
        </div>
        <v-form>
          <!-- 基础设置 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 px-3 py-2 bg-purple-lighten-5 d-flex align-center">
              <v-icon icon="mdi-tune" class="mr-2" color="purple" size="small"></v-icon>
              基础设置
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-play-circle-outline" size="small" :color="config.enabled ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">启用插件</div>
                          <div class="text-caption text-grey">是否启用开心农场插件</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #bc98fd;">
                          <input v-model="config.enabled" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-message-processing-outline" size="small" :color="config.notify ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">开启通知</div>
                          <div class="text-caption text-grey">操作完成后发送消息通知</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #73cffe;">
                          <input v-model="config.notify" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-earth" size="small" :color="config.use_proxy ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">使用代理</div>
                          <div class="text-caption text-grey">使用系统代理请求</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #9adf66;">
                          <input v-model="config.use_proxy" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 自动化功能 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 px-3 py-2 bg-green-lighten-5 d-flex align-center">
              <v-icon icon="mdi-robot-outline" class="mr-2" color="success" size="small"></v-icon>
              自动化功能
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-barley" size="small" :color="config.auto_plant ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">自动种植</div>
                          <div class="text-caption text-grey">定时任务自动种植/养殖</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #bc98fd;">
                          <input v-model="config.auto_plant" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-store-outline" size="small" :color="config.auto_sell ? 'warning' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">自动出售</div>
                          <div class="text-caption text-grey">定时任务自动出售仓库</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #73cffe;">
                          <input v-model="config.auto_sell" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
                <!-- 新增：临期自动出售 -->
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-timer-alert-outline" size="small" :color="config.expiry_sale_enabled ? 'deep-orange' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex align-center justify-space-between w-100">
                        <div class="setting-text">
                          <div class="text-subtitle-2 font-weight-bold">临期自动出售</div>
                          <div class="text-caption text-grey">剩余时间&lt;1小时自动出售</div>
                        </div>
                        <label class="switch" style="--switch-checked-bg: #9adf66;">
                          <input v-model="config.expiry_sale_enabled" type="checkbox" :disabled="saving">
                          <div class="slider">
                            <div class="circle">
                              <svg class="cross" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 365.696 365.696" y="0" x="0" height="6" width="6" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path data-original="#000000" fill="currentColor" d="M243.188 182.86 356.32 69.726c12.5-12.5 12.5-32.766 0-45.247L341.238 9.398c-12.504-12.503-32.77-12.503-45.25 0L182.86 122.528 69.727 9.374c-12.5-12.5-32.766-12.5-45.247 0L9.375 24.457c-12.5 12.504-12.5 32.77 0 45.25l113.152 113.152L9.398 295.99c-12.503 12.503-12.503 32.769 0 45.25L24.48 356.32c12.5 12.5 32.766 12.5 45.247 0l113.132-113.132L295.99 356.32c12.503 12.5 32.769 12.5 45.25 0l15.081-15.082c12.5-12.504 12.5-32.77 0-45.25zm0 0"></path></g></svg>
                              <svg class="checkmark" xml:space="preserve" style="enable-background:new 0 0 512 512" viewBox="0 0 24 24" y="0" x="0" height="10" width="10" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg"><g><path class="" data-original="#000000" fill="currentColor" d="M9.707 19.121a.997.997 0 0 1-1.414 0l-5.646-5.647a1.5 1.5 0 0 1 0-2.121l.707-.707a1.5 1.5 0 0 1 2.121 0L9 14.171l9.525-9.525a1.5 1.5 0 0 1 2.121 0l.707.707a1.5 1.5 0 0 1 0 2.121z"></path></g></svg>
                            </div>
                          </div>
                        </label>
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>

            <!-- 自动出售详细配置 -->
            <v-expand-transition>
              <div v-if="config.auto_sell">
                <v-divider class="my-1"></v-divider>
                <div class="px-3 py-2">
                  <v-row>
                    <v-col cols="12">
                      <v-text-field
                        v-model.number="config.auto_sell_threshold"
                        label="最低盈利百分比 (%)"
                        placeholder="0"
                        type="number"
                        variant="outlined"
                        density="compact"
                        :min="0"
                        :max="20"
                        :rules="[v => v === null || v === '' || (Number(v) >= 0 && Number(v) <= 20) || '百分比必须在0-20之间']"
                        hint="只有利润率(现价-成本)/成本 达到此数值才出售。设为0则不限制 (最大20%)。"
                        persistent-hint
                        prepend-inner-icon="mdi-percent-outline"
                        :disabled="saving"
                        class="text-caption"
                        hide-details="auto"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>
              </div>
            </v-expand-transition>
          </v-card>

          <!-- 认证与定时 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
              <v-icon icon="mdi-key" class="mr-2" color="warning" size="small" />
              <span>认证与定时</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="config.cookie"
                    label="Cookie"
                    placeholder="请输入站点的Cookie"
                    type="password"
                    variant="outlined"
                    hint="登录PlayLetpt站点后，从浏览器开发者工具中复制Cookie"
                    persistent-hint
                    prepend-inner-icon="mdi-cookie"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  >
                    <template #append-inner>
                      <div class="tooltip-container">
                        <v-btn 
                          icon
                          variant="tonal"
                          color="secondary"
                          @click="fillWithSiteCookie" 
                          :disabled="saving || loadingCookie" 
                          size="small"
                          class="tooltip-btn"
                        >
                          <template v-if="!loadingCookie">
                            <v-icon color="secondary" size="small" class="tooltip-icon">mdi-content-paste</v-icon>
                          </template>
                          <v-progress-circular
                            v-else
                            indeterminate
                            size="16"
                            width="2"
                            color="primary"
                          ></v-progress-circular>
                        </v-btn>
                        <div class="custom-tooltip">
                          <div class="custom-tooltip-content">
                            <span class="tooltip-text">使用已添加站点的Cookie</span>
                          </div>
                        </div>
                      </div>
                    </template>
                  </v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <VCronField
                    v-model="config.cron"
                    label="Cron表达式"
                    hint="设置执行周期，如：0 8 * * * (每天8点执行一次)"
                    persistent-hint
                    density="compact"
                  ></VCronField>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.retry_count"
                    label="重试次数"
                    type="number"
                    variant="outlined"
                    :min="0"
                    :max="10"
                    hint="请求失败时的重试次数 (0-10)"
                    persistent-hint
                    prepend-inner-icon="mdi-refresh"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="config.retry_interval"
                    label="重试间隔(秒)"
                    type="number"
                    variant="outlined"
                    :min="1"
                    :max="60"
                    hint="失败重试的间隔时间 (1-60秒)"
                    persistent-hint
                    prepend-inner-icon="mdi-timer-sand"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 玩法说明 -->
          <v-card flat class="rounded mb-3 border inner-card">
            <v-card-title class="text-subtitle-2 px-3 py-2 bg-blue-lighten-5 d-flex align-center">
              <v-icon icon="mdi-book-open-page-variant-outline" class="mr-2" color="info" size="small"></v-icon>
              玩法说明
            </v-card-title>
            <v-card-text class="px-3 py-2 text-caption">
              <div class="mb-2"><strong>🎯 核心目标：</strong>通过种植农作物、养殖动物收获物品，在菜市场出售获取魔力值，积累资源解锁更高价值的动植物，成为农场大亨～</div>
              
              <v-divider class="my-2"></v-divider>
              
              <div class="mb-1"><strong>📚 基础概念：</strong></div>
              <ul class="pl-4 mb-2">
                <li><strong>💎 魔力值：</strong>游戏核心货币，用于种植/养殖，出售物品可获得，页面顶部实时显示</li>
                <li><strong>⏳ 成长时间：</strong>作物/动物从种植/养殖到可收获的时间（单位：小时）</li>
                <li><strong>📅 有效期：</strong>收获后物品存入仓库，超过有效期自动失效（作物2天，动物5天）</li>
                <li><strong>📈 市场价格：</strong>出售物品的单价，每24小时随机波动±20%，菜市场可查看实时价格</li>
                <li><strong>🏠 仓库：</strong>存放收获的物品，最多存储10种不同物品，需及时出售避免过期</li>
              </ul>
              
              <v-divider class="my-2"></v-divider>

              <div class="mb-1"><strong>👣 操作步骤：</strong></div>
              <ol class="pl-4 mb-2">
                <li><strong>🌱 种植/养殖：</strong>在「农作物种植区」或「动物养殖区」，选择物品点击「种植」/「养殖」（需消耗对应魔力值，且未处于该物品的种植/养殖中）</li>
                <li><strong>🌾 收获物品：</strong>物品成熟后（剩余时间为0），点击「收获」或顶部「一键收获」，物品自动存入仓库</li>
                <li><strong>💰 出售赚钱：</strong>在「仓库」选择未过期物品点击「出售」，按菜市场实时价格获得魔力值（建议价格上涨时出售，赚更多哦）</li>
              </ol>

              <v-alert density="compact" type="info" variant="tonal" class="mt-2 text-caption" border="start">
                <strong>💡 温馨提示：</strong><br>
                1. 魔力值不足时，可先出售仓库物品获取资源<br>
                2. 同一物品同一时间只能种植/养殖一次，需收获后才能再次操作<br>
                3. 定期查看仓库物品有效期，避免过期损失<br>
                4. 市场价格每天更新一次，可关注高价时段集中出售
              </v-alert>
            </v-card-text>
          </v-card>
        </v-form>
      </v-card-text>

    </v-card>


  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue';

// 定义 Props
const props = defineProps({
  api: {
    type: Object,
    required: false,
    default: null
  },
  initialConfig: {
    type: Object,
    default: () => ({})
  }
});

// 定义 Emits
const emit = defineEmits(['close', 'switch', 'save']);

// 插件 ID
const PLUGIN_ID = 'PlayletFram';

// Client
const createDefaultApi = () => ({
  get: async (url) => {
    const res = await fetch(url);
    return res.json();
  },
  post: async (url, data) => {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  }
});

const apiClient = props.api || createDefaultApi();

const saving = ref(false);
const loadingCookie = ref(false);
const config = reactive({
  enabled: false,
  notify: true,
  cron: '',
  cookie: '',
  auto_plant: false,
  auto_sell: false,
  auto_sell_threshold: 0,
  expiry_sale_enabled: false,
  expiry_sale_enabled: false,
  use_proxy: false,
  retry_count: 3,
  retry_interval: 5
});

// 缓存原始配置用于重置
const originalConfig = reactive({});

const successMessage = ref('');
const errorMessage = ref('');

const showNotification = (message, color = 'success') => {
  if (color === 'success') {
    successMessage.value = message;
    errorMessage.value = '';
    setTimeout(() => {
      successMessage.value = '';
    }, 3000);
  } else {
    errorMessage.value = message;
    successMessage.value = '';
    setTimeout(() => {
      errorMessage.value = '';
    }, 3000);
  }
};

// 填充站点Cookie
const fillWithSiteCookie = async () => {
  loadingCookie.value = true;
  try {
    const url = `/plugin/${PLUGIN_ID}/cookie`;
    const res = await apiClient.get(url);
    
    if (res && res.success) {
      if (typeof res.cookie === 'string' && res.cookie.trim().toLowerCase() === 'cookie') {
        showNotification('站点Cookie无效，请在站点管理中配置真实Cookie', 'error');
        return;
      }
      config.cookie = res.cookie;
      showNotification('已成功获取站点Cookie', 'success');
    } else {
      showNotification(res.msg || '获取站点Cookie失败', 'error');
    }
  } catch (e) {
    console.error('获取站点Cookie失败:', e);
    showNotification('获取站点Cookie失败: ' + (e.message || '未知错误'), 'error');
  } finally {
    loadingCookie.value = false;
  }
};

// 加载配置
const loadConfig = async () => {
  try {
    const url = `/plugin/${PLUGIN_ID}/config`;
    const res = await apiClient.get(url);
    
    console.log('加载配置:', res);
    
    if (res) {
      config.enabled = res.enabled !== undefined ? res.enabled : false;
      config.notify = res.notify !== undefined ? res.notify : true;
      config.cron = res.cron || '';
      config.cookie = res.cookie || '';
      config.auto_plant = res.auto_plant !== undefined ? res.auto_plant : false;
      config.auto_sell = res.auto_sell !== undefined ? res.auto_sell : false;
      config.auto_sell_threshold = res.auto_sell_threshold !== undefined ? res.auto_sell_threshold : 0;
      config.expiry_sale_enabled = res.expiry_sale_enabled !== undefined ? res.expiry_sale_enabled : false;
      config.expiry_sale_enabled = res.expiry_sale_enabled !== undefined ? res.expiry_sale_enabled : false;
      config.use_proxy = res.use_proxy !== undefined ? res.use_proxy : false;
      config.retry_count = res.retry_count !== undefined ? res.retry_count : 3;
      config.retry_interval = res.retry_interval !== undefined ? res.retry_interval : 5;
      
      // 保存到缓存
      Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));

      showNotification('配置加载成功', 'success');
    }
  } catch (e) {
    console.error('加载配置失败:', e);
    showNotification('加载配置失败: ' + (e.message || '未知错误'), 'error');
  }
};

// 重置配置
const resetConfig = () => {
  try {
    if (Object.keys(originalConfig).length > 0) {
      Object.assign(config, JSON.parse(JSON.stringify(originalConfig)));
      showNotification('配置已重置为初始状态', 'success');
    } else {
      loadConfig();
    }
  } catch (e) {
    console.error('重置配置失败:', e);
    loadConfig();
  }
};

// 保存配置
const saveConfig = async () => {
  saving.value = true;
  try {
    console.log('保存配置:', config);
    
    // 使用 emit 触发保存，交由父组件/宿主处理
    emit('save', JSON.parse(JSON.stringify(config)));
    
    showNotification('已发送保存请求', 'success');
  } catch (e) {
    console.error('保存配置失败:', e);
    showNotification('保存配置失败: ' + (e.message || '未知错误'), 'error');
  } finally {
    saving.value = false;
  }
};

const switchToPage = () => {
  emit('switch', 'page');
};

const closePlugin = () => {
  emit('close');
};

watch(() => props.initialConfig, (newConfig) => {
  if (newConfig && Object.keys(newConfig).length > 0) {
    config.enabled = newConfig.enabled || false;
    config.notify = newConfig.notify !== false;
    config.cron = newConfig.cron || '';
    config.cookie = newConfig.cookie || '';
    config.auto_plant = newConfig.auto_plant || false;
    config.auto_sell = newConfig.auto_sell || false;
    config.auto_sell_threshold = newConfig.auto_sell_threshold || 0;
    config.expiry_sale_enabled = newConfig.expiry_sale_enabled || false;
    config.use_proxy = newConfig.use_proxy || false;
    config.retry_count = newConfig.retry_count !== undefined ? newConfig.retry_count : 3;
    config.retry_interval = newConfig.retry_interval !== undefined ? newConfig.retry_interval : 5;
    
    // 初始化时也保存一份到缓存
    Object.assign(originalConfig, JSON.parse(JSON.stringify(config)));
  }
}, { immediate: true, deep: true });

onMounted(() => {
  loadConfig();
});
</script>

<style scoped>
.plugin-config {
  margin: 0 auto;
  padding: 0.5rem;
}

/* 蓝色主题 */
.bg-gradient-primary {
  background: #3498db;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.3);
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.inner-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.inner-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 标题背景色 */
.bg-purple-lighten-5 {
  background-color: rgba(156, 39, 176, 0.07) !important;
}

.bg-green-lighten-5 {
  background-color: rgba(76, 175, 80, 0.1) !important;
}

.bg-orange-lighten-5 {
  background-color: rgba(255, 152, 0, 0.1) !important;
}

.bg-blue-lighten-5 {
  background-color: rgba(33, 150, 243, 0.1) !important;
}

/* 设置项样式 */
/* 设置项样式 */
.setting-item {
  /* 移除卡片背景 */
  background: transparent;
  padding: 0;
}

.setting-content {
  width: 100%;
}

.text-subtitle-1 {
  font-size: 1.1rem !important;
  font-weight: 500;
}

.text-subtitle-2 {
  font-size: 0.9rem !important;
  font-weight: 500;
}

/* 输入框样式适配 */
.v-textarea :deep(.v-field), .v-text-field :deep(.v-field) {
  border-radius: 8px !important;
}

/* 按钮组内按钮文本 */
.v-btn-group .v-btn .btn-text {
  font-weight: 500;
}


/* 自定义开关样式 */
.switch {
  /* switch */
  --switch-width: 36px;
  --switch-height: 20px;
  --switch-bg: rgb(131, 131, 131);
  --switch-checked-bg: rgb(0, 218, 80);
  --switch-offset: calc((var(--switch-height) - var(--circle-diameter)) / 2);
  --switch-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  /* circle */
  --circle-diameter: 16px;
  --circle-bg: #fff;
  --circle-shadow: 1px 1px 2px rgba(146, 146, 146, 0.45);
  --circle-checked-shadow: -1px 1px 2px rgba(163, 163, 163, 0.45);
  --circle-transition: var(--switch-transition);
  /* icon */
  --icon-transition: all .2s cubic-bezier(0.27, 0.2, 0.25, 1.51);
  --icon-cross-color: var(--switch-bg);
  --icon-cross-size: 6px;
  --icon-checkmark-color: var(--switch-checked-bg);
  --icon-checkmark-size: 10px;
  /* effect line */
  --effect-width: calc(var(--circle-diameter) / 2);
  --effect-height: calc(var(--effect-width) / 2 - 1px);
  --effect-bg: var(--circle-bg);
  --effect-border-radius: 1px;
  --effect-transition: all .2s ease-in-out;
}

.switch input {
  display: none;
}

.switch {
  display: inline-block;
  margin-left: 16px;
}

.switch svg {
  -webkit-transition: var(--icon-transition);
  -o-transition: var(--icon-transition);
  transition: var(--icon-transition);
  position: absolute;
  height: auto;
}

.switch .checkmark {
  width: var(--icon-checkmark-size);
  color: var(--icon-checkmark-color);
  -webkit-transform: scale(0);
  -ms-transform: scale(0);
  transform: scale(0);
}

.switch .cross {
  width: var(--icon-cross-size);
  color: var(--icon-cross-color);
}

.slider {
  -webkit-box-sizing: border-box;
  box-sizing: border-box;
  width: var(--switch-width);
  height: var(--switch-height);
  background: var(--switch-bg);
  border-radius: 999px;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  position: relative;
  -webkit-transition: var(--switch-transition);
  -o-transition: var(--switch-transition);
  transition: var(--switch-transition);
  cursor: pointer;
}

.circle {
  width: var(--circle-diameter);
  height: var(--circle-diameter);
  background: var(--circle-bg);
  border-radius: inherit;
  -webkit-box-shadow: var(--circle-shadow);
  box-shadow: var(--circle-shadow);
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  -webkit-box-pack: center;
  -ms-flex-pack: center;
  justify-content: center;
  -webkit-transition: var(--circle-transition);
  -o-transition: var(--circle-transition);
  transition: var(--circle-transition);
  z-index: 1;
  position: absolute;
  left: var(--switch-offset);
}

.slider::before {
  content: "";
  position: absolute;
  width: var(--effect-width);
  height: var(--effect-height);
  left: calc(var(--switch-offset) + (var(--effect-width) / 2));
  background: var(--effect-bg);
  border-radius: var(--effect-border-radius);
  -webkit-transition: var(--effect-transition);
  -o-transition: var(--effect-transition);
  transition: var(--effect-transition);
}

/* actions */
.switch input:checked+.slider {
  background: var(--switch-checked-bg);
}

.switch input:checked+.slider .checkmark {
  -webkit-transform: scale(1);
  -ms-transform: scale(1);
  transform: scale(1);
}

.switch input:checked+.slider .cross {
  -webkit-transform: scale(0);
  -ms-transform: scale(0);
  transform: scale(0);
}

/* Fix CSS parse error in original: .switch input:checked+.slider::before */
.switch input:checked+.slider::before {
  left: calc(100% - var(--effect-width) - (var(--effect-width) / 2) - var(--switch-offset));
}

.switch input:checked+.slider .circle {
  left: calc(100% - var(--circle-diameter) - var(--switch-offset));
  -webkit-box-shadow: var(--circle-checked-shadow);
  box-shadow: var(--circle-checked-shadow);
}

/* disabled state */
.switch input:disabled+.slider {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 系统深色模式适配 */
@media (prefers-color-scheme: dark) {
  .setting-item {
    background: transparent;
  }
  
  .bg-purple-lighten-5 {
    background-color: rgba(156, 39, 176, 0.2) !important;
  }
  
  .bg-green-lighten-5 {
    background-color: rgba(76, 175, 80, 0.2) !important;
  }
  
  .bg-orange-lighten-5 {
    background-color: rgba(255, 152, 0, 0.2) !important;
  }
  
  .bg-blue-lighten-5 {
    background-color: rgba(33, 150, 243, 0.2) !important;
  }
  
  .text-subtitle-2 {
    color: rgb(220, 220, 220) !important;
  }
}

/* 深色模式适配 - 使用 data 属性选择器 */
[data-theme="dark"] .setting-item,
[data-theme="purple"] .setting-item,
[data-theme="transparent"] .setting-item {
  background: transparent !important;
  box-shadow: none !important;
}

[data-theme="dark"] .bg-purple-lighten-5,
[data-theme="purple"] .bg-purple-lighten-5,
[data-theme="transparent"] .bg-purple-lighten-5 {
  background-color: rgba(156, 39, 176, 0.2) !important;
}

[data-theme="dark"] .bg-green-lighten-5,
[data-theme="purple"] .bg-green-lighten-5,
[data-theme="transparent"] .bg-green-lighten-5 {
  background-color: rgba(76, 175, 80, 0.2) !important;
}

[data-theme="dark"] .bg-orange-lighten-5,
[data-theme="purple"] .bg-orange-lighten-5,
[data-theme="transparent"] .bg-orange-lighten-5 {
  background-color: rgba(255, 152, 0, 0.2) !important;
}

/* 深色模式文字适配 */
[data-theme="dark"] .text-subtitle-2,
[data-theme="purple"] .text-subtitle-2,
[data-theme="transparent"] .text-subtitle-2 {
  color: rgb(220, 220, 220) !important;
}

[data-theme="dark"] .setting-text .text-caption,
[data-theme="purple"] .setting-text .text-caption,
[data-theme="transparent"] .setting-text .text-caption {
  color: rgb(170, 170, 170) !important;
}

/* Custom Tooltip Styles */
.tooltip-container {
  position: relative;
  display: inline-block;
}

.tooltip-btn .tooltip-icon {
  transition: transform 0.3s ease;
}

.tooltip-container:hover .tooltip-btn .tooltip-icon {
  transform: scale(1.1);
}

.custom-tooltip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%) translateY(5px);
  visibility: hidden;
  opacity: 0;
  transition: opacity 0.3s ease, transform 0.3s ease, visibility 0.3s ease;
  pointer-events: none;
  z-index: 1000;
  white-space: nowrap;
}

.tooltip-container:hover .custom-tooltip {
  visibility: visible;
  opacity: 1;
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

.custom-tooltip-content {
  padding: 3px 8px;
  background: #212121;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  text-align: center;
}

.custom-tooltip-content::before {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 12px;
  height: 12px;
  background: #212121;
  border-radius: 2px;
  margin-top: -6px;
}

.tooltip-text {
  color: white;
  font-size: 0.8rem;
  font-weight: 400;
}

.tooltip-btn {
  transition: transform 0.3s ease;
}

.tooltip-container:hover .tooltip-btn {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}

/* Alert Animation */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-20px);
  opacity: 0;
}
</style>
