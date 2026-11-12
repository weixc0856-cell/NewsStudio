# 《AI时代的基建》B 站专栏策划

> 状态：策划稿 ｜ 更新：2026-11-02
> 定位一句话：不做泛科技资讯，做 AI 时代真金白银的工程底座。

---

## 一、专栏定位

以「算力 / 能源 → 系统底层 → 物理 AI / 机器人 → 工业数字化」为主线，
系统化搬运、翻译并解读海外顶级技术内容，形成一个可长期更新、可沉淀技术资产的专栏合集。

不是零散发视频，而是做成一个栏目：**《AI时代的基建：算力、物理 AI 与工业重构全纪录》**。

## 二、为什么这个定位能打出差异化

1. **避开低门槛的"聊天吹水"红海**
   多数科技博主停留在泛新闻搬运和"AGI 何时毁灭人类"的情绪话题；
   "基建"讨论的是真金白银、实体产业与工程底座：算力芯片与电力能源、液冷数据中心、
   数字孪生与仿真（CFD / 物理引擎）、机器人产线重构、底层推理框架（llama.cpp、Vulkan、CUDA 生态）。
2. **契合个人技术底色**
   工程仿真（CFD）、系统级编程（Rust）、端侧模型部署的背景，决定了在翻译、时间戳、导读、
   切片点评时对术语（Inference Latency、Memory Bandwidth、Electromechanical System、
   Digital Twin）的把握，是普通搬运无法替代的。
3. **合集效应放大关注与收藏**
   长视频用户的典型心理是"先收藏，以后慢慢啃"。做一个合集后，观众看完一期黄仁勋，
   会顺藤摸瓜收藏其余内容并关注账号。

## 三、内容库规划

| 主线 | 内容形态 | 目标对象 / 来源 | 备注 |
|---|---|---|---|
| 算力与能源 | 主题演讲、产业对谈 | NVIDIA（黄仁勋在 GTC / SIGGRAPH / 工业峰会的长演讲）、AMD（苏姿丰）、Intel、TSMC 先进制程与 CoWoS 封装 | 已有柏林 GTC 一期素材 |
| 系统底层 | 开发者访谈、公开课 | Andrej Karpathy（软件 2.0、端侧 AI）、Georgi Gerganov（llama.cpp）、开源编译器 / 系统架构师 Podcast | 高密度干货，适合完整版 |
| 物理 AI 与具身智能 | 学术会议工程解析 | Boston Dynamics、Figure AI、Tesla Optimus；CoRL / ICRA 的工程原理拆解 | 需要一定二次解读 |
| 工业数字化 | 投资人与产业访谈 | Sequoia、a16z 谈 AI 与核能 / 电网 / 供应链重构 | 偏经济学视角，可与技术期交替 |

内容选择原则：**官方一手来源优先**，其次是有工程细节的深度访谈；不追纯情绪新闻。

### 3.1 信源雷达（渠道级分布）

按四条主线构建一手信源雷达。覆盖状态仅标定当前生态完备度（已有 / 部分 / 缺口），具体期数查验 `episodes_registry.json`。

| 主线 | 渠道 | 取用口径 | 覆盖 |
|---|---|---|---|
| **算力与能源** | NVIDIA GTC / CES / GTC Taipei | 主题演讲、架构 deep dive | 已有 |
| | AMD Advancing AI / OCP Summit | Instinct、Helios、ROCm、机柜供电 | 已有 |
| | Intel ON / Computex | 制程、至强、代工 | 部分 |
| | TSMC OIP / Technology Symposium | 先进封装、制程路线 | 缺口 |
| | Hot Chips | 芯片微架构一手披露 | 已有 |
| | SemiAnalysis（Dylan Patel） | CoWoS/HBM、集群成本、供应链 | 已有 |
| | bg2（Gurley / Gerstner） | 电力、芯片垄断、hyperscaler 竞争 | 已有 |
| **系统底层** | Microsoft Build（BRK 系列） | Azure 基础设施、分布式系统 | 已有 |
| | Dwarkesh Patel | 实验室核心人物、scaling / post-training | 缺口 |
| | No Priors（Sarah Guo / Elad Gil） | AI Infra 创始人、capex 动向 | 缺口 |
| | Latent Space | 推理引擎、agent 工程化 | 缺口 |
| | Stanford MLSys / HAI、BAIR | 分布式训练、显存优化、机器人学习 | 缺口 |
| | NeurIPS / ICML / ICLR / CVPR keynotes | 仅收录具备工程实测数据的 talk | 缺口 |
| **物理 AI / 机器人** | Figure / Sourcery、Waymo、ICRA / CoRL | 人形机器人、自动驾驶、端到端学习 | 已有 |
| **工业数字化** | Siemens、Schneider、Supermicro、Munro Live、PhysicsX/AWS | 工业 AI、数据中心电气、硬件拆解、工业仿真 | 已有 |

