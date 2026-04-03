<template>
  <div class="magicfram-page">
    <!-- 确认出售对话框 -->
    <v-dialog v-model="showSellDialog" max-width="400">
      <v-card>
        <v-card-title class="text-h6 bg-deep-orange-lighten-5 text-deep-orange">
          <v-icon icon="mdi-alert" class="mr-2" size="small"></v-icon>
          确认出售
        </v-card-title>
        <v-card-text class="pa-4">
          确定要一键出售仓库中的所有物品吗？
          <div class="text-caption text-grey mt-2">此操作不可撤销。</div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey-darken-1" variant="text" @click="showSellDialog = false">取消</v-btn>
          <v-btn color="deep-orange" variant="elevated" @click="confirmSellAll" :loading="loading">确认出售</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-card flat class="rounded border">
      <v-card-title class="text-subtitle-1 d-flex align-center px-3 py-2 bg-gradient-primary">
        <v-icon icon="mdi-sprout" class="mr-2" color="white" size="small"></v-icon>
        <span class="text-white">好学农场</span>
        <v-spacer></v-spacer>
        
        <!-- 操作按钮组 -->
        <v-btn-group variant="outlined" density="compact" class="mr-1">
          <v-btn color="white" @click="refreshData" :loading="loading" size="small">
            <v-icon icon="mdi-refresh" size="18"></v-icon>
          </v-btn>
          <v-btn color="white" @click="switchToConfig" size="small">
            <v-icon icon="mdi-cog" size="18"></v-icon>
          </v-btn>
          <v-btn color="white" @click="closePlugin" size="small">
            <v-icon icon="mdi-close" size="18"></v-icon>
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
        <v-row dense>
          <!-- 左侧：菜市场价格波动图表 -->
          <v-col cols="12" md="6" class="d-flex flex-column">
            <!-- 插件状态卡片 -->
            <v-card flat class="rounded mb-3 border">
              <v-card-title class="text-subtitle-2 px-3 py-2 bg-purple-lighten-5 d-flex align-center">
                <v-icon icon="mdi-information" class="mr-2" color="purple" size="small"></v-icon>
                插件运行状态
              </v-card-title>
              <v-card-text class="px-3 py-2">
                <v-row dense align="center">
                  <v-col cols="3">
                    <div class="text-caption text-grey text-center">插件状态</div>
                    <div class="d-flex align-center justify-center mt-1">
                      <v-icon icon="mdi-play-circle-outline" 
                              :color="pluginStatus.enabled ? 'success' : 'grey'" 
                              size="small" class="mr-1"></v-icon>
                      <span :class="pluginStatus.enabled ? 'text-success' : 'text-grey'">{{ pluginStatus.enabled ? '已启用' : '已禁用' }}</span>
                    </div>
                  </v-col>
                  <v-col cols="4">
                    <div class="text-caption text-grey text-center">代理状态</div>
                    <div class="d-flex align-center justify-center mt-1">
                      <v-icon icon="mdi-earth" 
                              :color="pluginStatus.use_proxy ? 'info' : 'grey'" 
                              size="small" class="mr-1"></v-icon>
                      <span :class="pluginStatus.use_proxy ? 'text-info' : 'text-grey'">{{ pluginStatus.use_proxy ? '已启用' : '未启用' }}</span>
                    </div>
                  </v-col>
                  <v-col cols="5">
                    <div class="text-caption text-grey text-center">下次执行时间</div>
                    <div class="d-flex align-center justify-center mt-1">
                      <v-icon icon="mdi-clock-outline" size="small" class="mr-1" color="grey"></v-icon>
                      <span class="text-body-2 text-truncate" v-if="pluginStatus.cron" :title="pluginStatus.next_run || '等待调度...'">
                        {{ pluginStatus.next_run || '等待调度' }}
                      </span>
                      <span class="text-body-2 text-warning" v-else>
                        未配置
                      </span>
                    </div>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>

            <v-card flat class="rounded border flex-grow-1 d-flex flex-column">
              <v-card-title class="text-subtitle-2 px-3 py-2 bg-blue-lighten-5 d-flex align-center">
                <v-icon icon="mdi-chart-line" class="mr-2" color="blue" size="small"></v-icon>
                菜市场价格波动
                <v-spacer></v-spacer>
                <!-- 火花显示 -->
                <v-chip color="blue-grey-lighten-4" size="small" class="px-3 text-grey-darken-3" variant="flat">
                  <v-icon icon="mdi-fire" size="small" class="mr-1 fire-anim" color="deep-orange"></v-icon>
                  <span class="font-weight-bold">{{ bonus }}</span>
                </v-chip>
              </v-card-title>
              <v-card-text class="px-3 py-2 flex-grow-1 d-flex flex-column">
                <!-- 价格波动图表 -->
                <div class="chart-container" style="min-height: 300px; flex: 1; position: relative;">
                  <div ref="chartRef" style="width: 100%; height: 100%;"></div>
                  <div v-if="!hasChartData" class="d-flex align-center justify-center text-grey bg-grey-lighten-5 rounded" style="position: absolute; top:0; left:0; right:0; bottom:0; z-index:1;">
                    <div class="text-center">
                      <v-icon icon="mdi-chart-line" size="40" class="mb-2 opacity-50"></v-icon>
                      <div>暂无市场波动数据</div>
                    </div>
                  </div>
                </div>
              </v-card-text>
            </v-card>

          </v-col>

          <!-- 右侧：农作物和动物 -->
          <v-col cols="12" md="6" class="d-flex flex-column">
            <!-- 农作物种植区 -->
            <v-card flat class="rounded mb-3 border">
              <v-card-title class="text-subtitle-2 px-3 py-2 bg-green-lighten-5 d-flex align-center">
                <v-icon icon="mdi-flower" class="mr-2" color="green" size="small"></v-icon>
                <div class="d-flex align-center overflow-hidden flex-grow-1 mr-2">
                  <span class="flex-shrink-0">农作物种植区</span>
                  <span class="text-caption text-grey ml-2 text-truncate" style="font-size: 0.7rem;">有效期5天 | 有20%概率双倍收获</span>
                </div>
                <v-btn
                  v-if="emptyCropsCount >= 2"
                  class="bg-gradient-success text-white flex-shrink-0"
                  size="small"
                  variant="elevated"
                  @click="plantAll('crop')"
                  :disabled="loading"
                  elevation="1"
                >
                  一键种植
                </v-btn>
                <v-btn
                  v-else
                  class="bg-gradient-success text-white flex-shrink-0"
                  size="small"
                  variant="elevated"
                  @click="harvestAll"
                  :disabled="loading"
                  elevation="1"
                >
                  一键收获
                </v-btn>
              </v-card-title>
              <v-card-text class="px-3 py-2">
                <v-row v-if="crops.length > 0" dense>
                  <v-col v-for="(item, i) in crops" :key="'crop-'+i" cols="12" sm="6">
                <v-card :color="getItemColor(item.state)" variant="outlined" class="horizontal-card">
                  <div class="d-flex">
                    <!-- 左侧：图片 + 成长时间 + 剩余时间 -->
                    <div class="flex-shrink-0 pa-2" style="width: 70px;">
                      <v-img :src="getImageUrl(item.image)" width="40" height="40" contain class="mx-auto"></v-img>
                      <div v-if="item.grow_time" class="text-center text-caption text-grey mt-1" style="font-size: 0.65rem; line-height: 1.1; white-space: nowrap;">
                        成长时间: {{ item.grow_time }}
                      </div>
                      <div v-if="item.state === 'growing' && item.status" class="text-center text-caption text-grey" style="font-size: 0.65rem; line-height: 1.1; white-space: nowrap;">
                        {{ item.status }}
                      </div>
                    </div>
                    
                    <!-- 右侧：信息区 -->
                    <div class="flex-grow-1 pa-2">
                      <!-- 第一行：名称 + 状态标签 + 按钮 -->
                      <div class="d-flex align-center mb-1">
                        <div class="text-body-2 font-weight-bold">{{ item.name }}</div>
                        <v-chip v-if="item.state === 'empty'" size="x-small" color="green" class="ml-2">空闲</v-chip>
                        <v-chip v-else-if="item.state === 'ripe'" size="x-small" color="orange" class="ml-2">已成熟</v-chip>
                        <v-spacer></v-spacer>
                        <v-btn v-if="item.state === 'empty'" color="green" size="x-small" variant="flat" @click="plant('crop', item.id)">种植</v-btn>
                        <v-btn v-if="item.state === 'ripe'" color="orange" size="x-small" variant="flat" @click="harvest('crop', item.id)">收获</v-btn>
                      </div>
                      
                      <!-- 价格信息 -->
                      <div class="text-caption text-grey-darken-1" style="line-height: 1.4;">
                        <div v-if="item.price">价格: {{ item.price }}</div>
                      </div>
                    </div>
                  </div>
                </v-card>
              </v-col>
            </v-row>
            <div v-else class="text-center text-grey py-4">
              暂无农作物数据
            </div>
          </v-card-text>
        </v-card>

        <!-- 动物养殖区 -->
        <v-card flat class="rounded border flex-grow-1">
          <v-card-title class="text-subtitle-2 px-3 py-2 bg-brown-lighten-5 d-flex align-center">
            <v-icon icon="mdi-cow" class="mr-2" color="brown" size="small"></v-icon>
            <div class="d-flex align-center overflow-hidden flex-grow-1 mr-2">
              <span class="flex-shrink-0">动物养殖区</span>
              <span class="text-caption text-grey ml-2 text-truncate" style="font-size: 0.7rem;">有效期5天</span>
            </div>
            <v-btn
              v-if="emptyAnimalsCount >= 2"
              class="bg-gradient-brown text-white flex-shrink-0"
              size="small"
              variant="elevated"
              @click="plantAll('animal')"
              :disabled="loading"
              elevation="1"
            >
              一键养殖
            </v-btn>
            <v-btn
              v-else
              class="bg-gradient-success text-white flex-shrink-0"
              size="small"
              variant="elevated"
              @click="harvestAll"
              :disabled="loading"
              elevation="1"
            >
              一键收获
            </v-btn>
          </v-card-title>
          <v-card-text class="px-3 py-2">
            <v-row v-if="animals.length > 0" dense>
              <v-col v-for="(item, i) in animals" :key="'animal-'+i" cols="12" sm="6">
                <v-card :color="getItemColor(item.state)" variant="outlined" class="horizontal-card">
                  <div class="d-flex">
                    <!-- 左侧：图片 + 成长时间 + 剩余时间 -->
                    <!-- 左侧：图片 + 成长时间 + 剩余时间 -->
                    <div class="flex-shrink-0 pa-2" style="width: 70px;">
                      <v-img :src="getImageUrl(item.image)" width="40" height="40" contain class="mx-auto"></v-img>
                      <!-- 成长时间在图片下方，不换行 -->
                      <!-- 成长时间在图片下方，不换行 -->
                      <div v-if="item.grow_time" class="text-center text-caption text-grey mt-1" style="font-size: 0.65rem; line-height: 1.1; white-space: nowrap;">
                        成长时间: {{ item.grow_time }}
                      </div>
                      <!-- 剩余时间在成长时间下方，不换行 -->
                      <div v-if="item.state === 'growing' && item.status" class="text-center text-caption text-grey" style="font-size: 0.65rem; line-height: 1.1; white-space: nowrap;">
                        {{ item.status }}
                      </div>
                    </div>
                    
                    <!-- 右侧：信息区 -->
                    <div class="flex-grow-1 pa-2">
                      <!-- 第一行：名称 + 状态标签 + 按钮 -->
                      <div class="d-flex align-center mb-1">
                        <div class="text-body-2 font-weight-bold">{{ item.name }}</div>
                        <v-chip v-if="item.state === 'empty'" size="x-small" color="green" class="ml-2">空闲</v-chip>
                        <v-chip v-else-if="item.state === 'ripe'" size="x-small" color="orange" class="ml-2">已成熟</v-chip>
                        <v-spacer></v-spacer>
                        <v-btn v-if="item.state === 'empty'" color="brown" size="x-small" variant="flat" @click="plant('animal', item.id)">养殖</v-btn>
                        <v-btn v-if="item.state === 'ripe'" color="orange" size="x-small" variant="flat" @click="harvest('animal', item.id)">收获</v-btn>
                      </div>
                      
                      <!-- 价格信息 -->
                      <div class="text-caption text-grey-darken-1" style="line-height: 1.4;">
                        <div v-if="item.price">价格: {{ item.price }}</div>
                      </div>
                    </div>
                  </div>
                </v-card>
              </v-col>
            </v-row>
            <div v-else class="text-center text-grey py-4">
              暂无动物数据
            </div>
          </v-card-text>
        </v-card>
          </v-col>
        </v-row>


        <!-- 仓库 -->
        <v-card flat class="rounded mb-3 border mt-3">
          <v-card-title class="text-subtitle-2 px-3 py-2 bg-amber-lighten-5 d-flex align-center">
            <v-icon icon="mdi-warehouse" class="mr-2" color="amber" size="small"></v-icon>
            仓库
            <!-- 排序控制 -->
            <v-menu location="bottom end">
              <template v-slot:activator="{ props }">
                <v-btn
                  variant="text"
                  size="small"
                  color="grey-darken-2"
                  class="ml-2"
                  v-bind="props"
                  prepend-icon="mdi-sort"
                >
                  {{ sortOrder === 'asc' ? '最近过期优先' : '最远过期优先' }}
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item @click="sortOrder = 'asc'" :active="sortOrder === 'asc'" color="primary">
                  <v-list-item-title>最近过期优先</v-list-item-title>
                </v-list-item>
                <v-list-item @click="sortOrder = 'desc'" :active="sortOrder === 'desc'" color="primary">
                  <v-list-item-title>最远过期优先</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
            <v-spacer></v-spacer>

            <!-- 一键出售按钮 -->
             <v-btn
              class="bg-gradient-sell text-white"
              size="small"
              variant="elevated"
              @click="sellAll"
              :disabled="loading || warehouse.length === 0"
              elevation="1"
            >
              一键出售
            </v-btn>
          </v-card-title>
          <v-card-text class="px-3 py-2">
            <div v-if="warehouse.length > 0">
              <v-table density="compact">
                <thead>
                  <tr>
                    <th>物品名称</th>
                    <th class="text-center">数量</th>
                    <th class="text-center">收获时间</th>
                    <th class="text-center">剩余时间</th>
                    <th class="text-center">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(item, i) in paginatedWarehouse" :key="'warehouse-'+i">
                    <td>{{ item.name }}</td>
                    <td class="text-center">{{ item.quantity }}</td>
                    <td class="text-center">{{ item.harvest_time }}</td>
                    <td class="text-center">
                      <span :class="{'text-red': item.remaining_time && item.remaining_time.includes('分') && !item.remaining_time.includes('小时')}">
                        {{ item.remaining_time }}
                      </span>
                    </td>
                    <td class="text-center">
                      <v-btn size="small" color="error" variant="text" @click="sell(item.key)" :loading="loading">出售</v-btn>
                    </td>
                  </tr>
                </tbody>
              </v-table>
              <div v-if="pageCount > 1" class="d-flex justify-center mt-2">
                <v-pagination
                  v-model="page"
                  :length="pageCount"
                  :total-visible="5"
                  density="compact"
                  active-color="primary"
                  variant="text"
                ></v-pagination>
              </div>
            </div>
            <div v-else class="text-center text-grey py-4">
              暂无物品
            </div>
          </v-card-text>
        </v-card>

        <!-- 菜市场 -->
        <v-card flat class="rounded mb-3 border">
          <v-card-title class="text-subtitle-2 px-3 py-2 bg-light-green-lighten-5">
            <v-icon icon="mdi-store" class="mr-2" color="light-green" size="small"></v-icon>
            菜市场
            <span class="text-caption text-grey ml-2" style="font-size: 0.7rem;">每日0、4、8、12、16、20点刷新 | 波动范围±50%</span>
          </v-card-title>
          <v-card-text class="px-3 py-2">
            <v-row v-if="market.length > 0">
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">农作物</div>
                <v-table density="compact">
                  <thead>
                    <tr>
                      <th>物品名称</th>
                      <th class="text-center">成本价</th>
                      <th class="text-center">当前价格</th>
                      <th class="text-center">波动幅度</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, i) in market.filter(m => m.type === 'crop')" :key="'market-crop-'+i">
                      <td>{{ item.name }}</td>
                      <td class="text-center text-grey">{{ item.last_price }}</td>
                      <td class="text-center font-weight-bold">{{ item.price }}</td>
                      <td class="text-center">
                        <template v-if="item.change_pct !== undefined && item.change_pct !== 0">
                          <span :class="item.change_pct > 0 ? 'text-red' : 'text-green'">
                            {{ item.change_pct > 0 ? '+' : '' }}{{ item.change_pct }}%
                          </span>
                        </template>
                        <span v-else class="text-grey">-</span>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-col>
              <v-col cols="12" md="6">
                <div class="text-subtitle-2 mb-2">动物</div>
                <v-table density="compact">
                  <thead>
                    <tr>
                      <th>物品名称</th>
                      <th class="text-center">成本价</th>
                      <th class="text-center">当前价格</th>
                      <th class="text-center">波动幅度</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, i) in market.filter(m => m.type === 'animal')" :key="'market-animal-'+i">
                      <td>{{ item.name }}</td>
                      <td class="text-center text-grey">{{ item.last_price }}</td>
                      <td class="text-center font-weight-bold">{{ item.price }}</td>
                      <td class="text-center">
                        <template v-if="item.change_pct !== undefined && item.change_pct !== 0">
                          <span :class="item.change_pct > 0 ? 'text-red' : 'text-green'">
                            {{ item.change_pct > 0 ? '+' : '' }}{{ item.change_pct }}%
                          </span>
                        </template>
                        <span v-else class="text-grey">-</span>
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </v-col>
            </v-row>
            <div v-else class="text-center text-grey py-4">
              暂无价格信息
            </div>
          </v-card-text>
        </v-card>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch, nextTick, onUnmounted } from 'vue';
