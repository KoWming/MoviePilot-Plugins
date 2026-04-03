import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'

export default defineConfig({
    plugins: [
        vue(),
        federation({
            name: 'medalwallpro',
            filename: 'remoteEntry.js',
            exposes: {
                './Page': './src/components/Page.vue',
                './Config': './src/components/Config.vue',
            },
            shared: {
                vue: {
                    requiredVersion: false,
                    generate: false,
                },
                vuetify: {
                    requiredVersion: false,
                    generate: false,
                    singleton: true,
                } as any,
                'vuetify/styles': {
                    requiredVersion: false,
                    generate: false,
                    singleton: true,
                } as any,
            },
            format: 'esm'
        } as any)
    ],
    build: {
        target: 'esnext',   // 必须设置为esnext以支持顶层await
        minify: false,      // 开发阶段建议关闭混淆
        cssCodeSplit: false, // Module Federation 需要关闭 CSS 代码分离
    },
    publicDir: 'public', // Vite 会将 public 目录的文件复制到 dist 根目录
    css: {
        preprocessorOptions: {
            scss: {
                additionalData: '/* 覆盖vuetify样式 */',
            }
        },
        postcss: {
            plugins: [
                {
                    postcssPlugin: 'internal:charset-removal',
                    AtRule: {
                        charset: (atRule) => {
                            if (atRule.name === 'charset') {
                                atRule.remove();
                            }
                        }
                    }
                },
                {
                    postcssPlugin: 'vuetify-filter',
                    Root(root) {
                        // 过滤掉所有vuetify相关的CSS
                        root.walkRules(rule => {
                            if (rule.selector && (
                                rule.selector.includes('.v-') ||
                                rule.selector.includes('.mdi-'))) {
                                rule.remove();
                            }
                        });
                    }
                }
            ]
        }
    },
    server: {
        port: 5002,   // 使用不同于主应用的端口，magicfram 用了 5001，这里用 5002
        cors: true,   // 启用CORS
        origin: 'http://localhost:5002'
    },
})
