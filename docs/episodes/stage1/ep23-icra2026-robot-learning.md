# 第 23 期：ICRA 2026 机器人学习四讲 — 开放世界、语言、几何与鲁棒性

- **状态**：已完成
- **信源**：IEEE Robotics and Automation Society 官方频道，
  <https://www.youtube.com/watch?v=a9f2rqxACHQ>
  （ICRA 2026，维也纳，2026-06-04 上午“Robot Learning, Planning & Foundation Models”主题报告场；
  2026-10-06 上传）
- **标题**：ICRA 2026 Keynote 5 - Robot Learning & Models
- **主持**：Karinne Ramirez-Amaro（查尔姆斯理工大学）
- **讲者与题目**：
  1. **David Hsu**（新加坡国立大学）— *Scalable Robot Decision Making in the Open World:
     Planning and Plan Prediction with LLMs*（00:56）
  2. **Stefanie Tellex**（布朗大学）— *Towards Complex Language in Partially Observed
     Environments*（21:06）
  3. **Noémie Jaquier**（KTH 瑞典皇家理工学院）— *Traveling the Robot Learning Manifold:
     A Tale of Geometries and Inductive Biases*（42:45）
  4. **Paolo Robuffo Giordano**（IRISA / Inria Rennes）— *Intrinsic Robustness: A Journey
     from Control-Aware Planning to Robust Robot Learning*（1:03:34）
- **规格**：原片 1:25:30，1080p24（VP9，最高画质），YouTube 自动英文字幕（无人工字幕），
  画面为幻灯片 + 讲者，无硬字幕
- **建议标题**：`【AI基建·第23期】ICRA 2026 机器人学习四讲：开放世界决策、语言编程、几何归纳偏置与内在鲁棒性（中英双语·85 分钟）`
- **定位**：机器人学习 / 物理 AI 理论篇，接第 17、20、22 期 Figure / Waymo 的工程与商业化内容。
  前面几期看“机器人怎么造、怎么量产、怎么在开放道路运行”，本期回答“机器人怎么在未知世界里
  做决定、怎么被编程、怎么利用几何结构、怎么在模型不确定时保持鲁棒”。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始会议 | ICRA 2026 官方 keynote 页面、IEEE RAS 官方 YouTube 频道 |
| 独立会议报道 | Habr / AIRI《Репортаж с ICRA 2026 из Вены》 |
| 讲者与实验室资料 | NUS David Hsu 主页、Brown Stefanie Tellex 主页、KTH Noémie Jaquier 主页、IRISA Paolo Robuffo Giordano 主页 |
| 论文与代码 | ApBot、Grounded Equivariant Manipulation、几何机器人学习、内在鲁棒性相关论文 |
| 会议日程 / 社区 | ICRA 2026 日程页、AdaComp 实验室行程、小红书参会笔记 |

结论：ICRA 官方日程页列出四位讲者与题目，IEEE RAS 发布完整场次录像，Habr/AIRI 做了独立
现场报道，四位讲者的学校主页与论文可交叉核对 → **通过**。

> 注意：这是一场四人联合主题报告，不是单篇论文宣讲；每位讲者只代表自己的研究，场次主题
> 由主持人串场。中文科技媒体对该场的专门报道较少，本片以官方日程、录像与讲者主页为准。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=a9f2rqxACHQ>
- ICRA 2026 Keynote 日程：<https://2026.ieee-icra.org/program/keynote-sessions/>
- Habr / AIRI 现场报道：<https://habr.com/ru/companies/airi/articles/1047528/>
- David Hsu 主页：<https://www.comp.nus.edu.sg/~dyhsu/>
- Stefanie Tellex 主页：<https://cs.brown.edu/people/stellex/>
- Noémie Jaquier 主页：<https://noemiejaquier.github.io/>
- Paolo Robuffo Giordano 主页：<https://people.irisa.fr/Paolo.Robuffo-Giordano/>

## 内容结构