import * as echarts from 'echarts';

// 定义 Props - 接收来自父组件的 API 和配置（可选）
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

// 定义 Emits - 向父组件发送事件
const emit = defineEmits(['close', 'switch']);

// 插件 ID
const PLUGIN_ID = 'MagicFram';

// 创建默认 API 实现（用于插件模式）
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

// 使用传入的 api 或默认实现
const apiClient = props.api || createDefaultApi();

// 响应式数据
const loading = ref(false);
const bonus = ref("0");
const crops = ref([]);
const animals = ref([]);
const warehouse = ref([]);
const market = ref([]);

const marketTrends = ref({});

// 计算属性：空闲数量
const emptyCropsCount = computed(() => {
  return crops.value.filter(item => item.state === 'empty').length;
});

const emptyAnimalsCount = computed(() => {
  return animals.value.filter(item => item.state === 'empty').length;
});

// 预定义颜色盘
const CHART_COLORS = [
  '#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5',
  '#2196F3', '#03A9F4', '#00BCD4', '#009688', '#4CAF50',
  '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800',
  '#FF5722', '#795548', '#9E9E9E', '#607D8B'
];

const successMessage = ref('');
const errorMessage = ref('');

const pluginStatus = reactive({
  enabled: false,
  cron: '',
  use_proxy: false,
  next_run: ''
});

