# 第 22 期：Waymo 的算力账 — 从 2 亿英里到 5nm 自研芯片

- **状态**：已完成
- **信源**：Hot Chips 2026 官方频道，<https://www.youtube.com/watch?v=3X6NN1csAF4>
  （Hot Chips 2026，斯坦福纪念礼堂，2026-08-24 下午主题演讲；2026-09-09 上传）
- **标题**：HC2026-K: Compute in Motion: Challenges of Autonomous Driving
- **讲者**：丹尼尔·罗森班德（Daniel Rosenband，Waymo 计算负责人）× 克里夫·杨
  （Cliff Young，Google，主持）
- **规格**：原片 1:04:03，1080p60（VP9，最高画质），YouTube 自动英文字幕（无人工字幕），
  画面为幻灯片 + 讲者 + 视频，无硬字幕
- **建议标题**：`【AI基建·第22期】Waymo 的算力账：2 亿英里、5nm 自研芯片与“超人驾驶员”（中英双语·64 分钟）`
- **定位**：物理 AI / 车规算力篇，接第 21 期“CPU 成为 AI 新瓶颈”。上一期讲数据中心里的算力
  结构，本期把镜头移到车里：同样的问题——延迟、带宽、冗余、成本——在一台“披萨盒”大小的
  计算平台上怎么解。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始演讲 | Hot Chips 2026 官方视频（HC38，2026-08-24）；Waymo 官方博客《A look under our trunk》 |
| 技术媒体 | ServeTheHome、SiliconANGLE、Design News、AI Business、Silicon Republic、Gigazine |
| 中文媒体 | 36Kr / 汽车之心、OFweek、智东西、EET-China、新浪财经、网易 |
| 国际 / 财经媒体 | MK（韩国）、3DNews（俄罗斯）、Axios、DutchStartup.ai |
| 独立分析 / 对照 | TeslAnt（指出 1000 TOPS 是前端多芯片合计，单芯片 160 TOPS INT8）、neXt Curve 播客 |

结论：Hot Chips 官方发布完整演讲，Waymo 官方博客提前披露芯片细节，ServeTheHome、
SiliconANGLE、Design News、AI Business 等从芯片架构角度独立报道，中文与韩国、俄罗斯媒体
做了完整编译，Axios 从商业化与监管角度跟进 → **通过**。

> 注意：芯片算力与事故率均为 Waymo 自报口径。1000 TOPS 指车辆前端多颗芯片的合计 ML 能力，
> 单颗 ASIC 在 Hot Chips 上披露的稠密 INT8 为 160 TOPS；13 倍事故率差异也未经第三方审计。
> 本期保留这些原始表述，并在简介中标注口径。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=3X6NN1csAF4>
- Hot Chips 2026：<https://hotchips.org/>
- Waymo 官方博客：<https://waymo.com/blog/2026/08/look-under-our-trunk/>
- ServeTheHome：<https://www.servethehome.com/infineon-risc-v-for-automotive-at-hot-chips-2026/>
- SiliconANGLE：<https://siliconangle.com/2026/08/20/waymo-details-the-custom-chip-in-its-autonomous-driving-system/>
- Design News：<https://www.designnews.com/automotive-engineering/waymo-unveils-custom-5nm-asic-to-power-real-time-autonomous-driving-with-1000-tops-performance>
- AI Business：<https://aibusiness.com/generative-ai/waymo-develops-own-chip-for-self-driving>
- 36Kr / 汽车之心：<https://eu.36kr.com/zh/p/3955803560934789>
- OFweek：<https://www.ofweek.com/auto/2026-09/ART-70109-11000-30701262.html>
- MK（韩国）：<https://www.mk.co.kr/news/it/12135448>
- Axios（商业化）：<https://www.axios.com/2026/09/01/waymos-robotaxi-expansion-china-ojai>
- TeslAnt（算力口径对照）：<https://teslant.com/en/news/waymo-custom-sensor-fusion-asic-hot-chips-2026-08>

## 内容结构

