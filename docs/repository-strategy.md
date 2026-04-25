# 双仓库与测试 Fork 方案

本文用于约定后续的仓库拆分方式：保留一个**主仓库**跑正式流程，另准备一个**测试仓库**专门验证工作流、Secrets、录制链路和发布链路。

## 1. 目标

拆成两套仓库的主要目的：

- 主仓库保持稳定，只承载正式录制与正式发布
- 测试仓库先验证 workflow、脚本和 Secrets 配置
- 避免调试阶段误发正式 Release 或误传 YouTube
- 让后续改动可以先在测试仓库跑通，再回到主仓库

## 2. 推荐结构

推荐保留以下角色：

### 2.1 主仓库

建议用途：

- 作为正式 upstream
- 保存正式 Secrets 与 Variables
- 运行定时检测与正式录制
- 发布正式 GitHub Release
- 上传正式 YouTube 视频

建议命名示例：

- `BiliFlow`
- `biliflow-main`

### 2.2 测试仓库

建议用途：

- 作为主仓库的测试副本
- 优先验证 workflow_dispatch 手动链路
- 验证 Secrets 是否齐全
- 验证录制、弹幕转换、Release、接力逻辑

建议命名示例：

- `BiliFlow-test`
- `biliflow-staging`

## 3. 推荐创建方式

优先推荐两种方式，二选一即可。

### 方案 A：测试仓库保留 fork 关系

适合场景：

- 你希望测试仓库页面上直接保留 `forked from ...`
- 你希望后续从测试仓库向主仓库提 PR 更直观

建议做法：

1. 先确定哪一个仓库是正式 upstream
2. 再创建一个测试用 fork
3. 所有实验性改动先在测试仓库完成
4. 验证通过后再回主仓库合并

适用提醒：

- fork 是独立仓库，会有自己的 Actions、Issues、Releases、Secrets 配置
- 测试仓库里的 Secrets 需要单独配置，不会自动从主仓库继承
- 如果测试仓库以后不想继续保持 fork 关系，可以再做 “detach fork / 转独立仓库”

### 方案 B：直接新建普通测试仓库

适合场景：

- 你只需要一份长期可控的测试环境
- 你不强求页面上保留 fork 关系
- 你希望后续自由调整测试仓库，而不受 fork 网络约束

建议做法：

1. 新建 `BiliFlow-test`
2. 从主仓库推送一份当前代码过去
3. 测试仓库单独维护测试配置
4. 需要同步时，从主仓库拉最新代码

这个方案更适合长期把测试仓库当 “staging” 使用。

## 4. 主仓库与测试仓库的职责边界

### 主仓库建议开启

- 定时检测
- 正式录制
- 正式 Release
- 正式 YouTube 上传
- 正式接力录制

### 测试仓库建议默认关闭或弱化

- 定时检测
- 正式 YouTube 上传
- 正式 Release 命名空间
- 长时间录制

建议测试仓库优先使用：

- `workflow_dispatch`
- 短时录制
- 测试房间号
- 非正式标题/标签
- 独立 Release tag 前缀

## 5. 配置建议

### 5.1 主仓库 Variables / Secrets

主仓库建议配置完整生产参数：

- `ROOM_ID`
- `MAX_RECORD_SECONDS`
- `BILIUP_DOWNLOAD_URL`（可选）
- `YOUTUBE_CATEGORY_ID`
- `YOUTUBE_CHANNEL_TAGS`
- `BILIUP_USER_COOKIE_JSON`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

### 5.2 测试仓库 Variables / Secrets

测试仓库建议按“最小可运行”原则配置：

- 可以先只配 `ROOM_ID`
- 若只测检测与弹幕转换，可暂时不配 YouTube Secrets
- 若只测本地或短时录制，可把 `MAX_RECORD_SECONDS` 调小
- 若只想验证录制，不想真的上传 YouTube，**不要配置**
  - `YOUTUBE_CLIENT_ID`
  - `YOUTUBE_CLIENT_SECRET`
  - `YOUTUBE_REFRESH_TOKEN`

当前代码里，YouTube 上传步骤只有在上述 3 个变量都存在时才会执行，因此测试仓库不配置它们即可跳过上传。

## 6. 测试仓库的安全建议

为了避免测试仓库误触发正式链路，建议：

- 默认先不要填正式 YouTube Secrets
- 不要直接复用主仓库的正式 `ROOM_ID`
- 不要直接沿用正式 Release tag 习惯
- 初期只走 `workflow_dispatch`
- 验证稳定后，再考虑是否开启 `schedule`

如果后面测试仓库也需要验证 Release 上传，建议在 tag 上增加明显前缀，例如：

- `test-room123-...`
- `staging-room123-...`

## 7. 同步方式建议

如果测试仓库是 fork：

- 测试仓库用于先行试错
- 验证通过后，通过 PR 合回主仓库
- 主仓库继续作为稳定入口

如果测试仓库是普通仓库：

- 主仓库作为唯一稳定源
- 测试仓库定期从主仓库同步
- 测试改动确认后，再手动回推主仓库

## 8. 推荐实际流程

建议后续按下面顺序推进：

1. 保留当前仓库作为主仓库
2. 再建立一个测试仓库
3. 测试仓库先只跑手动触发
4. 在测试仓库里补齐测试所需 Variables / Secrets
5. 先验证：
   - `check_live.sh`
   - `record.sh`
   - `capture_danmaku.py`
   - `convert_danmaku.py`
   - `publish_release.sh`
6. 确认测试仓库链路稳定后，再把改动并回主仓库
7. 最后才在主仓库开启正式定时运行

## 9. 当前项目下的推荐结论

结合本仓库当前阶段，我建议：

- **当前仓库继续当主仓库**
- **另外建一个测试仓库**
- 如果你确实想保留 fork 关系，就让测试仓库作为 fork 存在
- 如果你更看重长期灵活性，就直接建普通测试仓库

对现在这个项目来说，**测试仓库不配置 YouTube Secrets** 会更安全。

## 10. 参考

以下规则在写方案时已按 GitHub 官方文档核对：

- Fork 基本说明：<https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-forks>
- 创建 fork：<https://docs.github.com/github/getting-started-with-github/quickstart/fork-a-repo>
- 分离 fork：<https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/detaching-a-fork>
- Actions Secrets 使用说明：<https://docs.github.com/en/actions/how-tos/administering-github-actions/sharing-workflows-secrets-and-runners-with-your-organization>
