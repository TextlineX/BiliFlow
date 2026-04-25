# 项目架构设计

## 1. 项目目标

本项目的目标不是只做“自动录播”，而是做一条完整的自动化链路：

- 检测 B 站直播间是否开播
- 录制视频并抓取原始弹幕
- 录制结束后自动生成适配不同用途的弹幕格式
- 将视频上传到 YouTube
- 将弹幕文件发布到 GitHub Release
- 在 YouTube 简介中写入该场次对应的弹幕下载链接

## 2. 关键约束

### 2.1 GitHub Actions 运行限制

- 运行环境为 Ubuntu
- 单次 job 最长运行约 6 小时
- 录制任务必须在 6 小时前主动收尾
- 收尾后需要自动触发下一次 workflow，形成接力录制

### 2.2 弹幕展示与搜索是两条链路

- `ASS` 适合观看，不适合做精准搜索
- `XML` 适合导入 `danmaku-anywhere`
- `JSONL/CSV` 适合做按昵称、UID、关键词搜索
- `SRT` 仅适合 YouTube 字幕轨，不是飘屏弹幕

因此，项目必须优先保存原始弹幕日志，再由原始日志派生其他格式。

### 2.3 YouTube 不是弹幕平台

- YouTube 不提供 B 站式原生弹幕层
- 视频简介里只能提供弹幕文件下载链接
- 如果需要在 YouTube 页面叠加弹幕，需要依赖浏览器扩展 `danmaku-anywhere`

## 3. 数据流

### 3.1 主流程

1. 定时任务触发 workflow
2. `main.yml` 调用 `check_live` 查询直播间状态
3. 若未开播则结束
4. 若已开播且当前没有录制任务在运行，则派发 `record.yml`
5. `record.yml` 录制期间同步抓取原始弹幕
6. 录制结束后转换弹幕格式
7. 发布 GitHub Release 资源
8. 上传视频到 YouTube
9. 将弹幕下载链接写入 YouTube 视频简介
10. 若达到接力条件则再次派发 `record.yml`

### 3.2 产物流向

- `mp4` -> YouTube
- `xml` -> GitHub Release -> `danmaku-anywhere`
- `ass` -> GitHub Release -> 本地播放器
- `jsonl/csv` -> GitHub Release -> 后续搜索系统
- `srt` -> 可选上传到 YouTube 字幕轨

## 4. 模块设计

## 4.1 Trigger

职责：

- 通过 `schedule` 周期触发检测工作流
- 支持 `workflow_dispatch` 手动触发检测工作流
- 调用 B 站直播间接口判断 `live_status`
- 避免在已有录制 workflow 运行时重复派发

输入：

- `ROOM_ID`

输出：

- `is_live=true/false`
- 当前直播标题
- 当前房间真实 room id

## 4.2 Recorder

职责：

- 调用录制工具抓取直播流
- 使用 Cookie 获取高画质权限
- 负责将视频输出到工作目录

建议输出：

- `output/video.mp4`

## 4.3 Danmaku

职责：

- 在录制开始时同步连接弹幕源
- 将每条弹幕以结构化格式写入 `jsonl`
- 在录制结束后统一转换为 `xml`、`ass`、`csv`、`srt`

建议原始字段：

- `timestamp`
- `offset_ms`
- `user_name`
- `user_id`
- `message`
- `color`
- `mode`
- `font_size`

## 4.4 Guard

职责：

- 设定单次录制最长时长，例如 5.5 小时
- 超时后优雅停止录制与弹幕抓取
- 保证文件先落盘、再进入上传阶段
- 判断直播是否仍在继续，必要时触发下一棒

## 4.5 Release

职责：

- 为每段录制创建一个唯一标识的 Release
- 上传 `xml`、`ass`、`jsonl`、`csv`、`srt`
- 为外部播放器与搜索页提供稳定下载链接

Release 更适合弹幕文件的原因：

- 公开访问方便
- 适合长期保留和分享
- 比 workflow artifact 更适合当成稳定下载地址

## 4.6 YouTube

职责：

- 上传 `mp4`
- 生成标题、简介、标签
- 将对应 Release 的弹幕下载链接写入简介
- 可选上传 `srt` 字幕

依赖：

- OAuth 2.0 refresh token
- YouTube Data API 配额

## 4.7 Search

职责：

- 从原始弹幕日志中生成 `search-index.json`
- 为后续 GitHub Pages 搜索页提供静态输入
- 让第一版先做到“可快速搜索、可直接跳时间点”

第一版推荐形式：

- 原始数据：`jsonl`
- 人类可读导出：`csv`
- 轻量检索输入：`search-index.json`

## 5. 仓库目录建议

```text
.github/
  workflows/
    main.yml
    record.yml
docs/
  architecture.md
  confirmations.md
scripts/
  bootstrap_biliup.sh
  check_live.sh
  check_recorder_idle.sh
  record.sh
  capture_danmaku.py
  convert_danmaku.py
  publish_release.sh
  upload_youtube.py
  handoff.sh
```

## 6. 开发顺序建议

第一阶段：

- 写 `main.yml` 检测与派发流程
- 写 `record.yml` 执行主链路
- 写 `check_live.sh`
- 写 `record.sh`
- 明确产物目录结构

第二阶段：

- 写 `capture_danmaku.py`
- 写 `convert_danmaku.py`
- 跑通 `jsonl -> xml/ass/csv/search-index`

第三阶段：

- 写 `publish_release.sh`
- 写 `upload_youtube.py`
- 将 Release 链接注入 YouTube 简介

第四阶段：

- 补 `handoff.sh`
- 实现接力录制
- 处理失败重试与幂等
