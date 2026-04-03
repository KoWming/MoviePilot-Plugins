<template>
  <div class="plugin-config">
    <v-card flat class="rounded border">
      <!-- 标题区域 -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2">
        <v-icon icon="mdi-cog" class="mr-2" color="primary" size="small" />
        <span>象岛农场配置</span>
        <v-spacer />
        <v-btn color="info" @click="emit('switch')" prepend-icon="mdi-view-dashboard" :disabled="saving" variant="text" size="small" class="toolbar-btn">
          <span class="btn-text">状态页</span>
        </v-btn>
        <v-btn color="secondary" variant="text" @click="resetConfigToFetched" :disabled="!initialConfigLoaded || saving" prepend-icon="mdi-restore" size="small" class="toolbar-btn">
          <span class="btn-text">重置</span>
        </v-btn>
        <v-btn color="primary" :disabled="!isFormValid || saving" @click="saveFullConfig" :loading="saving" prepend-icon="mdi-content-save" variant="text" size="small" class="toolbar-btn">
          <span class="btn-text">保存配置</span>
        </v-btn>
        <v-btn color="grey" @click="emit('close')" prepend-icon="mdi-close" :disabled="saving" variant="text" size="small" class="toolbar-btn">
          <span class="btn-text">关闭</span>
        </v-btn>
      </v-card-title>
      
      <v-card-text class="px-3 py-2">
        <v-alert v-if="error" type="error" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ error }}</v-alert>
        <v-alert v-if="successMessage" type="success" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ successMessage }}</v-alert>

        <v-form ref="form" v-model="isFormValid" @submit.prevent="saveFullConfig">
          <!-- 基本设置卡片 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
              <v-icon icon="mdi-tune" class="mr-2" color="primary" size="small" />
              <span>基本设置</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-power" size="small" :color="editableConfig.enabled ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用插件</div>
                          <div class="text-caption text-grey">是否启用象岛农场插件</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.enabled"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-bell" size="small" :color="editableConfig.notify ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用通知</div>
                          <div class="text-caption text-grey">完成后发送消息通知</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.notify"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2">
                    <v-icon icon="mdi-proxy" size="small" :color="editableConfig.use_proxy ? 'info' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">使用代理</div>
                          <div class="text-caption text-grey">是否使用系统代理访问</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.use_proxy"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 执行设置 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
              <v-icon icon="mdi-clock-time-five" class="mr-2" color="primary" size="small" />
              <span>执行设置</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <v-row>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="editableConfig.cookie"
                    label="Cookie"
                    type="password"
                    variant="outlined"
                    hint="象岛农场的Cookie，用于访问网站"
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
                    v-model="editableConfig.cron"
                    label="Cron表达式"
                    hint="设置执行周期，如：30 8 * * * (每天凌晨8:30)"
                    persistent-hint
                    density="compact"
                  ></VCronField>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.farm_interval"
                    label="重试间隔(秒)"
                    type="number"
                    variant="outlined"
                    :min="1"
                    :max="60"
                    :rules="[v => v === null || v === '' || (Number.isInteger(Number(v)) && Number(v) >= 1 && Number(v) <= 60) || '必须是1-60之间的整数']"
                    hint="失败重试的间隔时间"
                    persistent-hint
                    prepend-inner-icon="mdi-timer"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="editableConfig.retry_count"
                    label="重试次数"
                    type="number"
                    variant="outlined"
                    :min="0"
                    :max="5"
                    :rules="[v => v === null || v === '' || (Number.isInteger(Number(v)) && Number(v) >= 0 && Number(v) <= 5) || '必须是0-5之间的整数']"
                    hint="请求失败时的重试次数"
                    persistent-hint
                    prepend-inner-icon="mdi-refresh"
                    :disabled="saving"
                    density="compact"
                    class="text-caption"
                  ></v-text-field>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 自动交易设置 -->
          <v-card flat class="rounded mb-3 border config-card">
            <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
              <v-icon icon="mdi-cart" class="mr-2" color="primary" size="small" />
              <span>自动交易设置</span>
            </v-card-title>
            <v-card-text class="px-3 py-2">
              <!-- 自动交易开关设置 -->
              <v-row>
                <!-- 启用自动进货开关 -->
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2 mb-5">
                    <v-icon icon="mdi-cart-arrow-down" size="small" :color="editableConfig.auto_purchase_enabled ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用自动进货</div>
                          <div class="text-caption text-grey">当农场价格低于阈值时自动进货</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.auto_purchase_enabled"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>

                <!-- 启用自动出售开关 -->
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2 mb-5">
                    <v-icon icon="mdi-cart-arrow-up" size="small" :color="editableConfig.auto_sale_enabled ? 'success' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用自动出售</div>
                          <div class="text-caption text-grey">当蔬菜店价格高于阈值时自动出售</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.auto_sale_enabled"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>

                <!-- 启用到期出售开关 -->
                <v-col cols="12" md="4">
                  <div class="setting-item d-flex align-center py-2 mb-5">
                    <v-icon icon="mdi-calendar-clock" size="small" :color="editableConfig.expiry_sale_enabled ? 'warning' : 'grey'" class="mr-3"></v-icon>
                    <div class="setting-content flex-grow-1">
                      <div class="d-flex justify-space-between align-center">
                        <div>
                          <div class="text-subtitle-2">启用到期出售</div>
                          <div class="text-caption text-grey">每周六14点前无论是否亏损将执行全部出售</div>
                        </div>
                        <CustomSwitch
                          v-model="editableConfig.expiry_sale_enabled"
                          :disabled="saving"
                        />
                      </div>
                    </div>
                  </div>
                </v-col>
              </v-row>

              <!-- 自动交易详细设置 -->
              <v-row>
                <!-- 自动进货设置 -->
                <v-col cols="12" md="6">
                  <!-- 设置项 -->
                  <template v-if="editableConfig.auto_purchase_enabled">
                    <v-text-field
                      v-model.number="editableConfig.purchase_price_threshold"
                      label="进货价格阈值"
                      type="number"
                      variant="outlined"
                      :min="0"
                      :rules="[v => v === null || v === '' || (Number(v) >= 0) || '价格必须大于等于0']"
                      hint="当农场价格低于或等于此价格时自动进货（阀值为0时不执行）"
                      persistent-hint
                      prepend-inner-icon="mdi-currency-usd"
                      :disabled="saving"
                      density="compact"
                      class="text-caption mb-5"
                    ></v-text-field>
                    <v-select
                      v-model="editableConfig.purchase_quantity_ratio"
                      label="进货数量比例"
                      :items="[
                        { title: '20%', value: 0.2 },
                        { title: '50%', value: 0.5 },
                        { title: '80%', value: 0.8 },
                        { title: '全部', value: 1 }
                      ]"
                      item-title="title"
                      item-value="value"
                      variant="outlined"
                      hint="根据象草余额按比例进货"
                      persistent-hint
                      prepend-inner-icon="mdi-percent"
                      :disabled="saving"
                      density="compact"
                      class="text-caption"
                    ></v-select>
                  </template>
                </v-col>

                <!-- 自动出售设置 -->
                <v-col cols="12" md="6">
                  <!-- 设置项 -->
                  <template v-if="editableConfig.auto_sale_enabled">
                    <v-row>
                      <v-col cols="12" md="12" style="min-width: 0;">
                        <div class="d-flex align-center" style="gap: 16px; flex-wrap: wrap;">
                          <v-select
                            v-model="saleThresholdType"
                            label="出售条件类型"
                            :items="[
                              { title: '价格阈值', value: 'price' },
                              { title: '盈利百分比', value: 'percentage' }
                            ]"
                            item-title="title"
                            item-value="value"
                            variant="outlined"
                            persistent-hint
                            prepend-inner-icon="mdi-tune"
                            :disabled="saving"
                            density="compact"
                            class="text-caption"
                            style="flex: 1 1 0; min-width: 160px; max-width: 260px;"
                          ></v-select>
                          <v-text-field
                            v-model.number="saleThresholdValueComputed"
                            :label="saleThresholdType === 'price' ? '出售价格阈值' : '盈利百分比阈值'"
                            type="number"
                            variant="outlined"
                            :min="0"
                            :max="saleThresholdType === 'percentage' ? 1000 : undefined"
                            :rules="saleThresholdType === 'price' 
                              ? [v => v === null || v === '' || (Number(v) >= 0) || '价格必须大于等于0']
                              : [v => v === null || v === '' || (Number(v) >= 0 && Number(v) <= 1000) || '百分比必须在0-1000之间']"
                            persistent-hint
                            :prepend-inner-icon="saleThresholdType === 'price' ? 'mdi-currency-usd' : 'mdi-percent'"
                            :disabled="saving"
                            density="compact"
                            class="text-caption"
                            style="flex: 1 1 0; min-width: 160px; max-width: 260px;"
                          ></v-text-field>
                        </div>
                        <div class="text-caption mb-4" style="color: #999; margin-top: 5px; margin-bottom: 19px;">
                          <template v-if="saleThresholdType === 'price'">
                            当蔬菜店价格高于或等于此价格时自动出售（阈值为0时不执行）
                          </template>
                          <template v-else>
                            当盈利百分比达到或超过此值时自动出售（设为0时不执行）
                          </template>
                        </div>
                      </v-col>
                    </v-row>
                    <v-select
                      v-model="editableConfig.sale_quantity_ratio"
                      label="出售数量比例"
                      :items="[
                        { title: '20%', value: 0.2 },
                        { title: '50%', value: 0.5 },
                        { title: '80%', value: 0.8 },
                        { title: '全部', value: 1 }
                      ]"
                      item-title="title"
                      item-value="value"
                      variant="outlined"
                      hint="根据库存按比例出售"
                      persistent-hint
                      prepend-inner-icon="mdi-percent"
                      :disabled="saving"
                      density="compact"
                      class="text-caption"
                    ></v-select>
                  </template>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 帮助信息 -->
          <div class="d-flex align-center px-3 py-2 mb-3 rounded bg-info-lighten-5">
            <v-icon icon="mdi-information" color="info" class="mr-2" size="small"></v-icon>
            <span class="text-caption">
              此插件用于监听象岛农场相关信息，支持定时执行、代理访问、失败重试等功能。
              获取象岛农场信息，建议根据实际情况调整。
            </span>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import CustomSwitch from './CustomSwitch.vue';

