<template>
  <div class="plugin-page">
    <v-card flat class="rounded border">
      <!-- 标题区域 -->
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2">
        <v-icon icon="mdi-farm" class="mr-2" color="primary" size="small" />
        <span>象岛农场</span>
        <v-spacer></v-spacer>
        <v-btn color="info" @click="emit('switch')" prepend-icon="mdi-cog" :disabled="loading" variant="text" size="small" class="toolbar-btn">
          <span class="btn-text">配置页</span>
        </v-btn>
        <v-btn color="primary" variant="text" size="small" prepend-icon="mdi-refresh" @click="refreshData" :loading="loading" class="toolbar-btn">
          <span class="btn-text">刷新</span>
        </v-btn>
        <v-btn color="grey" @click="emit('close')" prepend-icon="mdi-close" :disabled="loading" variant="text" size="small" class="toolbar-btn">
          <span class="btn-text">关闭</span>
        </v-btn>
      </v-card-title>
      
      <v-card-text class="px-3 py-2" style="background: transparent;">
        <v-alert v-if="successMessage" type="success" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ successMessage }}</v-alert>
        <v-alert v-if="error" type="error" density="compact" class="mb-2 text-caption" variant="tonal" closable>{{ error }}</v-alert>

        <!-- 第一排：当前状态、农场信息 -->
        <v-row align="stretch" class="mb-0" no-gutters>
          <!-- 当前状态卡片 -->
          <v-col cols="12" md="6" style="padding: 8px;">
            <v-card flat class="rounded mb-3 border config-card h-100">
              <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
                <v-icon icon="mdi-information" class="mr-2" color="primary" size="small" />
                <span>当前状态</span>
              </v-card-title>
              <v-card-text class="px-3 py-2">
                <v-list density="compact" class="pa-0">
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon icon="mdi-power" :color="status.enabled ? 'success' : 'grey'" size="small"></v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-2">插件状态</v-list-item-title>
                    <v-list-item-subtitle>{{ status.enabled ? '已启用' : '已禁用' }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon icon="mdi-clock-time-five" color="info" size="small"></v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-2">下次执行时间</v-list-item-title>
                    <v-list-item-subtitle>{{ status.next_run_time || '未设置' }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon icon="mdi-proxy" :color="status.use_proxy ? 'info' : 'grey'" size="small"></v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-2">代理状态</v-list-item-title>
                    <v-list-item-subtitle>{{ status.use_proxy ? '已启用' : '已禁用' }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon icon="mdi-timer" color="primary" size="small"></v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-2">重试间隔</v-list-item-title>
                    <v-list-item-subtitle>{{ status.farm_interval ? `${status.farm_interval}秒` : '未设置' }}</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item>
                    <template v-slot:prepend>
                      <v-icon icon="mdi-refresh" color="primary" size="small"></v-icon>
                    </template>
                    <v-list-item-title class="text-subtitle-2">重试次数</v-list-item-title>
                    <v-list-item-subtitle>{{ status.retry_count || '未设置' }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
          <!-- 市场单价趋势卡片 -->
          <v-col cols="12" md="6" style="padding: 8px;">
            <v-card flat class="rounded mb-3 border config-card h-100">
              <v-card-title class="text-subtitle-2 d-flex align-center px-3 py-2">
                <v-icon icon="mdi-history" class="mr-2" color="primary" size="small" />
                <span>市场单价趋势</span>
              </v-card-title>
              <v-card-text class="px-3 py-2" style="background: transparent;">
                <v-sheet class="history-container" max-height="400" style="background: transparent;">
                  <div ref="chartRef" style="width: 100%; height: 340px;"></div>
                </v-sheet>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <!-- 第二排：历史记录、蔬菜店信息 -->
        <v-row class="mt-1" no-gutters>
          <!-- 农场信息卡片 -->
          <v-col cols="12" md="6" style="padding: 8px;">
            <v-card flat class="mb-3 border rounded config-card h-100" style="height: 100%">
              <v-card-title class="text-subtitle-2 px-3 py-2 d-flex align-center">
                <v-icon icon="mdi-farm" class="mr-2" color="primary" size="small" />
                <span>农场信息</span>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="text" size="small" prepend-icon="mdi-refresh"
                       @click="refreshTask" :loading="loading">刷新农场信息</v-btn>
              </v-card-title>
              <v-card-text class="px-3 py-2">
                <v-list density="compact" class="pa-0">
                  <template v-if="latestFarmInfo && latestFarmInfo.farm">
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-label" color="primary" size="small"></v-icon></template>
                      <span>名称：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.名称 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-shape" color="info" size="small"></v-icon></template>
                      <span>类型：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.类型 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-information" color="success" size="small"></v-icon></template>
                      <span>状态：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.状态 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-currency-cny" color="warning" size="small"></v-icon></template>
                      <span>价格：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.价格 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-package-variant" color="warning" size="small"></v-icon></template>
                      <span>剩余配货量：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.剩余配货量 || '未知' }}kg</span>
                      <v-btn
                        v-if="latestFarmInfo.farm.剩余配货量 && latestFarmInfo.farm.剩余配货量 !== '未知' && Number(latestFarmInfo.farm.剩余配货量) > 0"
                        class="ml-2 sale-btn"
                        @click="purchaseDialog = true"
                      >进货</v-btn><span class="btn-spacer"></span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-note-text" color="secondary" size="small"></v-icon></template>
                      <span>说明：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.farm.说明 || '无' }}</span>
                    </v-list-item>
                  </template>
                  <template v-else>
                    <v-list-item>
                      <span class="text-subtitle-2">暂无数据</span>
                      <v-tooltip location="top">
                        <template v-slot:activator="{ props }">
                          <v-icon v-bind="props" icon="mdi-help-circle" color="grey" size="small" class="ml-2"></v-icon>
                        </template>
                        <span>数据加载中或暂无数据</span>
                      </v-tooltip>
                    </v-list-item>
                  </template>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
          <!-- 蔬菜店信息卡片 -->
          <v-col cols="12" md="6" style="padding: 8px;">
            <v-card flat class="mb-3 border rounded config-card h-100" style="height: 100%; min-height: 300px;">
              <v-card-title class="text-subtitle-2 px-3 py-2 d-flex align-center">
                <v-icon icon="mdi-storefront" class="mr-2" color="primary" size="small" />
                <span>蔬菜店信息</span>
              </v-card-title>
              <v-card-text class="px-3 py-2">
                <v-list density="compact" class="pa-0">
                  <template v-if="latestFarmInfo && latestFarmInfo.vegetable_shop">
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-label" color="primary" size="small"></v-icon></template>
                      <span>名称：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.名称 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-currency-cny" color="info" size="small"></v-icon></template>
                      <span>市场单价：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.市场单价 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-warehouse" color="success" size="small"></v-icon></template>
                      <span>库存：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.库存 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-cash" color="warning" size="small"></v-icon></template>
                      <span>成本：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.成本 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-percent" :color="calculateProfitPercentage() >= 0 ? 'success' : 'error'" size="small"></v-icon></template>
                      <span>盈利百分比：</span>
                      <span class="text-subtitle-2" :class="calculateProfitPercentage() >= 0 ? 'text-success' : 'text-error'">{{ calculateProfitPercentageText() }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-chart-line" color="secondary" size="small"></v-icon></template>
                      <span>开店累计盈利：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.开店累计盈利 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-target" color="error" size="small"></v-icon></template>
                      <span>盈利目标：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.盈利目标 || '未知' }}</span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-numeric" color="primary" size="small"></v-icon></template>
                      <span>可卖数量：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.可卖数量 || '未知' }}</span>
                      <v-btn
                        v-if="latestFarmInfo.vegetable_shop.可卖数量 && latestFarmInfo.vegetable_shop.可卖数量 !== '未知' && Number(latestFarmInfo.vegetable_shop.可卖数量) > 0"
                        color="success"
                        size="small"
                        class="ml-2 sale-btn"
                        @click="saleDialog = true"
                      >出售</v-btn><span class="btn-spacer"></span>
                    </v-list-item>
                    <v-list-item class="d-flex align-center">
                      <template v-slot:prepend><v-icon icon="mdi-note-text" color="grey" size="small"></v-icon></template>
                      <span>说明：</span>
                      <span class="text-subtitle-2">{{ latestFarmInfo.vegetable_shop.说明 || '无' }}</span>
                    </v-list-item>
                  </template>
                  <template v-else>
                    <v-list-item>
                      <span class="text-subtitle-2">暂无数据</span>
                      <v-tooltip location="top">
                        <template v-slot:activator="{ props }">
                          <v-icon v-bind="props" icon="mdi-help-circle" color="grey" size="small" class="ml-2"></v-icon>
                        </template>
                        <span>数据加载中或暂无数据</span>
                      </v-tooltip>
                    </v-list-item>
                  </template>
                </v-list>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
      
      <v-divider></v-divider>
    </v-card>

    <v-dialog v-model="purchaseDialog" max-width="360" >
      <v-card class="dialog-card">
        <v-card-title class="text-subtitle-2">确认进货</v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <v-row class="mb-2" dense>
            <v-col cols="12" sm="6">
              <v-sheet class="pa-2 text-center" color="grey-lighten-4" rounded>
                <v-icon size="18" color="primary" class="mb-1">mdi-package-variant</v-icon>
                <div class="caption">剩余配货量</div>
                <div class="font-weight-bold text-body-1">{{ latestFarmInfo.farm.剩余配货量 || '未知' }}<span class="text-caption"> kg</span></div>
              </v-sheet>
            </v-col>
            <v-col cols="12" sm="6">
              <v-sheet class="pa-2 text-center" color="grey-lighten-4" rounded>
                <v-icon size="18" color="success" class="mb-1">mdi-currency-cny</v-icon>
                <div class="caption">商品单价</div>
                <div class="font-weight-bold text-body-1">{{ latestFarmInfo.farm.价格 || '未知' }}</div>
              </v-sheet>
            </v-col>
          </v-row>
          <v-divider class="my-2"></v-divider>
          <div style="margin-bottom: 12px; display: flex; align-items: center;">
            <span>当前象草余额：</span>
            <v-icon size="18" color="success" class="mx-1">mdi-grass</v-icon>
            <b>{{ latestFarmInfo.bonus || '未知' }}</b>
          </div>
          <div style="margin-bottom: 12px;" v-if="latestFarmInfo.bonus && latestFarmInfo.farm.价格">
            目前最多可进货：
            <b>{{ calculateMaxPurchase() }}</b> kg
          </div>
          <v-text-field
            v-model="purchaseAmount"
            label="进货数量（kg）"
            placeholder="请输入进货数量"
            type="number"
            :rules="[
              v => !!v || '请输入进货数量',
              v => Number(v) > 0 || '数量需大于0',
              v => Number(v) <= Number(latestFarmInfo.farm.剩余配货量) || '不能超过剩余配货量',
              v => Number(v) <= calculateMaxPurchase() || '不能超过可进货数量'
            ]"
            min="1"
            :max="Math.min(Number(latestFarmInfo.farm.剩余配货量), calculateMaxPurchase())"
            required
            hide-details="auto"
            class="mb-2"
          />
          <v-alert v-if="purchaseError" type="error" class="mt-2" density="compact">{{ purchaseError }}</v-alert>
          <v-alert v-if="purchaseSuccess" type="success" class="mt-2" density="compact">{{ purchaseSuccess }}</v-alert>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions class="d-flex justify-center align-center pt-4 pb-4">
          <v-btn color="primary" variant="flat" :loading="purchaseLoading" @click="handlePurchase" class="dialog-btn mr-2" min-width="96">
            确定进货
          </v-btn>
          <v-btn color="grey" variant="tonal" @click="purchaseDialog = false" class="dialog-btn" min-width="96">
            取消
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="saleDialog" max-width="360" >
      <v-card class="dialog-card">
        <v-card-title class="text-subtitle-2">确认出售</v-card-title>
        <v-divider></v-divider>
        <v-card-text>
          <div class="sale-info-row">
            <div class="sale-info-card">
              <v-icon size="22" color="success" class="mb-1">mdi-warehouse</v-icon>
              <div class="sale-info-title">当前库存</div>
              <div class="sale-info-main">{{ latestFarmInfo.vegetable_shop.库存 || '未知' }}<span class="unit">kg</span></div>
            </div>
            <div class="sale-info-card">
              <v-icon size="22" color="info" class="mb-1">mdi-currency-cny</v-icon>
              <div class="sale-info-title">市场单价</div>
              <div class="sale-info-main">{{ latestFarmInfo.vegetable_shop.市场单价 || '未知' }}</div>
            </div>
            <div class="sale-info-card">
              <v-icon size="22" color="primary" class="mb-1">mdi-numeric</v-icon>
              <div class="sale-info-title">最多可出售</div>
              <div class="sale-info-main">{{ calculateMaxSaleAmount() }}<span class="unit">kg</span></div>
            </div>
          </div>
          <v-text-field
            v-model="saleAmount"
            label="出售数量（kg）"
            placeholder="请输入出售数量"
            type="number"
            :rules="[
              v => !!v || '请输入出售数量',
              v => Number(v) > 0 || '数量需大于0',
              v => Number(v) <= Number(latestFarmInfo.vegetable_shop.可卖数量) || '不能超过可卖数量',
              v => Number(v) <= calculateMaxSaleAmount() || '不能超过可出售数量'
            ]"
            min="1"
            :max="Math.min(Number(latestFarmInfo.vegetable_shop.可卖数量), calculateMaxSaleAmount())"
            required
            hide-details="auto"
            class="mb-2"
          />
          <v-row dense>
            <v-col cols="12" sm="6">
              <v-sheet v-if="saleAmount && Number(saleAmount) > 0" class="pa-2 text-center" color="blue-lighten-5" rounded>
                <v-icon size="22" color="success" class="mb-1">mdi-grass</v-icon>
                <div class="caption mb-1">可获得象草</div>
                <div style="color:#43a047;" class="font-weight-bold text-body-1">{{ calculateSaleBonus() }}</div>
              </v-sheet>
            </v-col>
            <v-col cols="12" sm="6">
              <v-sheet v-if="saleAmount && Number(saleAmount) > 0" class="pa-2 text-center" :color="calculateProfit() >= 0 ? 'green-lighten-5' : 'red-lighten-5'" rounded>
                <v-icon size="22" :color="calculateProfit() >= 0 ? 'success' : 'error'" class="mb-1">mdi-chart-line-variant</v-icon>
                <div class="caption mb-1">预计盈亏</div>
                <div :class="calculateProfit() >= 0 ? 'text-success' : 'text-error'" class="font-weight-bold text-body-1">{{ calculateProfit() }}</div>
              </v-sheet>
            </v-col>
          </v-row>
          <v-alert v-if="saleError" type="error" class="mt-2" density="compact">{{ saleError }}</v-alert>
          <v-alert v-if="saleSuccess" type="success" class="mt-2" density="compact">{{ saleSuccess }}</v-alert>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions class="d-flex justify-center align-center pt-4 pb-4">
          <v-btn color="primary" variant="flat" :loading="saleLoading" @click="handleSale" class="dialog-btn mr-2" min-width="96">
            确定出售
          </v-btn>
          <v-btn color="grey" variant="tonal" @click="saleDialog = false" class="dialog-btn" min-width="96">
            取消
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch, onUnmounted, nextTick } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  api: { 
    type: [Object, Function],
    required: true,
  }
});

