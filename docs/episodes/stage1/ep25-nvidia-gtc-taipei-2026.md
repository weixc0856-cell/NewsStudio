# 第 25 期：NVIDIA GTC Taipei 2026 — 黄仁勋：为智能体重造计算机

- **状态**：已完成
- **信源**：NVIDIA 官方频道，<https://www.youtube.com/watch?v=wSp6AiNIrsY>
  （GTC Taipei 2026 主题演讲全程回放，台北音乐中心，2026-06-01 开场 COMPUTEX；
  2026-06-01 上传）
- **标题**：NVIDIA GTC Taipei 2026 Keynote | Full Replay
- **讲者**：黄仁勋（Jensen Huang，NVIDIA 创始人兼 CEO）
- **规格**：原片 1:57:53，1080p60（VP9；YouTube 最高为 4K60），YouTube 自动英文字幕
  （无人工字幕），舞台画面干净、无硬字幕
- **建议标题**：`【AI基建·第25期】黄仁勋 GTC Taipei 2026：为智能体重造计算机——Vera Rubin、Vera CPU 与 RTX Spark（中英双语·118 分钟）`
- **定位**：NVIDIA 自己的产品总账。第 21 期 Dylan Patel 讲数据中心里的算力结构，第 24 期
  BG2 讲资本开支与单位 GW 收入；本期把答案落到产品上：agent 的计算模式（模型 + 运行框架 +
  工具 + 技能 + 运行时）、Vera Rubin 机架、Vera CPU、企业智能体工具包、RTX Spark PC，
  以及 Cosmos 3 / Alpamayo 2 / Isaac GR00T 三条物理 AI 线。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始演讲 | NVIDIA 官方 YouTube 全程回放（2026-06-01）、NVIDIA GTC Taipei 页面与新闻稿 |
| 技术媒体 | The Next Web、TahawulTech、King of Computer Media（完整回顾） |
| 财经 / 综合媒体 | 36Kr（中英文双版）、中时新闻网、星岛头条、芯智讯、全球半导体观察（DRAMX） |
| 中文产业媒体 | OFweek、腾讯云开发者社区转载、新浪财经行业周报 |
| 文字稿 / 章节 | YouTube 官方章节（44 段）、厂商新闻稿口径对照 |

结论：NVIDIA 官方发布全程回放与章节，The Next Web、TahawulTech 等英文媒体做了完整报道，
36Kr、中时、星岛、芯智讯从产品与产业角度独立拆解（Vera Rubin 量产、Vera CPU、RTX Spark、
Nemotron 3 Ultra、Cosmos 3），多方口径一致 → **通过**。

> 注意：性能数字（10× 智能体吞吐、Vera 比 x86 快 1.8×、SQL 3×、实时流处理 6×、验证周期
> 40×、Nemotron 3 Ultra 5× 更快/30% 更便宜）均为 NVIDIA 自报口径，未经第三方审计；
> “每 GW 50–60 亿美元、将到 80–100 亿美元”是黄仁勋的估算；RTX Spark 的定价与出货量
> 目前只有分析师预测。本期保留原始表述，并在简介中标注。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=wSp6AiNIrsY>
- GTC Taipei：<https://www.nvidia.com/en-tw/gtc/taipei/>
- The Next Web：<https://thenextweb.com/news/jensen-huang-computex-2026-keynote>
- TahawulTech：<https://www.tahawultech.com/industry/technology/nvidia-unveils-sweeping-ai-infrastructure-expansion-at-gtc-taipei/>
- King of Computer Media：<https://en.kocpc.com.tw/archives/3135>
- 36Kr（中文）：<https://eu.36kr.com/zh/p/3834268873058184>
- 中时新闻网：<https://www.chinatimes.com/cn/realtimenews/20260601002879-260410>
- 星岛头条（八大重点）：<https://www.stheadline.com/zh-hans/realtime-finance/3578341/>
- 芯智讯：<http://www.icsmart.cn/105590/>
- 全球半导体观察：<https://www.dramx.com/News/AI/20260602-40533.html>

