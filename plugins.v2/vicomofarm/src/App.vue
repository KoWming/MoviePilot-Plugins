<template>
  <div class="app-container">
    <v-app>
      <v-app-bar color="primary" app>
        <v-app-bar-title>象岛农场插件 - 本地测试</v-app-bar-title>
      </v-app-bar>

      <v-main style="padding-top: 64px;">
        <v-container>
          <v-tabs v-model="activeTab" bg-color="primary" grow>
            <v-tab value="page" class="mx-2">运行状态</v-tab>
            <v-tab value="config" class="mx-2">插件配置</v-tab>
            <v-tab value="dashboard" class="mx-2">仪表盘组件</v-tab>
          </v-tabs>

          <v-window v-model="activeTab" class="mt-4">
            <v-window-item value="page">
              <h2 class="text-h5 mb-4">运行状态与操作 (Page.vue)</h2>
              <div class="component-preview">
                <page-component 
                  :api="mockPluginApiWrapper" 
                  @switch="switchToConfig" 
                  @close="handleClose('Page')"
                ></page-component>
              </div>
            </v-window-item>

            <v-window-item value="config">
              <h2 class="text-h5 mb-4">插件配置 (Config.vue)</h2>
              <div class="component-preview">
                <config-component 
                  :api="mockPluginApiWrapper"
                  :initial-config="mockDatabase.config" 
                  @config-updated-on-server="handleConfigUpdatedOnServer" 
                  @close="handleClose('Config')"
                  @switch="switchToPage"
                ></config-component>
              </div>
            </v-window-item>

            <v-window-item value="dashboard">
              <h2 class="text-h5 mb-4">仪表盘组件 (Dashboard.vue)</h2>
              <v-row align="center">
                 <v-col cols="12" md="6">
                   <v-switch v-model="dashboardWidgetConfig.attrs.border" label="显示边框" color="primary" density="compact" class="mb-n4"></v-switch>
                </v-col>
                 <v-col cols="12" md="6">
                  <v-text-field v-model="dashboardWidgetConfig.attrs.title" label="组件标题" variant="outlined" density="compact"></v-text-field>
                </v-col>
              </v-row>
              <div class="component-preview" style="height: 220px;">
                <dashboard-component 
                  :api="mockPluginApiWrapper"
                  :config="dashboardWidgetConfig" 
                  :allow-refresh="true" 
                  :refresh-interval="30000"
                ></dashboard-component>
              </div>
            </v-window-item>
          </v-window>
        </v-container>
      </v-main>

      <v-footer app color="primary" class="text-center d-flex justify-center">
        <span class="text-white">MoviePilot 象岛农场插件本地测试 ©{{ new Date().getFullYear() }}</span>
      </v-footer>
    </v-app>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="snackbar.timeout" location="top end">
      {{ snackbar.text }}
      <template v-slot:actions>
        <v-btn variant="text" @click="snackbar.show = false"> 关闭 </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import PageComponent from './components/Page.vue'
import ConfigComponent from './components/Config.vue'

const activeTab = ref('page');

const mockDatabase = reactive({
  config: {
    enable: false,
    notify: false,
    cron: '30 3 * * *',
    rows: 300,
    selected_ids: [],
    onlyonce: false,
  },
  status: {
    enabled: false,
    cron: '',
    next_run_time: 'N/A',
    last_run_results: [],
    cleaning_history: [],
  },
  installed_plugins: [],
});

// 现在返回插件ID字符串，而不是API客户端对象
// 这符合MoviePilot的实际行为
const mockPluginApiWrapper = () => {
  return "LogsClean"; // 返回插件ID字符串
};