const emit = defineEmits(['close', 'switch']);

const loading = ref(false);
const error = ref(null);
const successMessage = ref(null);

// 状态数据
const status = reactive({
  enabled: false,
  next_run_time: null,
  farm_interval: 15,
  use_proxy: true,
  retry_count: 2,
  sign_dict: []
});

// 最新一条农场和蔬菜店信息
const latestFarmInfo = computed(() => {
  if (status.sign_dict && status.sign_dict.length > 0) {
    const firstRecord = status.sign_dict[0];
    if (firstRecord && firstRecord.farm_info) {
      return firstRecord.farm_info;
    }
  }
  return {};
});

// 购买相关
const purchaseAmount = ref('');
const purchaseDialog = ref(false);
const purchaseLoading = ref(false);
const purchaseError = ref('');
const purchaseSuccess = ref('');

// 出售相关
const saleDialog = ref(false);
const saleAmount = ref('');
const saleLoading = ref(false);
const saleError = ref('');
const saleSuccess = ref('');

const chartRef = ref(null);
let chartInstance = null;

// 获取插件ID
const getPluginId = () => {
  return "VicomoFarm";
};

// 获取时间线点的颜色
const getTimelineDotColor = (item, index) => {
  const colors = ['primary', 'secondary', 'success', 'info', 'warning', 'error'];
  // 使用索引确保每个时间线项的颜色是固定的
  return colors[index % colors.length];
};