> 选源补充：Lex Fridman 等长播客不作为常规全期信源，仅在当期嘉宾为一线芯片、机器人或自动驾驶核心工程师时定向选剪。

### 3.2 待做选题队列（按优先级，2026-11-02）

| 顺位 | 候选 | 链接 | 备注 |
|---|---|---|---|
| ep32 | Dwarkesh × Intel 先进制程 | <https://www.youtube.com/watch?v=frYSOKvNiiE> | 已完成 |
| ep33 | Munro Live × Tesla Semi 工厂 | <https://www.youtube.com/watch?v=qLp-QJYiJCw> | 已完成 |
| ep34 | G20 创新部长级会议：黄仁勋 × Anthropic 首席算力官 Tom Brown | <https://www.youtube.com/watch?v=cTqtHIufCRw> | 已完成（改选题）；原 100:25 直播中无 Musk/Altman，按 §7 切除政务段后 37:15 |
| ep35 | 黄仁勋 × Astana Hub：从出口能源到出口智能 | <https://www.youtube.com/watch?v=ncoMBc-oj_8> | 已完成；33:29 → 27:47（按 §7 切除政务/政策段） |
| ep36 | 黄仁勋 × CSIS：平台五层栈、能源约束与「任务不是工作」 | <https://www.youtube.com/watch?v=OT_9HqGQzhw> | 已完成；51:52 → 15:19（China/Geopolitics/Industrial policy/National security 四章整章切除） |
| ep37 | Latent Space × Modal：GPU 算力为什么是「长方形」 | <https://www.youtube.com/watch?v=IiZ9yd2Do8I> | 已完成；1:25:33，纯技术无切除 |
| ep38 | No Priors × Fractile：为前沿模型造前沿芯片 | <https://www.youtube.com/watch?v=OpeCP4wCxkA> | 已完成；35:39，纯技术无切除 |
| ep39 | Stanford Robotics × Danfei Xu：人类数据与 EgoVerse | <https://www.youtube.com/watch?v=NUtaN10cVDc> | 已完成；1:09:07，纯技术无切除 |
| ep40 | CoRL 2026 × Jim Fan：GR00T 2 世界动作模型与开源机器人栈 | <https://www.youtube.com/watch?v=F_4AAOQsWlA> | 已完成；17:40（从 8:55:50 官方直播截取演讲段）|
| ep41 | CoRL 2026 × Hang Zhao：Organizing Physical AI Across Timescales | <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=4910s> | 同一场直播；9:30–10:00 |
| ep42 | CoRL 2026 × Negar Mehr：How Can Robots Learn to Interact and Coordinate with Others? | <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=21560s> | 同一场直播；约 14:00–14:30 |
| ep43 | CoRL 2026 × Wolfram Burgard：Challenges to Realize Embodied AI | <https://www.youtube.com/watch?v=F_4AAOQsWlA&t=26000s> | 同一场直播；约 15:15 起 |
| ep44 | Dwarkesh × Reiner Pope：Chip design from the bottom up | <https://www.youtube.com/watch?v=oIk3R-sMX5o> | 黑板课；1:20 |
| ep45 | Dwarkesh × Dylan Patel：算力扩展的三大瓶颈 | <https://www.youtube.com/watch?v=mDG_Hx3BSUE> | 2:30；含 China/Taiwan 段，需按 §7 切除 |

> 队列只代表优先级，不锁定期数；每期开始前按 §9.1 重新查重 `episodes_registry.json`，并按 §9.2 做三方验证。

