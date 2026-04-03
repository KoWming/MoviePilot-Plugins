<template>
  <v-app>
    <v-app-bar color="green" app>
      <v-app-bar-title>好学农场 - 本地测试环境</v-app-bar-title>
      <v-spacer></v-spacer>
      <v-chip color="white" variant="outlined" size="small">开发模式</v-chip>
    </v-app-bar>

    <v-main>
      <v-container>
        <v-tabs v-model="tab" color="green" class="mb-4">
          <v-tab value="page">运行状态 (Page.vue)</v-tab>
          <v-tab value="config">插件配置 (Config.vue)</v-tab>
        </v-tabs>

        <v-window v-model="tab">
          <v-window-item value="page">
            <PageComponent 
              :api="apiWrapper"
              :initial-config="pluginConfig"
              @close="handleClose('Page')"
              @switch="switchTab"
            />
          </v-window-item>
          
          <v-window-item value="config">
            <ConfigComponent 
              :api="apiWrapper"
              :initial-config="pluginConfig"
              @close="handleClose('Config')"
              @switch="switchTab"
            />
          </v-window-item>
        </v-window>
      </v-container>
    </v-main>

    <!-- 全局通知 -->
    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </v-app>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import PageComponent from './components/Page.vue';
import ConfigComponent from './components/Config.vue';
import { createRequest } from './utils/request';

// 当前激活的标签页
const tab = ref('page');

// 插件配置
const pluginConfig = reactive({
  enabled: false,
  notify: true,
  cron: '',
  cookie: ''
});

// 全局通知
const snackbar = reactive({
  show: false,
  message: '',
  color: 'success'
});

// 创建 API 包装器 - 模拟 MoviePilot 主应用的 API 调用
// 在开发模式下使用本地或代理的后端服务
const baseURL = 'http://localhost:3000'; // 根据实际后端服务地址调整
const request = createRequest(baseURL);

// API 包装器 - 统一封装请求方法
const apiWrapper = {
  get: async (url, config) => {
    try {
      const res = await request.get(url, config);
      return res;
    } catch (error) {
      console.error('GET请求失败:', url, error);
      showNotification(`请求失败: ${error.message}`, 'error');
      throw error;
    }
  },
  post: async (url, data, config) => {
    try {
      const res = await request.post(url, data, config);
      return res;
    } catch (error) {
      console.error('POST请求失败:', url, error);
      showNotification(`请求失败: ${error.message}`, 'error');
      throw error;
    }
  },
  put: async (url, data, config) => {
    try {
      const res = await request.put(url, data, config);
      return res;
    } catch (error) {
      console.error('PUT请求失败:', url, error);
      showNotification(`请求失败: ${error.message}`, 'error');
      throw error;
    }
  },
  delete: async (url, config) => {
    try {
      const res = await request.delete(url, config);
      return res;
    } catch (error) {
      console.error('DELETE请求失败:', url, error);
      showNotification(`请求失败: ${error.message}`, 'error');
      throw error;
    }
  }
};

// 显示通知
const showNotification = (message, color = 'success') => {
  snackbar.message = message;
  snackbar.color = color;
  snackbar.show = true;
};

// 加载插件配置
const loadPluginConfig = async () => {
  try {
    const url = '/plugin/magicfram/config';
    const res = await apiWrapper.get(url);
    
    if (res) {
      pluginConfig.enabled = res.enabled || false;
      pluginConfig.notify = res.notify !== false;
      pluginConfig.cron = res.cron || '';
      pluginConfig.cookie = res.cookie || '';
      
      console.log('插件配置已加载:', pluginConfig);
    }
  } catch (error) {
    console.error('加载插件配置失败:', error);
    // 开发环境下失败不影响使用
  }
};

// 切换标签页
const switchTab = (tabName) => {
  tab.value = tabName;
  showNotification(`切换到${tabName === 'page' ? '运行状态' : '插件配置'}`, 'info');
};

// 处理关闭事件
const handleClose = (componentName) => {
  showNotification(`${componentName} 组件关闭 (开发模式模拟)`, 'info');
  console.log(`${componentName} 组件触发关闭事件`);
};

// 组件挂载时加载配置
onMounted(async () => {
  console.log('开发环境初始化...');
  console.log('API 基础地址:', baseURL);
  
  // 尝试加载配置，失败不影响使用
  await loadPluginConfig();
  
  showNotification('开发环境已就绪', 'success');
});
</script>

<style scoped>
/* 可以添加一些开发环境特有的样式 */
.v-app-bar {
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
</style>