// 刷新数据
async function refreshData() {
  error.value = null;
  loading.value = true;
  try {
    const pluginId = getPluginId();
    if (!pluginId) {
      throw new Error('获取插件ID失败');
    }
    const data = await props.api.get(`plugin/${pluginId}/status`);
    if (data) {
      Object.assign(status, data);
      if (Array.isArray(data.sign_dict)) {
        status.sign_dict.splice(0, status.sign_dict.length, ...data.sign_dict);
      }
      successMessage.value = '数据已刷新';
    } else {
      throw new Error('获取状态数据失败');
    }
  } catch (err) {
    error.value = err.message || '刷新数据失败，请检查网络或API';
  } finally {
    loading.value = false;
    setTimeout(() => { error.value = null; successMessage.value = null; }, 3000);
  }
}

// 购买操作
async function handlePurchase() {
  purchaseError.value = '';
  purchaseSuccess.value = '';
  purchaseLoading.value = true;
  try {
    const pluginId = getPluginId();
    const num = Number(purchaseAmount.value);
    if (!num || num <= 0 || !Number.isInteger(num)) {
      purchaseError.value = '请输入有效的购买数量';
      purchaseLoading.value = false;
      return;
    }
    const url = `plugin/${pluginId}/purchase?buy_num=${num}`;
    const res = await props.api.post(url);
    if (res && res.success) {
      purchaseSuccess.value = res.msg || '购买成功';
      // 前端临时减少剩余配货量
      if (latestFarmInfo.value && latestFarmInfo.value.farm && typeof latestFarmInfo.value.farm.剩余配货量 !== 'undefined') {
        let remain = parseInt(String(latestFarmInfo.value.farm.剩余配货量).replace(/,/g, ''));
        if (!isNaN(remain)) {
          let newRemain = remain - num;
          if (newRemain < 0) newRemain = 0;
          latestFarmInfo.value.farm.剩余配货量 = newRemain;
        }
      }
      // 前端临时增加蔬菜店库存
      if (latestFarmInfo.value && latestFarmInfo.value.vegetable_shop && typeof latestFarmInfo.value.vegetable_shop.库存 !== 'undefined') {
        let stock = parseInt(String(latestFarmInfo.value.vegetable_shop.库存).replace(/,/g, ''));
        if (!isNaN(stock)) {
          let newStock = stock + num;
          if (newStock < 0) newStock = 0;
          latestFarmInfo.value.vegetable_shop.库存 = newStock;
        }
      }
      purchaseAmount.value = '';
      // 延迟1.5秒后自动关闭弹窗
      setTimeout(() => {
        purchaseDialog.value = false;
      }, 1500);
      // 不立即刷新数据，等用户手动刷新
    } else {
      purchaseError.value = (res && res.msg) || '购买失败';
    }
  } catch (e) {
    purchaseError.value = e.message || '购买失败';
  } finally {
    purchaseLoading.value = false;
    setTimeout(() => { purchaseError.value = ''; }, 3000);
  }
}