## 四、标准化流水线打法

### 1. 标题格式化

`【AI基建·第X期】<人物/事件>：<核心命题>（中英双语·<时长>完整版）`

示例：

- `【AI基建·第1期】黄仁勋柏林 91 分钟超长演讲：物理 AI 时代的完整推演（中英双语·4K）`
- `【AI基建·第2期】黄仁勋对话德国总理默茨：工业 AI 与欧洲的算力焦虑（中英双语·24 分钟）`

### 2. 合集与账号结构

- B 站创作中心建立合集：**《AI时代的基建：算力、物理与工业新浪潮》**
- 每期发布后归入合集，保持编号连续
- 长短结合：完整版入库，另切 5–10 分钟高密度片段引流

### 3. 统一视频简介结构（固定三段）

1. **一句话硬核提炼**：这期讲清了哪个底座问题（不是"讲了什么"，而是"解决了什么认知"）
2. **带时间戳的导航**：按章节给出跳播链接，方便按需观看
3. **出处与致谢**：标注海外官方来源、原视频链接与版权说明，遵守转载礼仪

### 4. 技术资产沉淀

SRT / ASS 双语字幕、术语表、思维导图、精炼笔记可同步沉淀到个人网站（Wayne-Blog），
与 B 站形成互相引流的矩阵；同一份素材同时服务"输入学习"和"对外 IP"两个目标。

## 五、现有素材（本仓库已产出）

| 素材 | 时长 | 分辨率 | 字幕状态 | 建议用途 |
|---|---|---|---|---|
| 第 1–30 期素材清单 | — | — | 已封存 | 见 [stage1/STAGE1_EPISODES.md](episodes/stage1/STAGE1_EPISODES.md) |

> 第 1–30 期的完整素材清单已封存；新素材从第 31 期起写入 stage2。

> 素材来源均为官方频道：NVIDIA、德国联邦经济与能源部、AMD、Intel、Google Cloud、Microsoft、Cadence、Schneider Electric、Open Compute Project、Bipartisan Policy Center、AWS、CNBC、UC Berkeley EECS、Tiff In Tech、Sourcery。
> 发布时需在简介中保留原链接与来源说明。

> 每期的三方验证、章节、简介模板与制作结果，见第十节「期数档案」。

## 六、制作流水线（已工程化）

> **执行口径**：日常制作仅执行“无字幕原片下载 → 本地大模型翻译 → QSV 硬件压制与校验”主链路；四阶段切片与合集流水线默认关闭，具体执行参数与异常避坑统一以根目录 `README.md` 与 `CLAUDE.md` 为唯一事实源。

本仓库已把重复劳动固化为脚本，后续每期按同一流程跑：

1. **只下载无字幕原片**：`uv run yt-dlp "URL"`（自动选最高画质，不写内嵌字幕）
2. **只抓原语种字幕**：`yt-dlp --write-auto-subs --sub-langs "<原语种>"`
3. **本地大模型翻译**：Qwen3-30B-A3B（llama.cpp / SYCL）逐句翻译，术语表统一
4. **生成双语**：英文在上、中文在下（`scripts/build_subs.py` → `scripts/translate_local.py`）
5. **烧录成品**：QSV 硬件编码，4K 约 35 分钟；原片保留
6. **沉淀资产**：双语 SRT / ASS 归档，供时间戳与网站使用

细节命令与参数见仓库 `README.md` 的「字幕规则」「本地大模型翻译」两节。

## 七、首期执行建议

- **选题**：GTC Berlin 2026 黄仁勋主题演讲（已有 4K 中英硬字幕成片）
- **一句话提炼（待定稿）**：从加速计算到物理 AI，黄仁勋如何把"AI 工厂"讲成一套产业基础设施
- **时间戳导航**：从双语 SRT 按主题切章节（建议 6–10 个节点，每个 8–15 分钟）
- **切片选题**：物理 AI、数字孪生、机器人工厂、欧洲算力与能源，各剪 3–5 分钟
- **第二期**：默茨 × 黄仁勋对谈，作为"工业 AI 与政策"视角的补充，可与第一期形成互文

## 八、节奏与风险

**节奏建议**

