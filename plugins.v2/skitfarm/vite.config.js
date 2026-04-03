import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'
import fs from 'fs'
import path from 'path'

// 自定义插件：构建后移动图片到 dist/public
const movePublicAssetsPlugin = () => {
    return {
        name: 'move-public-assets',
        closeBundle() {
            const distDir = path.resolve(__dirname, 'dist')
            const targetDir = path.resolve(distDir, 'public')

            if (!fs.existsSync(targetDir)) {
                fs.mkdirSync(targetDir, { recursive: true })
            }

            // 需要移动的文件列表 (也可以扫描目录)
            const files = ['小麦.webp', '玉米.webp', '土豆.webp', '花生.webp', '鸡.webp', '猪.webp', '牛.webp', '羊.webp']

            files.forEach(file => {
                const srcPath = path.resolve(distDir, file)
                const destPath = path.resolve(targetDir, file)

                if (fs.existsSync(srcPath)) {
                    fs.renameSync(srcPath, destPath)
                    console.log(`Moved ${file} to dist/public/`)
                }
            })
        }
    }
}

export default defineConfig({
    plugins: [
        vue(),
        movePublicAssetsPlugin(),
        federation({
            name: 'SkitFarm',
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
                },
                'vuetify/styles': {
                    requiredVersion: false,
                    generate: false,
                    singleton: true,
                },
            },
            format: 'esm'
        })
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
        port: 5001,   // 使用不同于主应用的端口
        cors: true,   // 启用CORS
        origin: 'http://localhost:5001'
    },
})