// SVG 尺寸配置 (Deprecated, kept for reference if needed, but logic moved to ECharts)
const chartRef = ref(null);
let chartInstance = null;

const hasChartData = computed(() => {
  const items = Object.keys(marketTrends.value || {});
  return items.length > 0;
});

// 渲染 ECharts 图表
const renderChart = () => {
    nextTick(() => {
      if (!chartRef.value) return;
      
      const trends = marketTrends.value || {};
      const seriesNames = Object.keys(trends);
      
      if (seriesNames.length === 0) {
        if (chartInstance) {
          chartInstance.dispose();
          chartInstance = null;
        }
        return;
      }
      
      if (!chartInstance) {
        chartInstance = echarts.init(chartRef.value);
      }
      
      // 准备数据
      const categories = [];
      const seriesList = [];
      
      // 获取 x 轴标签 (取第一个有数据的系列的标签)
      if (seriesNames.length > 0) {
         const firstData = trends[seriesNames[0]];
         if (Array.isArray(firstData)) {
            firstData.forEach(item => {
               categories.push(item.label || item.time || '');
            });
         }
      }
      
      seriesNames.forEach((name, index) => {
         const rawData = trends[name] || [];
         if (rawData.length === 0) return;
         
         // 直接使用原始价格
         const displayData = rawData.map(item => parseFloat(item.price));
         
         seriesList.push({
             name: name,
             type: 'line',
             smooth: true,
             symbol: 'circle',
             symbolSize: 6,
             data: displayData,
             lineStyle: { width: 3 },
             itemStyle: { color: CHART_COLORS[index % CHART_COLORS.length] }
         });
      });
      
      
      // Determine label color based on theme
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
                     window.matchMedia('(prefers-color-scheme: dark)').matches;
      const labelColor = isDark ? '#ccc' : '#333';

      const option = {
          tooltip: {
              trigger: 'axis',
              appendToBody: true,
              formatter: function(params) {
                  if (!params.length) return '';
                  
                  // Use a simplified formatter or just return the html
                  // We need to rebuild the formatter logic here because we are replacing the whole function block potentially if allows multiple
                  // But wait, the previous code block for renderChart is simpler. 
                  // Let's just update the legend textStyle.
                  
                  let res = params[0].name + '<br/>';
                  
                  params.forEach(param => {
                      const val = param.value;
                      const name = param.seriesName;
                      const color = param.color;
                      
                      // 从 market 数据中查找成本价 (last_price 现在存储的是成本价)
                      let fluctuationStr = '';
                      const marketItem = market.value.find(m => m.name === name);
                      
                      if (marketItem) {
                          // 解析成本价
                          const costPriceStr = String(marketItem.last_price).replace(/[^\d.]/g, '');
                          const costPrice = parseFloat(costPriceStr);
                          
                          if (costPrice > 0) {
                              const pct = ((val - costPrice) / costPrice) * 100;
                              const sign = pct > 0 ? '+' : '';
                              const colorClass = pct > 0 ? '#F44336' : (pct < 0 ? '#4CAF50' : '#999'); // 红涨绿跌
                              fluctuationStr = ` <span style="color:${colorClass}; font-size:0.9em;">(${sign}${pct.toFixed(2)}%)</span>`;
                          }
                      }
                      
                      res += `<div style="display:flex; align-items:center; justify-content:space-between;">
                                <div>
                                    <span style="display:inline-block;margin-right:5px;border-radius:10px;width:10px;height:10px;background-color:${color};"></span>
                                    <span>${name}</span>
                                </div>
                                <span style="margin-left:10px; font-weight:bold;">${val}${fluctuationStr}</span>
                              </div>`;
                  });
                  return res;
              },
              className: 'echarts-tooltip-popup',
              padding: 10,
              backgroundColor: 'rgba(255, 255, 255, 0.9)', // Default, overridden by CSS if !important used
              borderColor: '#ccc',
              textStyle: { color: '#333' },
              extraCssText: 'box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); border-radius: 4px;'
          },
          grid: {
              left: '3%',
              right: '4%',
              bottom: '10%',
              top: '10%',
              containLabel: true
          },
          legend: {
              data: seriesNames,
              bottom: 0,
              type: 'scroll',
              icon: 'roundRect',
              itemWidth: 10,
              itemHeight: 10,
              textStyle: { fontSize: 11, color: labelColor }
          },
          xAxis: {
              type: 'category',
              boundaryGap: false,
              data: categories,
              axisLine: { lineStyle: { color: isDark ? '#555' : '#e0e0e0' } },
              axisLabel: { color: isDark ? '#aaa' : '#999', fontSize: 10 }
          },
          yAxis: {
              type: 'value',
              name: '价格',
              scale: true,
              axisLine: { show: false },
              axisTick: { show: false },
              splitLine: { lineStyle: { type: 'dashed', color: isDark ? '#444' : '#eee' } },
              axisLabel: { color: isDark ? '#aaa' : '#999', fontSize: 10 },
              nameTextStyle: { color: isDark ? '#aaa' : '#999' }
          },
          series: seriesList
      };
      
      chartInstance.setOption(option, true);
      chartInstance.resize();
    });
};