const props = defineProps({
  api: { 
    type: [Object, Function],
    required: true,
  },
  initialConfig: {
    type: Object,
    default: () => ({}),
  }
});

const emit = defineEmits(['close', 'switch', 'config-updated-on-server', 'save']);

const form = ref(null);
const isFormValid = ref(true);
const error = ref(null);
const successMessage = ref(null);
const saving = ref(false);
const initialConfigLoaded = ref(false);
const loadingCookie = ref(false);

// 智能输入框相关变量
const saleThresholdType = ref('price'); // 'price' 或 'percentage'

// 计算属性：根据类型设置相应的值
const saleThresholdValueComputed = computed({
  get() {
    if (saleThresholdType.value === 'price') {
      return editableConfig.sale_price_threshold;
    } else {
      return editableConfig.sale_profit_percentage;
    }
  },
  set(value) {
    if (saleThresholdType.value === 'price') {
      editableConfig.sale_price_threshold = value;
    } else {
      editableConfig.sale_profit_percentage = value;
    }
  }
});

// 保存从服务器获取的配置，用于重置
const serverFetchedConfig = reactive({
  enabled: false,
  notify: false,
  cron: '',
  farm_interval: 5,
  use_proxy: false,
  retry_count: 3,
  cookie: '',
  onlyonce: false,
  auto_purchase_enabled: false,
  purchase_price_threshold: 0,
  purchase_quantity_ratio: 0.5,
  auto_sale_enabled: false,
  sale_price_threshold: 0,
  sale_quantity_ratio: 1,
  sale_profit_percentage: 0,
  sale_threshold_type: 'price', // 新增：保存出售条件类型
  expiry_sale_enabled: false, // 新增：到期出售开关
});

