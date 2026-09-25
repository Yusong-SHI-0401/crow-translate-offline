# 测试与性能

## 测试范围

初始部署与项目化安装在 Ubuntu 22.04 / glibc 2.35 / Python 3.10 / x86_64 上完成。
工作站为双路 Xeon E5-2696 v4，支持 AVX2；只使用 CPU，限制推理线程数。
不以这台机器的结果保证低功耗笔记本、ARM、Wayland 或其他 Python 版本的表现。

项目化安装验收包括：

- 全新虚拟环境，不沿用原部署的 site-packages。
- 在含空格的新路径安装并运行。
- 固定版本依赖与 `pip check`。
- 英文→中文、中文→英文的本地 API。
- Crow 4.1.0 CLI 通过 direct API 调用本地引擎。
- 只有 `lo` 的命名空间、外部连接得到 `ENETUNREACH`。
- 从完整缓存断网重装。
- 安装器防止覆盖已有目录，卸载检查安装标识和菜单内容。

## 实测数据

原部署的样本：

| 输入或阶段 | 耗时 |
| --- | --- |
| 引擎就绪，不含模型预热 | 0.813 秒 |
| Hello world.，含首次英文模型加载 | 0.251 秒 |
| Single-cell RNA sequencing reveals changes in gene expression. | 0.080 秒 |
| We identified distinct cell types in the human retina. | 0.065 秒 |
| 185 字符、两句英文段落 | 0.172 秒 |
| 我们研究基因表达和细胞类型。含首次反向模型加载 | 0.257 秒 |

项目化全新安装的再次验收：引擎就绪约 0.815 秒；首句英文 0.295 秒，下一句 0.064 秒；
首次中文反向 0.225 秒；Crow CLI 完整调用分别约 0.539 / 0.083 秒。

内存 RSS：原部署中英文模型预热后引擎约 255 MiB，双向模型均使用后约 343 MiB；Crow GUI 约 81 MiB。
新项目全新安装的引擎双向测试 RSS 约 342 MiB。RSS 不能直接等同于独占物理内存。
原部署空闲采样 35 秒，CPU 时间约 0.028 秒，约为一个核的 0.08%。

这些是少量句子与特定机器上的观测值。没有测试全文论文吞吐量、长期压力、GPU 或大语言模型替代方案。

## 已知译文问题

正确或基本可用的例子：

> Single-cell RNA sequencing reveals changes in gene expression.
>
> 单细胞RNA测序揭示出基因表达的变化.

明显错误的例子：

> Spatial transcriptomics preserves the location of each cell.
>
> 空间记录仪保存每个细胞的位置。

后者的学科术语应为“空间转录组学”。速度和离线性通过验收，不代表专业翻译质量达到高质量云端服务水平。

## 自己运行测试

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh

# 完整安装后，以新网络命名空间调用真实模型和真实 Crow CLI
~/.local/share/crow-translate-offline/crow-offline test
```

每次完整测试都会在安装目录 `state/verification-<timestamp>.json` 创建新报告，不覆盖旧报告。
自动化测试不读取剪贴板或个人文献。

仍需用户界面验收：在你常用的 PDF 阅读器里选区、快捷键触发、弹窗显示和字体。
原部署已确认 GUI 进程和 D-Bus 正常，但未做界面视觉验收。