// 刷新任务
async function refreshTask() {
  error.value = null;
  loading.value = true;
  
  try {
    const pluginId = getPluginId();
    if (!pluginId) {
      throw new Error('获取插件ID失败');
    }
    
    const res = await props.api.post(`plugin/${pluginId}/task`);
    console.log('[VicomoFarm] refreshTask API response:', res);
    
    if (res) {
      // 刷新数据
      await refreshData();
    } else {
      // 这里打印 res 以便排查
      console.error('[VicomoFarm] refreshTask: res 为空或无效', res);
      throw new Error('执行任务失败');
    }
  } catch (err) {
    // 这里打印 err 的详细内容
    console.error('执行任务失败:', err, err && err.response, err && err.stack);
    error.value = (err && err.message) || '执行任务失败，请检查网络或API';
  } finally {
    loading.value = false;
    setTimeout(() => { error.value = null; }, 3000);
  }
}

// 出售操作
async function handleSale() {
  saleError.value = '';
  saleSuccess.value = '';
  saleDialog.value = true;
  saleLoading.value = true;
  try {
    const pluginId = getPluginId();
    const num = Number(saleAmount.value);
    const maxNum = Number(latestFarmInfo.value.vegetable_shop.可卖数量);
    if (!num || num <= 0 || !Number.isInteger(num)) {
      saleError.value = '请输入有效的出售数量';
      saleLoading.value = false;
      return;
    }
    if (num > maxNum) {
      saleError.value = `最大可卖数量为${maxNum}`;
      saleLoading.value = false;
      return;
    }
    const url = `plugin/${pluginId}/sale?sale_num=${num}`;
    const res = await props.api.post(url);
    if (res && res.success) {
      saleSuccess.value = res.msg || '出售成功';
      // 前端临时减少蔬菜店库存
      if (latestFarmInfo.value && latestFarmInfo.value.vegetable_shop && typeof latestFarmInfo.value.vegetable_shop.库存 !== 'undefined') {
        let stock = parseInt(String(latestFarmInfo.value.vegetable_shop.库存).replace(/,/g, ''));
        if (!isNaN(stock)) {
          let newStock = stock - num;
          if (newStock < 0) newStock = 0;
          latestFarmInfo.value.vegetable_shop.库存 = newStock;
        }
      }
      saleAmount.value = '';
      // 延迟1.5秒后自动关闭弹窗
      setTimeout(() => {
        saleDialog.value = false;
      }, 1500);
      refreshData();
    } else {
      saleError.value = (res && res.msg) || '出售失败';
    }
  } catch (e) {
    saleError.value = e.message || '出售失败';
  } finally {
    saleLoading.value = false;
    setTimeout(() => { saleError.value = ''; saleSuccess.value = ''; }, 3000);
  }
}

