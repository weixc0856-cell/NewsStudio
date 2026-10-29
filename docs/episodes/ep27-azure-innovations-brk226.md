# 第 27 期：Mark Russinovich — Azure 基础设施的内部创新（Build 2026 BRK226）

- **状态**：已完成
- **信源**：Microsoft Developer 官方频道，<https://www.youtube.com/watch?v=yByo-WWGnMs>
  （Microsoft Build 2026，2026-06-03，Gateway Pavilion Cowell Theater，Advanced/300；
  2026-06-11 上传）
- **标题**：Inside Azure innovations with Mark Russinovich | BRK226
- **讲者**：马克·鲁西诺维奇（Mark Russinovich，Azure CTO 兼 Deputy CISO）；
  远程演示 Katar（Microsoft Research Cambridge）
- **规格**：原片 44:53，1080p29.97（VP9，最高画质），**人工英文字幕**（`en-ehkg1hFWq8A`），
  舞台 + 幻灯片 + 终端演示；画面干净、无硬字幕、无常驻横幅
- **建议标题**：`【AI基建·第27期】Azure 的底层创新：Azure Boost、MRC 网络、机密计算与微 LED 光互连（中英双语·45 分钟）`
- **定位**：云厂商视角的“地基”篇。第 21、22 期从芯片与数据中心角度看算力，第 25 期是
  NVIDIA 的产品总账；本期把镜头放到超大规模云内部：卸载卡怎么把数据面搬离 CPU、
  10 万 GPU 的网络协议怎么抗故障、容器怎么做到热迁移、KV 缓存怎么跨服务器共享、
  机密计算怎么在“使用中”保护数据，以及用微 LED 替代激光做光互连的实验。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始演讲 | Microsoft Developer 官方视频（BRK226）、Build 2026 session 页（aka.ms/build26/BRK226）、官方 GitHub 资源仓库 |
| 技术媒体 / 社区 | openjny.github.io《MS Build 2026》日文详解、blog.azure.moe（日文逐节笔记）、EnterpriseZone.cc、DeepCamp、tech.xebia.ms |
| 官方后续资料 | microsoft.github.io/build26-next-steps（Cloud Platform & Data 索引） |
| 中文资料 | 未检索到可靠的一手中文报道；中文站点关于 Azure Boost DPU 的文章实际对应 Ignite，不能作为本场出处 |

结论：微软官方视频、session 页与 GitHub 资源仓库构成一手来源；日文技术社区（openjny、
blog.azure.moe）逐节记录了 Azure Boost、MRC、Context Cache、机密计算与 Project Mosaic 的
数字与演示；EnterpriseZone.cc 等英文站点做了独立摘要，多方数字一致 → **通过**。

> 注意：本场多数内容为“尚未 GA / 仍在开发中”的预览或实验（Bare Metal、容器热迁移、
> 机密虚机热迁移、Project Mosaic），讲者在开场即声明不保证最终产品形态。性能数字
> （20 GB/s、1M IOPS、95 GB/s、96% 命中率、18,800 次签名/秒等）均为微软演示口径。
> 中文互联网缺少本场的一手报道，本期简介以官方与日文技术笔记为准。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=yByo-WWGnMs>
- Build session：<https://build.microsoft.com/en-US/sessions/eeee0fa1-d7ee-47e5-8ce1-70da4a287fb7>
- 官方 GitHub：<https://github.com/microsoft/Build26-BRK226-inside-azure-innovations-with-mark-russinovich>
- openjny 日文详解：<https://openjny.github.io/msbuild-2026/sessions/brk226.html>
- blog.azure.moe：<https://blog.azure.moe/2026/06/04/microsoft-build-2026-day-2-inside-azure-innovations-with-mark-russinovich/>
- EnterpriseZone.cc：<https://enterprisezone.cc/mark-russinovich-unveils-azures-deep-infrastructure-innovations-at-microsoft-build/>
- tech.xebia.ms：<https://tech.xebia.ms/security/videos/inside-azure-innovations-with-mark-russinovich-brk226>

