# 使用与故障排查

以下命令中的 `APP` 指向实际安装目录：

```bash
APP="$HOME/.local/share/crow-translate-offline"
"$APP/crow-offline" status
"$APP/crow-offline" logs
"$APP/crow-offline" test
```

## 快捷键没有反应

1. 确认应用已经启动，并用 `Ctrl+Alt+C` 显示主窗口。
2. 先粘贴普通英文，按 `Ctrl+Enter`，区分翻译引擎问题和选区问题。
3. X11 下选中英文后按 `Ctrl+Alt+E`。检查 Crow 的快捷键设置是否与其他应用冲突。
4. Wayland 会限制跨应用选区读取及全局快捷键。本项目只实测 X11；Wayland 下可先用复制粘贴。

扫描版 PDF 没有可选文本，需要先 OCR。OCR 不在本项目的已验证范围，不应把选不中的扫描文字视为翻译失败。

## 提示已有另一个 Crow

同一桌面会话的 Crow 使用固定 D-Bus 名称。先从另一个 Crow 的托盘菜单彻底退出，再启动本项目。
本项目不会强行关闭其他安装。不同安装目录的服务名不同，停止一个不会主动终止另一个。

## `bwrap` / namespace / Operation not permitted

系统可能禁止普通用户创建网络命名空间，或者你在受限容器、远程执行沙箱中测试。
先在普通桌面终端运行 `bash install.sh --check`。如果只有受限执行环境失败，不能据此认定代理或翻译服务故障。

安装器不会关闭系统安全策略或退回联网运行。若本机策略确实不允许 namespace，需要管理员提供合适环境，
或明确接受并实现另一种隔离方式。本版本保持“失败即停止”。

## `127.0.0.1:5805` 在浏览器打不开

这是预期现象。服务位于仅供 Crow 与引擎使用的网络命名空间里，主机浏览器的 loopback 不是同一个网络。
Web UI 也已关闭。请使用 `crow-offline test` 验证，而不是从普通浏览器访问端口。

## 下载失败、HTTP 错误、校验不符

- 需要代理时通过 `--proxy` 明确传入。安装器不自动沿用环境中的代理，也不切换节点。
- 安装器没有自动重试。先解决网络问题，再人工重试；已校验的缓存会复用。
- 校验不符时停止，不执行该文件。查看缓存内容，移走损坏文件后重试；不要跳过校验。
- 安装失败后的非空目录不会被覆盖，先清理本次失败安装，或选择新的 `--prefix`。

## 模型已下载，但首次查询仍想联网

本项目正常安装后不会出现此情况。检查 `cache/minisbd/en.onnx`、`cache/minisbd/zh-hans.onnx`，
以及 `data/argos-translate/packages` 下两种翻译方向的模型。
使用本项目的 `crow-offline` 启动，不要绕过 `server.py` 直接运行 `libretranslate`；后者可能使用不同缓存目录。

## 启动日志提示 GPU device discovery failed

已遇到 ONNX Runtime 探测 GPU 时的警告；本项目明确使用 CPU。
如果 `crow-offline test` 通过，它不代表翻译失败，也不需要安装 CUDA。其他错误仍应逐项判断。

## 译文质量不佳

Argos 小模型速度快，但不保证专业术语、长距离指代和复杂句子准确。英文→中文的“Spatial transcriptomics”
在实测中被误译。建议对照原文，缩短输入段落，人工确认重要术语。本项目不会擅自更换云端或付费引擎。

## 报告问题

提供发行版、Python 版本、桌面会话类型、安装器最后一段错误和 `crow-offline test` 结果。
测试使用固定示例文本。分享日志前检查是否包含自己的文本、路径或其他私人信息，不要提交令牌或代理订阅。
