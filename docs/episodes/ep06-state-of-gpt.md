# 第 6 期：State of GPT（Andrej Karpathy / Microsoft Build 2023）

- **状态**：已完成
- **信源**：Microsoft Developer 官方频道，<https://www.youtube.com/watch?v=bZQun8Y4L2A>
- **标题**：State of GPT | BRK216HFS
- **规格**：42:40，1080p30（该视频最高画质），官方人工英文字幕（`en-US`），2023-05-25 上传
- **建议标题**：`【AI基建·第6期】Karpathy：GPT 的现状——从预训练到 RLHF，以及如何真正用好大模型（中英双语·43 分钟）`
- **定位**：基础篇 / 方法论，但**不是过时内容**。前五期看的是 2026 年的算力、云与智能体，
  这一期回到“模型是怎么炼成的”：预训练、SFT、奖励模型、RLHF 四段流水线，以及
  “LLM 只会模仿、不会反思”这一影响所有提示词与 Agent 实践的心智模型。演讲发布于 2023 年，
  但底层框架至今仍是理解大模型产品的地图；2026 年回看，反而更容易分清哪些是不变的地基、
  哪些是后来演进的枝节。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 | Microsoft Developer 频道；Microsoft Build 2023 session BRK216HFS；Karpathy 官方幻灯片 |
| 技术/研究 | Karpathy `stateofgpt.pdf`；GitHub 幻灯片镜像；Glasp 全文转录 |
| 独立分析 | TheMind.io、Lawrence Wu 笔记、The Blind Machine、AMTdev |
| 中文媒体 | 澎湃新闻（转机器之心，2023-05-30）、知乎、CSDN、WaytoAGI 全文翻译 |
| 中文视频/切片 | B 站 `BV1Xh4y1x7BT`（GPT-4 双语字幕）、`BV1ts4y1T7UH`（中文字幕版） |
| 数据集/镜像 | Hugging Face `weege007/youtube_videos` |

结论：官方录制之外，至少 10 个不同背景的站点做了笔记、全文翻译、双语字幕或镜像，
未被单一机构垄断版权 → **通过**。B 站已有多个双语版本，制作时需在简介标注官方来源，
并说明本版中文由本地模型重新翻译。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=bZQun8Y4L2A>
- 官方幻灯片：<https://karpathy.ai/stateofgpt.pdf>
- Microsoft Build session：<https://build.microsoft.com/en-US/sessions/db3f4859-cd30-4445-a0cd-553c3304f8e2>
- GitHub 幻灯片镜像：<https://github.com/giachat/State-of-GPT-2023>
- TheMind 分析：<https://www.themind.io/blog-posts/state-of-gpt-andrej-karpathys-talk>
- Lawrence Wu 笔记：<https://lawrencewu.net/posts/2023-06-13-karpathy-state-of-gpt/>
- 澎湃 / 机器之心：<https://www.thepaper.cn/newsDetail_forward_23278327>
- 知乎笔记：<https://zhuanlan.zhihu.com/p/634038281>
- B 站双语版：<https://www.bilibili.com/video/BV1Xh4y1x7BT/>
- Glasp 转录：<https://glasp.co/youtube/p/state-of-gpt-microsoft-build-andrej-karpathy-openai>

## 内容结构（官方章节）

| 时间 | 环节 |
|---|---|
| 00:00 | Intro / 开场 |
| 00:58 | GPT Assistant training pipeline / GPT 助手训练流水线 |
| 02:04 | Data collection / 数据收集 |
| 03:23 | 2 example models / 两个示例模型 |
| 08:13 | Base models learn powerful, general representations / 基座模型学到通用表征 |
| 13:24 | RM Dataset / 奖励模型数据集 |
| 14:05 | RM Training / 奖励模型训练 |
| 18:47 | Mode collapse / 模式坍缩 |
| 25:50 | Ensemble multiple attempts / 多次采样集成 |
| 26:47 | Ask for reflection / 让模型自我反思 |
| 32:13 | Tool use / Plugins / 工具使用与插件 |
| 37:15 | Default recommendations / 默认建议 |

## 简介模板（可直接粘贴）