// 监听数据变化刷新图表
watch(marketTrends, () => {
   renderChart();
}, { deep: true });

onMounted(() => {
    // 监听窗口大小变化
    window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
    if (chartInstance) {
        chartInstance.dispose();
        chartInstance = null;
    }
    window.removeEventListener('resize', handleResize);
});

const handleResize = () => {
    if (chartInstance) {
        chartInstance.resize();
    }
};

// 显示通知
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

// 刷新数据 - 强制从站点获取最新数据
const refreshData = async () => {
  loading.value = true;
  try {
    // 调用 refresh API 强制获取最新数据
    const url = `/plugin/${PLUGIN_ID}/refresh`;
    const res = await apiClient.post(url, {});
    
    console.log('强制刷新农场数据:', res);
    
    if (res && res.success && res.farm_status) {
      const data = res.farm_status;
      bonus.value = data.bonus || "0";
      crops.value = data.crops || [];
      animals.value = data.animals || [];
      warehouse.value = data.warehouse || [];
      market.value = data.market || [];
      marketTrends.value = data.market_trends?.data || {};
      
      showNotification(`数据刷新成功（更新时间: ${res.last_update}）`, 'success');
    } else {
      const errorMsg = (res && res.message) || '获取农场数据失败';
      showNotification(errorMsg, 'error');
    }
  } catch (e) {
    console.error('刷新数据失败:', e);
    showNotification('刷新数据失败: ' + (e.message || '未知错误'), 'error');
  } finally {
    loading.value = false;
  }
};