| 时间 | 环节 |
|---|---|
| 00:00 | Karinne Ramirez-Amaro 开场：介绍四位讲者 |
| 00:56 | David Hsu：开放世界中的可扩展机器人决策 |
| 02:00 | 开放世界家庭机器人：规模与不确定性 |
| 03:00 | 基于模型 vs 数据驱动：两条路线与泛化问题 |
| 05:00 | 二维空间：表示（结构化/非结构化）× 推理（规划/计划预测） |
| 08:30 | 家用电器说明书 → 结构化模型 + 宏动作 |
| 11:00 | 厨房未知场景：假设生成、主动验证与 PDDL 规划 |
| 19:21 | David Hsu Q&A |
| 21:06 | Stefanie Tellex：面向部分可观测环境的复杂语言 |
| 21:45 | 为什么仍然需要“编程”机器人 |
| 23:30 | 任务指定的几种方式：代码、语言、奖励、示教 |
| 25:00 | 示教 + 强化学习：残差 RL 与 Q2RL |
| 26:10 | 自然语言编程：形式化表示 vs 端到端 |
| 29:45 | Grounded Equivariant Manipulation：用等变性减少数据 |
| 33:35 | 物体搜索、手势与非人类（小狗）理解 |
| 41:52 | Stefanie Tellex Q&A |
| 42:45 | Noémie Jaquier：在机器人学习流形上旅行 |
| 44:00 | 机器人变量的几何：球面、旋转、环面、对称正定矩阵 |
| 46:00 | 位置 + 姿态的运动策略学习 |
| 52:00 | 可变形物体：高维构型、潜空间动力学与拉格朗日结构 |
| 59:54 | Noémie Jaquier Q&A |
| 1:03:34 | Paolo Robuffo Giordano：内在鲁棒性 |
| 1:04:47 | 动机：建模不确定性为什么不等于加噪声 |
| 1:07:50 | 敏感度矩阵：闭环状态对参数变化的响应 |
| 1:10:00 | 四旋翼轨迹优化：不改控制器也能提升鲁棒性 |
| 1:19:00 | 从控制感知规划到鲁棒机器人学习 |
| 1:25:20 | 主持人收尾 |

## 简介模板（可直接粘贴）

**一句话提炼**：四场 ICRA 2026 主题报告从不同角度回答同一个问题——机器人如何在开放世界里
可靠地行动：David Hsu 把 LLM 的常识与结构化规划结合，Stefanie Tellex 讨论如何把复杂语言
变成可执行任务，Noémie Jaquier 把几何结构当作归纳偏置，Paolo Robuffo Giordano 用控制感知
规划获得对模型误差的内在鲁棒性。

**为什么今天还值得看**

- **开放世界的“假设—验证”闭环**：面对没见过的家电和厨房，机器人先提出关于物体、谓词和
  动作效果的假设，再用结构化规划去验证；LLM 负责提出候选，规划器负责保证可执行。
- **语言编程的两端**：一端是把自然语言翻译成 Python / LTL / PDDL 等形式语言，另一端是
  直接从语言和像素回归动作；两种路线在数据效率、跨平台、安全与可解释性上各有取舍。
- **几何归纳偏置**：姿态在球面上、关节在环面上、惯量矩阵在对称正定流形上；把这些结构
  写进网络，比在欧氏空间里硬学更省数据，也更容易保持物理一致性。
- **可变形物体的潜空间动力学**：600 自由度的布料的动力学可以压缩到 10 维潜空间，并保留
  拉格朗日/哈密顿结构，再做潜空间控制。
- **内在鲁棒性**：不换控制器、不加通用过程噪声，而是优化轨迹本身，让闭环对参数误差不敏感；
  四旋翼在质量、推力系数和质心位置偏差下仍能到达目标。
- **四种研究风格的对照**：符号规划 + LLM、语言 grounding + 等变网络、几何深度学习、
  控制理论 + 鲁棒学习——同一场次里能看到机器人学习的不同“学派”。

**时间戳导航**

```
00:00 开场与四位讲者
00:56 David Hsu：开放世界中的可扩展决策
08:30 家电说明书 → 结构化模型
11:00 厨房假设生成与验证
21:06 Stefanie Tellex：复杂语言与部分可观测
25:00 示教 + 强化学习
26:10 形式化语言 vs 端到端
33:35 物体搜索与手势
42:45 Noémie Jaquier：机器人学习流形
52:00 可变形物体的潜空间动力学
1:03:34 Paolo Robuffo Giordano：内在鲁棒性
1:07:50 敏感度矩阵与四旋翼
1:19:00 鲁棒机器人学习
1:25:20 收尾
```