## 内容结构（按讲稿整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场：Azure CTO 的“内部创新”巡览 |
| 00:01:06 | Fairwater 数据中心（威斯康星 / 亚特兰大）：液冷、布线、机架 |
| 00:02:57 | Azure Boost 卸载卡：DPU + ARM 核 + FPGA，数据面搬离 CPU |
| 00:04:00 | 新一代 Boost 指标：远端存储 20 GB/s、100 万 IOPS、400 Gb 网络 |
| 00:05:33 | Bare Metal 实例与 OpenAI 的 Fairwater 集群（ND144 v6） |
| 00:06:45 | 从 InfiniBand 转向以太网：MRC 多路径可靠连接 |
| 00:08:04 | MRC 演示：8 个平面、95 GB/s，拔掉一台交换机不掉速 |
| 00:11:00 | 虚机间 RDMA：prefill / decode 分离，吞吐约翻倍 |
| 00:13:38 | 无服务器：ACI 用 Hyper-V 做隔离 |
| 00:15:37 | Direct Virtualization：容器与管理虚机平级，去掉嵌套开销 |
| 00:17:03 | 首次公开容器热迁移演示（tick 695 无缝续上） |
| 00:18:54 | Manifold：把 GPU/CPU/FPGA/ASIC 当作一个算力池 |
| 00:22:24 | Azure Context Cache：跨服务器的 KV 缓存（命中率 96%） |
| 00:26:04 | 容器沙箱与内存快照：1 万个沙箱、平均 2 秒启动 |
| 00:28:52 | 机密计算：使用中加密、硬件证明与密钥释放 |
| 00:32:57 | 首次公开机密虚机热迁移（Intel TDX + MigTD） |
| 00:35:16 | Caliptra 与 Azure Integrated HSM（FIPS 140-3 L3） |
| 00:38:38 | Project Mosaic：微 LED + 成像光纤的数据中心光互连 |
| 00:44:08 | 收尾与致谢 |

## 简介模板（可直接粘贴）

**一句话提炼**：Mark Russinovich 用一场 45 分钟的“机房内部巡览”说明超大规模云真正难的地方
不在 GPU 本身：把数据面卸载到 Azure Boost 卡、用 MRC 让 10 万 GPU 的网络抗住故障、
把容器做成可热迁移、把 KV 缓存放到服务器之外、把密钥锁进每台服务器的 HSM，
最后用微 LED 替代激光做光互连。

**为什么今天还值得看**

- **Azure Boost 是“隐形 CPU”**：存储与网络数据面被搬到带 DPU、ARM 核与 FPGA 的卸载卡上；
  新代做到 20 GB/s 远端存储、100 万 IOPS、36 GB/s 本地 NVMe、400 Gb 网络，已覆盖 30% 机队。
- **Bare Metal 给的是“没有 hypervisor 的 GPU 服务器”**：OpenAI 在 Fairwater 用的就是
  ND144 v6 裸金属实例，管理面全部在 Boost 卡上；即将作为通用产品提供。
- **MRC 是给 10 万 GPU 准备的网络协议**：与 OpenAI 共同开发，把包喷洒到多个独立“平面”，
  现场演示拔掉一台交换机后带宽不掉；微软称其已成为大型训练网络的事实标准。
- **RDMA 让推理集群少绕路**：prefill / decode 分池后，虚机间 RDMA 把 vLLM 吞吐从
  3,400 提到 7,637 词元/秒，首词元时间从 123 秒降到 47 秒。
- **容器正在追上虚机**：Direct Virtualization 去掉嵌套层；首次公开容器热迁移，
  演示里的计数器 695 无缝续上；1 万个智能体沙箱用内存快照平均 2 秒拉起。
