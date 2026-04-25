# workflows

这里将存放 GitHub Actions 工作流文件。

当前工作流文件：

- `main.yml`
- `record.yml`

`main.yml` 将负责：

- 定时触发
- 开播检测
- 判断录制工作流是否空闲
- 派发录制工作流

`record.yml` 将负责：

- 录制与弹幕抓取
- 弹幕格式转换
- 发布 Release
- 上传 YouTube
- 接力录制
