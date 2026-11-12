# 第 42 期：让机器人学会互相配合 — Negar Mehr 在 CoRL 2026 谈多智能体协调与持续学习

- **状态**：已完成
- **信源**：Conference on Robot Learning 官方频道，CoRL 2026 Day 1 全场直播中的 early-career keynote
  <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=21660s>（2026-11-02 上传；演讲日期 2026-11-09，Austin）
- **出镜**：Negar Mehr（加州大学伯克利分校机械工程系助理教授，Berkeley ICON Lab 负责人）
- **规格**：25:49，1080p，英语原声，本地 Whisper 转写（直播无字幕轨）
- **建议标题**：`【AI基建·机器人篇】让机器人学会互相配合：Negar Mehr 在 CoRL 2026 谈多智能体协调与持续学习（中英双语·26 分钟）`
- **定位**：物理 AI 主线的「交互与学习」侧。ep39 讲数据、ep40 讲模型与栈、ep41 讲分层时钟，
  这一期讲的是机器人如何与另一个机器人（或人）配合：为什么多智能体模仿学习更难、
  为什么多智能体 RL 学不会协调、基础模型能不能当教练，以及多智能体的共识视角
  如何反过来解决单智能体的灾难性遗忘。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | CoRL 官方 YouTube 直播；CoRL 2026 Early Career Keynotes 官方页 |
| 高校 / 实验室 | UC Berkeley BAIR 的 CoRL 2026 参会汇总；Berkeley ICON Lab 主页 |
| 学术活动 | Stanford Robotics Center 同名讲座页面 |
| 中文科技媒体 | AI 热报、BAIR 中文转载等 |

结论：官方直播 + 官方议程页 + BAIR / 实验室页面 + 中文二次传播，未被单一机构垄断 → **通过**。

### 验证链接（留档）

- 官方直播（演讲起点）：<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=21660s>
- CoRL 2026 Early Career Keynotes：<https://2026.corl.org/program/early-career-keynotes>
- BAIR 参会汇总：<https://theaitoday.com/bair-at-corl-2026/>
- 中文转载：<https://airebao.com/item/55910>
- Stanford Robotics Center 活动页：<https://src.stanford.edu/src-events/bot4nbr3a8ykux3lkkyvea47c9dmt0-3r4ac-jymyn-yef4t-34mft-2m575-r7k3h-6lyd5-9wygr-5rsgw>

## 内容结构（按演讲段落整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 主持欢迎 |
| 00:05 | 开场：机器人已经很强，下一步是进入我们的生活 |
| 00:21 | 为什么现在要研究多智能体交互 |
| 02:41 | 两人抬篮子的例子：去中心化策略与隐式耦合 |
| 03:18 | 模仿学习：多智能体和单智能体的差别 |
| 07:33 | 扩散策略与去中心化执行 |
| 08:29 | 冻结已有技能，只学协调修正 |
| 10:24 | 强化学习为什么学不会协调 |
| 11:42 | 让基础模型当教练 |
| 16:38 | 教练还要会做信用分配 |
| 17:42 | 反过来：多智能体经验用于单智能体持续学习 |
| 19:15 | 把持续学习看成时间共识 |
| 22:32 | 用 π0.5 验证：SFT 会忘，共识不会 |
| 25:38 | 结语与致谢 |

## 简介模板（可直接粘贴）

**一句话提炼**：Negar Mehr 把「机器人怎么配合」拆成三个问题：多智能体模仿学习为什么难
（一个机器人稍微偏离，整个协作就失败，所以要看可利用性而不是价值差）；多智能体 RL 为什么难
（信用分配），于是让基础模型当教练、当信用设计者；最后再把多智能体的共识视角反过来用在
单智能体持续学习上——把「不要忘记旧任务」写成一个参数空间的时间共识，做到无需回放的微调。

**时间戳导航**

```
00:00  主持欢迎
00:05  开场：机器人进入我们的生活
02:41  两人抬篮子：去中心化与隐式耦合
03:18  多智能体模仿学习难在哪
07:33  扩散策略与去中心化执行
08:29  冻结技能，只学协调修正
10:24  多智能体 RL 的困境
11:42  让基础模型当教练
16:38  教练与信用分配
17:42  多智能体经验用于持续学习
19:15  持续学习作为时间共识
22:32  π0.5 实验：SFT 会忘，共识不会
25:38  结语
```

**出处与致谢**：原视频来自 Conference on Robot Learning 官方频道的 CoRL 2026 Day 1 直播
（<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=21660s>），本片中英字幕由本地 Whisper
转写后翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：直播源 `CoRL2026-Day1 [F_4AAOQsWlA].mkv`，`3,685,435,902 字节（3.43 GiB）`，
  VP9 1920×1080 30fps + Opus 48k 立体声，`8:55:50`，无字幕；交付用无字幕片段
  `CoRL 2026 Negar Mehr Keynote [F_4AAOQsWlA].mkv`，`267,658,208 字节（255.3 MiB）`，
  H.264 1920×1080 30fps + Opus 160k，`1549.500 s（25:49.5）`，1.38 Mbps，
  从直播源 21659.54 s 起裁切
- **字幕**：直播无字幕轨，本地 faster-whisper（medium.en）转写 74 分钟窗口 → 667 cue；
  截取 21659.54–23209.00 s → 271 cue；人工校正专名与误听 8 处（Negar Mehr、MAPPO/HAPPO/LIPO、
  π0.5、TACO、EWC、replay 等），Qwen3-30B-A3B 翻译 271/271，零空译
- **成片**：`… [中英字幕].mkv`，`275,149,040 字节（262.4 MiB）`，H.264 1920×1080 30fps
  + Opus 原音轨（直接复制自无字幕片段），1.42 Mbps，`1549.500 s（25:49.5）`，
  硬字幕（英上中下，271 条，**MarginV=100**，底部白色区域），QSV 烧录 2 分 00 秒
- **字幕文件**：`F_4AAOQsWlA.negar.zh.bilingual.srt/.ass`（成片用）、
  `F_4AAOQsWlA.negar.bilingual.srt`（全段英文）、`F_4AAOQsWlA.negar.en.ass`（全段英文单语）
- **校验**：成片与无字幕片段时长一致（1549.500 s）；音轨包数据 MD5 相同
  （`d1950579472a6dd05090716c3a7fdb3a`）；head/tail 解码无报错；
  抽帧 3 处（30/700/1500 s）确认字幕在底部白色区域，未遮挡幻灯片主体

## 备注

- 源为 8:55:50 的会议直播，本期只截取 Negar Mehr 的 keynote（含主持欢迎词），不含 Q&A。
- 直播无字幕轨，按 README 兜底流程用本地 faster-whisper（medium.en）转写，再人工校正专名。
- 本期为纯技术内容，无 §7 时政 / 新闻风险段。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
