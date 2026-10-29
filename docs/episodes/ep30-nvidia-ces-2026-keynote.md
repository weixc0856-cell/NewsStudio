# 第 30 期：黄仁勋 CES 2026 — 两次平台转移与 Vera Rubin 全面量产

- **状态**：已完成
- **信源**：NVIDIA 官方频道，<https://www.youtube.com/watch?v=0NBILspM4c4>
  （CES 2026，拉斯维加斯 Fontainebleau，2026-01-05；NVIDIA Live at CES 全程回放）
- **标题**：NVIDIA Live at CES with CEO Jensen Huang
- **讲者**：黄仁勋（Jensen Huang，NVIDIA 创始人兼 CEO）
- **规格**：原片 1:31:40，1080p60（AV1；源最高 4K60），YouTube 自动英文字幕
  （无人工字幕），舞台演讲 + 幻灯片 + 产品演示；画面干净、无硬字幕
- **建议标题**：`【AI基建·第30期】黄仁勋 CES 2026：两次平台转移、会思考的自动驾驶与 Vera Rubin 量产（中英双语·92 分钟）`
- **定位**：年度总纲。第 25 期 GTC Taipei 与第 29 期 OCP 分别从 NVIDIA、AMD 两侧讲机架；
  本期回到 2026 年初的原点：黄仁勋把「智能体 + 物理 AI」两次平台转移、开源模型家族、
  Alpamayo 自动驾驶与 Vera Rubin 六芯片平台放在同一场演讲里，是理解后续所有期次的底稿。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始演讲 | NVIDIA 官方 YouTube 全程回放、NVIDIA 官方博客《NVIDIA Rubin Platform, Open Models, Autonomous Driving》 |
| 科技媒体 | Engadget《Everything NVIDIA announced at CES 2026》、Mashable、ShiftDelete |
| 财经 / 综合媒体 | Indian Express、Business Tech News、Spectrum News、Belfast Telegraph |
| 中文媒体 | 36Kr / IT之家 / 机器之心等对 CES 2026 首日的编译报道（以官方口径为主） |

结论：NVIDIA 官方视频与博客给出完整口径，Engadget、Mashable、Indian Express 等独立整理
「Vera Rubin 全面量产、Alpamayo 开源、Siemens 合作、DLSS 4.5」四大要点，数字与命名一致
→ **通过**。

> 注意：50 PFLOPS（NVFP4 推理）、3360 亿晶体管、5× 训练性能、1/10 词元成本均为 NVIDIA
> 自报口径；「全面量产」指已进入量产、产品在 2026 年下半年出货。演讲末尾包含约 2 分钟
> 花絮（outtakes），已保留在成片中。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=0NBILspM4c4>
- NVIDIA 博客：<https://blogs.nvidia.com/blog/2026-ces-special-presentation/>
- Engadget：<https://www.engadget.com/ai/everything-nvidia-announced-at-ces-2026-225653684.html>
- Mashable：<https://me.mashable.com/tech/65366/ces-2026-nvidia-introduces-vera-rubin-platform-successor-to-blackwell>
- Indian Express：<https://indianexpress.com/article/technology/artificial-intelligence/what-is-rubin-nvidia-ai-supercomputing-platform-ces-2026-10458164/>
- Business Tech News：<https://businesstech.news/nvidia-ces-2026-vera-rubin-alpamayo/>

