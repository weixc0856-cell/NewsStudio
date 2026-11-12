# 第 41 期：机器人不能等模型 — 赵行在 CoRL 2026 谈 System 2/1/0 与多时钟架构

- **状态**：已完成
- **信源**：Conference on Robot Learning 官方频道，CoRL 2026 Day 1 全场直播中的 early-career keynote
  <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=4979s>（2026-11-02 上传；演讲日期 2026-11-09，Austin）
- **出镜**：赵行（Hang Zhao，清华大学交叉信息研究院助理教授、星海图 Galaxea 联合创始人）
- **规格**：27:20，1080p，英语原声，本地 Whisper 转写（直播无字幕轨）
- **建议标题**：`【AI基建·机器人篇】机器人不能等模型：赵行在 CoRL 2026 谈 System 2/1/0 与多时钟架构（中英双语·27 分钟）`
- **定位**：物理 AI 主线的「系统架构」侧。ep40 讲的是英伟达把模型与工具链整套开源，
  这一期讲的是另一个问题：机器人不能像聊天机器人那样等模型思考。赵行按「反应速度」把智能拆成
  System 2 / 1 / 0 三层，用时钟而不是功能来划分边界，并指出今天最缺的不是更快的单模型，
  而是层与层之间的反馈通道。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | CoRL 官方 YouTube 直播；CoRL 2026 Early Career Keynotes 官方页 |
| 行业媒体 / 会议复盘 | 42how 英文报道；Voxel51 的 CoRL 2026 Day 1 复盘 |
| 讲者主页 | 赵行个人主页（Tsinghua MARS Lab）活动与演讲列表 |
| 中文科技媒体 | 42how 中文站、网易科技等对 CoRL 2026 的报道 |

结论：官方直播 + 官方议程页 + 行业媒体复盘 + 讲者主页，未被单一机构垄断 → **通过**。

### 验证链接（留档）

- 官方直播（演讲起点）：<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=4979s>
- CoRL 2026 Early Career Keynotes：<https://2026.corl.org/program/early-career-keynotes>
- 42how 报道：<https://ai.42how.com/en/article/13695ef2-7910-4ef0-88ee-8b760b528662>
- Voxel51 Day 1 复盘：<https://voxel51.com/blog/corl-2026-day-1-robot-policy-latency-memory>
- 赵行主页：<https://hangzhaomit.github.io/index.html#activities>

## 内容结构（按演讲段落整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 主持介绍：清华 MARS Lab 与星海图 |
| 00:57 | 为什么机器人需要「时间」：从自动驾驶到人形机器人 |
| 02:16 | GPT-6 Astra：机器人 97% 的时间在等模型 |
| 04:15 | 五种控制策略与 50 秒时限：慢模型必须配 System 1 |
| 07:29 | 用时钟定义层级：System 2 / 1 / 0 |
| 11:00 | 用「反应对象」判断一层属于哪个时钟 |
| 13:44 | 三个成本：视频生成、文本推理、动作块 |
| 15:00 | FastWAM：跳过测试时的未来画面生成 |
| 17:00 | G0.5：推理开/关，90% 任务没有差别 |
| 18:53 | 层间传什么：意图向下、反馈向上 |
| 22:55 | 失败都发生在层级交接处 |
| 24:02 | 两条未来路线：分层时钟 vs 统一模型 |
| 25:57 | 结论：让模型适配时钟，而不是反过来 |

## 简介模板（可直接粘贴）

**一句话提炼**：赵行把机器人智能按「反应速度」而不是「功能」重新分层：System 2 在秒级处理任务与语言，
System 1 在几十赫兹处理手与物体的相对运动，System 0 在数百赫兹处理接触与力。他用一个很直接的
数字说明问题：前沿模型直接控制机器人时，机器人 97% 的时间在等模型思考。结论不是造一个更快的
万能模型，而是让每一层在自己的时钟上闭环，并把失败与置信度向上反馈。

**时间戳导航**

```
00:00  主持介绍
00:57  为什么机器人需要「时间」
02:16  97% 的时间在等模型
04:15  五种控制策略与 50 秒时限
07:29  用时钟定义层级：System 2/1/0
13:44  三个成本：视频生成、文本推理、动作块
18:53  层间传什么：意图向下、反馈向上
22:55  失败都发生在层级交接处
24:02  分层时钟 vs 统一模型
25:57  结论
```

**出处与致谢**：原视频来自 Conference on Robot Learning 官方频道的 CoRL 2026 Day 1 直播
（<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=4979s>），本片中英字幕由本地 Whisper
转写后翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：直播源 `CoRL2026-Day1 [F_4AAOQsWlA].mkv`，`3,685,435,902 字节（3.43 GiB）`，
  VP9 1920×1080 30fps + Opus 48k 立体声，`8:55:50`，无字幕；交付用无字幕片段
  `CoRL 2026 Hang Zhao Keynote [F_4AAOQsWlA].mkv`，`209,495,684 字节（199.8 MiB）`，
  H.264 1920×1080 30fps + Opus 160k，`1640.100 s（27:20.1）`，1.02 Mbps，
  从直播源 4978.95 s 起裁切
- **字幕**：直播无字幕轨，本地 faster-whisper（medium.en）转写 36:40 窗口 → 354 cue；
  截取 4978.95–6619.00 s → 265 cue；人工校正专名与误听约 20 处（Hang Zhao、Cybercabs、
  GPT-6 Astra、π0.5、RoboCasa、VLA/VLM、FastWAM、G0.7、G0.5、RTX 5090、CoRL、
  Tsinghua MARS Lab、parkour 等），Qwen3-30B-A3B 翻译 265/265，零空译
- **成片**：`… [中英字幕].mkv`，`216,624,352 字节（206.6 MiB）`，H.264 1920×1080 30fps
  + Opus 原音轨（直接复制自无字幕片段），1.06 Mbps，`1640.100 s（27:20.1）`，
  硬字幕（英上中下，265 条，**MarginV=100**，底部白色区域），QSV 烧录 1 分 40 秒
- **字幕文件**：`F_4AAOQsWlA.hang.zh.bilingual.srt/.ass`（成片用）、
  `F_4AAOQsWlA.hang.bilingual.srt`（全段英文）、`F_4AAOQsWlA.hang.en.ass`（全段英文单语）
- **校验**：成片与无字幕片段时长一致（1640.100 s）；音轨包数据 MD5 相同
  （`fc456c59b425e4b8e98319cbb09e2699`）；head/tail 解码无报错；
  抽帧 3 处（30/600/1400 s）确认字幕在底部白色区域，未遮挡幻灯片主体

## 备注

- 源为 8:55:50 的会议直播，本期只截取赵行的 keynote（含主持欢迎词），不含 Q&A。
- 直播无字幕轨，按 README 兜底流程用本地 faster-whisper（medium.en）转写，再人工校正专名。
- 本期为纯技术内容，无 §7 时政 / 新闻风险段。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