## 内容结构（官方章节）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场影片：token 工厂与「智能如何被制造」 |
| 03:16 | 黄仁勋登场：回到台湾，感谢供应链生态 |
| 06:30 | 有用的 AI 已经到来：GitHub 提交量三倍增长 |
| 10:55 | 智能体上岗：模型 + 运行框架 + 工具 + 技能 + 运行时 |
| 16:08 | CUDA-X 库成为智能体的工具（cuLitho、cuOpt、cuDSS、AIQ、Aerial、Warp、Parabricks） |
| 20:01 | 智能体是彻底的离散、分布式计算模式；内存与 KV 缓存 |
| 25:36 | NVIDIA DSX：AI 工厂的设计与运营蓝图 |
| 26:49 | 全世界都在建 AI 工厂：DSX Sim / DSX OS / Max LPS / Flex |
| 29:38 | DSX AI 工厂生态：每 GW 50–60 亿美元，将到 80–100 亿美元 |
| 31:46 | 世界级 AI 云：CoreWeave、Nebius、Yotta、GMI 等 |
| 34:07 | 算力就是收入：每瓦词元吞吐决定回报 |
| 40:39 | Vera Rubin 全面量产：7 颗新芯片、6 万亿晶体管、150 家台湾伙伴 |
| 41:44 | Vera Rubin 拆解：NVL72、ConnectX-9、BlueField-4、Vera CPU 机架、Groq 3 LPX |
| 46:51 | Vera Rubin 机架与系统现场演示 |
| 51:48 | Vera CPU：为智能体而生的 CPU（88 个 Olympus 核心） |
| 55:24 | 为智能体设计：IPC、每核带宽、总带宽、能效 |
| 59:28 | 对 x86 最强劲的竞争 |
| 1:00:05 | Vera CPU 规格：3.6 TB/s 内部带宽、PCIe 6.0、LPDDR5X 1.2 TB/s |
| 1:04:44 | Vera 让 SQL 快 3 倍 |
| 1:05:25 | Vera 让实时流处理快 6 倍（纽约证券交易所） |
| 1:06:56 | Vera 打开全新市场：为智能体造 CPU |
| 1:09:00 | 发布 NVIDIA 企业 AI 智能体工具包（模型 / 运行框架 / 工具 / 运行时） |
| 1:12:10 | 发布 Cadence 芯片设计超级智能体 |
| 1:12:43 | Cadence 用 AI 工程师与 OpenShell 把验证从数周压到数小时 |
| 1:16:04 | 发布 Nemotron 3 Ultra：混合 SSM + MoE，5× 更快、30% 更便宜、完全开源 |
| 1:18:43 | 企业软件平台在 NVIDIA 上构建智能体 |
| 1:19:45 | 个人计算 40 年 |
| 1:21:33 | NVIDIA 与微软重造 PC |
| 1:23:22 | RTX Spark 重新定义 Windows PC（Blackwell + 20 核 Grace，1 PFLOPS） |
| 1:25:06 | RTX Spark 笔记本 |
| 1:25:57 | N1X 芯片演示 |
| 1:27:46 | RTX Spark 家居设计智能体演示 |
| 1:30:11 | 发布 RTX Spark 版 Adobe Premiere 与 Photoshop |
| 1:31:33 | 三款革命性的 Windows 机器：笔记本、桌面、DGX Station |
| 1:36:18 | 新产线、新起点 |
| 1:38:28 | 算力就是数据：物理 AI 的数据难题 |
| 1:40:04 | 发布 Cosmos 3：物理 AI 的前沿 |
| 1:41:00 | Cosmos 3：VLM / 世界模型 / 模拟器 / 策略 |
| 1:43:23 | AI 领袖加入 Cosmos 联盟 |
| 1:43:30 | 发布 Alpamayo 2：超级自动驾驶出租车推理模型 |
| 1:44:07 | 全球车企在 NVIDIA DRIVE Hyperion 上造 Robotaxi |
| 1:44:45 | Alpamayo「说出思考」演示 |
| 1:46:25 | NVIDIA Isaac GR00T 人形机器人平台 |
| 1:47:51 | 发布 Isaac GR00T 参考人形机器人 |
| 1:48:46 | 用 Isaac GR00T 加速人形机器人开发 |
| 1:51:00 | 回顾 |
| 1:53:53 | 收尾 |
| 1:54:15 | GTC Taipei 2026 闭幕歌曲 |