// 种植/养殖
const plant = async (type, id) => {
  console.log(`Planting ${type} ${id}`);
  try {
    const url = `/plugin/${PLUGIN_ID}/plant`;
    await apiClient.post(url, { item_type: type, item_id: id });
    showNotification(`${type === 'crop' ? '种植' : '养殖'}成功`, 'success');
    // 刷新数据
    await refreshData();
  } catch (e) {
    console.error('操作失败:', e);
    showNotification('操作失败: ' + (e.message || '未知错误'), 'error');
  }
};

// 收获
const harvest = async (type, id) => {
  console.log(`Harvesting ${type} ${id}`);
  try {
    const url = `/plugin/${PLUGIN_ID}/harvest`;
    await apiClient.post(url, { item_type: type, item_id: id });
    showNotification('收获成功', 'success');
    // 刷新数据
    await refreshData();
  } catch (e) {
    console.error('收获失败:', e);
    showNotification('收获失败: ' + (e.message || '未知错误'), 'error');
  }
};

// 一键收获
const harvestAll = async () => {
  console.log("Harvesting all...");
  try {
    const url = `/plugin/${PLUGIN_ID}/harvest-all`;
    await apiClient.post(url, {});
    showNotification('一键收获成功', 'success');
    // 刷新数据
    await refreshData();
  } catch (e) {
    console.error('一键收获失败:', e);
    showNotification('一键收获失败: ' + (e.message || '未知错误'), 'error');
  }
};


