# 安装

## 范围

- 实测环境：Ubuntu 22.04、x86_64、glibc 2.35、GNOME X11、Python 3.10。
- 安装器允许 Python 3.10–3.12；3.11/3.12 尚未实机验收。
- 需要普通桌面用户、可用的 `systemd --user` 和允许创建用户网络命名空间的系统。
- 需要 `bwrap`、`unsquashfs`、`gdbus`、`systemctl`、`systemd-run`、`desktop-file-validate`、`update-desktop-database`。
- 安装器不使用 sudo，不改系统包。缺依赖时停止并指出名称；由你或管理员按发行版方式安装。
- 建议至少预留 3 GiB 磁盘空间，覆盖程序、模型、下载和 wheel 缓存。

对应的 Ubuntu 软件包通常为 `bubblewrap`、`squashfs-tools`、`libglib2.0-bin`、`desktop-file-utils`。
系统 Python 需能导入 `venv`；安装器会使用固定 pip wheel 引导环境，因此不要求 `ensurepip` 可用。

## 默认安装

下载 Release 的 `.tar.gz` 或 `.zip`，解压，在项目目录运行：

```bash
bash install.sh --check
bash install.sh
```

默认安装目录：`${XDG_DATA_HOME:-$HOME/.local/share}/crow-translate-offline`。
默认下载缓存：`${XDG_CACHE_HOME:-$HOME/.cache}/crow-translate-offline`。
默认解释器：`/usr/bin/python3`。不使用当前 Conda 环境的 Python。

安装器会：

1. 检查架构、glibc、Python、工具和网络隔离能力。
2. 从上游下载固定版本 Crow、两个翻译模型、两个断句模型和 Python 引导包，并核对 SHA-256。
3. 在最终目录建立全新虚拟环境，安装 `requirements.lock` 中的固定依赖。
4. 解包 AppImage，不依赖 FUSE；配置 Crow 的 LibreTranslate direct API。
5. 在断网环境执行英文与中文 API / Crow CLI 测试。
6. 测试通过后创建菜单入口，保存安装清单。

不会自动切换镜像、重试 Google 或更改代理节点。下载失败时保留已有完整缓存，下次无需重新下载。

## 代理和自定义路径

```bash
bash install.sh --proxy http://127.0.0.1:7897

bash install.sh \
  --python /usr/bin/python3.10 \
  --prefix "$HOME/Applications/Crow Offline" \
  --cache "$HOME/.cache/crow-translate-offline"
```

代理只用于安装下载。运行环境会移除代理变量。含空格的安装路径受支持；含换行的路径被拒绝。
不要在安装后直接移动目录，因为虚拟环境的 shebang 和菜单入口包含绝对路径。

`--no-desktop` 跳过菜单安装，适合测试或只使用本地 CLI 验收。
`--check` 是只读检查，不下载文件、不创建安装目录。

## 从缓存完全离线安装

先在同架构、相同 Python 次版本的联网机器完成一次安装。复制完整源码目录和下载缓存到离线机器，运行：

```bash
bash install.sh --offline --cache /path/to/copied-cache
```

缓存必须包含 `assets.lock.json` 列出的文件，以及对应的 `wheels-py3.10`、`wheels-py3.11` 或 `wheels-py3.12`。
缓存中的 wheels 来自首次联网安装时的 PyPI 下载/构建，离线模式不会下载缺失依赖。
请把缓存视为可执行软件，只使用可信机器生成的缓存。

Release 源码包本身不包含数百 MB 的上游程序和模型；它是开箱安装工具，不是预装二进制合集。

## 失败或已有目录

安装器不会覆盖非空目的目录。失败后先查看错误与目录内容：

- 如果已生成 `crow-offline`，可执行 `crow-offline uninstall --purge` 清理本次失败目录。
- 若失败很早，尚无启动器，确认这是本次新建的测试目录后由文件管理器删除它。
- 保留下载缓存，选一个新的空目录重试。

原有 Crow、GoldenDict、Conda 或其他词典不受影响。
