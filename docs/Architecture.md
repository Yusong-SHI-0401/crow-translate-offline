# 实现原理

## 三层组件

**Crow Translate** 提供选区获取、全局快捷键、托盘和翻译窗口。本项目使用 4.1.0 的 LibreTranslate direct 模式，
把 `POST /translate` 发送到本地实例，而不是公网上的 Mozhi 聚合实例。

**LibreTranslate** 提供与 Crow 兼容的 HTTP 接口。只监听独立网络空间里的 `127.0.0.1:5805`，
关闭 Web UI 和文件翻译，不配置 API key 或云端服务。

**Argos / CTranslate2** 加载英文→简体中文、简体中文→英文模型，在 CPU 上做 int8 推理。
MiniSBD 负责断句。所有模型在安装阶段下载到独立目录。

## 为什么需要 direct 模式

Crow 的传统 Mozhi 模式使用 `/api/translate` 聚合协议；LibreTranslate 使用 `/translate` JSON POST。
仅把实例地址换成本机是不够的，还必须设置：

```ini
[Translation]
Backend=1
Instance=http://127.0.0.1:5805
LibreTranslateDirect=true

[MainWindow]
CurrentEngine=4
```

这些数字对应固定的 Crow 4.1.0 枚举。升级 Crow 前需要核对，不能假定其他版本的配置完全兼容。
源语言和目标语言默认固定为英文与简体中文；不依赖自动语言检测决定翻译方向。

## 真正断网运行

启动流程：`crow-offline` → 临时 `systemd --user` 服务 → `bwrap --unshare-net` → 会话监督程序 → 引擎和 Crow。

bubblewrap 为两个进程创建同一个只有 `lo` 的网络命名空间。它们能互相通信，但没有通往主机代理或公网的路由。
测试会检查网卡并尝试连接 RFC 5737 文档地址，要求得到 `ENETUNREACH`。不会向 Google 或其他真实翻译站发送测试文本。

这是网络隔离，不是完整应用沙箱。桌面显示、会话 D-Bus 和文件系统仍可用，以支持选区与窗口功能。
程序可能通过桌面请求其他应用打开帮助链接；隔离承诺指本项目翻译进程自身的 IP 网络连接。

## 生命周期与资源

- 服务名根据安装路径计算，避免误停其他安装。
- 检测到其他 Crow 占用 D-Bus 名称时，提示先退出，不强制终止它。
- 退出 Crow 后监督程序终止引擎；启动失败也会清理子进程。
- systemd 使用 `KillMode=control-group`，停止服务会清理其进程组。
- 不安装固定服务单元、不启用开机自启；再次点击启动器显示已有窗口。
- CTranslate2 使用 4 个推理线程、1 个并行 worker；MiniSBD 限制为 2 个线程；均不使用 GPU。

## 两个容易忽略的问题

1. **MiniSBD 缓存路径**：Argos 在导入时重新赋值 MiniSBD 的缓存目录。因此本项目在导入 Argos 之后设置缓存路径，
   否则即使模型已下载，首次断网查询仍可能试图联网下载并失败。
2. **日志文本**：Argos 默认可能在 INFO 级别输出源文本。启动脚本把该 logger 限制到 WARNING，Crow 的 debug 日志也关闭。
   不配置翻译历史持久化；排查故障时仍应先审查日志再分享。

这些调整都在独立的 `server.py` 中完成，不修改第三方包源码。