| 时间 | 环节 |
|---|---|
| 00:00 | Cliff Young 开场：Hot Chips 的“Waymo 日” |
| 04:00 | Daniel Rosenband：物理 AI 与数字 AI 的三点差异 |
| 07:30 | 提纲：历史、传感器、计算、模型 |
| 08:00 | 2009 年的起点：红绿灯长尾与早期算力 |
| 12:30 | 规模化拐点：2 亿英里、15 个城市、4–5 千辆车 |
| 15:20 | 传感器套件：摄像头、激光雷达、毫米波雷达、麦克风 |
| 20:50 | 四类计算面：BFC、控制、座舱、连接 |
| 23:30 | BFC：感知—预测—规划—控制 |
| 25:00 | 车规封装、液冷、冗余与极端环境测试 |
| 27:10 | 性能曲线：CPU / GPU 持平，ML 需求持续上涨 |
| 31:00 | BFC 内部：A/B 双面、冷板、故障切换 |
| 33:30 | 计算流水线：ISP/DSP → 融合 → 大模型 → 优化与验证 |
| 35:00 | 自研传感器处理芯片：为什么要把 ISP/融合做进硅 |
| 37:00 | 稀疏点云到稠密矩阵：软硬件协同设计 |
| 38:30 | 与数据中心计算的差异：单芯片、低批量、低延迟 |
| 39:30 | 模型架构：快速融合编码器 + 慢速 VLM + 世界解码器 |
| 44:00 | 仿真：飞机降落、大象出逃、金门大桥下雪 |
| 46:00 | 结果：事故率约为人类的 1/13；下一步是雪地、伦敦与东京 |
| 49:50 | Q&A：液冷、失效模式、经济性、麦克风、V2X、GPU vs TPU/ASIC、万亿参数模型 |

## 简介模板（可直接粘贴）

**一句话提炼**：Waymo 用 13 年把自动驾驶从“能开的演示”做成 15 个城市的商业服务；支撑它的
是车里那只“披萨盒”——多传感器融合、液冷、A/B 双面冗余，以及一颗 5nm 自研传感器融合芯片。
Daniel Rosenband 的核心论点很直接：要做出比人安全得多的驾驶员，摄像头不够，必须把延迟、
冗余和算力放在一起设计。

**为什么今天还值得看**

- **传感器路线之争**：为什么 Waymo 坚持摄像头 + 激光雷达 + 毫米波雷达 + 麦克风；凤凰城沙尘暴
  里，摄像头看不见的行人由激光雷达补上。
- **车规计算不是数据中心计算的缩小版**：毫秒级延迟、批量 1、单芯片、液冷不制冷、后备箱空间
  有限，每一个约束都会改变芯片与系统设计。
- **自研 5nm 芯片的动机**：把 ISP、时序降噪、传感器融合和前段 ML 做进专用硅，缩短
  “像素到执行器”的延迟；官方口径前端合计 >1000 TOPS，单颗 ASIC 稠密 INT8 为 160 TOPS。
- **冗余是产品的一部分**：A/B 双面计算、双引擎、断电与传感器故障下的降级运行，决定了车队
  能不能在无人状态下收车、靠边或继续完成任务。
- **模型架构的“快思考 / 慢思考”**：快速融合编码器负责毫秒级感知，VLM 用几百毫秒回答
  “前方消防栓喷水还能不能过”，世界模型与仿真负责长尾场景。
- **规模与安全数据**：2 亿英里、15 个城市、约 4–5 千辆车，事故率约为人类的 1/13（Waymo 口径）；
  下一个战场是雪地、伦敦、东京和更大规模的车队。

**时间戳导航**

```
00:00 开场：Hot Chips 的 Waymo 日
04:00 物理 AI 与数字 AI 的差异
08:00 2009 年的起点与长尾问题
12:30 2 亿英里、15 个城市
15:20 传感器套件与沙尘暴案例
20:50 四类计算面
23:30 BFC 与感知规划控制
25:00 液冷、冗余与车规测试
27:10 CPU/GPU/ML 性能曲线
31:00 A/B 双面与故障切换
33:30 计算流水线
35:00 自研传感器处理芯片
39:30 快思考/慢思考模型架构
44:00 仿真：飞机、大象、下雪
46:00 1/13 事故率与下一步
49:50 Q&A
```