- 双周一期完整版，周中发 1–2 条切片
- 先储备 3 期再开更，避免断更
- 每期发布后同步网站笔记与字幕文件

**风险与合规**

- 转载需注明官方来源与原链接；有条件时先取得授权
- 选品前先完成三方验证（见第九节「选品安全守则」），不碰独家授权或限制转载的内容
- 机翻必须人工校对专有名词与数字，避免误导
- 术语表长期维护（token→词元、AI factory→AI 工厂、physical AI→物理 AI 等）
- 不篡改原意，不在字幕中夹带观点；点评放在导读或片头单独说明

## 九、选品安全守则（The Multi-Publisher Rule）

### 9.1 选题漏斗与准入过滤

候选视频在进入制作前，必须按顺序通过以下 5 级过滤网：

1. **主线匹配**：明确落入四条主线（算力能源、系统底层、物理 AI、工业数字化）之一。纯算法演进或模型理论（如不涉及工程落地的纯 SSM/Mamba 架构）不入库。
2. **查重检验**：严格只读根目录 `episodes_registry.json`，按 `url → core_entity → event → tags` 顺序核验。同一实体允许再做，但 `event` 与 `tags` 必须与已有记录不同，且应有技术增量。
3. **三看原则**：
   - 看**物理与资源瓶颈**：电力供给、机柜液冷、HBM/显存带宽、互联拓扑（NVLink/InfiniBand）、封装工艺；
   - 看**系统工程与架构突破**：MoE 路由与显存置换、KV cache 优化、vLLM/SGLang 等推理引擎落地实战；
   - 看**第一手技术拆解**：原厂架构师、芯片设计者对着架构图与工程约束进行的白皮书级讲解。
4. **三不看原则**：
   - 不看只有概念或口号、没有架构图、技术路线图或具体参数的通稿（一手原厂 Keynote 具备硬核内容的除外）；
   - 不看非技术背景主播的纯主观观点输出（能拿到一线工程实物、工厂拆解或核心技术嘉宾访谈的除外）；
   - 不看缺乏具体工程数字、约束条件与成本参数的商业喊话。
5. **可操作测试**：能否从标题、简介或初筛片段中指出**至少一个具体数字、架构型号或工程物理约束**？无法指出则直接淘汰；通过后再进入 §9.2 开展三方验证。

### 9.2 三方验证

**核心原则：三方验证。** 选定目标视频前，先在 YouTube 与全网检索该视频的核心关键词，
确认至少有 **3 家以上不同背景**的媒体、机构或自媒体已公开发布或切片过该内容，
判断其未被单一机构垄断版权，再溯源下载画质最高的无字幕原版进行中英双语制作。

#### 操作清单

1. 提取核心关键词：人物 + 场合 + 主题（例：Jensen Huang / GTC Berlin 2026 / physical AI）
2. 在 YouTube 与全网检索，记录发布者与形态（完整版 / 切片 / 图文报道）
3. 核对是否达到 3 家以上，且背景不同（官方、专业媒体、综合新闻、自媒体）
4. 判断版权是否被单一机构垄断（独家授权、付费墙、仅一家可转载）
5. 溯源原始发布方，优先官方频道，下载画质最高的无字幕原版
6. 通过后再进入双语制作流水线；未通过则暂缓或更换选题

#### 判定与留档

| 情形 | 处理 |
|---|---|
| ≥3 家不同背景发布 / 切片 | 通过，进入制作 |
| 仅官方 1 家发布，但有 3 家以上媒体独立报道 / 切片 | 通过（以报道链接留档） |
| 仅 1–2 家且无法确认独立来源 | 暂缓，先观察或更换选题 |
| 明确独家授权 / 付费墙 / 版权声明限制转载 | 放弃，不做 |

- 每期在发布记录中保留至少 3 条不同来源链接，作为选品依据留档
- 官方素材仍需在简介标注来源与原链接；三方验证不替代授权与署名

#### 本次已通过校验的素材