// 计算最大可进货数量
function calculateMaxPurchase() {
  if (!latestFarmInfo.value.bonus || !latestFarmInfo.value.farm.价格 || !latestFarmInfo.value.farm.剩余配货量) {
    return 0;
  }
  // 去除千分位逗号
  const bonus = parseFloat(String(latestFarmInfo.value.bonus).replace(/,/g, ''));
  const price = parseFloat(String(latestFarmInfo.value.farm.价格).replace(/,/g, ''));
  const remainingSupply = parseInt(String(latestFarmInfo.value.farm.剩余配货量).replace(/,/g, ''));

  if (isNaN(bonus) || isNaN(price) || price === 0 || isNaN(remainingSupply)) {
    return 0;
  }

  const maxQuantityByBonus = Math.floor(bonus / price);
  return Math.min(maxQuantityByBonus, remainingSupply);
}

// 添加新的计算函数用于出售
function calculateMaxSaleAmount() {
  if (!latestFarmInfo.value.vegetable_shop.可卖数量) {
    return 0;
  }
  return Number(latestFarmInfo.value.vegetable_shop.可卖数量);
}

// 计算出售可获得的象草
function calculateSaleBonus() {
  if (!saleAmount.value || !latestFarmInfo.value.vegetable_shop.市场单价) {
    return '0';
  }
  const maxAmount = calculateMaxSaleAmount();
  let amount = Number(saleAmount.value);
  if (isNaN(amount) || amount <= 0) return '0';
  amount = Math.min(amount, maxAmount);
  const price = Number(String(latestFarmInfo.value.vegetable_shop.市场单价).replace(/,/g, ''));
  if (isNaN(price)) {
    return '0';
  }
  return (amount * price).toLocaleString();
}

// 计算盈亏
function calculateProfit() {
  if (!saleAmount.value || !latestFarmInfo.value.vegetable_shop.市场单价 || !latestFarmInfo.value.vegetable_shop.成本) {
    return '0';
  }
  const maxAmount = calculateMaxSaleAmount();
  let amount = Number(saleAmount.value);
  if (isNaN(amount) || amount <= 0) return '0';
  amount = Math.min(amount, maxAmount);
  const price = Number(String(latestFarmInfo.value.vegetable_shop.市场单价).replace(/,/g, ''));
  const cost = Number(String(latestFarmInfo.value.vegetable_shop.成本).replace(/,/g, ''));
  if (isNaN(price) || isNaN(cost)) {
    return '0';
  }
  const profit = amount * (price - cost);
  return profit.toLocaleString();
}

// 计算盈利百分比
function calculateProfitPercentage() {
  if (!latestFarmInfo.value.vegetable_shop.市场单价 || !latestFarmInfo.value.vegetable_shop.成本) {
    return 0;
  }
  const marketPrice = Number(String(latestFarmInfo.value.vegetable_shop.市场单价).replace(/,/g, ''));
  const cost = Number(String(latestFarmInfo.value.vegetable_shop.成本).replace(/,/g, ''));
  if (isNaN(marketPrice) || isNaN(cost) || cost === 0) {
    return 0;
  }
  const percentage = ((marketPrice - cost) / cost) * 100;
  return percentage;
}

// 计算盈利百分比文本
function calculateProfitPercentageText() {
  const percentage = calculateProfitPercentage();
  if (percentage === 0) return '未知';
  return percentage.toFixed(2) + '%';
}

// 处理市场单价趋势数据，只保留周一到周六
function getMarketPriceTrend() {
  if (!status.sign_dict || !Array.isArray(status.sign_dict)) return { dates: [], prices: [] };
  // 只保留周一到周六
  const weekMap = ["日", "一", "二", "三", "四", "五", "六"];
  const result = status.sign_dict.filter(item => {
    if (!item.date || !item.farm_info || !item.farm_info.vegetable_shop) return false;
    // 支持日期格式如2024-05-27或2024/05/27
    let d = item.date.replace(/-/g, '/');
    let day = new Date(d).getDay();
    return day >= 1 && day <= 6;
  }).map(item => {
    // 只取日期部分（前10位）
    const dateStr = item.date ? item.date.slice(0, 10) : '';
    return {
      date: dateStr,
      price: (item.farm_info.vegetable_shop.市场单价 && !isNaN(Number(String(item.farm_info.vegetable_shop.市场单价).replace(/,/g, ''))))
        ? Number(String(item.farm_info.vegetable_shop.市场单价).replace(/,/g, '')) : null
    };
  }).filter(item => item.price !== null);
  return {
    dates: result.map(i => i.date),
    prices: result.map(i => i.price)
  };
}

