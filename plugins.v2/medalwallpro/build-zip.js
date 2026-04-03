import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import archiver from 'archiver'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const initFilePath = path.join(__dirname, '__init__.py')

function getPluginZipBaseName() {
    if (!fs.existsSync(initFilePath)) {
        throw new Error('缺少必需文件: __init__.py')
    }

    const initContent = fs.readFileSync(initFilePath, 'utf-8')
    const pluginClassMatch = initContent.match(/^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(_PluginBase\)\s*:/m)

    if (!pluginClassMatch) {
        throw new Error('无法从 __init__.py 中解析 _PluginBase 子类名称')
    }

    return pluginClassMatch[1].toLowerCase()
}

const pluginZipBaseName = getPluginZipBaseName()
const zipFileName = `${pluginZipBaseName}.zip`

const outputFilePath = path.join(__dirname, zipFileName)
const output = fs.createWriteStream(outputFilePath)
const archive = archiver('zip', {
    zlib: { level: 9 } // 设定压缩级别
})

output.on('close', () => {
    console.log(`\n\x1b[32m[打包成功]\x1b[0m 已生成插件安装包: ${zipFileName}`)
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

function addRequiredFile(fileName) {
    const filePath = path.join(__dirname, fileName)
    if (!fs.existsSync(filePath)) {
        throw new Error(`缺少必需文件: ${fileName}`)
    }

    archive.file(filePath, { name: fileName })
}

function addOptionalFile(fileName) {
    const filePath = path.join(__dirname, fileName)
    if (fs.existsSync(filePath)) {
        archive.file(filePath, { name: fileName })
        return true
    }

    console.warn(`\x1b[33m[打包警告]\x1b[0m 跳过缺失文件: ${fileName}`)
    return false
}

// 添加后端代码与依赖声明
addRequiredFile('__init__.py')
addOptionalFile('requirements.txt')

// 添加后端子目录
const handlersDir = path.join(__dirname, 'handlers')
if (fs.existsSync(handlersDir)) {
    archive.directory(handlersDir, 'handlers')
    console.log('已将 handlers 目录加入压缩包...')
} else {
    console.warn('\x1b[33m[打包警告]\x1b[0m 找不到 handlers 目录，压缩包将不包含处理器代码。')
}

// 添加完整 dist 目录
const distDir = path.join(__dirname, 'dist')
if (fs.existsSync(distDir)) {
    archive.directory(distDir, 'dist')
    console.log(`已将完整 dist 目录加入压缩包...`)
} else {
    console.warn('\x1b[33m[注意]\x1b[0m 找不到 dist 目录，压缩包将不包含前端产物。')
}

archive.finalize()