- GTC Berlin 2026 主题演讲：NVIDIA 官方发布，Yahoo Finance 等多家媒体完整转播 / 切片
- 默茨 × 黄仁勋对谈：德国联邦经济与能源部官方发布，多家新闻台独立切片
- Google Cloud Next '26 开幕演讲：Google Cloud 官方发布，CIO.com、SiliconANGLE、ITPro、Futurum 等独立报道，B 站有完整回放
- State of GPT（Karpathy / Build 2023）：Microsoft Developer 官方发布，GitHub 幻灯片、Glasp 转录、多家中文媒体笔记与 B 站双语版广泛传播
- CadenceLIVE 2024 黄仁勋对谈：Cadence 官方发布，SemiWiki、EDN、Cambrian AI、每日经济新闻、Infobae 等独立报道
- NVIDIA GTC Studio × Schneider Electric：NVIDIA 官方发布，Frank's World、Data Center Frontier、AutomationWorld、赛迪网等独立报道 / 分析
- OCP 800 VDC AI Factories：Open Compute Project 官方发布，NVIDIA 博客、Data Center News Asia、Network World、Dell'Oro、财联社等独立报道 / 分析
- 黄仁勋 × 美国两党政策中心：BPC 官方与 C-SPAN 全程，Axios、E&E News、Utility Dive、POLITICO Pro 等独立报道
- PhysicsX × AWS（re:Invent STP109）：AWS 官方与案例，IAA Mobility 同题演讲、AI Business、CDFAM、Business Times 等独立报道
- CNBC ASML High-NA 独家：CNBC 原始报道，Reuters/CGTN、Benzinga、TrendForce、DIGITIMES、36Kr、钛媒体等独立转述 / 分析
- UC Berkeley EECS EUV 讲座：Berkeley 官方发布，Stanford/Purdue/MIT 同讲者讲座、Class Central、SEMI 讲者简介等交叉验证
- 扎克伯格 × Tiff In Tech：Tiff In Tech 原始访谈，Meta Connect 2024 被 The Verge、Reuters、Business Insider、36Kr、钛媒体等广泛报道
- NVIDIA GTC 2025 通用机器人圆桌：NVIDIA 官方，The Robot Report、The Verge、TechCrunch、腾讯新闻、今日头条等独立报道
- 黄仁勋 CES 2025 × Tiff In Tech：Tiff In Tech 原始访谈，证券时报、21 世纪经济报道、东方财富等直接编译，CNBC、China Daily 等报道 CES 主题演讲
- Figure 创始人 Brett Adcock × Sourcery：Sourcery 原创访谈，PANews 全文编译、BigGo 摘要、
  Podscan / Quicklets / TeaHose 转录，Forbes、Interesting Engineering、财联社等独立报道与核查
  （Forbes 调查对部署规模提出质疑，作为对照阅读留档）
  - Supermicro CEO 梁见后 Computex 2026：Supermicro 官方发布，PR Newswire 同步，
  Tom's Hardware、TechTimes、The Elec、电波新闻、智东西、遠見等独立报道与核查
  （1000 倍电阻抗冷却液声明待第三方验证，作为对照阅读留档）
  - 西门子 CES 2026 工业 AI 主题演讲：Siemens 官方发布，Business Wire、DPA（南德意志报 /
  Zeit）、AI Business、Forrester、e-works、新浪财经等独立报道与核查（厂商/试点口径数字，
  作为对照阅读留档）
  - Figure 首次公开总部与工厂：Sourcery 原创拍摄，Sourcery Substack、Apple/Spotify/Podscan
  收录，新浪财经逐字编译、B 站中英双语版、知乎/36Kr 独立解读（公司主导参观，口径需对照
  第 17 期 Forbes 调查阅读）

## 十、期数档案

每期一个独立档案，按阶段存放：第 1–30 期见 `episodes/stage1/`，第 31 期起见 `episodes/stage2/`；
专栏主文档只保留阶段入口与通用规则。