// 编辑中的配置
const editableConfig = reactive({
  enabled: false,
  notify: false,
  cron: '',
  farm_interval: 5,
  use_proxy: false,
  retry_count: 3,
  cookie: '',
  onlyonce: false,
  auto_purchase_enabled: false,
  purchase_price_threshold: 0,
  purchase_quantity_ratio: 0.5,
  auto_sale_enabled: false,
  sale_price_threshold: 0,
  sale_quantity_ratio: 1,
  sale_profit_percentage: 0,
  expiry_sale_enabled: false, // 新增：到期出售开关
});

// 更新编辑中的配置
const setEditableConfig = (sourceConfig) => {
  if (sourceConfig && typeof sourceConfig === 'object') {
    Object.keys(editableConfig).forEach(key => {
      if (sourceConfig.hasOwnProperty(key)) {
        editableConfig[key] = JSON.parse(JSON.stringify(sourceConfig[key]));
      }
    });
    
    // 智能判断出售条件类型
    if (sourceConfig.sale_profit_percentage && sourceConfig.sale_profit_percentage > 0) {
      saleThresholdType.value = 'percentage';
    } else if (sourceConfig.sale_price_threshold && sourceConfig.sale_price_threshold > 0) {
      saleThresholdType.value = 'price';
    } else {
      // 默认使用价格阈值
      saleThresholdType.value = 'price';
    }
  }
};