// 一键种植/养殖
const plantAll = async (type) => {
  const typeName = type === 'crop' ? '一键种植' : '一键养殖';
  console.log(`${typeName}...`);
  // 开启 loading 防止重复点击
  loading.value = true;
  try {
    const url = `/plugin/${PLUGIN_ID}/plant-all`;
    const res = await apiClient.post(url, { type });
    
    if (res && res.success) {
      showNotification(`${typeName}成功: ${res.msg}`, 'success');
    } else {
      showNotification(`${typeName}失败: ` + (res.msg || '未知错误'), 'error');
    }
    
    // 刷新数据
    await refreshData();
    
  } catch (e) {
    console.error(`${typeName}失败:`, e);
    showNotification(`${typeName}失败: ` + (e.message || '未知错误'), 'error');
  } finally {
    loading.value = false;
  }
};

// 仓库排序
const sortOrder = ref('asc'); // asc, desc

// 解析剩余时间字符串为分钟数
const parseTime = (timeStr) => {
  if (!timeStr) return 999999;
  if (timeStr.includes('已过期')) return -1;
  
  let totalMinutes = 0;
  
  // 提取数字和单位
  const days = timeStr.match(/(\d+)天/);
  const hours = timeStr.match(/(\d+)小时/);
  const mins = timeStr.match(/(\d+)分/);
  
  if (days) totalMinutes += parseInt(days[1]) * 24 * 60;
  if (hours) totalMinutes += parseInt(hours[1]) * 60;
  if (mins) totalMinutes += parseInt(mins[1]);
  
  // 如果没有任何匹配，可能是 "刚刚" 或其他，视为 0
  if (totalMinutes === 0 && !timeStr.includes('分')) return 999999;
  
  return totalMinutes;
};

// 排序后的仓库数据
const sortedWarehouse = computed(() => {
  if (!warehouse.value) return [];
  
  let data = [...warehouse.value];
  
  if (sortOrder.value === 'default') {
    return data;
  }
  
  return data.sort((a, b) => {
    const timeA = parseTime(a.remaining_time);
    const timeB = parseTime(b.remaining_time);
    
    if (sortOrder.value === 'asc') {
      // 最近过期优先 (剩余时间小的在前)
      return timeA - timeB;
    } else {
      // 最远过期优先 (剩余时间大的在前)
      return timeB - timeA;
    }
  });
});

// 分页相关
const page = ref(1);
const itemsPerPage = 10;

