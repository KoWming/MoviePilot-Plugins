import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import archiver from 'archiver'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const outputFilePath = path.join(__dirname, 'autospeed.zip')
const output = fs.createWriteStream(outputFilePath)
const archive = archiver('zip', {
    zlib: { level: 9 } // 设定压缩级别
})

output.on('close', () => {
    console.log(`\n\x1b[32m[打包成功]\x1b[0m 已生成插件安装包: autospeed.zip`)
    console.log(`\x1b[36m文件大小:\x1b[0m ${(archive.pointer() / 1024).toFixed(2)} KB`)
    console.log(`可以直接在 MoviePilot 插件页面上传此 ZIP 文件。\n`)
})

archive.on('warning', (err) => {
    if (err.code === 'ENOENT') {
        console.warn('\x1b[33m[打包警告]\x1b[0m', err.message)
    } else {
        throw err
    }
})

archive.on('error', (err) => {
    console.error('\x1b[31m[打包失败]\x1b[0m', err)
    throw err
})

archive.pipe(output)

// 添加后端代码与依赖声明
archive.file(path.join(__dirname, '__init__.py'), { name: '__init__.py' })
archive.file(path.join(__dirname, 'requirements.txt'), { name: 'requirements.txt' })

// 添加完整 dist 目录
const distDir = path.join(__dirname, 'dist')
if (fs.existsSync(distDir)) {
    archive.directory(distDir, 'dist')
    console.log(`已将完整 dist 目录加入压缩包...`)
} else {
    console.warn('\x1b[33m[注意]\x1b[0m 找不到 dist 目录，压缩包将不包含前端产物。')
}

archive.finalize()