const getPluginId = () => {
  return "VicomoFarm";
};

// 加载初始配置
async function loadInitialData() {
  error.value = null;
  saving.value = true;
  initialConfigLoaded.value = false;
  
  if (!props.initialConfig) { 
    error.value = '初始配置丢失，无法加载配置'; 
    saving.value = false; 
    return; 
  }
  
  try {
    const pluginId = getPluginId();
    if (!pluginId) { 
      throw new Error('获取插件ID失败'); 
    }
    
    const data = await props.api.get(`plugin/${pluginId}/config`);
    
    if (data) {
      setEditableConfig(data);
      Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(data)));
      initialConfigLoaded.value = true;
      successMessage.value = '当前配置已从服务器加载';
    } else {
      throw new Error('从服务器获取配置失败，使用宿主提供的初始配置');
    }
  } catch (err) {
    console.error('加载配置失败:', err);
    error.value = err.message || '加载配置失败，请检查网络或API';
    setEditableConfig(props.initialConfig);
    Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(props.initialConfig)));
    successMessage.value = null;
  } finally {
    saving.value = false;
    setTimeout(() => { successMessage.value = null; error.value = null; }, 4000);
  }
}

// 保存配置
async function saveFullConfig() {
  error.value = null;
  successMessage.value = null;
  if (!form.value) return;
  const validation = await form.value.validate();
  if (!validation.valid) {
    error.value = '请检查表单中的错误';
    return;
  }

  saving.value = true;

  try {
    // 设置onlyonce为false，确保兼容后端
    editableConfig.onlyonce = false;
    
    // 通过emit事件保存配置
    emit('save', JSON.parse(JSON.stringify(editableConfig)));
    successMessage.value = '配置已发送保存请求';
  } catch (err) {
    console.error('保存配置失败:', err);
    error.value = err.message || '保存配置失败，请检查网络或查看日志';
  } finally {
    saving.value = false;
    setTimeout(() => { 
      successMessage.value = null; 
      if (error.value && !error.value.startsWith('保存配置失败') && !error.value.startsWith('配置已部分保存')) { 
        error.value = null; 
      }
    }, 5000); 
  }
}

