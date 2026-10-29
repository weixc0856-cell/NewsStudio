# 《AI时代的基建》B 站专栏策划

> 状态：策划稿 ｜ 更新：2026-10-27
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

**核心原则：三方验证。** 选定目标视频前，先在 YouTube 与全网检索该视频的核心关键词，
确认至少有 **3 家以上不同背景**的媒体、机构或自媒体已公开发布或切片过该内容，
判断其未被单一机构垄断版权，再溯源下载画质最高的无字幕原版进行中英双语制作。

### 操作清单

1. 提取核心关键词：人物 + 场合 + 主题（例：Jensen Huang / GTC Berlin 2026 / physical AI）
2. 在 YouTube 与全网检索，记录发布者与形态（完整版 / 切片 / 图文报道）
3. 核对是否达到 3 家以上，且背景不同（官方、专业媒体、综合新闻、自媒体）
4. 判断版权是否被单一机构垄断（独家授权、付费墙、仅一家可转载）
5. 溯源原始发布方，优先官方频道，下载画质最高的无字幕原版
6. 通过后再进入双语制作流水线；未通过则暂缓或更换选题

### 判定与留档

| 情形 | 处理 |
|---|---|
| ≥3 家不同背景发布 / 切片 | 通过，进入制作 |
| 仅官方 1 家发布，但有 3 家以上媒体独立报道 / 切片 | 通过（以报道链接留档） |
| 仅 1–2 家且无法确认独立来源 | 暂缓，先观察或更换选题 |
| 明确独家授权 / 付费墙 / 版权声明限制转载 | 放弃，不做 |

- 每期在发布记录中保留至少 3 条不同来源链接，作为选品依据留档
- 官方素材仍需在简介标注来源与原链接；三方验证不替代授权与署名

### 本次已通过校验的素材

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