function isDarkTheme() {
  const theme = document.documentElement.getAttribute('data-theme');
  if (theme === 'dark' || theme === 'purple' || theme === 'transparent') return true;
  // 兜底：如果没设置data-theme，检测系统
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function renderChart() {
  nextTick(() => {
    if (!chartRef.value) return;
    if (!chartInstance) {
      chartInstance = echarts.init(chartRef.value);
    }
    const { dates, prices } = getMarketPriceTrend();
    const dark = isDarkTheme();
    const textColor = dark ? '#E7E3FC' : '#333';
    const axisColor = textColor;
    const splitLineColor = dark ? '#444' : '#e3f2fd';
    const tooltipBg = dark ? '#232323' : '#fff';
    const tooltipBorder = dark ? '#12B1D1' : '#12B1D1';
    const lineColor = dark ? '#50a8ff' : '#12B1D1';
    const areaGradFrom = dark ? 'rgba(80,168,255,0.18)' : 'rgba(18,177,209,0.25)';
    const areaGradTo = dark ? 'rgba(80,168,255,0.03)' : 'rgba(67,160,71,0.05)';
    const option = {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'axis',
        backgroundColor: tooltipBg,
        borderColor: tooltipBorder,
        borderWidth: 1,
        textStyle: { color: textColor },
        formatter: params => {
          if (!params.length) return '';
          const p = params[0];
          return `${p.axisValue}<br/>市场单价: <b style='color:${lineColor}'>${p.data}</b>`;
        }
      },
      grid: { left: 45, right: 10, top: 30, bottom: 70 },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: axisColor } },
        axisLabel: {
          color: textColor,
          fontWeight: 500,
          rotate: 45,
          interval: 0,
          formatter: function(value) {
            if (window.innerWidth <= 600) {
              return value ? value.slice(-2) + '日' : value;
            } else {
              return value ? value.slice(5) : value;
            }
          },
        }
      },
      yAxis: {
        type: 'value',
        axisLine: { lineStyle: { color: axisColor } },
        splitLine: { lineStyle: { color: splitLineColor } },
        axisLabel: { color: textColor, fontWeight: 500 }
      },
      series: [
        {
          name: '市场单价',
          type: 'line',
          smooth: true,
          data: prices,
          symbol: 'circle',
          symbolSize: 8,
          lineStyle: {
            width: 3,
            color: lineColor
          },
          itemStyle: {
            color: lineColor,
            borderColor: '#fff',
            borderWidth: 2
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: areaGradFrom },
              { offset: 1, color: areaGradTo }
            ])
          },
          label: {
            color: textColor
          }
        }
      ],
      legend: {
        textStyle: {
          color: textColor
        }
      }
    };
    chartInstance.setOption(option, true);
    chartInstance.resize();
  });
}

onMounted(() => {
  refreshData();
  renderChart();
});

watch(() => status.sign_dict, () => {
  renderChart();
}, { deep: true });

watch(chartRef, () => {
  renderChart();
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
});
</script>

<style scoped>
.plugin-page {
  max-width: 80rem;
  margin: 0 auto;
  padding: 1rem;
}

.bg-primary-lighten-5 {
  background: linear-gradient(0deg, rgb(255, 255, 255) 0%, rgb(244, 247, 251) 100%);
}

.border {
  border: 5px solid rgba(255, 255, 255, 0.9);
  border-radius: 40px;
  box-shadow: 
    0 10px 30px -15px rgba(133, 189, 215, 0.3),
    0 0 0 1px rgba(133, 189, 215, 0.1);
  backdrop-filter: blur(10px);
}

.config-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border-radius: 30px;
  padding: 20px;
  border: 3px solid rgba(255, 255, 255, 0.9);
  box-shadow: 
    0 15px 25px -10px rgba(133, 189, 215, 0.2),
    0 0 0 1px rgba(133, 189, 215, 0.1);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

/* 深色模式适配 - 使用 data 属性选择器避免被过滤 */
[data-theme="dark"] .config-card,
[data-theme="purple"] .config-card,
[data-theme="transparent"] .config-card {
  background: linear-gradient(135deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%);
  border: 3px solid rgba(60, 60, 60, 0.9);
  box-shadow: 
    0 15px 25px -10px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(60, 60, 60, 0.1);
}

/* 系统深色模式适配 */
@media (prefers-color-scheme: dark) {
  .config-card {
    background: linear-gradient(135deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%);
    border: 3px solid rgba(60, 60, 60, 0.9);
    box-shadow: 
      0 15px 25px -10px rgba(0, 0, 0, 0.4),
      0 0 0 1px rgba(60, 60, 60, 0.1);
  }
}

.config-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #12B1D1, #43a047);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.config-card:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 20px 30px -15px rgba(133, 189, 215, 0.3),
    0 0 0 1px rgba(133, 189, 215, 0.15);
}

.config-card:hover::before {
  opacity: 1;
}

.v-btn {
  border-radius: 20px !important;
  text-transform: none !important;
  font-weight: 600 !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative;
  overflow: hidden;
}

.v-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.5);
  opacity: 0;
  border-radius: 100%;
  transform: scale(1, 1) translate(-50%);
  transform-origin: 50% 50%;
}

.v-btn:hover {
  transform: scale(1.03);
  box-shadow: 0 8px 20px -10px rgba(133, 189, 215, 0.4) !important;
}

.v-btn:hover::after {
  animation: ripple 1s ease-out;
}

.v-btn:active {
  transform: scale(0.98);
}

@keyframes ripple {
  0% {
    transform: scale(0, 0);
    opacity: 0.5;
  }
  100% {
    transform: scale(20, 20);
    opacity: 0;
  }
}

.v-text-field {
  margin-top: 15px;
}

.v-text-field :deep(.v-field) {
  border-radius: 20px !important;
  background: rgba(255, 255, 255, 0.9) !important;
  box-shadow: 
    0 8px 15px -5px rgba(133, 189, 215, 0.15),
    0 0 0 1px rgba(133, 189, 215, 0.1) !important;
  border: 2px solid transparent !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  backdrop-filter: blur(5px);
}

.v-text-field :deep(.v-field:hover) {
  border-color: rgba(18, 177, 209, 0.3) !important;
  box-shadow: 
    0 10px 20px -8px rgba(133, 189, 215, 0.2),
    0 0 0 1px rgba(133, 189, 215, 0.15) !important;
}

.v-text-field :deep(.v-field--focused) {
  border-color: #12B1D1 !important;
  box-shadow: 
    0 12px 25px -10px rgba(133, 189, 215, 0.3),
    0 0 0 1px rgba(133, 189, 215, 0.2) !important;
}

.v-alert {
  border-radius: 20px !important;
  box-shadow: 
    0 8px 15px -5px rgba(133, 189, 215, 0.15),
    0 0 0 1px rgba(133, 189, 215, 0.1) !important;
  backdrop-filter: blur(5px);
  transition: all 0.3s ease;
}