**出处与致谢**：原视频来自 IEEE Robotics and Automation Society 官方频道
（<https://www.youtube.com/watch?v=a9f2rqxACHQ>），本片中英字幕由 YouTube 自动英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`ICRA 2026 Keynote 5 - Robot Learning & Models [a9f2rqxACHQ].mkv`，
  577,930,702 字节（551.2 MiB），VP9 1920×1080 23.976fps + Opus 48kHz 立体声，
  5130.141s（1:25:30），整体码率 0.90 Mbps，无内嵌字幕、画面无硬字幕；幻灯片底部有 IEEE RAS 红色页脚
- **字幕**：YouTube 自动英文（json3，4437 个事件 → 1015 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 1015/1015，3 条缺译已手工补齐；批量翻译出现若干局部错位
  （约 65–70、261–265、293–312、323–325、870–876、1004–1006），已按原文逐条重排；
  专名与技术术语人工校对（Karinne Ramirez-Amaro、David Hsu、Stefanie Tellex、
  Noémie Jaquier、Paolo Robuffo Giordano、PDDL、Grounding DINO、CLIPort、OpenVLA、
  Lagrangian、Riemannian、SE(3)、MPPI 等）
- **成片**：`ICRA 2026 Keynote 5 - Robot Learning & Models [a9f2rqxACHQ] [中英字幕].mkv`，
  1,175,642,439 字节（1.09 GiB），H.264（QSV `-global_quality:v 19`）1920×1080 23.976fps CFR
  + Opus 48kHz 立体声（原音轨直接复制），5130.141s（1:25:30），整体码率 1.83 Mbps，
  **硬字幕**（英上中下，1015 条，`MarginV=36`，落在底部 IEEE RAS 红色页脚带内），QSV 烧录 4 分 35 秒
- **字幕文件**：`subtitles/a9f2rqxACHQ.zh.bilingual.srt` / `.ass`（英上中下，1015 条，
  `MarginV=36`，落在红色页脚带内）、`subtitles/a9f2rqxACHQ.en.ass`（英文单语）
- **校验**：成片 5130.141s，与原片完全一致（未剪辑）；head 60s / tail 30s 解码无报错；
  音轨 MD5 与原片一致（`fe4d7eb5a618ac2734c3ba9ff49b1760`），确认直接复制、无音画偏移；
  抽帧 01:00 / 05:00 / 1:00:00 / 1:23:20，确认双语字幕落在红色页脚带内（y≈876–1052，
  页脚带 y=894–1079）：两行 cue 完整在带内，四行 cue（约 2%）上沿高出带顶约 18 px
- **重烧记录（2026-11-04）**：首版用 `MarginV=230`，字幕块 y≈820–902，主体压在幻灯片底部，
  盖住讲稿内容；按“把字幕放进底部红色页脚带”的要求改为 `MarginV=36` 并整片重烧，
  字幕文件 `zh.bilingual.ass` / `en.ass` 同步改为该值

## 备注

- 该视频只有自动英文字幕（无人工字幕）；自动字幕专名错误较多，翻译前已修正
  （`Karin Ramirez Samaro → Karinne Ramirez-Amaro`、`Charmer's → Chalmers`、
  `David Hu → David Hsu`、`MBIdia → NVIDIA Research Lab`、`Stephanie Telix → Stefanie Tellex`、
  `Brond → Brown`、`No Jlair → Noémie Jaquier`、`Paulo Robufo Jordano → Paolo Robuffo Giordano`、
  `Ursia → IRISA`、`lrenchian → Lagrangian`、`ukidian → Euclidean`、`endeector → end-effector`、
  `Taurus → torus`、`PDDDL → PDDL`、`induction hooker → induction cooker` 等）
- 全片为四场连续主题报告 + 每场 Q&A，无赞助口播、无广告段，成片时间轴与原片一致，无需删段
- 画面为幻灯片与讲者，无硬字幕；幻灯片底部有 IEEE RAS 红色页脚（1080p 下 y=894–1079），
  双语字幕用 `MarginV=36` 直接落在红色页脚带内，不再压住幻灯片
- 四位讲者的题目以 ICRA 2026 官方日程为准；Stefanie Tellex 的官方拼写为 Stefanie（非 Stephanie）
- 与第 17、20 期 Figure 和第 22 期 Waymo 形成“物理 AI 工程实现 → 机器人学习理论”的对照