## 内容结构（按讲稿整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场：CES 2026，两次平台转移同时发生 |
| 02:42 | 五层计算栈被重写：训练软件、GPU 运行、逐词元生成 |
| 05:09 | 「钱从哪里来」：10 万亿美元旧计算的现代化与研发预算迁移 |
| 08:10 | 2025 回顾：o1 测试时扩展、智能体、DeepSeek R1 与开源模型 |
| 12:37 | 前沿开源模型：La Proteina、OpenFold 3、Evo 2、Earth 2、FourCastNet、CorrDiff、NeMo-Megatron 3、Cosmos、GR00T |
| 14:07 | Alpamayo：连训练数据一起开源的自动驾驶模型 |
| 16:54 | 智能体应用框架：多模态、多模型、多云的蓝图 |
| 21:36 | 个人助理演示：Brev + DGX Spark + Reachy 机器人 + 11 Labs |
| 25:23 | 企业平台：Palantir、ServiceNow、Snowflake、CodeRabbit、CrowdStrike、NetApp |
| 27:28 | 物理 AI 的三个计算机：训练、仿真、推理 |
| 29:32 | Cosmos：世界基础模型，把算力变成数据 |
| 34:12 | Alpamayo：世界首个「会思考」的自动驾驶 AI |
| 40:00 | 奔驰 CLA、NCAP 最安全车型与双栈安全护栏 |
| 45:19 | 机器人：Isaac Sim / Lab 与 R2-D2、C-3PO 同台 |
| 49:09 | 工业软件：Cadence、Synopsys 与西门子接入 CUDA-X |
| 54:00 | Vera Rubin 的命名：维拉·鲁宾与暗物质 |
| 57:03 | 计算需求：模型 10×/年、词元 5×/年 |
| 58:30 | Vera Rubin 全面量产 |
| 01:01:58 | Rubin pod、Vera CPU（88 核 / 176 线程）与 Rubin GPU |
| 01:05:54 | NVFP4 Tensor Core：1.6× 晶体管换来数量级性能 |
| 01:09:49 | ConnectX-9、Spectrum-X、BlueField-4 与 NVLink 6 |
| 01:13:53 | 机架：2 英里铜缆、45°C 液冷、2 吨重 |
| 01:18:07 | KV 缓存与上下文内存：BlueField-4 存储平台 |
| 01:22:15 | 机密计算、电源平滑与机架级指标 |
| 01:26:24 | 性能对比：10 万亿参数模型、1/4 系统、1/10 词元成本 |
| 01:29:20 | 花絮：NG 镜头与「平台转移」 |

## 简介模板（可直接粘贴）

**一句话提炼**：黄仁勋在 CES 2026 把 2026 年定义成「两次平台转移」——智能体把应用建在 AI 之上，
物理 AI 把 AI 带进真实世界；支撑它们的是全面量产的 Vera Rubin 六芯片平台、会「说出思考」的
开源自动驾驶模型 Alpamayo，以及一整套从芯片到应用的开源模型家族。

**为什么今天还值得看**

- **两次平台转移同时发生**：过去是应用跑在新电脑上；现在是应用建在 AI 上，而且软件的开发与
  运行方式（训练、GPU、逐词元生成）也被重写，五层计算栈每一层都在重做。
- **钱从哪里来**：约 10 万亿美元的旧计算要现代化，每年数千亿美元风险投资，加上 100 万亿
  美元产业里几个百分点的研发预算，正在从经典方法迁移到 AI。
- **开源模型已成体系**：从 La Proteina、OpenFold 3、Evo 2、Earth 2、FourCastNet、CorrDiff
  到 NeMo-Megatron 3（混合 Transformer + SSM）、Cosmos、GR00T、Alpamayo；不只开源模型，
  还开源训练数据与配方。
- **智能体是新的应用架构**：多模态、多模型、多云、混合云；用意图路由器把请求分给最合适的
  前沿或本地模型；现场用 DGX Spark + Brev + Reachy 机器人演示了「任何人都能搭」的个人助理。
- **物理 AI 需要三个计算机**：训练、仿真（Omniverse）、推理（车/机器人/边缘）；Cosmos 把
  算力变成合成数据，解决真实世界数据稀缺与长尾问题。
- **Alpamayo 会「说出思考」**：端到端从摄像头到执行器，同时输出将要采取的动作、理由与轨迹；
  长尾场景被拆成可理解的小场景；奔驰 CLA 成为首款搭载完整 NVIDIA AV 栈的车型，
  并用双栈（Alpamayo + 经典 AV 栈）做安全护栏。
- **Vera Rubin 全面量产**：六颗芯片、100 PFLOPS 级计算板、Vera CPU 88 核 / 176 线程、
  Rubin GPU 5× Blackwell 浮点性能、NVFP4 张量核、NVLink 6 交换机 400 Gb/s、
  Spectrum-X 共封装光学；NVL72 机架 18 个计算托盘、9 个交换托盘、2.2 亿亿晶体管、近 2 吨。