- **KV 缓存放进存储**：Azure Context Cache 把前缀缓存放到服务器之外，命中率从 81% 到 96%。
- **机密计算的最后一块拼图是热迁移**：与 Intel 合作，用 MigTD 做策略管控，
  首次公开机密虚机在线迁移；Azure Integrated HSM 把密钥锁在每台服务器内，
  签名性能从 640 提升到 18,800 次/秒。
- **Project Mosaic 是“反激光”路线**：用商用 micro-LED 阵列 + 成像光纤 + 硅相机传感器，
  在几十米距离上做低功耗高带宽互连，来自微软剑桥研究院的现场演示。

**时间戳导航**

```
00:00 开场
01:06 Fairwater 数据中心
02:57 Azure Boost 卸载卡
05:33 Bare Metal 与 OpenAI
06:45 MRC 网络协议
08:04 MRC 抗故障演示
11:00 虚机间 RDMA
13:38 ACI 与 Hyper-V 隔离
15:37 Direct Virtualization
17:03 容器热迁移
18:54 Manifold 算力池
22:24 Azure Context Cache
26:04 一万个容器沙箱
28:52 机密计算
32:57 机密虚机热迁移
35:16 Azure Integrated HSM
38:38 Project Mosaic
44:08 收尾
```

**出处与致谢**：原视频来自 Microsoft Developer 官方频道
（<https://www.youtube.com/watch?v=yByo-WWGnMs>），本片中英字幕基于官方人工英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`Inside Azure innovations with Mark Russinovich ｜ BRK226 [yByo-WWGnMs].mkv`，
  273,780,339 字节（261 MiB），VP9 1920×1080 29.97fps（30000/1001）+ Opus 48kHz 立体声，
  2692.781s（44:52.8），整体码率 0.81 Mbps，无内嵌字幕、画面无硬字幕
- **字幕**：**官方人工英文**（`en-ehkg1hFWq8A`，json3，484 条句级 cue，保留
  Mark Russinovich / Katar / All 讲者标签）；中文由本地 Qwen3-30B-A3B 用
  `translate_groups.py` 按句组翻译（420 组 → 484/484 条，0 缺译），中文按英文长度比例
  回填到各 cue；人工校对时修正设备名被意译的问题（`Dev Box 6 / Server Dev 6`）
- **成片**：`Inside Azure innovations with Mark Russinovich ｜ BRK226 [yByo-WWGnMs] [中英字幕].mkv`，
  580,737,226 字节（554 MiB），H.264（QSV `-global_quality:v 19 -preset slow`）
  1920×1080 29.97fps + Opus 48kHz 立体声（原音轨直接复制），2692.781s（44:52.8），
  整体码率 1.73 Mbps，**硬字幕**（英上中下，484 条，`MarginV=100`），
  QSV 烧录 3 分 16 秒（13.7×）
- **字幕文件**：`subtitles/yByo-WWGnMs.zh.bilingual.srt` / `.ass`（双语，成片用，484 条，
  `MarginV=100`）、`subtitles/yByo-WWGnMs.en.ass`（英文单语）、
  `subtitles/yByo-WWGnMs.bilingual.srt`（英文句级底稿）
- **校验**：成片 2692.781s，与原片完全一致（未剪辑）；音轨包数据 MD5 与原片一致
  （`7fb724d5d28aeac097294d5460872667`），确认直接复制、无音画偏移；head 60s / tail 20s
  解码无报错；抽帧 00:00:20 / 00:03:30 / 00:17:45 / 00:29:30 / 00:41:00，确认英上中下、
  无裁切

## 备注

- 本期使用**官方人工英文字幕**（`en-ehkg1hFWq8A`，484 条句级 cue），按句组合并后翻译；
  与自动字幕相比专名更准确，仅保留讲者标签（Mark Russinovich / Katar / All）
- 全片为 Build 分会场演讲 + 终端演示，无赞助口播、无广告段
- 按用户要求（并已写入 `CLAUDE.md` 作为长期默认），本期不做自动高光切片与片头合集
