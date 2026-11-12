# 第 43 期：把西西弗斯的石头推上山 — Wolfram Burgard 在 CoRL 2026 谈具身智能的三次尝试

- **状态**：已完成
- **信源**：Conference on Robot Learning 官方频道，CoRL 2026 Day 1 全场直播中的 keynote
  <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=26345s>（2026-11-02 上传；演讲日期 2026-11-09，Austin）
- **出镜**：Wolfram Burgard（纽伦堡工业大学教授，《概率机器人学》作者之一）
- **规格**：57:43，1080p，英语原声，本地 Whisper 转写（直播无字幕轨）
- **建议标题**：`【AI基建·机器人篇】把西西弗斯的石头推上山：Wolfram Burgard 在 CoRL 2026 谈具身智能的三次尝试（中英双语·58 分钟）`
- **定位**：物理 AI 主线的「学科复盘」侧。ep40 是模型与栈、ep41 是分层时钟、ep42 是多智能体交互，
  这一期是三十年视角的复盘：概率机器人学、深度学习、基础模型三次把石头推上山，
  各自在什么地方滑下来，以及他为什么认为触觉与力是下一段路的关键。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | CoRL 官方 YouTube 直播；CoRL 2026 Keynotes 官方页 |
| 学术活动 | Northwestern CRB Seminar 同名讲座（2026-04-22）页面 |
| 中文科技媒体 | 今日头条逐段复盘；TheBotage 中文解读 |
| 会议信息站 | AI What's On、Physical AI Lab 的 CoRL 2026 日程页 |

结论：官方直播 + 官方议程页 + 同名学术讲座 + 多家中文复盘，未被单一机构垄断 → **通过**。

### 验证链接（留档）

- 官方直播（演讲起点）：<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=26345s>
- CoRL 2026 Keynotes：<https://2026.corl.org/program/keynotes>
- 今日头条复盘：<https://www.toutiao.com/article/7707147102774411830/>
- TheBotage 解读：<https://www.thebotage.com/article-30529.html>
- Northwestern CRB Seminar：<https://www.mccormick.northwestern.edu/events/event-info.php?eid=641442>

## 内容结构（按演讲段落整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 主持介绍：Dieter Fox 介绍三十年的老朋友 |
| 00:12 | Burgard 开场：第一次全会演讲 |
| 05:50 | 西西弗斯：机器人学的三次推石头上山 |
| 08:06 | 第一次：《概率机器人学》与自动驾驶 |
| 13:31 | 第二次：深度学习与语义分割 |
| 18:31 | 第三次：基础模型与它的边界 |
| 31:00 | VLA：端到端还是组合式 |
| 37:23 | 触觉：FlowTouch 与触觉预测 |
| 42:01 | 力控制：WrenchACT 与 Siemens 合作 |
| 53:07 | 工业落地与统一评测 |
| 57:41 | 结语：石头终于推上山顶 |

## 简介模板（可直接粘贴）

**一句话提炼**：Burgard 用西西弗斯的故事复盘机器人学三十年：概率方法把状态估计做到毫米级，
但依赖高精地图与手工建模；深度学习解决了感知，却要求预先枚举世界类别；基础模型能理解开放世界，
却只输出位置、缺少力与触觉反馈。他的判断是，下一步不是再换一块更大的石头，
而是把触觉、力与多模态反馈补进模型与评测里——这也是他实验室 FlowTouch、WrenchACT
与工业合作项目在做的事。

**时间戳导航**

```
00:00  主持介绍
00:12  开场：第一次全会演讲
05:50  西西弗斯与三次尝试
08:06  概率机器人学与自动驾驶
13:31  深度学习阶段
18:31  基础模型阶段
31:00  VLA：端到端还是组合式
37:23  触觉：FlowTouch
42:01  力控制：WrenchACT
53:07  工业落地与评测
57:41  结语
```

**出处与致谢**：原视频来自 Conference on Robot Learning 官方频道的 CoRL 2026 Day 1 直播
（<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=26345s>），本片中英字幕由本地 Whisper
转写后翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：直播源 `CoRL2026-Day1 [F_4AAOQsWlA].mkv`，`3,685,435,902 字节（3.43 GiB）`，
  VP9 1920×1080 30fps + Opus 48k 立体声，`8:55:50`，无字幕；交付用无字幕片段
  `CoRL 2026 Wolfram Burgard Keynote [F_4AAOQsWlA].mkv`，`567,692,697 字节（541.4 MiB）`，
  H.264 1920×1080 30fps + Opus 160k，`3463.508 s（57:43.5）`，1.31 Mbps，
  从直播源 26344.50 s 起裁切
- **字幕**：直播无字幕轨，本地 faster-whisper（medium.en）转写 60:20 窗口 → 555 cue；
  截取 26344.50–29808.00 s → 537 cue；人工校正专名与误听 7 处（Dieter Fox、Björn Ommer、
  Probabilistic Robotics、WrenchACT、policy ACT 等）；因批量翻译出现整段错行，
  改用逐句模式重译 537/537，零空译
- **成片**：`… [中英字幕].mkv`，`583,045,613 字节（556.1 MiB）`，H.264 1920×1080 30fps
  + Opus 原音轨（直接复制自无字幕片段），1.35 Mbps，`3463.508 s（57:43.5）`，
  硬字幕（英上中下，537 条，**MarginV=100**，底部白色区域），QSV 烧录 4 分 00 秒
- **字幕文件**：`F_4AAOQsWlA.burgard.zh.bilingual.srt/.ass`（成片用）、
  `F_4AAOQsWlA.burgard.bilingual.srt`（全段英文）、`F_4AAOQsWlA.burgard.en.ass`（全段英文单语）
- **校验**：成片与无字幕片段时长一致（3463.508 s）；音轨包数据 MD5 相同
  （`732721675f94a1d7daf6014563bf1d3f`）；head/tail 解码无报错；
  抽帧 3 处（30/1500/3400 s）确认字幕在底部白色区域，未遮挡幻灯片主体

## 备注

- 源为 8:55:50 的会议直播，本期只截取 Burgard 的 keynote（含主持欢迎词），不含 Q&A。
- 直播无字幕轨，按 README 兜底流程用本地 faster-whisper（medium.en）转写，再人工校正专名。
- 本期为纯技术内容，无 §7 时政 / 新闻风险段。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