.v-alert:hover {
  transform: translateY(-1px);
  box-shadow: 
    0 12px 20px -8px rgba(133, 189, 215, 0.2),
    0 0 0 1px rgba(133, 189, 215, 0.15) !important;
}

.v-divider {
  margin: 20px 0 !important;
  opacity: 0.1 !important;
  background: linear-gradient(90deg, transparent, rgba(133, 189, 215, 0.2), transparent) !important;
}

.v-card-title {
  font-weight: 600 !important;
  color: rgb(16, 137, 211) !important;
  padding: 15px 20px !important;
  border-bottom: 2px solid rgba(16, 137, 211, 0.1) !important;
  margin-bottom: 10px !important;
  letter-spacing: 0.5px !important;
  background: linear-gradient(90deg, rgba(16, 137, 211, 0.05), transparent) !important;
}

.v-card-title .v-icon {
  opacity: 0.8;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.v-card-title:hover .v-icon {
  opacity: 1;
  transform: scale(1.1) rotate(5deg);
}

.dialog-card {
  border-radius: 16px !important;
  box-shadow: 
    0 20px 30px -15px rgba(133, 189, 215, 0.3),
    0 0 0 1px rgba(133, 189, 215, 0.1) !important;
  border: 3px solid rgba(255, 255, 255, 0.9) !important;
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%) !important;
  padding: 20px 10px 10px 10px !important;
  backdrop-filter: blur(10px);
}

/* 深色主题下的弹窗适配 */
[data-theme="dark"] .dialog-card,
[data-theme="purple"] .dialog-card,
[data-theme="transparent"] .dialog-card {
  background: linear-gradient(135deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%) !important;
  border: 3px solid rgba(60, 60, 60, 0.9) !important;
  box-shadow: 
    0 20px 30px -15px rgba(0, 0, 0, 0.4),
    0 0 0 1px rgba(60, 60, 60, 0.1) !important;
}

/* 系统深色模式兜底 */
@media (prefers-color-scheme: dark) {
  .dialog-card {
    background: linear-gradient(135deg, rgb(30, 30, 30) 0%, rgb(45, 45, 45) 100%) !important;
    border: 3px solid rgba(60, 60, 60, 0.9) !important;
    box-shadow: 
      0 20px 30px -15px rgba(0, 0, 0, 0.4),
      0 0 0 1px rgba(60, 60, 60, 0.1) !important;
  }
}

.dialog-btn {
  border-radius: 20px !important;
  font-weight: 600 !important;
  min-width: 96px !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  position: relative;
  overflow: hidden;
}

.dialog-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.5);
  opacity: 0;
  border-radius: 100%;
  transform: scale(1, 1) translate(-50%);
  transform-origin: 50% 50%;
}

.dialog-btn:hover {
  transform: scale(1.03);
  box-shadow: 0 8px 20px -10px rgba(133, 189, 215, 0.4) !important;
}

.dialog-btn:hover::after {
  animation: ripple 1s ease-out;
}

.dialog-btn:active {
  transform: scale(0.98);
}

.sale-info-row {
  margin-bottom: 18px;
  display: flex;
  gap: 12px;
}

.sale-info-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 12px;
  box-shadow: 
    0 8px 15px -5px rgba(133, 189, 215, 0.15),
    0 0 0 1px rgba(133, 189, 215, 0.1);
  padding: 16px 0 10px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(5px);
}

.sale-info-card:hover {
  transform: translateY(-2px);
  box-shadow: 
    0 12px 20px -8px rgba(133, 189, 215, 0.2),
    0 0 0 1px rgba(133, 189, 215, 0.15);
}

.sale-info-title {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
  font-weight: 500;
  transition: color 0.3s ease;
}

.sale-info-card:hover .sale-info-title {
  color: #333;
}

.sale-info-main {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  line-height: 1.1;
  display: flex;
  align-items: flex-end;
  transition: all 0.3s ease;
}

.sale-info-card:hover .sale-info-main {
  transform: scale(1.05);
}

.sale-info-main .unit {
  font-size: 15px;
  color: #888;
  font-weight: 400;
  margin-left: 2px;
  margin-bottom: 1px;
  transition: color 0.3s ease;
}

.sale-info-card:hover .sale-info-main .unit {
  color: #666;
}

.history-container {
  background: transparent !important;
  transition: all 0.3s ease;
}

.purchase-btn,
.sale-btn {
  font-size: 12px !important;
  padding: 0 10px !important;
  min-width: 48px !important;
  height: 28px !important;
  position: relative;
  overflow: hidden;
}

.purchase-btn::after,
.sale-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.5);
  opacity: 0;
  border-radius: 100%;
  transform: scale(1, 1) translate(-50%);
  transform-origin: 50% 50%;
}

