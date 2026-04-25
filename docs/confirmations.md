# 待确认事项

以下事项里，核心默认值已经确认，其余可在后续迭代时再细化。

## 1. 直播间信息

- 目标直播间 `ROOM_ID`
- 是否只录单个房间
- 是否后续支持多个房间

## 2. 视频发布策略

- YouTube 上传后默认可见性：`public`
- 单场直播是否拆成多段视频
- YouTube 标题格式是否要固定模板

## 3. 弹幕发布策略

- Release 是每场一个，还是每天一个
- Release tag 命名规则
- 是否始终上传 `xml + ass + jsonl + csv`
- 是否需要额外生成 `srt`

## 4. 搜索能力范围

- 第一版优先生成 `search-index.json`
- 后续可补 GitHub Pages 搜索页面

## 5. 录制策略

- 计划使用的录制引擎版本
- 单段最大录制时长超出后自动接力
- 断流后是否自动重试

## 6. 认证与 Secrets

预计至少需要以下 secrets：

- `ROOM_ID`
- `BILI_SESSDATA`
- `BILI_COOKIE` 或拆分 Cookie 字段
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `GITHUB_TOKEN`

## 7. 当前默认假设

在你没有进一步指定前，我先按以下默认值推进：

- 单直播间
- 每场录制按时间切段
- 视频上传到 YouTube `public`
- 弹幕上传到 GitHub Release
- 同时保留 `xml`、`ass`、`jsonl`、`csv`
- `srt` 作为可选导出
- 生成 `search-index.json`
- 后续再补 GitHub Pages 搜索页