const paginatedWarehouse = computed(() => {
  const start = (page.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return sortedWarehouse.value.slice(start, end);
});

const pageCount = computed(() => {
  return Math.ceil(sortedWarehouse.value.length / itemsPerPage);
});

// 数据变化时重置页码
watch(() => sortedWarehouse.value, () => {
    // 只有当当前页超出范围时才重置，或者是排序变化可能需要重置？
    // 为了简单体验，列表刷新或重新排序后回到第一页通常是合理的
    page.value = 1;
});

// 出售物品
const sell = async (key) => {
  console.log(`Selling item with key: ${key}`);
  try {
    const url = `/plugin/${PLUGIN_ID}/sell`;
    const res = await apiClient.post(url, { key });
    if (res && res.success) {
      showNotification('出售成功', 'success');
      // 刷新数据
      await refreshData();
    } else {
      showNotification(res.msg || '出售失败', 'error');
    }
  } catch (e) {
    console.error('出售失败:', e);
    showNotification('出售失败: ' + (e.message || '未知错误'), 'error');
  }
};

// 一键出售
// 一键出售相关逻辑
const showSellDialog = ref(false);

// 点击一键出售
const sellAll = () => {
  console.log("sellAll clicked");
  if (warehouse.value.length === 0) {
    showNotification('仓库为空', 'warning');
    return;
  }
  showSellDialog.value = true;
  console.log("showSellDialog set to true", showSellDialog.value);
};

// 确认一键出售
const confirmSellAll = async () => {
  showSellDialog.value = false;
  loading.value = true;
  try {
    const url = `/plugin/${PLUGIN_ID}/sell-all`;
    const res = await apiClient.post(url, {});
    if (res && res.success) {
      showNotification(res.msg, 'success');
      await refreshData();
    } else {
      showNotification(res.msg || '一键出售失败', 'error');
    }
  } catch (e) {
    console.error('一键出售异常:', e);
    showNotification('一键出售异常: ' + (e.message || '未知错误'), 'error');
  } finally {
    loading.value = false;
  }
};

// 切换到配置页
const switchToConfig = () => {
  emit('switch', 'config');
};

// 关闭插件
const closePlugin = () => {
  emit('close');
};

// 获取项目颜色
const getItemColor = (state) => {
  if (state === 'ripe') return 'orange-lighten-4';
  if (state === 'growing') return 'green-lighten-4';
  if (state === 'empty') return '';
  return '';
};

// 获取图片 URL（直接使用后端返回的完整URL）
const getImageUrl = (path) => {
  if (!path) return '';
  // 后端已经返回完整的图片URL，直接使用
  return path;
};

// 组件挂载时自动加载历史数据
onMounted(async () => {
  loading.value = true;
  try {
    const url = `/plugin/${PLUGIN_ID}/status`;
    const res = await apiClient.get(url);
    
    console.log('获取农场历史数据:', res);
    
    if (res) {
      // 更新插件状态
      pluginStatus.enabled = res.enabled || false;
      pluginStatus.cron = res.cron || '';
      pluginStatus.use_proxy = res.use_proxy || false;
      pluginStatus.next_run = res.next_run_time || '';

      if (res.farm_status) {
        const data = res.farm_status;
        bonus.value = data.bonus || "0";
        crops.value = data.crops || [];
        animals.value = data.animals || [];
        warehouse.value = data.warehouse || [];
        warehouse.value = data.warehouse || [];
        market.value = data.market || [];
        marketTrends.value = data.market_trends?.data || {};
        
        // 显示最后更新时间
        if (res.last_run) {
          showNotification(`已加载农场数据（最后更新: ${res.last_run}）`, 'success');
        } else {
          // 如果有数据但没有时间，也认为是由于缓存加载成功的
           showNotification('已加载农场数据', 'success');
        }
      } else {
        showNotification('暂无历史数据，请点击刷新获取最新数据', 'info');
      }
    }
  } catch (e) {
    console.error('加载历史数据失败:', e);
    showNotification('点击右上角刷新按钮获取最新数据', 'info');
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.magicfram-page {
  margin: 0 auto;
  padding: 0.5rem;
}

/* 棕色渐变 - 动物养殖 */
.bg-gradient-brown {
  background: linear-gradient(135deg, #795548 0%, #8d6e63 100%);
  box-shadow: 0 2px 8px rgba(121, 85, 72, 0.3);
}

.bg-gradient-primary {
  background: linear-gradient(135deg, #4caf50 0%, #66bb6a 100%);
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.07);
}

.bg-green-lighten-5 {
  background-color: rgba(76, 175, 80, 0.1);
}

.bg-brown-lighten-5 {
  background-color: rgba(121, 85, 72, 0.1);
}

.border {
  border: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.v-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.v-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.text-subtitle-1 {
  font-size: 1.1rem !important;
  font-weight: 500;
}

.text-subtitle-2 {
  font-size: 0.9rem !important;
  font-weight: 500;
}

/* 火花芯片动画 */
.v-chip {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.9;
  }
}

/* 横向卡片样式 */
.horizontal-card {
  min-height: 70px;
  height: 100%;
}

.horizontal-card .d-flex {
  align-items: flex-start;
}

.horizontal-card .text-body-2 {
  line-height: 1.3;
}

.horizontal-card .text-caption {
  font-size: 0.75rem;
  line-height: 1.3;
}

.horizontal-card .v-btn {
  min-width: 45px;
  padding: 0 8px;
  font-size: 0.7rem;
  height: 22px;
}

/* 火花动画 */
.fire-anim {
  animation: fire-pulse 1.5s infinite alternate;
}

@keyframes fire-pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.2); opacity: 1; text-shadow: 0 0 5px orange; }
}

/* 收获按钮渐变 */
.bg-gradient-success {
  background: linear-gradient(45deg, #66bb6a, #43a047) !important;
  transition: all 0.3s ease;
}

.bg-gradient-success:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4) !important;
}

/* 出售按钮渐变 */
.bg-gradient-sell {
  background: linear-gradient(45deg, #FF7043, #F4511E) !important;
  transition: all 0.3s ease;
}

.bg-gradient-sell:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(244, 81, 30, 0.4) !important;
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

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .bg-primary-lighten-5 {
    background-color: rgba(var(--v-theme-primary), 0.15);
  }
  
  .bg-purple-lighten-5 {
    background-color: rgba(156, 39, 176, 0.2) !important;
  }

  .bg-blue-lighten-5 {
    background-color: rgba(33, 150, 243, 0.2) !important;
  }
  
  .bg-green-lighten-5 {
    background-color: rgba(76, 175, 80, 0.2) !important;
  }
  
  .bg-brown-lighten-5 {
    background-color: rgba(121, 85, 72, 0.2) !important;
  }

  .bg-amber-lighten-5 {
    background-color: rgba(255, 193, 7, 0.2) !important;
  }

  .bg-grey-lighten-5 {
    background-color: rgba(158, 158, 158, 0.1) !important;
  }

  .bg-light-green-lighten-5 {
    background-color: rgba(139, 195, 74, 0.2) !important;
  }

  .bg-blue-grey-lighten-4 {
    background-color: rgba(69, 90, 100, 0.5) !important;
  }

  .text-grey-darken-3 {
    color: rgb(220, 220, 220) !important;
  }

  .text-subtitle-2 {
    color: rgb(220, 220, 220) !important;
  }
}

/* 深色模式适配 - 使用 data 属性选择器 */
[data-theme="dark"] .bg-primary-lighten-5,
[data-theme="purple"] .bg-primary-lighten-5,
[data-theme="transparent"] .bg-primary-lighten-5 {
  background-color: rgba(var(--v-theme-primary), 0.15);
}

[data-theme="dark"] .bg-purple-lighten-5,
[data-theme="purple"] .bg-purple-lighten-5,
[data-theme="transparent"] .bg-purple-lighten-5 {
  background-color: rgba(156, 39, 176, 0.2) !important;
}

[data-theme="dark"] .bg-blue-lighten-5,
[data-theme="purple"] .bg-blue-lighten-5,
[data-theme="transparent"] .bg-blue-lighten-5 {
  background-color: rgba(33, 150, 243, 0.2) !important;
}

[data-theme="dark"] .bg-green-lighten-5,
[data-theme="purple"] .bg-green-lighten-5,
[data-theme="transparent"] .bg-green-lighten-5 {
  background-color: rgba(76, 175, 80, 0.2) !important;
}

[data-theme="dark"] .bg-brown-lighten-5,
[data-theme="purple"] .bg-brown-lighten-5,
[data-theme="transparent"] .bg-brown-lighten-5 {
  background-color: rgba(121, 85, 72, 0.2) !important;
  color: rgb(220, 220, 220) !important;
}

[data-theme="dark"] .bg-amber-lighten-5,
[data-theme="purple"] .bg-amber-lighten-5,
[data-theme="transparent"] .bg-amber-lighten-5 {
  background-color: rgba(255, 193, 7, 0.2) !important;
}

[data-theme="dark"] .bg-light-green-lighten-5,
[data-theme="purple"] .bg-light-green-lighten-5,
[data-theme="transparent"] .bg-light-green-lighten-5 {
  background-color: rgba(139, 195, 74, 0.2) !important;
}

[data-theme="dark"] .bg-grey-lighten-5,
[data-theme="purple"] .bg-grey-lighten-5,
[data-theme="transparent"] .bg-grey-lighten-5 {
  background-color: rgba(158, 158, 158, 0.1) !important;
}

[data-theme="dark"] .bg-blue-grey-lighten-4,
[data-theme="purple"] .bg-blue-grey-lighten-4,
[data-theme="transparent"] .bg-blue-grey-lighten-4 {
  background-color: rgba(69, 90, 100, 0.5) !important;
}

[data-theme="dark"] .text-grey-darken-3,
[data-theme="purple"] .text-grey-darken-3,
[data-theme="transparent"] .text-grey-darken-3 {
  color: rgb(220, 220, 220) !important;
}

/* 深色模式文字适配 */
[data-theme="dark"] .text-subtitle-2,
[data-theme="purple"] .text-subtitle-2,
[data-theme="transparent"] .text-subtitle-2 {
  color: rgb(220, 220, 220) !important;
}
</style>

<style>
/* ECharts Tooltip Adapt - Must be global because appendToBody is true */
.echarts-tooltip-popup {
  background-color: rgba(255, 255, 255, 0.95) !important;
  border-width: 1px !important;
  border-color: #ccc !important;
  color: #333 !important;
  z-index: 9999;
}

/* 深色模式适配 */
@media (prefers-color-scheme: dark) {
  .echarts-tooltip-popup {
    background-color: rgba(50, 50, 50, 0.95) !important;
    border-color: #555 !important;
    color: #eee !important;
  }
}

[data-theme="dark"] .echarts-tooltip-popup,
[data-theme="purple"] .echarts-tooltip-popup,
[data-theme="transparent"] .echarts-tooltip-popup {
  background-color: rgba(50, 50, 50, 0.95) !important;
  border-color: #555 !important;
  color: #eee !important; 
}
</style>
