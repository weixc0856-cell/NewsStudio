# 第 36 期：黄仁勋 CSIS 对谈 — 平台五层栈、能源约束与「任务不是工作」

- **状态**：已完成
- **信源**：Associated Press（CSIS 活动直播录像），<https://www.youtube.com/watch?v=OT_9HqGQzhw>
- **原事件**：CSIS fireside chat「Securing U.S. Leadership in AI」，2025-12-03，主持 John Hamre（CSIS 总裁）
- **出镜**：Jensen Huang（NVIDIA 创始人兼 CEO）
- **规格**：51:52（3112.381 s），1080p30 VP9，英语原声，自动字幕
- **建议标题**：`【AI基建·第36期】黄仁勋 CSIS 对谈：平台五层栈、能源约束，以及「任务不是工作」（中英双语·15 分钟）`
- **定位**：把「AI 基建」讲成一套可拆的栈——能源、芯片、软件/基础设施、模型、应用；并给出两个
  工程判断：算力需求的速度超过能效改进的速度，所以必须自己解决电力；以及「任务」会被自动化、
  「工作」不会——放射科与软件工程师是两个可验证的例子。

> 选题说明：CSIS 官方章节里 China AI competition、Geopolitics and markets、Industrial policy、
> National security and tech 四章（约 26 分钟）按 §7 整章切除；保留了平台、能源、机器人、
> 任务与工作四段技术内容，成片 15:19。原始完整录像仍保留在 `downloads/`。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | CSIS 活动（主持人 John Hamre）；Associated Press 直播录像 |
| 国际媒体 | The National《Nvidia's Jensen Huang courts Washington amid China chip export debate》、Times of India、Global Times（中方视角报道） |
| 财经媒体 | Yahoo Finance / Barchart《'We've Done Our Country a Great Disservice' by Offshoring》 |
| 中文媒体 | 环球时报（Global Times 中文稿）、国内科技媒体转述 |

结论：官方活动 + 国际媒体 + 财经媒体 + 中文媒体独立报道同一场对谈与同一组观点 → **通过**。

### 验证链接（留档）

- 原始视频：<https://www.youtube.com/watch?v=OT_9HqGQzhw>
- The National：<https://www.thenationalnews.com/future/technology/2025/12/03/jensen-huang-washington-china-nvidia/>
- Global Times：<https://www.globaltimes.cn/page/202512/1349940.shtml>
- Times of India：<https://timesofindia.indiatimes.com/technology/tech-news/nvidia-ceo-jensen-huang-on-his-warning-and-and-clarification-to-americans-that-china-is-winning-the-ai-race-let-me-simplify-this-/articleshow/126103244.cms>
- Yahoo Finance：<https://finance.yahoo.com/news/ve-done-country-great-disservice-165645441.html>
- Barchart：<https://www.barchart.com/story/news/37069799/it-makes-no-sense-to-me-nvidias-jensen-huang-slams-americans-who-vilified-energy-praises-trump-for-sticking-his-neck-out>

## 内容结构（成片时间轴）

| 时间 | 环节 |
|---|---|
| 00:00 | 什么是「平台」：技术公司里最底层的那一层 |
| 01:19 | 五层栈：能源 → 芯片 → 软件与基础设施 → 模型 → 应用 |
| 02:25 | 模型层与应用层：150 万个 AI 模型，CUDA 是共同语言 |
| 06:07 | 能源约束：不能指望现成电网，要建在表后（behind the meter） |
| 08:48 | 机器人：视频生成模型为什么能迁移到电机 |
| 10:20 | 大学里的三种态度：工程、科学与人文学科 |
| 11:14 | 任务 vs 工作：放射科医生为什么没失业 |
| 13:10 | 软件工程师与财务分析师：同一个逻辑 |
| 15:10 | 收尾：写作用的 AI 与 MRI 玩笑 |

## 简介模板（可直接粘贴）

**一句话提炼**：黄仁勋在 CSIS 把 AI 拆成五层栈：能源、芯片、软件与基础设施、模型、应用；
他算的两笔账是——能效每年提升 5–10 倍，但需求每年涨得更多，所以必须自己解决电力；
以及「任务」会被自动化、「工作」不会，放射科与软件工程师就是两个已经发生的例子。

**时间戳导航**

```
00:00  什么是平台：站在最底层
01:19  五层栈：能源、芯片、软件、模型、应用
02:25  150 万个模型与 CUDA
06:07  能源约束：建在表后，不等电网
08:48  机器人：从视频生成到电机控制
11:14  任务不是工作：放射科的例子
13:10  软件工程师与财务分析师
```

**出处与致谢**：原视频来自 Associated Press 对 CSIS 活动的公开直播录像
（<https://www.youtube.com/watch?v=OT_9HqGQzhw>），本片中英字幕由自动英文字幕翻译整理，
仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`LIVE： NVIDIA CEO Jensen Huang speaks on securing US leadership in AI [OT_9HqGQzhw].mkv`，
  `654,060,797 字节（624 MiB）`，VP9 1920×1080 29.998fps + Opus 48k 立体声，51:52.381，无字幕
- **字幕**：源仅自动英文字幕（youtube-transcript-api 1200 段 → 624 cue，人工校正 12 处）；
  按 §7 切段后 185 cue；Qwen3-30B-A3B 逐条翻译 185/185，零空译，人工订正 2 处
- **成片**：`… [中英字幕].mkv`，`211,228,706 字节（201 MiB）`，H.264 1920×1080 29.998fps + Opus 160k，
  1.84 Mbps，`15:19.142（919.142 s）`，硬字幕（英上中下，185 条，**MarginV=280**，
  抬到常驻 CSIS 横幅上方），QSV 烧录 1 分 34 秒（9.8×）
- **字幕文件**：`OT_9HqGQzhw.zh.bilingual.srt/.ass`（成片用）、`OT_9HqGQzhw.bilingual.srt`（全片英文）、
  `OT_9HqGQzhw.en.ass`（全片英文单语）
- **校验**：成片时长 919.142 s = 原片 3112.381 − 切除 2193.239 s；原片音轨 MD5
  `8ddc0b57b87a1848cd3418f14cd8512b`（因删段重编码，仅留档）；head/tail 解码无报错；
  5 个接缝音频互相关 0.983–1.000、偏移 −9.5 ~ +1.5 ms；抽帧 3 处确认字幕在横幅上方

## 备注

- 按 §7 整章切除：China AI competition（8:05–16:01）、Geopolitics and markets（16:01–23:40）、
  Industrial policy（23:40–30:36）、National security and tech（30:36–34:03）；
  另逐句切除：开场国家安全框架（0:00–1:43）、政府能源政策表态（3:02–3:17）、
  中美发电量对比（34:03–34:23）、「联邦优先权」评论与机器人中国占比（36:59–37:39）、
  中美日德机器人能力对比（39:13–41:19）、结尾华盛顿与产业政策表述（46:39–51:52）。
- 源视频只有自动英文字幕，专名已人工校正（ChatGPT、Anthropic、Claude、xAI、Grok、CUDA、moat）。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
