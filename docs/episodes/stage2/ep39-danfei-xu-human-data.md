# 第 39 期：从人类经验里学机器人 — Danfei Xu 谈人类数据、EgoMimic 与 EgoVerse

- **状态**：已完成
- **信源**：Stanford Online（Stanford Robotics Seminar ENGR319 / AA289），
  <https://www.youtube.com/watch?v=NUtaN10cVDc>（2026-04-10 讲座，2026-04-21 上传）
- **出镜**：Danfei Xu（佐治亚理工学院交互计算学院教授，NVIDIA 研究员）
- **规格**：69:07（4147 s），1080p，英语原声，自动字幕
- **建议标题**：`【AI基建·机器人篇】从人类经验里学机器人：Danfei Xu 谈人类数据、EgoMimic 与 EgoVerse（中英双语·69 分钟）`
- **定位**：物理 AI 主线的「数据侧」——如果说第 31/33 期算的是产线与 BOM、第 22 期算的是算力，
  这一期算的是「数据从哪来」：人类第一人称视频能不能替代遥操作？三个假设（能力随人类数据扩展、
  人类数据会多到不知怎么用、进步需要同时扩展科学与规模），以及 EgoMimic、EgoBridge、
  EgoVerse 这条研究路线。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | Stanford Robotics Center 活动页；Stanford Robotics Seminar 日程；Stanford Online 视频 |
| 学术 | EgoVerse 论文（arXiv:2604.07607，Stanford / UCSD / ETH / Georgia Tech 等） |
| 文字稿 / 摘要站 | Summify、Podwise、CourseHive 课程页 |
| 中文媒体 | 小红书讲座笔记；B 站 WhynotTV #5（Danfei Xu 专访，覆盖同一批工作） |

结论：官方活动页 + 论文 + 多家摘要站 + 中文二次传播，未被单一机构垄断 → **通过**。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=NUtaN10cVDc>
- Stanford SRC 活动页：<https://src.stanford.edu/src-events/bot4nbr3a8ykux3lkkyvea47c9dmt0-3r4ac-jymyn-yef4t-34mft-2m575-r7k3h-6lyd5-9wygr-e2s42>
- 研讨会日程：<https://stanfordasl.github.io/robotics_seminar/>
- EgoVerse 论文：<https://arxiv.org/html/2604.07607>
- Summify：<https://summify.io/discover/stanford-robotics-seminar-engr319-spring-2026-robot-learning-NUtaN1>
- Podwise：<https://beta.podwise.ai/episodes/8439574>
- B 站 WhynotTV #5：<https://www.bilibili.com/list/14145636?oid=116499075303246&bvid=BV1usRgBEESe>

## 内容结构（官方章节）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场：三个假设 |
| 01:33 | 瓶颈问题：遥操作能教什么、教不了什么 |
| 05:39 | EgoMimic：用第一人称人类视频扩展模仿学习 |
| 13:14 | 跨域对齐：EgoBridge 与表示学习 |
| 19:55 | 移动操作：没有「移动遥操作」这回事 |
| 24:54 | 规模化：2 万小时人类数据与对数线性扩展 |
| 35:48 | 涌现迁移：跨具身与人类预训练 |
| 41:50 | EgoVerse：全球第一人称人类数据协作平台 |
| 53:40 | 结论与问答 |

## 简介模板（可直接粘贴）

**一句话提炼**：Danfei Xu 把「机器人从人类经验里学习」拆成两个耦合问题：从人类经验里提取
物理智能的先验，再把这些先验落到机器人的具身上。EgoMimic 用第一人称视频替代大量遥操作，
EgoBridge 做跨域对齐，EgoVerse 把全球的第一人称人类数据组织成可协作的数据集；
他也直说了局限——没有「移动遥操作」，跨具身迁移依赖数据对齐，规模化的收益不是免费的。

**时间戳导航**

```
00:00  三个假设
01:33  瓶颈：遥操作教不了什么
05:39  EgoMimic：用人类视频扩展模仿学习
13:14  EgoBridge：跨域对齐
19:55  移动操作为什么难
24:54  2 万小时人类数据的扩展曲线
35:48  涌现迁移与跨具身
41:50  EgoVerse：全球数据协作平台
53:40  结论与问答
```

**出处与致谢**：原视频来自 Stanford Online 的 Stanford Robotics Seminar（ENGR319 / AA289）
（<https://www.youtube.com/watch?v=NUtaN10cVDc>），本片中英字幕由自动英文字幕翻译整理，
仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`Stanford Robotics Seminar ENGR319 ｜ Spring 2026 ｜ Robot Learning from Human Experience [NUtaN10cVDc].mkv`，
  `327,791,444 字节（313 MiB）`，VP9 1920×1080 30fps + Opus 48k 立体声，69:07.421，无字幕
- **字幕**：源仅自动英文字幕（youtube-transcript-api 1714 段 → 753 cue，人工校正专名与漏译 20 处）；
  Qwen3-30B-A3B 逐条翻译 753/753，零空译；无 §7 切除，时间轴与原片一致
- **成片**：`… [中英字幕].mkv`，`748,400,426 字节（714 MiB）`，H.264 1920×1080 30fps
  + Opus **原音轨（直接复制）**，1.44 Mbps，`69:07.421（4147.421 s）`，
  硬字幕（英上中下，753 条，**MarginV=120**），QSV 烧录 4 分 35 秒（15.1×）
- **字幕文件**：`NUtaN10cVDc.zh.bilingual.srt/.ass`（成片用）、`NUtaN10cVDc.bilingual.srt`（全片英文）、
  `NUtaN10cVDc.en.ass`（全片英文单语）
- **校验**：成片时长与原片一致（4147.421 s）；音轨包数据 MD5 与原片相同
  （`986573b5c5d9c02e1c4d69167d79ba91`）；head/tail 解码无报错；
  抽帧 3 处确认字幕位置正常（讲座幻灯片画面，未遮挡幻灯片内容）

## 备注

- 本期为纯技术内容，无需 §7 切除，时间轴与原片一致。
- 自动字幕专名已人工校正（EgoMimic、EgoVerse、teleoperation 等）。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
