# 第 29 期：苏姿丰 — 为 AI 智能体重建基础设施（OCP Global Summit 2026）

- **状态**：已完成
- **信源**：Open Compute Project 官方频道，<https://www.youtube.com/watch?v=3nFDQMaoNKc>
  （OCP Global Summit 2026，圣何塞，2026-10-12；2026-10-13 上传）
- **标题**：Building the Next Era of AI Infrastructure
- **讲者**：苏姿丰（Lisa Su，AMD 董事长兼 CEO）
- **规格**：原片 27:38，1080p60（VP9，最高画质），YouTube 自动英文字幕（无人工字幕），
  舞台演讲 + 幻灯片；画面干净、无硬字幕、无常驻横幅
- **建议标题**：`【AI基建·第29期】苏姿丰 OCP 2026：为智能体重建基础设施——Helios、Helion 与 EPYC Verano（中英双语·28 分钟）`
- **定位**：算力供给的另一极。第 25 期是 NVIDIA 的产品总账，第 27/28 期是微软云的内部
  工程；本期是 AMD 的回应：机架级 Helios 进入量产、面向智能体的 Helion 机架、
  以及被智能体重新拉高的 CPU 市场。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始演讲 | OCP 官方频道完整视频、AMD Newsroom《OCP 2026: AMD CEO Highlights Open Infrastructure for AI》 |
| 技术媒体 | TweakTown、Asia Economy（英文/中文版） |
| 中文财经媒体 | 中时新闻网《苏姿丰宣告「没有业者能独吞 AI」》、MoneyDJ、老鸭窝（laoyaoba）《Helios 之后再落一子》 |
| 财经 / 市场媒体 | Asianet Newsable（1.5 万亿美元需求、60% 推理） |
| 文字稿 / 章节 | YouTube 视频页、AMD 官方回顾 |

结论：OCP 发布完整演讲，AMD Newsroom 同步给出要点回顾，TweakTown、Asia Economy、
中时、MoneyDJ、老鸭窝等从产品、机架与市场角度独立报道，关键数字（60% 推理、2000 亿美元
CPU TAM、Helion 11 月 26 日供货）互相印证 → **通过**。

> 注意：$1.5T 加速器 TAM、$200B CPU TAM、30% tokens/dollar、40% 性能提升均为 AMD
> 自报口径；Helios 的“最高性能机架”是厂商定位，不是第三方基准。Helion 的 CPU 配置
> （3.2 万核 / 96 颗高频 Venice）与 MI350/MI350P 数量以 AMD 官方规格为准。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=3nFDQMaoNKc>
- AMD Newsroom：<https://newsroom.amd.com/news/ocp-2026-amd-ceo-lisa-su-keynote-takeaways/>
- TweakTown：<https://www.tweaktown.com/news/114071/amd-ceo-lisa-su-calls-2026-the-year-of-inference-and-says-the-cpu-market-will-grow-tenfold-to-dollars200b-by-2030/index.html>
- Asia Economy：<https://www.asiae.co.kr/lang/print.htm?idxno=2026101313501668854&lang=en>
- 中时新闻网：<https://www.chinatimes.com/cn/realtimenews/20261014002655-260410>
- 老鸭窝：<https://www.laoyaoba.com/html/share/news/1118754>
- Asianet Newsable：<https://newsable.asianetnews.com/markets/amd-ceo-lisa-su-sees-ai-inference-boom-fueling-1-5t-demand-by-2030-about-60-of-the-market-going-forward-articleshow-27gdiuo>

## 内容结构（按讲稿整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场：第一次参加 OCP Global Summit |
| 00:41 | AMD 视角：变化最快的市场 |
| 01:17 | 开放是 AMD 的原则：Naples、UEC、UALink、ESUN |
| 03:04 | 需求：token 两年 95 倍、每月近 40 万亿推理词元 |
| 04:35 | 2026 是推理之年：推理约占市场 60%，智能体流量 14 倍增长 |
| 06:12 | TAM：AI 加速器 2030 年近 1.5 万亿美元；CPU 市场被三次上调至 2000 亿 |
| 07:59 | 三个原则：算力领导力、AI 无处不在、开放 |
| 09:31 | Helios 机架：72 GPU、1.8 万计算单元、4600 个 Zen 6 核 |
| 11:56 | 与 Meta 共同设计：OCP 开放机架、开放电源与网络 |
| 13:26 | 网络伙伴：博通、思科、Arista、HPE、DriveNets |
| 14:16 | 软件与 Hyperloom：1.4 万个 Hugging Face 模型、约 40% 性能提升 |
| 15:30 | Helios 指标：每美元多 30% 词元；9 月开始出货 |
| 18:05 | 智能体基础设施：Muse、OpenAI、Anthropic 的智能体实践 |
| 19:47 | 不同智能体需要不同算力与不同机架 |
| 21:03 | 发布 Helion Agentic AI Rack：21 英寸、3.2 万核、32 颗 MI350P |
| 24:40 | 芯片：Venice 家族与首次亮相的 EPYC Verano |
| 27:08 | 收尾：开放贯穿硬件、规范、软件与生态 |

## 简介模板（可直接粘贴）

