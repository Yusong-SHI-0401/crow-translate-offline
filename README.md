# Crow Translate Offline

**Linux 上的中英离线划词、划句翻译。一次安装，之后无需联网。**

将 Crow Translate 的桌面交互与 LibreTranslate / Argos 本地 CPU 引擎连接起来。
安装器处理版本固定、文件校验、独立 Python 环境、中英模型、应用菜单和断网验收。

English: a user-level installer for Crow Translate + a local English↔Chinese engine.
Runs both processes inside a loopback-only network namespace. No cloud API or GPU is needed.
The source release downloads upstream components during setup; everyday translation is offline.

## 快速开始

**已实测：Ubuntu 22.04、x86_64、GNOME X11、系统 Python 3.10。**
需要 glibc ≥ 2.35、Python 3.10–3.12（含 `venv`）、`bwrap`、`unsquashfs`、用户 systemd、
`gdbus` 和 `desktop-file-utils`。Python 3.11/3.12 与其他桌面目前未实机验证。

下载本仓库的 Release 源码包并解压，在目录中运行：

```bash
# 先做只读环境检查
bash install.sh --check

# 安装到 ~/.local/share/crow-translate-offline
bash install.sh
```

网络需要代理时，明确传入自己的代理地址：

```bash
bash install.sh --proxy http://127.0.0.1:7897
```

安装完成后，在应用菜单搜索 **Crow Translate 离线**，或运行：

```bash
~/.local/share/crow-translate-offline/crow-offline start
```

**不要使用 sudo 运行安装器。** 它不会修改 Conda base、系统 Python、GoldenDict 或系统网络设置，
也不会自动安装系统包、启用开机自启或覆盖已有安装目录。默认不自动打开窗口。

## 日常使用

| 操作 | 快捷键 / 入口 |
| --- | --- |
| 选中英文后弹窗翻译 | `Ctrl+Alt+E` |
| 显示主窗口 | `Ctrl+Alt+C` |
| 翻译输入框中的文本 | `Ctrl+Enter` |
| 中文译成英文 | 在窗口选择中文源语言、英文目标语言 |
| 关闭应用和引擎 | 托盘菜单退出，或 `crow-offline stop` |

关闭窗口可能只是隐藏到托盘。默认方向为英文 → 简体中文；发音和 OCR 不属于本项目已验证的功能。
Wayland 下全局快捷键和跨应用选区可能受桌面限制，首选已验证的 X11 会话。

## 工作方式

```mermaid
flowchart LR
    A[PDF / 浏览器中选中文本] --> B[Crow Translate]
    subgraph N[独立网络命名空间：只有 lo]
      B -->|POST 127.0.0.1:5805/translate| C[LibreTranslate]
      C --> D[Argos + CTranslate2 CPU int8]
      D --> E[本地中英模型]
    end
    E --> B
```

安装时需要网络或完整的预备缓存；运行时由 bubblewrap 隔离网络。它不修改主机防火墙，
不向局域网开放 API，也不会在失败后切换到云端翻译。此隔离针对网络，不是文件系统安全沙箱。

## 性能与质量

初始工作站上的少量短句测试：引擎翻译约 0.07–0.25 秒；英文模型预热后引擎 RSS 约 255 MiB，
双向模型均使用后约 343 MiB，Crow 窗口约 81 MiB。部署约 1.1 GiB，另需下载缓存空间。
这是特定硬件和样本的结果，不是所有电脑或长文的速度承诺。

**Argos 对专业术语有明显局限。** 例如测试中把 “Spatial transcriptomics” 误译为“空间记录仪”。
适合辅助阅读，重要信息请对照原文。详细样本和验证边界见 [测试与性能](docs/Verification.md)。

## Wiki 与维护

- [Wiki 首页](docs/Home.md)
- [安装、代理和离线重装](docs/Installation.md)
- [实现原理](docs/Architecture.md)
- [使用与故障排查](docs/Troubleshooting.md)
- [测试与性能](docs/Verification.md)
- [更新与卸载](docs/Maintenance.md)

```bash
~/.local/share/crow-translate-offline/crow-offline test    # 实际断网翻译测试
~/.local/share/crow-translate-offline/crow-offline logs    # 本应用日志
~/.local/share/crow-translate-offline/crow-offline stop
~/.local/share/crow-translate-offline/crow-offline uninstall
```

`uninstall` 停止服务并移除/还原菜单入口，保留应用和模型；确认不要后使用 `uninstall --purge` 删除安装目录。
下载缓存独立保留。项目源码脚本使用 MIT 许可；[第三方组件使用各自许可](THIRD_PARTY.md)。

这是独立的集成项目，与 KDE Crow Translate、LibreTranslate 和 Argos 上游没有官方隶属关系。
