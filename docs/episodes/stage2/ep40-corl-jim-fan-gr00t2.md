# 第 40 期：从「做梦」到「做事」 — Jim Fan 在 CoRL 2026 发布 GR00T 2

- **状态**：已完成
- **信源**：Conference on Robot Learning 官方频道，CoRL 2026 Day 1 全场直播中的主题演讲段
  <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=20483s>（2026-11-02 上传；演讲日期 2026-11-09，Austin）
- **出镜**：Jim Fan（范麟熙，NVIDIA 机器人研究总监、杰出科学家）
- **规格**：17:40，1080p，英语原声，本地 Whisper 转写（直播无字幕轨）
- **建议标题**：`【AI基建·机器人篇】GR00T 2：从「做梦」到「做事」——Jim Fan 在 CoRL 2026 谈世界动作模型与开源机器人栈（中英双语·17 分钟）`
- **定位**：物理 AI 主线的「模型与栈」侧。ep31/33 算的是产线，ep39 算的是数据从哪来；
  这一期是 NVIDIA 给出的答案：20 亿参数的世界动作模型在一个扩散过程里同时预测未来画面与动作，
  用 X-Adapt 把人类视频、动捕、仿真数据零样本迁移到机器人，再把模型、仿真引擎、智能体框架、
  标注工具、训练数据与硬件图纸整套开源。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始活动 | CoRL 官方 YouTube 直播；NVIDIA GEAR 实验室 GR00T 2 项目页与白皮书 |
| 行业媒体 | Humanoids Daily、RobotsBeat、42how（英文版） |
| 中文科技媒体 | 网易科技、知乎专栏、新浪财经、今日头条 |
| 视频二次传播 | B 站中文字幕剪辑（BV1gnWM6NEaZ） |

结论：官方直播 + 项目页/白皮书 + 多家行业与中文媒体独立报道 + B 站二次剪辑，未被单一机构垄断 → **通过**。

### 验证链接（留档）

- 官方直播（演讲起点）：<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=20483s>
- NVIDIA GR00T 2 项目页：<https://research.nvidia.com/labs/gear/gr00t-2/>
- Humanoids Daily：<https://www.humanoidsdaily.com/news/nvidia-gr00t-2-world-action-model-corl-2026>
- RobotsBeat：<https://robotsbeat.com/briefs/nvidia-jim-fan-uncut-autonomous-robot-demo-corl/>
- 42how 英文报道：<https://ai.42how.com/en/article/a0bbf892-c067-43c5-9ae2-dc13cf0d3b90>
- 网易科技：<https://www.163.com/dy/article/LBGVH2JO0556CQ0L_pdya11y.html>
- 知乎专栏：<https://zhuanlan.zhihu.com/p/2103536647686174305>
- B 站中文字幕剪辑：<https://www.bilibili.com/video/BV1gnWM6NEaZ/>

## 内容结构（按演讲段落整理）

| 时间 | 环节 |
|---|---|
| 00:00 | 主持介绍：NVIDIA 机器人研究总监 Jim Fan |
| 00:22 | 开场：Astra 发布与「机器人学的五个阶段」 |
| 02:35 | 正确的问题不是 System 1 还要不要，而是「什么是一个好技能」 |
| 02:44 | GR00T 2：20 亿参数的世界动作模型，一个扩散过程同时出画面与动作 |
| 03:44 | 演示：换内存条、UPS 贴标、粗盐过滤、长程清理 |
| 05:53 | X-Adapt：人类第一人称视频、动捕、外骨骼数据零样本迁移 |
| 07:15 | DexUMI：与机器人手一比一机械映射的外骨骼 |
| 08:20 | 仿真：Isaac Lab 强化学习 + 域随机化，零样本回到真实世界 |
| 10:26 | 统一认知：WAM API 把推理与物理拆开，Astra 在画面上画引导 |
| 11:34 | WAM Edit：Astra 监控本体感知，只在必要时修正动作 |
| 12:45 | Aspire：智能体框架把代码技能与 GR00T 2 串起来 |
| 14:58 | 开源清单：GR00T 2 / Turbo 权重、X-Adapt 配方、Sim Foundry、Aspire、Flora、Human One Million、硬件图纸 |
| 16:51 | 「还有一件事」：实时自主点火演示 |
| 17:31 | 结尾：夏天来了 |