**一句话提炼**：苏姿丰把 2026 年定义为“推理之年”——推理已占 AI 算力约六成，智能体又把
CPU 需求重新拉高；AMD 的答案是两条机架线：量产中的 Helios 与面向智能体的 Helion，
外加一颗把 LPDDR 引入 EPYC 的 Verano。

**为什么今天还值得看**

- **推理成为主战场**：过去两年 token 用量涨了 95 倍，达到每月近 40 万亿推理词元；
  2026 年推理约占市场 60%，智能体流量一年增长 14 倍。
- **CPU 被智能体重新定价**：传统 CPU 市场原本约 200 亿美元、个位数增长；AMD 九个月内
  三次上调 TAM，现在预计 2030 年超过 2000 亿美元、约 50% 年复合增长。
- **Helios 进入量产**：72 颗 GPU 作为一个加速器、1.8 万多个 GPU 计算单元、4600 个 Zen 6 核，
  单托盘 160 磅、整机架近 7000 磅；与 Meta 共同设计，采用 OCP 开放机架标准。
- **开放的网络与软件**：前端与扩展网络交给博通、思科、Arista、HPE、DriveNets；
  用 UALink over Ethernet 与 ESUN 做 scale-up；前 15 个开源 AI 社区原生支持。
- **Hyperloom 的智能体调优**：让智能体在 1.4 万个 Hugging Face 模型上无人值守地持续调优，
  拿到约 40% 的性能提升——这是“智能体改进硬件”的实例。
- **Helion 是“智能体专用机架”**：21 英寸、风冷或液冷、最高 3.2 万个 Zen 6 核（比同类高 40%）
  或 32 颗 MI350P；内置 token 路由器，把请求分给合适的前沿或开源模型；11 月 26 日起由
  生态伙伴供货，架构贡献给 OCP。
- **EPYC Verano 首次亮相**：Venice 核心家族、6 个 CCD × 32 核最高 192 核、面向最低系统功耗，
  首次在 EPYC 上引入 LPDDR 内存接口，改善 CPU-GPU 带宽，2027 年上半年量产。
- **异构是常态**：没有一种算力能通吃；超大规模要分离的 CPU/GPU 机架，企业更需要一体化机架，
  开放标准决定了能不能混搭。

**时间戳导航**

```
00:00 开场
00:41 AMD 视角的市场
01:17 开放原则与 OCP 历史
03:04 需求：token 与推理
06:12 TAM：加速器与 CPU
07:59 三个原则
09:31 Helios 机架
11:56 与 Meta 共同设计
14:16 软件与 Hyperloom
15:30 Helios 量产与指标
18:05 智能体基础设施
19:47 不同智能体，不同算力
21:03 Helion Agentic AI Rack
24:40 Venice 与 EPYC Verano
27:08 收尾
```

**出处与致谢**：原视频来自 Open Compute Project 官方频道
（<https://www.youtube.com/watch?v=3nFDQMaoNKc>），本片中英字幕由 YouTube 自动英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`Building the Next Era of AI Infrastructure [3nFDQMaoNKc].mkv`，
  171,699,528 字节（164 MiB），VP9 1920×1080 60fps + Opus 48kHz 立体声，
  1657.961s（27:38），整体码率 0.83 Mbps，无内嵌字幕、画面无硬字幕
- **字幕**：YouTube 自动英文（`en-orig`，json3，285 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 285/285，1 条空译已补齐；翻译前统一 AMD 术语
  （agentic、ESUN、EPYC、Norrod、21-inch、gigantic racks），翻译后把 Venice / Verano
  保留英文并修正中文里的“Verona”
- **成片**：`... [中英字幕].mkv`，435,186,072 字节（415 MiB），H.264（QSV
  `-global_quality:v 19 -preset slow`）1920×1080 60fps + Opus 48kHz 立体声
  （原音轨直接复制），1657.961s（27:38），整体码率 2.10 Mbps，**硬字幕**
  （英上中下，285 条，`MarginV=100`），QSV 烧录 3 分 40 秒（7.54×）
- **字幕文件**：`subtitles/3nFDQMaoNKc.zh.bilingual.srt` / `.ass`（双语，成片用，285 条，
  `MarginV=100`）、`subtitles/3nFDQMaoNKc.en.ass`（英文单语）、
  `subtitles/3nFDQMaoNKc.bilingual.srt`（英文句级底稿）
- **校验**：成片 1657.961s，与原片完全一致（未剪辑）；音轨包数据 MD5 与原片一致
  （`c50b9e96538f15e24b92fbe2fe5a508a`），确认直接复制、无音画偏移；head 60s / tail 20s
  解码无报错；抽帧 00:06:35 / 00:21:20 / 00:25:38，确认英上中下、无裁切

## 备注

- 自动英文字幕错误已修正：`Agnostic / Egentic / agnetic / agendic / a genetic → agentic`、
  `ESON → ESUN`、`Epic → EPYC`、`Open AI → OpenAI`、`OCC → OCP`、`Nord → Norrod`、
  `21-in → 21-inch`、`gigantic rocks → gigantic racks`、`Verona → Verano`
- 全片为 OCP 主题演讲，无赞助口播、无广告段
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集