## 简介模板（可直接粘贴）

**一句话提炼**：黄仁勋把「有用的 AI」归结为一个新的计算模式——模型、运行框架、工具、技能、
运行时——并据此重造了整条产品线：为智能体量产的 Vera Rubin 机架、为智能体而生的 Vera CPU、
让企业自己造智能体的工具包，以及把 PC 变成个人 AI 的 RTX Spark。

**为什么今天还值得看**

- **智能体是新的计算模式**：应用 → 智能体；代码 → 运行框架；操作系统 → 运行时。
  模型是大脑，运行框架是身体，工具是车间；一次推理会点亮整架 Grace Blackwell，一次工具调用
  落到 CPU 与 CUDA-X 库上，安全隔离跑在 BlueField DPU 上。
- **token 经济学**：GitHub 提交量从 2023 年的 3 亿涨到 2025 年的 5 亿，2026 年初几个月几乎
  翻三倍；每年 3 万亿美元工资产出约 9 万亿美元的工作量。词元可盈利之后，算力需求变成约束。
- **算力就是收入**：一座 1 GW 的 AI 工厂，每瓦产出的词元就是收入；这也是为什么英伟达强调
  每瓦吞吐、可靠性与资产寿命，而不是单芯片价格。
- **Vera Rubin 全面量产**：7 颗新芯片、6 万亿晶体管、单板 1.8 万个元件、150 家台湾伙伴；
  机架组装从 2 小时缩到 5 分钟；供应链规模是 Grace Blackwell 的两倍。
- **Vera CPU 为智能体而生**：88 个 Olympus 核心、单核 IPC 世界第一、3.6 TB/s 片上带宽、
  PCIe 6.0、LPDDR5X 1.2 TB/s；SQL 快 3 倍、纽约证券交易所实时流处理快 6 倍。
- **企业智能体工具包**：模型、OpenShell 运行框架、CUDA-X 工具与技能、运行时；Cadence 用它
  把芯片验证从数周压到数小时（40×）。
- **Nemotron 3 Ultra 完全开源**：混合 SSM + MoE，推理快 5 倍、成本低 30%，连训练数据与脚本
  一起开放；Nemotron 4 已在路上。
- **RTX Spark 重造 PC**：Blackwell RTX（6144 CUDA 核心、1 PFLOPS）+ 20 核 Grace（与联发科
  合作）、128 GB 统一内存、台积电 3nm；另有 768 GB / 20 PFLOPS 的 DGX Station for Windows。
- **物理 AI 三件套**：Cosmos 3（世界模型/模拟器/策略）、Alpamayo 2（开源的自动驾驶推理模型）、
  Isaac GR00T（参考人形机器人，每只手 25 自由度）。

**时间戳导航**

```
00:00 开场影片：智能如何被制造
03:16 黄仁勋登场
06:30 有用的 AI 已经到来
10:55 智能体的计算模式
16:08 CUDA-X 成为智能体的工具
25:36 NVIDIA DSX：AI 工厂蓝图
34:07 算力就是收入
40:39 Vera Rubin 全面量产
46:51 机架现场演示
51:48 Vera CPU：为智能体而生
1:04:44 SQL 快 3 倍
1:05:25 实时流处理快 6 倍
1:09:00 企业 AI 智能体工具包
1:12:10 Cadence 芯片设计超级智能体
1:16:04 Nemotron 3 Ultra
1:19:45 个人计算 40 年
1:23:22 RTX Spark 重造 Windows PC
1:31:33 三款 Windows 机器
1:38:28 算力就是数据
1:40:04 Cosmos 3
1:43:30 Alpamayo 2 与 DRIVE Hyperion
1:46:25 Isaac GR00T 参考人形机器人
1:51:00 回顾与收尾
```

