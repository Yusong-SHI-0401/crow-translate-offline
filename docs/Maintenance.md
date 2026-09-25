# 更新、备份与卸载

## 目录结构

```text
安装目录/
  crow-offline            # 用户命令入口
  controller.py           # systemd 启停、窗口复用、卸载
  session.py              # 网络隔离内的进程监督与验收
  server.py               # 本地引擎适配
  common.py               # 独立路径、CPU 和代理环境
  crow/                   # 官方 AppImage 解包
  engine/                 # Python 虚拟环境
  config/                 # 仅供本项目的配置
  data/argos-translate/   # 中英双向模型
  cache/minisbd/           # 中英断句模型
  state/                  # 验收报告、菜单备份等
  installation.json       # 安装标识和菜单恢复信息
```

下载缓存位于独立缓存目录，包含上游文件、wheelhouse 与 pip 缓存。
项目源码 Git 仓库不包含上述运行数据。

## 备份

更改配置前先退出 Crow，备份 `config/crow-translate/crow-translate.conf`。
运行中的 Crow 可能在退出时保存设置，因此不要直接覆盖其正在使用的配置。
复制整个安装目录可以保留数据，但不能当作可移动安装包使用；换路径后应重新安装。

## 更新

v0.1.0 刻意不提供原地覆盖升级。保留旧目录，在新的空目录安装新版本，验收后再切换。
用户需要安装新版本时，应先退出旧 Crow，避免 D-Bus 名称冲突。

维护者更新步骤：

1. 核对 Crow direct API、QSettings 配置键和枚举。
2. 更新 `assets.lock.json` 的版本、官方下载地址与 SHA-256。
3. 更新 `requirements.lock`，重新解析/检查依赖。
4. 验证全新安装、断网重装、两种语言方向、异常退出和卸载。
5. 更新 Wiki、CHANGELOG，构建新的源码 Release。

不应仅修改版本号而继续沿用旧校验值或声称未经测试的平台已经支持。

## 卸载与回滚

```bash
APP="$HOME/.local/share/crow-translate-offline"
"$APP/crow-offline" stop
"$APP/crow-offline" uninstall
```

`uninstall` 停止该安装的临时服务，并移除本项目菜单入口；若安装前已有同名入口，则还原备份。
应用和模型保留，方便恢复。菜单入口如果被其他工具或用户修改，卸载器停止并要求人工检查，不覆盖新内容。

要永久删除这一安装目录及其中的模型、配置和报告：

```bash
"$APP/crow-offline" uninstall --purge
```

清除前会核对 `installation.json`，只删除标记匹配的安装目录。下载缓存与源码仓库仍保留。
你可以在不再需要离线重装时单独删除下载缓存。

## 开发和源码打包

```bash
python3 -m unittest discover -s tests -v
python3 scripts/package.py
```

产物在 `dist/`：`.tar.gz`、`.zip`、`SHA256SUMS`。打包器使用文件白名单，不包含运行环境、模型、日志或凭据。
已存在的发布包不会被静默覆盖，重新打包前先备份旧 `dist/`。

文档源为 `docs/`。`scripts/wiki.py` 可生成可直接推送到 GitHub Wiki 仓库的页面，同时转换页面链接。
仓库的 GitHub Actions 运行轻量单元检查；大型模型端到端安装测试需要在受支持的 Linux 环境单独执行。