// 重置配置
function resetConfigToFetched() {
  if (initialConfigLoaded.value) {
    setEditableConfig(serverFetchedConfig);
    error.value = null;
    successMessage.value = '配置已重置为上次从服务器加载的状态';
    if (form.value) form.value.resetValidation();
  } else {
    error.value = '尚未从服务器加载配置，无法重置';
  }
  setTimeout(() => { successMessage.value = null; error.value = null; }, 3000);
}

async function fillWithSiteCookie() {
  error.value = null;
  successMessage.value = null;
  loadingCookie.value = true;
  
  try {
    const pluginId = getPluginId();
    const response = await props.api.get(`plugin/${pluginId}/cookie`);
    
    if (response && response.success) {
      if (typeof response.cookie === 'string' && response.cookie.trim().toLowerCase() === 'cookie') {
        throw new Error('站点Cookie无效，请在站点管理中配置真实Cookie');
      }
      editableConfig.cookie = response.cookie;
      successMessage.value = '已成功获取站点Cookie';
    } else {
      throw new Error(response?.msg || '获取站点Cookie失败');
    }
  } catch (err) {
    console.error('获取站点Cookie失败:', err);
    error.value = err.message || '获取站点Cookie失败，请检查站点配置';
  } finally {
    loadingCookie.value = false;
    setTimeout(() => { successMessage.value = null; error.value = null; }, 3000);
  }
}

onMounted(() => {
  // 使用初始配置显示，然后从服务器获取
  setEditableConfig(props.initialConfig);
  Object.assign(serverFetchedConfig, JSON.parse(JSON.stringify(props.initialConfig)));
  
  loadInitialData();
});
</script>

<style scoped>
.plugin-config {
  max-width: 80rem;
  margin: 0 auto;
  padding: 1rem;
}

.bg-primary-lighten-5 {
  background: linear-gradient(0deg, rgb(255, 255, 255) 0%, rgb(244, 247, 251) 100%);
}

.border {
  border: 5px solid rgb(255, 255, 255);
  border-radius: 40px;
  box-shadow: rgba(133, 189, 215, 0.8784313725) 0px 30px 30px -20px;
}

.config-card {
  background: linear-gradient(0deg, rgb(255, 255, 255) 0%, rgb(244, 247, 251) 100%);
  border-radius: 30px;
  padding: 20px;
  border: 3px solid rgb(255, 255, 255);
  box-shadow: rgba(133, 189, 215, 0.8784313725) 0px 20px 20px -15px;
  transition: all 0.3s ease;
}

/* 深色模式适配 - 使用 data 属性选择器避免被过滤 */
[data-theme="dark"] .config-card,
[data-theme="purple"] .config-card,
[data-theme="transparent"] .config-card {
  background: linear-gradient(0deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%);
  border: 3px solid rgb(60, 60, 60);
  box-shadow: rgba(0, 0, 0, 0.4) 0px 20px 20px -15px;
}

/* 系统深色模式适配 */
@media (prefers-color-scheme: dark) {
  .config-card {
    background: linear-gradient(0deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%);
    border: 3px solid rgb(60, 60, 60);
    box-shadow: rgba(0, 0, 0, 0.4) 0px 20px 20px -15px;
  }
}

.config-card:hover {
  transform: translateY(-2px);
  box-shadow: rgba(133, 189, 215, 0.8784313725) 0px 25px 25px -15px;
}

