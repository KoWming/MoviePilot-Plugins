<template>
  <v-app>
    <v-main>
      <v-container fluid>
        <v-tabs v-model="tab" color="green" density="compact" class="mb-3">
          <v-tab value="page">运行状态</v-tab>
          <v-tab value="config">插件配置</v-tab>
        </v-tabs>
        <v-window v-model="tab">
          <v-window-item value="page">
            <Page :api="api" :initial-config="config" @switch="tab = $event" @close="closePlugin" />
          </v-window-item>
          <v-window-item value="config">
            <Config :api="api" :initial-config="config" @switch="tab = $event" @close="closePlugin" />
          </v-window-item>
        </v-window>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { reactive, ref } from 'vue'
import Page from './components/Page.vue'
import Config from './components/Config.vue'

const tab = ref('page')
const config = reactive({ enabled: false, notify: true, cron: '5 */4 * * *', seed_id: '1' })
const api = {
  get: async (url) => (await fetch(url)).json(),
  post: async (url, data = {}) => (await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })).json()
}

function closePlugin() {
  window.parent?.postMessage?.({ action: 'close' }, '*')
  window.close?.()
}
</script>
