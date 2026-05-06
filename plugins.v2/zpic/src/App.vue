<template>
  <v-app>
    <v-main class="zpic-dev-shell">
      <div class="zpic-dev-shell__inner">
        <h1>Vue-Zpic图库</h1>
        <p>该前端用于 MoviePilot 插件远程组件开发。请在 MoviePilot 中加载插件进行真实联调。</p>
      </div>
    </v-main>
  </v-app>
</template>

<style scoped>
.zpic-dev-shell {
  min-height: 100vh;
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
  color: #e5e7eb;
}

.zpic-dev-shell__inner {
  max-width: 720px;
  margin: 0 auto;
  padding: 72px 24px;
}

h1 {
  margin-bottom: 16px;
  font-size: 32px;
}

p {
  line-height: 1.7;
  color: #cbd5e1;
}
</style>