// 为模拟环境添加全局fetch拦截器，以处理所有API请求
const setupMockFetch = () => {
  // 保存原始fetch
  const originalFetch = window.fetch;
  
  // 替换全局fetch
  window.fetch = async (url, options = {}) => {
    console.log(`[Mock Fetch] Request to: ${url}`, options);
    
    // 模拟延迟
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // 匹配插件API请求
    if (url.includes('/api/v1/plugin/LogsClean/')) {
      const endpoint = url.split('/api/v1/plugin/LogsClean/')[1];
      
      // 处理GET请求
      if (!options.method || options.method === 'GET') {
        if (endpoint === 'config') {
          return {
            ok: true,
            json: async () => JSON.parse(JSON.stringify(mockDatabase.config))
          };
        }
        if (endpoint === 'status') {
          const currentMockStatus = {
            enabled: mockDatabase.config.enable,
            cron: mockDatabase.config.cron,
            next_run_time: mockDatabase.config.enable ? new Date(Date.now() + Math.random() * 10000000).toLocaleString() : '插件已禁用',
            last_run_results: mockDatabase.status.last_run_results,
            cleaning_history: mockDatabase.status.cleaning_history,
          };
          return {
            ok: true,
            json: async () => JSON.parse(JSON.stringify(currentMockStatus))
          };
        }
        if (endpoint === 'installed_plugins') {
          return {
            ok: true,
            json: async () => JSON.parse(JSON.stringify(mockDatabase.installed_plugins))
          };
        }
      }
      
      // 处理POST请求
      else if (options.method === 'POST') {
        // 解析请求体
        let payload = {};
        if (options.body) {
          try {
            payload = JSON.parse(options.body);
          } catch (e) {
            console.error("无法解析请求体", e);
          }
        }
        
        if (endpoint === 'config') {
          Object.assign(mockDatabase.config, payload);
          showNotification('配置已在Mock API中更新', 'success');
          if (payload.onlyonce && payload.enable) {
            console.log('[Mock API] Simulating "onlyonce" task run after config save.');
            mockDatabase.status.last_run_results = [{ plugin_id: 'mock_cleaned_once', original_lines: 100, kept_lines: 0, cleaned_lines: 100 }];
            mockDatabase.status.cleaning_history.unshift({ timestamp: new Date().toLocaleString(), total_plugins_processed:1, total_lines_cleaned: 100});
            mockDatabase.config.enable = false;
            mockDatabase.config.onlyonce = false;
            console.log('[Mock API] "onlyonce" complete. Plugin disabled, onlyonce reset.');
            showNotification('"仅运行一次"任务模拟完成，插件已禁用。', 'info');
          }
          return {
            ok: true,
            json: async () => ({ message: "配置已成功保存 (模拟)", saved_config: JSON.parse(JSON.stringify(mockDatabase.config)) })
          };
        }
        
        if (endpoint === 'clean') {
          if (!mockDatabase.config.enable) {
            const errorData = { message: '插件已禁用，无法执行清理 (模拟)', error: true };
            showNotification('插件已禁用，无法执行清理 (模拟)', 'error');
            return {
              ok: false,
              json: async () => errorData
            };
          }
          
          const linesCleaned = Math.floor(Math.random() * 1000);
          const filesProcessed = mockDatabase.config.selected_ids?.length || 1;
          mockDatabase.status.last_run_results = (mockDatabase.config.selected_ids?.length ? mockDatabase.config.selected_ids : ['all_mock']).map(id => ({
            plugin_id: id, original_lines: Math.floor(Math.random() * 500) + linesCleaned,
            kept_lines: mockDatabase.config.rows, cleaned_lines: Math.floor(Math.random() * 500)
          }));
          mockDatabase.status.cleaning_history.unshift({ timestamp: new Date().toLocaleString(), total_plugins_processed: filesProcessed, total_lines_cleaned: linesCleaned });
          if (mockDatabase.status.cleaning_history.length > 10) mockDatabase.status.cleaning_history.pop();
          showNotification('清理任务已在Mock API中模拟触发', 'success');
          return {
            ok: true,
            json: async () => ({ message: '清理任务已模拟触发', result: { processed_files: filesProcessed, cleaned_lines: linesCleaned } })
          };
        }
      }
      
      // 默认404响应
      console.error(`[Mock Fetch] Endpoint not found: ${endpoint}`);
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: `Mock API endpoint not found: ${endpoint}` })
      };
    }
    
    // 对于其他请求，使用原始fetch
    return originalFetch(url, options);
  };
};

const dashboardWidgetConfig = reactive({
  id: 'logsclean_dashboard_widget',
  name: 'LogsClean Status',
  attrs: {
    title: '日志清理概览',
    border: true,
  },
});

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success',
  timeout: 3000,
});

function showNotification(text, color = 'success') {
  snackbar.text = text;
  snackbar.color = color;
  snackbar.show = true;
}

function handleConfigUpdatedOnServer(newConfigFromServer) {
  console.log('App.vue received config-updated-on-server with:', newConfigFromServer);
  if (newConfigFromServer) {
      Object.assign(mockDatabase.config, newConfigFromServer);
      showNotification('App.vue: 服务端配置已同步至本地 mockDatabase。', 'info');
  }
}

function switchToConfig() { activeTab.value = 'config'; }
function switchToPage() { activeTab.value = 'page'; }
function handleClose(componentName) {
  showNotification(`${componentName} 已关闭 (模拟)`, 'info');
}

onMounted(async () => {
  try {
    showNotification('App.vue: 正在加载初始模拟数据...', 'info');
    
    // 设置模拟fetch拦截器
    setupMockFetch();
    
    // 加载初始配置
    const configResponse = await fetch('/api/v1/plugin/LogsClean/config');
    const configData = await configResponse.json();
    if (configData) Object.assign(mockDatabase.config, configData);

    // 加载状态数据
    const statusResponse = await fetch('/api/v1/plugin/LogsClean/status');
    const statusData = await statusResponse.json();
    if (statusData) Object.assign(mockDatabase.status, statusData);
    
    // 加载插件列表
    const pluginsResponse = await fetch('/api/v1/plugin/LogsClean/installed_plugins');
    const pluginsData = await pluginsResponse.json();
    if (pluginsData) mockDatabase.installed_plugins = pluginsData;
    
    // 初始化模拟插件列表
    if (!mockDatabase.installed_plugins || mockDatabase.installed_plugins.length === 0) {
      mockDatabase.installed_plugins = [
        { title: '日志清理', value: 'logsclean' },
        { title: '豆瓣刮削器', value: 'douban' },
        { title: 'TMDB元数据', value: 'tmdb' },
        { title: '自动签到', value: 'signin' }
      ];
    }

    showNotification('App.vue: 初始模拟数据加载完毕。', 'success');
  } catch (e) {
    console.error("Error during App.vue onMounted mock data fetch:", e);
    showNotification(`App.vue 初始化模拟数据加载失败: ${e.message || '未知错误'}`, 'error');
  }
});

</script>

<style scoped>
.app-container { }
.component-preview {
  overflow: hidden;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px; 
  background-color: #f9f9f9; 
}
.v-tab {
  text-transform: none !important; 
}
</style>