.setting-item {
  min-height: 48px;
  background: white;
  border-radius: 20px;
  padding: 15px 20px;
  box-shadow: #cff0ff 0px 10px 10px -5px;
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

/* 深色模式适配 - 使用 data 属性选择器避免被过滤 */
[data-theme="dark"] .setting-item,
[data-theme="purple"] .setting-item,
[data-theme="transparent"] .setting-item {
  background: rgb(45, 45, 45);
  box-shadow: rgba(0, 0, 0, 0.3) 0px 10px 10px -5px;
  border: 2px solid transparent;
}

/* 系统深色模式适配 */
@media (prefers-color-scheme: dark) {
  .setting-item {
    background: rgb(45, 45, 45);
    box-shadow: rgba(0, 0, 0, 0.3) 0px 10px 10px -5px;
    border: 2px solid transparent;
  }
}

.setting-item:hover {
  border-color: #12B1D1;
  transform: translateY(-1px);
}

.setting-content {
  width: 100%;
}

.text-subtitle-2 {
  color: rgb(16, 137, 211);
  font-weight: 600;
}

.text-caption.text-grey {
  color: rgb(170, 170, 170);
}

/* 深色模式文字颜色适配 */
[data-theme="dark"] .text-subtitle-2,
[data-theme="purple"] .text-subtitle-2,
[data-theme="transparent"] .text-subtitle-2 {
  color: rgb(100, 200, 255);
}

[data-theme="dark"] .text-caption.text-grey,
[data-theme="purple"] .text-caption.text-grey,
[data-theme="transparent"] .text-caption.text-grey {
  color: rgb(180, 180, 180);
}

/* 系统深色模式文字颜色适配 */
@media (prefers-color-scheme: dark) {
  .text-subtitle-2 {
    color: rgb(100, 200, 255);
  }
  
  .text-caption.text-grey {
    color: rgb(180, 180, 180);
  }
}

/* 按钮样式 */
.v-btn {
  border-radius: 20px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  transition: all 0.2s ease-in-out !important;
}

.v-btn:hover {
  transform: scale(1.03);
  box-shadow: rgba(133, 189, 215, 0.8784313725) 0px 20px 10px -15px !important;
}

.v-btn:active {
  transform: scale(0.95);
}

/* 输入框样式 */
.v-text-field {
  margin-top: 15px;
}

.v-text-field :deep(.v-field) {
  border-radius: 20px !important;
  background: white !important;
  box-shadow: #cff0ff 0px 10px 10px -5px !important;
  border: 2px solid transparent !important;
  transition: all 0.2s ease !important;
}

.v-text-field :deep(.v-field:hover) {
  border-color: #12B1D1 !important;
}

.v-text-field :deep(.v-field--focused) {
  border-color: #12B1D1 !important;
  box-shadow: rgba(133, 189, 215, 0.8784313725) 0px 15px 15px -10px !important;
}

/* 提示信息样式 */
.v-alert {
  border-radius: 20px !important;
  box-shadow: #edf5fd 0px 10px 10px -5px !important;
}

/* 帮助信息样式 */
.bg-info-lighten-5 {
  border-radius: 10px !important;
  box-shadow: #cff0ff 0px 10px 10px -5px !important;
  background-color: #f5faff;
  color: #50a8ff;
  position: relative;
  overflow: hidden;
  border-left: 4px solid #9155fd;
  padding-left: calc(20px + 4px) !important;
}

.bg-info-lighten-5 .v-icon {
  color: #1976d2;
}

/* 深色模式适配 - 使用 data 属性选择器避免被过滤 */
[data-theme="dark"] .bg-info-lighten-5,
[data-theme="purple"] .bg-info-lighten-5,
[data-theme="transparent"] .bg-info-lighten-5 {
  background-color: rgba(30, 60, 90, 0.8);
  color: rgb(150, 200, 255);
  box-shadow: rgba(0, 0, 0, 0.4) 0px 20px 20px -15px !important;
  border-left: 4px solid #6E66ED;
}

[data-theme="dark"] .bg-info-lighten-5 .v-icon,
[data-theme="purple"] .bg-info-lighten-5 .v-icon,
[data-theme="transparent"] .bg-info-lighten-5 .v-icon {
  color: rgb(150, 200, 255);
}

/* 系统深色模式适配 */
@media (prefers-color-scheme: dark) {
  .bg-info-lighten-5 {
    background-color: rgba(30, 60, 90, 0.8);
    color: rgb(150, 200, 255);
    box-shadow: rgba(0, 0, 0, 0.4) 0px 20px 20px -15px !important;
    border-left: 4px solid #6E66ED;
  }
  
  .bg-info-lighten-5 .v-icon {
    color: rgb(150, 200, 255);
  }
}

.bg-info-lighten-5 .text-caption {
  flex-grow: 1;
}

/* 图标样式 */
.v-icon {
  transition: all 0.2s ease !important;
}

.setting-item:hover .v-icon {
  transform: scale(1.1);
}

/* 分割线样式 */
.v-divider {
  margin: 20px 0 !important;
  opacity: 0.1 !important;
}

/* 卡片标题样式 */
.v-card-title {
  font-weight: 600 !important;
  color: rgb(16, 137, 211) !important;
  padding: 15px 20px !important;
  border-bottom: 2px solid rgba(16, 137, 211, 0.1) !important;
  margin-bottom: 10px !important;
  letter-spacing: 0.5px !important;
}

.v-card-title .v-icon {
  opacity: 0.8;
  transition: all 0.2s ease !important;
}

.v-card-title:hover .v-icon {
  opacity: 1;
  transform: scale(1.1);
}

/* 卡片内容样式 */
.v-card-text {
  padding: 20px !important;
}

/* Custom Tooltip Styles - Pure CSS */
.tooltip-container {
  position: relative;
  display: inline-block; /* Ensure the container wraps the button tightly */
}

.tooltip-btn .tooltip-icon {
  transition: transform 0.3s ease;
}

.tooltip-container:hover .tooltip-btn .tooltip-icon {
  transform: scale(1.1);
}

.custom-tooltip {
  position: absolute;
  bottom: calc(100% + 12px); /* Position further above the button to avoid overlap */
  left: 50%;
  transform: translateX(-50%) translateY(5px); /* Initial position slightly below final + horizontal center */
  visibility: hidden;
  opacity: 0;
  transition: opacity 0.3s ease, transform 0.3s ease, visibility 0.3s ease; /* Increased transition duration */
  pointer-events: none; /* Do not block mouse events on the button */
  z-index: 1000; /* Ensure tooltip is above other content */
  white-space: nowrap; /* Prevent text wrapping */
}

.tooltip-container:hover .custom-tooltip {
  visibility: visible;
  opacity: 1;
  transform: translateX(-50%) translateY(0); /* Final position */
  pointer-events: auto; /* Allow interaction with tooltip if needed (though not in this case) */
}

.custom-tooltip-content {
  padding: 3px 8px; /* Reduced vertical padding to decrease height */
  background: #212121; /* Changed to opaque background */
  border-radius: 6px; /* Increased border radius */
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); /* Softer shadow */
  text-align: center;
}

.custom-tooltip-content::before {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%) rotate(45deg); /* Arrow pointing down */
  width: 12px;
  height: 12px;
  background: #212121; /* Changed to opaque background */
  border-radius: 2px;
  margin-top: -6px; /* Adjust to position the arrow correctly below the content */
}

.tooltip-text {
  color: white;
  font-size: 0.8rem; /* Slightly reduced font size */
  font-weight: 400;
}

/* Optional: Add a slight scale transform to the button on hover */
.tooltip-btn {
  transition: transform 0.3s ease;
}

.tooltip-container:hover .tooltip-btn {
  transform: translateY(-2px); /* Match the button lift from previous version */
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important; /* Match the shadow from previous version */
}

.toolbar-btn {
  margin-left: 8px;
  margin-right: 0;
  min-width: 36px;
  padding-left: 10px;
  padding-right: 10px;
}
@media (max-width: 600px) {
  .toolbar-btn .btn-text {
    display: none !important;
  }
  .toolbar-btn {
    min-width: 32px !important;
    padding-left: 4px !important;
    padding-right: 4px !important;
    margin-left: 2px !important;
  }
  .toolbar-btn .v-icon {
    margin-right: 0 !important;
  }
}
</style> 