.purchase-btn:hover {
  background: linear-gradient(90deg, #43a047 0%, #12B1D1 100%) !important;
  box-shadow: 0 8px 20px -10px rgba(18,177,209,0.3) !important;
  transform: scale(1.03);
}

.purchase-btn:hover::after,
.sale-btn:hover::after {
  animation: ripple 1s ease-out;
}

.sale-btn {
  padding: 0 14px !important;
  border-radius: 14px !important;
  background: linear-gradient(90deg, #43a047 0%, #12B1D1 100%) !important;
  color: #fff !important;
  font-weight: 700 !important;
  box-shadow: 0 8px 15px -5px rgba(67,160,71,0.2) !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  min-width: 60px;
  margin-left: 14px !important;
}

.sale-btn:hover {
  background: linear-gradient(90deg, #12B1D1 0%, #43a047 100%) !important;
  box-shadow: 0 12px 25px -10px rgba(67,160,71,0.3) !important;
  transform: scale(1.03);
}

.v-list,
.v-card-text,
.v-col,
.v-row,
.v-list-item:has(.sale-btn),
.v-list-item:has(.purchase-btn) {
  overflow: visible !important;
}

.sale-btn::after,
.purchase-btn::after {
  content: "";
  display: inline-block;
  width: 40px;
  height: 1px;
}

.btn-spacer {
  display: inline-block;
  width: 40px;
}

/* 添加列表项hover效果 */
.v-list-item {
  transition: all 0.3s ease;
  border-radius: 12px;
  margin: 2px 0;
}

.v-list-item:hover {
  background: rgba(133, 189, 215, 0.05) !important;
  transform: translateX(4px);
}

/* 优化图表容器 */
.history-container {
  position: relative;
  padding: 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.5) !important;
  backdrop-filter: blur(5px);
  transition: all 0.3s ease;
}

.history-container:hover {
  background: rgba(255, 255, 255, 0.8) !important;
  box-shadow: 
    0 12px 20px -8px rgba(133, 189, 215, 0.2),
    0 0 0 1px rgba(133, 189, 215, 0.15);
}

/* 添加页面背景动画 */
.plugin-page::before {
  content: '';
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 0% 0%, rgba(18,177,209,0.05) 0%, transparent 50%),
    radial-gradient(circle at 100% 100%, rgba(67,160,71,0.05) 0%, transparent 50%);
  z-index: -1;
  animation: gradientShift 15s ease infinite;
}

@keyframes gradientShift {
  0% {
    background-position: 0% 0%;
  }
  50% {
    background-position: 100% 100%;
  }
  100% {
    background-position: 0% 0%;
  }
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

[data-theme="dark"] .history-container,
[data-theme="purple"] .history-container,
[data-theme="transparent"] .history-container {
  background: #232323 !important;
  color: #fff !important;
  box-shadow: 0 12px 20px -8px rgba(0,0,0,0.5), 0 0 0 1px rgba(60, 60, 60, 0.15);
  backdrop-filter: blur(5px);
}
[data-theme="dark"] .history-container:hover,
[data-theme="purple"] .history-container:hover,
[data-theme="transparent"] .history-container:hover {
  background: #292929 !important;
}
[data-theme="dark"] .history-container *,
[data-theme="purple"] .history-container *,
[data-theme="transparent"] .history-container * {
  color: #fff !important;
}

@media (prefers-color-scheme: dark) {
  .history-container {
    background: #232323 !important;
    color: #fff !important;
    box-shadow: 0 12px 20px -8px rgba(0,0,0,0.5), 0 0 0 1px rgba(60, 60, 60, 0.15);
    backdrop-filter: blur(5px);
  }
  .history-container:hover {
    background: #292929 !important;
  }
  .history-container * {
    color: #fff !important;
  }
}

/* 深色主题下的.sale-info-card适配 */
[data-theme="dark"] .sale-info-card,
[data-theme="purple"] .sale-info-card,
[data-theme="transparent"] .sale-info-card {
  background: rgba(30, 30, 30, 0.95) !important;
  box-shadow: 0 8px 15px -5px rgba(0,0,0,0.4), 0 0 0 1px rgba(60,60,60,0.15) !important;
}

[data-theme="dark"] .sale-info-card:hover,
[data-theme="purple"] .sale-info-card:hover,
[data-theme="transparent"] .sale-info-card:hover {
  background: rgba(45, 45, 45, 0.98) !important;
  box-shadow: 0 12px 20px -8px rgba(0,0,0,0.5), 0 0 0 1px rgba(60,60,60,0.18) !important;
}

[data-theme="dark"] .sale-info-title,
[data-theme="purple"] .sale-info-title,
[data-theme="transparent"] .sale-info-title {
  color: #bbb !important;
}

[data-theme="dark"] .sale-info-card:hover .sale-info-title,
[data-theme="purple"] .sale-info-card:hover .sale-info-title,
[data-theme="transparent"] .sale-info-card:hover .sale-info-title {
  color: #fff !important;
}

[data-theme="dark"] .sale-info-main,
[data-theme="purple"] .sale-info-main,
[data-theme="transparent"] .sale-info-main {
  color: #fff !important;
}

[data-theme="dark"] .sale-info-main .unit,
[data-theme="purple"] .sale-info-main .unit,
[data-theme="transparent"] .sale-info-main .unit {
  color: #aaa !important;
}

[data-theme="dark"] .sale-info-card:hover .sale-info-main .unit,
[data-theme="purple"] .sale-info-card:hover .sale-info-main .unit,
[data-theme="transparent"] .sale-info-card:hover .sale-info-main .unit {
  color: #fff !important;
}

/* 系统深色模式兜底 */
@media (prefers-color-scheme: dark) {
  .sale-info-card {
    background: rgba(30, 30, 30, 0.95) !important;
    box-shadow: 0 8px 15px -5px rgba(0,0,0,0.4), 0 0 0 1px rgba(60,60,60,0.15) !important;
  }
  .sale-info-card:hover {
    background: rgba(45, 45, 45, 0.98) !important;
    box-shadow: 0 12px 20px -8px rgba(0,0,0,0.5), 0 0 0 1px rgba(60,60,60,0.18) !important;
  }
  .sale-info-title {
    color: #bbb !important;
  }
  .sale-info-card:hover .sale-info-title {
    color: #fff !important;
  }
  .sale-info-main {
    color: #fff !important;
  }
  .sale-info-main .unit {
    color: #aaa !important;
  }
  .sale-info-card:hover .sale-info-main .unit {
    color: #fff !important;
  }
}
</style> 