**出处与致谢**：原视频来自 Hot Chips 2026 官方频道
（<https://www.youtube.com/watch?v=3X6NN1csAF4>），本片中英字幕由 YouTube 自动英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`HC2026-K： Compute in Motion： Challenges of Autonomous Driving [3X6NN1csAF4].mkv`，
  361,654,866 字节（344.9 MiB），VP9 1920×1080 59.94fps + Opus 48kHz 立体声，
  3843.401s（64:03），整体码率 0.75 Mbps，无内嵌字幕、画面无硬字幕；讲者/问答镜头底部有会议横幅
- **字幕**：YouTube 自动英文（json3，3025 个事件 → 810 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 810/810、0 缺译；批量翻译出现 4 处局部错位
  （约 60–72、593–600、642–648、794–805），已按原文逐条重排；其余专名与术语人工校对
  （Waymo、Hot Chips、Ojai、Ioniq 5、lidar、TOPS、CNNs、co-design、Sabareesh/Pieter 等）
- **成片**：`HC2026-K： Compute in Motion： Challenges of Autonomous Driving [3X6NN1csAF4] [中英字幕].mkv`，
  1,156,316,283 字节（1.08 GiB），H.264（QSV `-global_quality:v 19`）1920×1080 59.94fps CFR
  + Opus 48kHz 立体声（原音轨直接复制），3843.401s（64:03），整体码率 2.41 Mbps，
  **硬字幕**（英上中下，810 条；幻灯片段 `MarginV=100`，开场与问答镜头 `MarginV=260` 避开会议横幅），QSV 烧录 9 分 24 秒
- **字幕文件**：`subtitles/3X6NN1csAF4.zh.bilingual.srt` / `.ass`（英上中下，810 条；
  分段样式：幻灯片 100 / 会议镜头 260）、`subtitles/3X6NN1csAF4.en.ass`（英文单语）
- **校验**：成片 3843.401s，与原片完全一致（未剪辑）；head 60s / tail 30s 解码无报错；
  音轨 MD5 与原片一致（`b4a0ba33b170d6ac168e1d86d431d48d`），确认直接复制、无音画偏移；
  片尾 30s 解码有 2 处重复 DTS 警告（源为 60fps VFR，播放无影响）；抽帧 01:00 / 05:00 / 30:00 / 60:00，
  确认幻灯片段用低位（不压正文）、会议镜头段用高位（不遮挡横幅）

## 备注

- 该视频只有自动英文字幕（无人工字幕）；自动字幕专名错误较多，翻译前已修正
  （`Whimo → Waymo`、`Hot Ships → Hot Chips`、`Ohigh → Ojai`、`Ionic 5 → Ioniq 5`、
  `lightars/LAR → lidar`、`tops → TOPS`、`connets → CNNs`、`codeesign/codees → co-design`、
  `V2X`、`AlexNet`、`Sabish and Peter → Sabareesh and Pieter`、`Kevin Cwell → Kevin Krewell` 等）
- 全片为连续主题演讲 + Q&A，无赞助口播、无广告段，成片时间轴与原片一致，无需删段
- 画面为幻灯片、讲者与演示视频，无硬字幕；双语字幕分两套样式：幻灯片段 `MarginV=100`（常规底部），
  开场与问答镜头 `MarginV=260`（抬到会议横幅上方）
- 芯片细节以 Waymo 官方博客与 Hot Chips 披露为准；算力与事故率为厂商口径，简介中需保留说明
- 城市数量：演讲中为“15 个城市”，同期媒体报道多为“11 个美国城市 / 14 个城市”，统计口径可能
  包含已运营、已宣布与即将上线市场；成片字幕按演讲原话翻译，简介中使用“15 个城市（演讲口径）”
- 与第 21 期（Dylan Patel：CPU 成为 AI 新瓶颈）构成“算力供给”两集：数据中心 → 车内
