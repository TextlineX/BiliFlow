# BiliFlow

BiliFlow 用于在 GitHub Actions 的 Ubuntu 环境中自动完成以下流程：

- 定时检测 B 站直播状态
- 开播后自动录制直播视频
- 同步抓取原始弹幕并转换为多种格式
- 将视频上传到 YouTube
- 将弹幕文件发布到 GitHub Release
- 在 YouTube 简介中附带弹幕下载链接
- 生成适合后续搜索的轻量索引

当前仓库已进入第一版实现阶段：包含检测工作流、录制工作流和核心脚本骨架。

## 目标

- 视频发布到 YouTube
- 弹幕独立保存，不依赖网盘
- 兼容 `danmaku-anywhere` 的 `XML` 导入
- 保留可搜索的原始弹幕日志
- 输出 `search-index.json` 作为搜索第一版基础
- 兼容 GitHub Actions 6 小时运行上限，支持接力录制

## 产物设计

每段录制结束后，预期产出以下文件：

- `video.mp4`：直播视频文件
- `danmaku.xml`：供 `danmaku-anywhere` 导入
- `danmaku.ass`：供本地播放器观看飘屏弹幕
- `danmaku.jsonl`：原始弹幕事件日志
- `danmaku.csv`：便于搜索和导出
- `danmaku.srt`：可选，用于 YouTube 普通字幕轨
- `search-index.json`：轻量搜索索引
- `summary.json`：单段统计摘要

## 模块划分

- `Trigger`：定时触发与开播检测
- `Recorder`：调用录制引擎抓流
- `Danmaku`：抓取原始弹幕并生成多格式输出
- `Guard`：处理 6 小时超时与接力重启
- `Release`：上传弹幕文件到 GitHub Release
- `YouTube`：上传视频并写入弹幕下载链接
- `Search`：生成第一版可直接消费的静态索引

## 目录规划

```text
.github/workflows/
docs/
scripts/
```

## 当前工作流

- `main.yml`：定时检测直播间状态，只负责判定和派发
- `record.yml`：执行录制、弹幕抓取、格式转换、Release 发布、YouTube 上传、超时接力

详细设计见 `docs/architecture.md:1`。  
已确认的默认决策见 `docs/confirmations.md:1`。
双仓库与测试 fork 方案见 `docs/repository-strategy.md:1`。