| 期数 | 主题 | 档案 | 状态 |
|---|---|---|---|
| 第 1–30 期 | 阶段一（已封存） | [stage1/STAGE1_EPISODES.md](episodes/stage1/STAGE1_EPISODES.md) | 已完成 |
| 第 31 期 | 特斯拉 Cybercab 工程拆解：25 个工位造一台无人出租车 | [ep31-tesla-cybercab-munro.md](episodes/stage2/ep31-tesla-cybercab-munro.md) | 已完成 |
| 第 32 期 | 英特尔 CTO 拆解 2045 年的芯片：GAA、CFET、High-NA EUV 与 AI 产能墙 | [ep32-intel-chips-2045.md](episodes/stage2/ep32-intel-chips-2045.md) | 已完成 |
| 第 33 期 | 特斯拉 Semi 工厂全流程：Munro 现场拆解电动重卡怎么造 | [ep33-tesla-semi-munro.md](episodes/stage2/ep33-tesla-semi-munro.md) | 已完成 |
| 第 34 期 | G20 现场：黄仁勋 × Anthropic 首席算力官算的两笔 AI 基建账 | [ep34-g20-ai-infrastructure.md](episodes/stage2/ep34-g20-ai-infrastructure.md) | 已完成 |
| 第 35 期 | 黄仁勋 × 哈萨克斯坦副总理：从能源到智能，一个国家怎么建 AI 经济 | [ep35-astana-ai-nation.md](episodes/stage2/ep35-astana-ai-nation.md) | 已完成 |
| 第 36 期 | 黄仁勋 CSIS 对谈：平台五层栈、能源约束与「任务不是工作」 | [ep36-csis-ai-platform.md](episodes/stage2/ep36-csis-ai-platform.md) | 已完成 |
| 第 37 期 | GPU 算力为什么是「长方形」：Modal CEO 谈推理云 | [ep37-modal-gpu-cloud.md](episodes/stage2/ep37-modal-gpu-cloud.md) | 已完成 |
| 第 38 期 | 为前沿模型造前沿芯片：Fractile CEO 谈内存带宽赌注 | [ep38-fractile-inference-chips.md](episodes/stage2/ep38-fractile-inference-chips.md) | 已完成 |
| 第 39 期 | 从人类经验里学机器人：Danfei Xu 谈人类数据与 EgoVerse | [ep39-danfei-xu-human-data.md](episodes/stage2/ep39-danfei-xu-human-data.md) | 已完成 |
| 第 40 期 | 从「做梦」到「做事」：Jim Fan 在 CoRL 2026 发布 GR00T 2 | [ep40-corl-jim-fan-gr00t2.md](episodes/stage2/ep40-corl-jim-fan-gr00t2.md) | 已完成 |
| 第 41 期 | 机器人不能等模型：赵行在 CoRL 2026 谈 System 2/1/0 与多时钟架构 | [ep41-corl-hang-zhao-multiclock.md](episodes/stage2/ep41-corl-hang-zhao-multiclock.md) | 已完成 |
| 第 42 期 | 让机器人学会互相配合：Negar Mehr 在 CoRL 2026 谈多智能体协调与持续学习 | [ep42-corl-negar-mehr-multiagent.md](episodes/stage2/ep42-corl-negar-mehr-multiagent.md) | 已完成 |
| 第 43 期 | 把西西弗斯的石头推上山：Wolfram Burgard 在 CoRL 2026 谈具身智能的三次尝试 | [ep43-corl-burgard-embodied-ai.md](episodes/stage2/ep43-corl-burgard-embodied-ai.md) | 已完成 |
| 第 31 期起 | 阶段二（进行中） | [stage2/](episodes/stage2/) | 按 `episodes_registry.json` 增量登记 |

> 查重与三方校验只读根目录 `episodes_registry.json`；阶段一复盘见 [stage1/STAGE1_SUMMARY.md](episodes/stage1/STAGE1_SUMMARY.md)。

**新增一期的流程**

1. 复制 `episodes/_template.md` 为 `episodes/stage2/epNN-<slug>.md`
2. 按模板填写三方验证、内容章节、简介模板与制作结果
3. 在根目录 `episodes_registry.json` 追加一条记录；素材放入 `downloads/`，字幕放入 `subtitles/`

---

## 附：可复用资产索引

| 资产 | 位置 |
|---|---|
| 下载与字幕规则 | `README.md` |
| 字幕重建 / 翻译脚本 | `scripts/build_subs.py`、`scripts/translate_local.py` |
| 本地模型启动参数 | `README.md`「本地大模型翻译」 |
| 已产出的双语字幕 | `subtitles/` |
| 成片与无字幕原片 | `downloads/` |