**一句话提炼**：Karpathy 用 43 分钟把 GPT 助手的训练拆成预训练、SFT、奖励模型与 RLHF 四步，
并解释为什么大模型“只会模仿、不会反思”，以及如何用提示、工具和检索把它用对。
放在 2026 年看，它依然是理解大模型训练与使用的底层地图。

**为什么今天还值得看**

- **训练管线没变**：预训练 → SFT → 奖励模型 → RLHF 仍是今天主流对齐方案的基本盘；
  后来的 DPO、RLAIF、推理模型与 Agent 训练，都能放回这张图里理解。
- **LLM 的心智模型没变**：token 模拟器、不会主动反思、需要提示/工具/检索来补足——
  这些仍是今天写 prompt、做 Agent 的底层假设。
- **方法分层没变**：先把提示和上下文用好，再考虑微调，最后才是 RLHF；
  这个投入产出顺序在今天依然成立。
- **时效说明**：演讲中的产品名、模型版本和数字以 2023 年为准，但四段流水线与使用方法不过时。

**时间戳导航**

```
00:00 开场
00:58 GPT 助手训练流水线
02:04 数据收集
03:23 两个示例模型
08:13 基座模型学到通用表征
13:24 奖励模型数据集
14:05 奖励模型训练
18:47 模式坍缩
25:50 多次采样集成
26:47 让模型自我反思
32:13 工具使用与插件
37:15 默认建议
```

**出处与致谢**：原视频来自 Microsoft Developer 官方频道
（<https://www.youtube.com/watch?v=bZQun8Y4L2A>），本片中英字幕由官方人工英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`State of GPT ｜ BRK216HFS [bZQun8Y4L2A].mkv`，469.8 MB，
  VP9 1920×1080 29.97fps + Opus 48kHz 立体声（eng 原声），2559.84s（42:40），
  整体码率 1.54 Mbps，无字幕
- **字幕**：官方人工英文字幕 `en-US`（1133 条事件，合并为 464 条句级 cue）；
  中文由本地 Qwen3-30B-A3B 翻译 464/464，术语统一为“卡帕西 / 词元 / 词元模拟器 /
  监督微调 / 奖励模型 / 基座模型 / 强化学习 / 检索增强 / 幻觉”，GPT、RLHF、PPO、LoRA 等保留英文
- **成片**：`State of GPT ｜ BRK216HFS [bZQun8Y4L2A] [中英字幕].mkv`，
  492.0 MB（515,922,524 字节），H.264 1920×1080 29.97fps + Opus 48kHz 立体声，
  2559.84s（42:40），整体码率 1.61 Mbps，硬字幕（英上中下），QSV 烧录 3 分 11 秒
- **字幕文件**：`subtitles/bZQun8Y4L2A.zh.bilingual.srt` / `.ass`（双语，MarginV=100）、
  `subtitles/bZQun8Y4L2A.en-US.ass`（英文单语）
- **校验**：时长与源一致（2559.84s）；抽帧 1:40 / 10:00 / 30:00 / 40:00 字幕均在位；
  长中文已换行、无裁切；原片头部 60s / 尾部 30s 与成片尾部 30s 解码均无报错

## 备注

- 该视频为 2023 年 Build 演讲，最高画质 1080p30；格式 616（VP9 标称 5.24 Mbps，Premium）
  与 614（VP9 标称 2.70 Mbps）可选，实际成片约 1.54 Mbps（幻灯片内容码率低）
- 该视频带大量自动配音音轨（de-DE / es-US / fr-FR / hi / id / it / ja / pl），
  必须显式指定原声 `251-8`（Opus 107k）或 `234-8`（AAC），不能用裸 `251`，
  否则 yt-dlp 会报 `Requested format is not available`
- 官方人工英文字幕为 `en-US`（不是自动字幕），适合沿用第 5 期的 `--manual` 人工字幕流程
- 简介中需写明“为什么今天还值得看”：训练管线、LLM 心智模型、方法分层三层参考价值；
  同时注明“产品名与数字以 2023 年为准”，避免把旧版本当成现状
- 中文长行由 `write_ass()` 的 `_wrap_cjk()` 自动换行，本片有 18 条做了二次断行