**出处与致谢**：原视频来自 NVIDIA 官方频道（<https://www.youtube.com/watch?v=wSp6AiNIrsY>），
本片中英字幕由 YouTube 自动英文字幕翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`NVIDIA GTC Taipei 2026 Keynote ｜ Full Replay [wSp6AiNIrsY].mkv`，
  2,062,246,293 字节（1.92 GiB），VP9 1920×1080 60fps + Opus 48kHz 立体声，
  7072.983s（1:57:53），整体码率 2.33 Mbps，无内嵌字幕、画面无硬字幕；中文只出现在
  少量发布标题卡上（如 RTX Spark），不是字幕轨
- **字幕**：YouTube 自动英文（`en-orig`，json3，1439 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 1439/1439，1 个批次回退逐条重译，0 缺译；
  批量翻译的 1 处局部错位（00:26:34–00:26:58）已按原文逐条重排，并补上 1 条空译；
  专名与技术术语人工校对（Nemotron、Isaac GR00T、Alpamayo、Groq、OpenShell、
  CoWoS、DOCA、NVL72、Grace Blackwell 等）
- **成片**：`NVIDIA GTC Taipei 2026 Keynote ｜ Full Replay [wSp6AiNIrsY] [中英字幕].mkv`，
  3,298,729,992 字节（3.07 GiB），H.264（QSV `-global_quality:v 19 -preset slow`）
  1920×1080 60fps + Opus 48kHz 立体声（原音轨直接复制），7072.984s（1:57:53），
  整体码率 3.73 Mbps，**硬字幕**（英上中下，1439 条，`MarginV=100`），
  QSV 烧录 15 分 52 秒（7.43×）
- **字幕文件**：`subtitles/wSp6AiNIrsY.zh.bilingual.srt` / `.ass`（双语，成片用，1439 条，
  `MarginV=100`）、`subtitles/wSp6AiNIrsY.en.ass`（英文单语）、
  `subtitles/wSp6AiNIrsY.bilingual.srt`（英文句级底稿）
- **校验**：成片 7072.984s，与原片 7072.983s 一致（未剪辑）；音轨包数据 MD5 与原片一致
  （`1a32c5a84e4ab47f6e7b3f2163b03b71`），确认直接复制、无音画偏移；head 60s / tail 30s
  解码无报错；视频流 60/1 CFR；抽帧 00:00:12 / 00:10:55 / 00:30:00 / 00:51:50 /
  01:16:05 / 01:25:00，确认英上中下、无裁切

## 备注

- 自动英文字幕专名错误较多，翻译前已修正：`Nematron/Neumotron/NeMoTron/Numatron → Nemotron`、
  `Grace Blackwalls → Grace Blackwells`、`Doka → DOCA`、`Ariel → Aerial`、`Grok 3 → Groq 3`、
  `MVL 72 → NVL72`、`TSMCs cook process → TSMC's CoWoS process`、`Open Show → OpenShell`、
  `Cloud Code → Claude Code`、`AlphaMine → Alpamayo`、`Isaac Groot → Isaac GR00T`、
  `Envion fusion → NVLink Fusion`、`Alpha my OC's → Alpamayo` 等
- 全程为主题演讲，无赞助口播、无广告段，成片时间轴与原片一致，无需删段
- YouTube 源最高为 4K60（VP9，11.35 GiB）；受下载带宽限制，选用 1080p60 VP9
  `303+251`（1.92 GiB），与既有 1080p60 期次（第 21、22 期）规格一致
- 按用户要求，本期不做自动高光切片与片头合集，只交付无字幕原片 + 中英字幕成片 + 双语 SRT