- **为词元工厂而设计**：45°C 热水液冷省掉冷水机组、电源平滑省掉 25% 过度配置、
  BlueField-4 把 KV 缓存搬进机架（每 GPU 多 16 TB）、全链路加密的机密计算。
- **性能账**：10 万亿参数模型在 100 万亿词元上训练，只需 1/4 的系统；每瓦吞吐约为 Blackwell
  的 10 倍；词元成本约 1/10。

**时间戳导航**

```
00:00 开场与两次平台转移
08:10 2025：推理、智能体与开源
12:37 开源模型家族
16:54 智能体应用框架
21:36 个人助理演示
27:28 物理 AI 三个计算机
29:32 Cosmos
34:12 Alpamayo
40:00 奔驰 CLA 与双栈安全
45:19 机器人与 Isaac
49:09 Cadence / Synopsys / Siemens
54:00 Vera Rubin 命名
58:30 全面量产
01:01:58 Vera CPU 与 Rubin GPU
01:09:49 网络与 BlueField-4
01:13:53 机架与液冷
01:18:07 KV 缓存与上下文内存
01:26:24 性能对比
01:29:20 花絮
```

**出处与致谢**：原视频来自 NVIDIA 官方频道
（<https://www.youtube.com/watch?v=0NBILspM4c4>），本片中英字幕由 YouTube 自动英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`NVIDIA Live at CES with CEO Jensen Huang [0NBILspM4c4].mkv`，
  1,158,684,700 字节（1.08 GiB），AV1 1920×1080 59.94fps（19001/317）+ Opus 48kHz 立体声，
  5499.801s（1:31:39.8），整体码率 1.69 Mbps，无内嵌字幕、画面无硬字幕
- **字幕**：YouTube 自动英文（`en-orig`，json3，1014 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 1014/1014，1 条空译补齐；翻译前修正 CES 术语
  （见备注），翻译后把 `Vera Rubin`、`Rubin`、`Alpamayo`、`Cosmos`、`GR00T`、`BlueField`
  统一保留英文，避免音译
- **成片**：`... [中英字幕].mkv`，3,179,027,880 字节（2.96 GiB），H.264（QSV
  `-global_quality:v 19 -preset slow`）1920×1080 59.94fps + Opus 48kHz 立体声
  （原音轨直接复制），5499.801s（1:31:39.8），整体码率 4.62 Mbps，**硬字幕**
  （英上中下，1014 条，`MarginV=100`），QSV 烧录 14 分 41 秒（6.24×）
- **字幕文件**：`subtitles/0NBILspM4c4.zh.bilingual.srt` / `.ass`（双语，成片用，1014 条，
  `MarginV=100`）、`subtitles/0NBILspM4c4.en.ass`（英文单语）、
  `subtitles/0NBILspM4c4.bilingual.srt`（英文句级底稿）
- **校验**：成片 5499.801s，与原片完全一致（未剪辑）；音轨包数据 MD5 与原片一致
  （`bf26a4ba37a8149d88698dc65d6f2e50`），确认直接复制、无音画偏移；head 60s / tail 20s
  解码无报错；抽帧 00:34:20 / 00:58:40 / 01:22:30，确认英上中下、无裁切

## 备注

- 自动英文字幕错误已修正：`MVL-72 → NVL72`、`La Pertina → La Proteina`、
  `ForecastNet → FourCastNet`、`ClimaDiv → CorrDiff`、`Groot → GR00T`、
  `ElpaMayo / Alpha Mylo → Alpamayo`、`Bluefield → BlueField`、`Nvidia → NVIDIA`、
  `KB cache → KV cache`
- 产品名在中文里统一保留英文：`Vera Rubin`、`Rubin`、`Alpamayo`、`Cosmos`、`GR00T`、`BlueField`
- 全片为主题演讲，无赞助口播、无广告段；片尾约 2 分钟花絮保留
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集
