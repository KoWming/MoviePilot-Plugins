import { createApp } from 'vue'
import { createVuetify } from 'vuetify'
import App from './App.vue'

const vuetify = createVuetify()
const app = createApp(App)
app.use(vuetify)
app.mount('#app')

