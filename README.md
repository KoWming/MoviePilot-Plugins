# 🎬 MoviePilot-Plugins

MoviePilot第三方插件库，提供了一系列实用的插件来增强MoviePilot的功能。

> ⚠️ 注意：本插件库为个人维护，代码结构参考了其他开源项目。推荐优先使用[官方插件库](https://github.com/jxxghp/MoviePilot-Plugins)。

## 📦 插件列表
- [外部消息转发 (MsgNotify)（v1.4.1）](#1--外部消息转发-msgnotify)
- [Lucky助手 (LuckyHelper)（v1.2.6）](#2--lucky助手-luckyhelper)
- [群聊区 (GroupChatZone)（v2.1.4）](#3--群聊区-groupchatzone)
- [朱雀助手 (ZhuqueHelper)（v1.3.2）](#4--朱雀助手-zhuquehelper)
- [Cloudflare订阅 (CloudflaresSubscribe)（v1.0.5）](#5-%EF%B8%8F-cloudflare订阅-cloudflaressubscribe)
- [本地插件安装 (LocalPluginInstall)（v1.2）](#6--本地插件安装-localplugininstall)
- [象岛传说竞技场 (VicomoVS)（v1.2.4）](#7--象岛传说竞技场-vicomovs)
- [织梦勋章套装奖励 (ZmedalRwd)（v1.2.1）](#8--织梦勋章套装奖励-zmedalrwd)
- [勋章墙 (MedalWall)（v1.1）](#9--勋章墙-medalwall)
- [NAT类型检测 (NATdetect)（v1.0）](#10--nat类型检测-natdetect)
- [Vue-象岛农场 (VicomoFarm)（v1.2.5）](#11--vue-象岛农场-vicomofarm)
- [资源探索集合 (ExploreServices)（v1.0.2）](#12--资源探索集合-exploreservices)

### 1. 📢 外部消息转发 (MsgNotify)
- 版本：v1.4.1
- 功能：接收外部应用自定义消息并推送。
- 标签：消息通知
- 特点：
  - 🔄 支持POST/GET两种API接口方式
  - 🔐 内置API令牌校验机制
  - 📝 支持自定义消息格式
  - 🔌 适配多种外部应用（群晖、QD框架、Lucky等）
- 更新说明：
  - v1.4.1: 移除主程序消息模块挟持，避免消息重复发送问题。
  - v1.3.9: 修复已知问题，优化代码结构。
  - v1.3.8: 修复通知类型识别、消息发送异常问题。
  - v1.3.6: 简化了自定义通知样式配置方法，Card样式支持无图推送。
  - v1.3.5: 支持配置多个URL随机选择，添加style字段控制通知样式。
  - v1.3.4: 新增卡片通知样式自定义图片。
  - v1.3.3: 新增卡片通知样式，优化设置界面UI。
  - v1.3.2: 添加使用示例：README.md
  - v1.3.1: 增加GET_API请求接口，添加API令牌校验以及相关提示说明。
  - v1.3: 修复显示异常。
  - v1.2: 更新主页链接适配UI。
  - v1.1: 更新描述文档。
  - v1.0: 接收外部应用自定义消息并推送。

### 2. 🍀 Lucky助手 (LuckyHelper)
- 版本：v1.2.6
- 功能：定时备份Lucky配置文件
- 标签：备份
- 特点：
  - ⏰ 支持定时自动备份
  - 📁 智能备份文件管理
  - 📨 备份状态实时通知
  - ⚙️ 支持自定义备份周期
  - 💾 新增本地备份开关，支持WebDAV备份
- 更新说明：
  - v1.2.6: 移除开关前面的图标，优化界面显示，更新使用说明。
  - v1.2.5: 修复移动端UI显示异常。
  - v1.2.4: 新增本地备份开关，新增WebDAV备份设置，优化备份通知消息输出格式。(感谢M.Jinxi大佬提供WebDAV备份功能和美化方案)
  - v1.2.3: 新增定时框根据版本动态切换(V2版本使用VCronField组件,V1版本使用VTextField组件)。
  - v1.2.2: 调整消息类型为插件。
  - v1.2.1: 优化消息推送结构。
  - v1.2: 修复备份删除逻辑。
  - v1.1: 适配VCronField、修复显示异常。
  - v1.0: 初始版本。

### 3. 💬 群聊区 (GroupChatZone)
- 版本：v2.1.4
- 功能：执行站点喊话、获取反馈、定时任务
- 标签：站点
- 特点：
  - 🌐 支持多站点喊话管理
  - 🤖 智能识别特殊喊话内容
  - 📊 自动获取站点反馈
  - ⏱️ 动态注册定时任务
  - ⏭️ 支持消息跳过机制
- 更新说明：
  - v2.1.4: 优化站点选择
  - v2.1.3: 新增青蛙每日福利购买，更新插件使用说明添加【特别说明】
  - v2.1.2: 新增独立织梦喊话功能添加对应说明，优化织梦获取反馈方法、优化配置UI新增定时框根据版本动态切换
  - v2.1.1: 修复未选择Zm站点导致频繁注册定时器的问题
  - v2.1.0: 优化Zm定时器注册方法，Zm站点消息发送使用独立线程、单独推送反馈信息。移除【任务系统】功能(已独立为插件)，优化UI界面
  - v2.0.3: 修复求vip、求彩虹id小写导致无法跳过消息
  - v2.0.2: 添加Zm站点消息跳过后输出下次执行时间
  - v2.0.1: 优化大青龙跳过求VIP判断逻辑，统一上传量、下载量计算单位
  - v2.0: 模块化、界面美化，优化喊话内容识别

### 4. 🦅 朱雀助手 (ZhuqueHelper)
- 版本：v1.3.2
- 功能：技能释放、一键升级、获取执行记录
- 标签：站点
- 特点：
  - ⚡ 支持技能自动释放
  - ⬆️ 一键角色升级功能
  - 📈 收益统计图表展示
  - ⏲️ 支持释放时间微调
  - 📱 移动端优化显示
  - 📋 完整的执行记录追踪
- 更新说明：
  - v1.3.2: 新增使用代理开关，新增使用站点Cookie开关，优化推送消息输出格式，优化配置UI新增定时框根据版本动态切换
  - v1.3.1: 修复用户信息获取失败问题
  - v1.3.0: 简化移动端图表显示
  - v1.2.9: 修复释放收益统计图表显示异常
  - v1.2.8: 新增下次释放微调时间最大300秒，新增平滑曲线统计图表

### 5. ☁️ Cloudflare订阅 (CloudflaresSubscribe)
- 版本：v1.0.5
- 功能：自动订阅Cloudflare免费DNS服务
- 标签：网络
- 特点：
  - 📦 支持批量订阅管理
  - 🔄 自动DNS服务更新
  - 🔁 订阅失败自动重试
  - ⏰ 定时任务自动执行
  - 🌐 支持自定义Hosts配置
- 更新说明：
  - v1.0.5: 新增使用代理开关，新增定时框根据版本动态切换
  - v1.0.4: 调整消息类型为插件
  - v1.0.3: 优化空值判断，添加订阅失败重试机制
  - v1.0.2: 优化立即运行一次定时器注册逻辑

### 6. 📥 本地插件安装 (LocalPluginInstall)
- 版本：v1.2
- 功能：上传本地ZIP插件包进行安装
- 标签：工具
- 特点：
  - 📦 支持本地ZIP包安装
  - 🖥️ 简单的安装界面
  - 🚀 快速插件部署
  - 🛠️ 支持自定义插件包
  - 🤖 智能依赖处理，自动检测并安装插件依赖
- 更新说明：
  - v1.2: 新增智能依赖处理功能：自动检测并安装插件依赖，优化插件导入验证逻辑，改进错误提示信息
  - v1.1: 优化插件性能，重构插件安装加载逻辑确保插件安装正确显示。新增插件安装前备份旧插件设置
  - v1.0: 初始版本

### 7. 🎮 象岛传说竞技场 (VicomoVS)
- 版本：v1.2.4
- 功能：象岛传说竞技场，对战boss
- 标签：站点
- 特点：
  - 🎯 对战次数统计
  - 📜 历史记录追踪
  - 📤 优化的消息输出
  - 🤖 自动对战功能
  - 🔄 失败重试机制
  - ⚙️ 代理启用开关
- 更新说明：
  - v1.2.4: 修复对战失败问题，优化失败重试
  - v1.2.3: 新增使用站点Cookie开关，新增对战失败达重试上限后执行定时重试失败场次
  - v1.2.2: 优化对战逻辑
  - v1.2.1: 优化对战次数判断，修复历史记录显示
  - v1.2: 新增代理启用开关，新增失败重试机制，优化场次计数逻辑，移除数据页面图表
  - v1.1: 修复历史记录页面显示，新增角色池判断、对战次数判断，优化消息输出格式
  - v1.0: 初始版本

### 8. 🏆 织梦勋章套装奖励 (ZmedalRwd)
- 版本：v1.2.1
- 功能：领取勋章套装奖励
- 标签：站点
- 特点：
  - 🎖️ 支持勋章系列开关
  - ⏰ 动态定时器组件
  - 📱 适配V1/V2版本
- 更新说明：
  - v1.2.1: 修复定时器注册缺少kwargs参数可能导致注册错误的问题
  - v1.2: 新增使用代理开关，新增使用站点Cookie开关
  - v1.1: 新增勋章系列开关，新增定时框根据版本动态切换
  - v1.0: 初始版本

### 9. 🏅 勋章墙 (MedalWall)
- 版本：v1.1
- 功能：站点勋章购买提醒、统计、展示
- 标签：站点
- 特点：
  - 🔔 勋章购买提醒
  - 📊 勋章统计展示
  - ⏰ 定时任务自动执行
  - 🔄 支持多站点管理
- 更新说明：
  - v1.1: 新增适配多个站点，优化消息推送结构

### 10. 🌐 NAT类型检测 (NATdetect)
- 版本：v1.0
- 功能：使用Lucky服务检测NAT类型
- 标签：站点
- 特点：
  - 🌍 支持多服务器检测
  - 🔑 API令牌校验
  - 📝 实时日志输出
  - ⚡ 一键检测NAT类型
- 更新说明：
  - v1.0: 初始版本

### 11. 🌾 Vue-象岛农场 (VicomoFarm)
- 版本：v1.2.5
- 功能：监听象岛农场相关信息，我在PT学卖菜。
- 标签：站点
- 特点：
  - 🌱 农场信息监控
  - 📊 数据统计分析
  - ⏰ 定时任务执行
  - 🔄 自动操作功能
- 更新说明：
  - v1.2.5: 新增出售盈利百分比阈值，优化页面UI显示。
  - v1.2.4: 修复进货、出售浮点计算问题。
  - v1.2.3: 修复定时任务重复执行问题。
  - v1.2.2: 优化进货、出售功能，增加空值检查。
  - v1.2.1: 新增自动进货、出售功能(待测试)、优化页面UI显示。
  - v1.2: 修复说明获取显示，优化进货、出售弹窗显示。
  - v1.1: 修复农场信息数据显示异常、修复了数据刷新问题、修复下次执行时间显示调度器未运行，优化页面显示、弹窗显示。
  - v1.0: 初始版本。

### 12. 🔍 资源探索集合 (ExploreServices)
- 版本：v1.0.2
- 功能：统一管理和配置所有探索数据源插件。
- 标签：探索
- 特点：
  - 📺 支持多个视频平台
  - 🔄 自动更新内容
  - 📱 移动端优化显示
  - 🎯 精准资源推荐
- 更新说明：
  - v1.0.2: 模块化处理，适配新插件加载机制。
  - v1.0.1: 修复咪咕视频封面图片加载错误。
  - v1.0: 初始版本。

## 📖 使用说明

1. 在MoviePilot中安装插件
2. 根据插件说明配置相关参数
3. 启用插件并设置定时任务（如需要）

## ⚠️ 注意事项

1. 本插件库中的插件均为个人维护，使用前请仔细阅读说明
2. 部分插件需要特定权限或配置才能正常使用
3. 如遇到问题，请先查看插件说明或提交Issue
4. 建议定期更新插件以获取最新功能和修复

## 🤝 贡献

欢迎提交Issue和Pull Request来帮助改进插件。

## 📄 许可证

本项目采用MIT许可证，详见[LICENSE](LICENSE)文件。