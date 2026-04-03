<script setup lang="ts">
import Page from './components/Page.vue'
import Config from './components/Config.vue'
import { ref } from 'vue'

const currentView = ref('page')

// Mock API for local development
const mockApi = {
  get: async (url: string) => {
    console.log('GET', url)
    if (url.includes('medals')) {
        return [
            {
                name: '测试勋章1',
                site: '测试站点',
                price: '1000',
                imageSmall: 'https://via.placeholder.com/150',
                description: '这是一个测试勋章',
                saleBeginTime: '2023-01-01',
                saleEndTime: '2023-12-31',
                purchase_status: '购买'
            }
        ]
    }
    if (url.includes('sites')) {
        return [
            { title: '测试站点1', value: 'site1' },
            { title: '测试站点2', value: 'site2' }
        ]
    }
    return {}
  },
  post: async (url: string, data: any) => {
    console.log('POST', url, data)
    return { success: true }
  }
}

function handleSwitch() {
  currentView.value = currentView.value === 'page' ? 'config' : 'page'
}

function handleClose() {
  console.log('Close requested')
}
</script>

<template>
  <v-app>
    <v-main>
      <v-container>
        <Page 
            v-if="currentView === 'page'" 
            :api="mockApi"
            @switch="handleSwitch"
            @close="handleClose"
        />
        <Config 
            v-else 
            :api="mockApi"
            @switch="handleSwitch"
            @close="handleClose"
        />
      </v-container>
    </v-main>
  </v-app>
</template>