## 简介模板（可直接粘贴）

**一句话提炼**：Jim Fan 把机器人基础模型的问题重新定义了一遍：不是「System 1 还需不需要」，
而是「什么才算一个好技能」——能靠演示教、能靠推理引导、能跨具身迁移。GR00T 2 用 20 亿参数的
世界动作模型在一次扩散里同时预测未来画面和动作；X-Adapt 把人类视频、动捕和仿真数据零样本搬到
机器人手上；配套的 Sim Foundry、Aspire、Flora、Human One Million 与硬件图纸则整套开源。
他的判断很直接：前沿模型降低了机器人学的门槛，机器人不再是精英运动。

**时间戳导航**

```
00:00  主持介绍
00:22  开场：Astra 与机器人学的五个阶段
02:35  什么才算一个好技能
02:44  GR00T 2：世界动作模型
03:44  自主演示：内存条、贴标、化学实验
05:53  X-Adapt：人类数据零样本迁移
07:15  DexUMI 外骨骼
08:20  仿真与 Isaac Lab
10:26  WAM API：把推理与物理拆开
11:34  WAM Edit：必要时才修正
12:45  Aspire 智能体框架
14:58  开源清单
16:51  还有一件事
17:31  夏天来了
```

**出处与致谢**：原视频来自 Conference on Robot Learning 官方频道的 CoRL 2026 Day 1 直播
（<https://www.youtube.com/watch?v=F_4AAOQsWlA&t=20483s>），本片中英字幕由本地 Whisper
转写后翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：直播源 `CoRL2026-Day1 [F_4AAOQsWlA].mkv`，`3,685,435,902 字节（3.43 GiB）`，
  VP9 1920×1080 30fps + Opus 48k 立体声，`32150.021 s（8:55:50）`，无字幕；
  交付用无字幕片段 `CoRL 2026 Jim Fan Keynote [F_4AAOQsWlA].mkv`，`418,933,815 字节（399.5 MiB）`，
  H.264 1920×1080 30fps + Opus 160k，`1060.308 s（17:40.3）`，3.16 Mbps，
  从直播源 20483.30 s 起裁切
- **字幕**：直播无字幕轨，按 README 兜底流程用本地 faster-whisper（medium.en）转写
  20:40 窗口 → 238 cue；截取 103.30–1163.60 s → 200 cue；人工校正专名与误听约 40 处
  （GR00T 2、X-Adapt、DexUMI、Isaac Lab、Jetson AGX Thor/Orin、Astra、teleop、
  Sim Foundry、Aspire、Flora 等），Qwen3-30B-A3B 翻译 200/200，零空译
- **成片**：`… [中英字幕].mkv`，`399,279,753 字节（380.8 MiB）`，H.264 1920×1080 30fps
  + Opus 原音轨（直接复制自无字幕片段），3.01 Mbps，`1060.308 s（17:40.3）`，
  硬字幕（英上中下，200 条，**MarginV=100**，底部白色区域（覆在 CoRL 会议横幅文字上）），
  QSV 烧录 1 分 40 秒
- **字幕文件**：`F_4AAOQsWlA.zh.bilingual.srt/.ass`（成片用）、`F_4AAOQsWlA.bilingual.srt`（全段英文）、
  `F_4AAOQsWlA.en.ass`（全段英文单语）
- **校验**：成片与无字幕片段时长一致（1060.308 s）；音轨包数据 MD5 相同
  （`713d1fd37263c7083afa0a2485eacc5c`）；head/tail 解码无报错；
  抽帧 2 处（30/600 s）确认字幕落在底部白色区域，未遮挡幻灯片主体

## 备注

- 源为 8:55:50 的会议直播，本期只截取 Jim Fan 演讲段（含主持介绍与致谢），其余场次不收录。
- 直播无字幕轨，按 README 兜底流程用本地 faster-whisper（medium.en）转写，再人工校正专名。
- 本期为纯技术内容，无 §7 时政 / 新闻风险段。
- 按 2026-10-29 起生效的长期默认（`CLAUDE.md`），本期不做高光切片与片头合集。
