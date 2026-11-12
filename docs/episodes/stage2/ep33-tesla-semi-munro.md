# 第 33 期：特斯拉 Semi 工厂全流程 — Munro 现场拆解电动重卡怎么造

- **状态**：已完成
- **信源**：Munro Live 官方频道，<https://www.youtube.com/watch?v=qLp-QJYiJCw>
  （Tesla Semi Rollout 活动现场，2026-09-24 内华达 Sparks；2026-10-02 上传）
- **标题**：We Toured the Tesla Semi Factory. Here's What Stood Out
- **出镜**：Kevin（Munro Live 主讲，Munro & Associates 工程顾问）+ 特斯拉 Semi 工厂现场工程师
  （Tesla Rollout 站台讲解）
- **规格**：54:32（3271.961 s），源最高 4K24，现场英文原声，2026-10-02 发布
- **建议标题**：`【AI基建·第33期】特斯拉 Semi 工厂拆解：冲压、白车身、电池包到总装，54 分钟看懂电动重卡怎么造（中英双语·54 分钟）`
- **定位**：制造主线第三篇（接第 31 期 Cybercab 拆解、第 32 期 Intel 制程），
  从“乘用车怎么少工位”走到“重卡怎么把电池、车身与总装串起来”：
  Semi 专用厂的冲压线、白车身、电池包结构、车桥与动力总成、电池与驾驶室合装、
  以及 Munro 视角下哪些设计选择真正降本。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 / 原始会议 | Tesla Semi Rollout Event（2026-09-24，Sparks, NV，毗邻 Giga Nevada）；Munro Live 官方视频与现场拍摄 |
| 行业媒体 | TT News《Tesla launches high-volume Semi production》《Tesla Sees "Many Thousands" of Semis Being Built in 2026》、Quartz / Yahoo Finance《Tesla opens Nevada Semi truck factory targeting 50,000 units a year》、Teslarati、Not a Tesla App |
| 一手参观记录 | Atlas EV Hub《A Look Inside Tesla's Plans to Scale Electric Trucking》 |
| 技术拆解媒体 | The Automotive Channel（Munro 巡厂与电池自动安装线专题）、EVsoup |
| 中文媒体 | IT之家《特斯拉 Semi 电动卡车开启量产交付，工厂年产能 5 万辆》、36氪、智通财经、观点网、Notebookcheck 中文版 |

结论：Tesla 官方活动与多家行业媒体独立报道了同一场 Rollout 与同一座工厂（1.7 M sq ft、
设计年产能 5 万辆），Munro Live 为现场受邀媒体并自行拍摄讲解，中文媒体做了完整编译 →
**通过**。

> 注意：5 万辆/年是**设计年产能**，2026 年实际交付预期远低于此（中文报道普遍给出
> 5,000–15,000 辆），产能受 4680 干电极爬坡制约。本片讲的是“怎么造”，不替交付数字背书。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=qLp-QJYiJCw>
- TT News（量产）：<https://www.ttnews.com/articles/tesla-semi-high-volume>
- TT News（2026 产量）：<https://www.ttnews.com/articles/tesla-semis-build-2026>
- Quartz：<https://qz.com/tesla-semi-truck-nevada-factory-sparks-092526>
- Yahoo Finance：<https://finance.yahoo.com/technology/articles/tesla-opens-nevada-semi-truck-114819316.html>
- Teslarati：<https://www.teslarati.com/tesla-semi-truck-factory-nevada/>
- Atlas EV Hub：<https://www.atlasevhub.com/weekly-digest/a-look-inside-teslas-plans-to-scale-electric-trucking/>
- The Automotive Channel：<https://www.the-automotive-channel.com/inside-teslas-automated-semi-battery-install-line/>
- IT之家：<https://www.ithome.com/1/007/084.htm>
- 36氪：<https://eu.36kr.com/zh/p/4002529714704517>
- 智通财经：<https://www.zhitongcaijing.com/content/detail/1516457.html>

## 内容结构（官方章节）

| 时间 | 环节 |
|---|---|
| 00:00 | 现场开场：Semi Rollout 与工厂参观说明 |
| 00:45 | 冲压线：车身覆盖件与电池箱体 |
| 06:10 | 电池包结构 |
| 13:38 | 白车身（Body in White） |
| 17:57 | 高顶制造 |
| 20:36 | 涂装与表面处理 |
| 25:50 | 内饰与座椅 |
| 28:05 | 车桥与动力总成装配 |
| 34:32 | 电池合装与底盘总装 |
| 41:16 | 驾驶室合装与热管理 |
| 45:49 | 仪表台与收尾 |

## 简介模板（可直接粘贴）

**一句话提炼**：Munro 团队受邀走进特斯拉在内华达 Sparks 的 Semi 专用工厂，从一卷钢板开始，
跟完冲压、电池箱、白车身、涂装、车桥与动力总成、电池与驾驶室合装的全过程；Kevin 的判断是——
Semi 的难点不在某一项黑科技，而在于把乘用车上验证过的做法（大型铝铸件、结构胶混合连接、
模块化合装）放大到一台满载 8 万磅的 8 级重卡上。

**为什么今天还值得看**

- **冲压**：一条串联线把开卷、落料、成形、修边、冲孔、整形串起来，下车体是大面积铝板件；
  每个零件都要过检具，再过扫描工位与数模比对，绿灯才算合格。
- **电池箱即结构件**：电池包外壳本身承担车身刚度，顶盖用激光钎焊密封——这是把“电池厂”
  和“车身厂”两套工艺缝在一起的地方。
- **白车身**：电阻点焊 + 结构胶混合连接；高顶单独分装后再落装，因为风阻直接换续航
  （目标 1.7 kWh/英里，长续航版 500 英里）。
- **涂装**：前处理、电泳、粉末涂层到面漆，Semi 走的是完整乘用车级涂装线，不是商用车常见的
  “喷一层了事”。
- **车桥与动力总成**：定子与逆变器与 Cybertruck 共用，中央大铝铸件承力；电驱模块的朝向与
  布置和乘用车完全不同。
- **合装**：机器人把电池包举升到车架，靠铸铝外伸支架承载；随后驾驶室落装、热管理接管——
  整套“滑板式”总装顺序是为重卡的维修与产能折中过的。
- **Munro 的判读**：空气制动这类部件仍是成熟商品件，真正的新东西在结构集成、连接工艺与
  合装顺序，而不是零件本身。

**时间戳导航**

```
00:00 现场开场
00:45 冲压线
06:10 电池包结构
13:38 白车身
17:57 高顶制造
20:36 涂装与表面处理
25:50 内饰与座椅
28:05 车桥与动力总成
34:32 电池合装与底盘总装
41:16 驾驶室合装与热管理
45:49 仪表台与收尾
```

**出处与致谢**：原视频来自 Munro Live 官方频道（<https://www.youtube.com/watch?v=qLp-QJYiJCw>），
本片中英字幕由 YouTube 自动英文字幕翻译整理，仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`We Toured the Tesla Semi Factory. Here's What Stood Out [qLp-QJYiJCw].mkv`，
  910,837,230 字节（869 MiB），H.264 1920×1080 24fps CFR + Opus 48kHz 立体声，
  3271.961 s（54:32），整体码率 2.23 Mbps，无内嵌字幕；
  **部分段落自带烧死的英文字幕**（Tesla 现场工程师讲话段，y=815–910）
- **字幕**：YouTube 自动字幕的 timedtext 接口连续 429（8 次重试 + 换 client 均失败），
  改用 `youtube-transcript-api`（走 `/youtubei/v1/get_transcript`）取到官方自动字幕 1663 段
  （带标点；滚动字幕时间互相重叠）；按句合并、按标点重切、再对时间做去重叠夹紧，
  得 795 条显示 cue；专名修正 `Mineral → Munro`、`semi → Semi`、`mega charger → Megacharger`、
  `Ride-A-Drive → Ride and Drive` 等；中文由本地 Qwen3-30B-A3B **逐条**翻译 795/795，零空译
  （每批 12 条的批量模式出现整段串行错位，改逐条后归零；术语订正 `坚果细胞 → 螺母工位`、
  `车站 → 工位`）
- **版式（两段式）**：硬字幕检测出 9 段、约占 34.5% 的时长，按“不叠加同语种”规则分两套位置——
  干净段落英上中下（`MarginV=100`，535 条）；带硬字幕段落只叠简体中文并抬到
  `MarginV=380`（底边 y≈795，正好在烧录字幕 y=815 上方，260 条）
- **成片**：`We Toured the Tesla Semi Factory. Here's What Stood Out [qLp-QJYiJCw] [中英字幕].mkv`，
  2,136,500,580 字节（1.99 GiB），H.264（QSV `-global_quality:v 19 -preset slow`）
  1920×1080 24fps CFR + Opus 原音轨（直接复制），3271.961 s（54:32），整体码率 5.22 Mbps，
  **硬字幕**（795 条，两段式版式），QSV 烧录约 3 分钟（18.5×）
- **字幕文件**：`qLp-QJYiJCw.zh.bilingual.srt` / `.ass`（双语，`MarginV=100`）、
  `qLp-QJYiJCw.en.official.srt`（官方自动字幕底稿，1663 段）、`qLp-QJYiJCw.en.whisper-raw.srt`（Whisper 兜底原文）、
  `qLp-QJYiJCw.zh.bilingual.tiered.ass`（**成片用**，抬高段仅中文，`MarginV=380`）、
  `qLp-QJYiJCw.en.ass`（英文单语）、`qLp-QJYiJCw.en.srt`（清理后的显示 cue）
- **校验**：成片 3271.961 s，与原片完全一致（未剪辑）；音轨包数据 MD5 与原片相同
  （`f81297904390bf42fd97c1c95cd5d30c`）；head 60 s / tail 30 s 解码无报错；
  抽帧 00:00:06 / 00:05:00 / 00:20:05 / 00:35:20 / 00:45:00 / 00:54:20，
  确认干净段落英上中下、硬字幕段落中文位于烧录英文字幕上方且无重叠

## 备注

- **源片部分段落自带烧死的英文字幕**（Tesla 现场工程师讲话段，y=815–910）：这些段落只叠简体中文
  并抬到烧录字幕上方；其余段落英上中下常规位置。9 段区间用逐帧判据给出——白字黑边像素且
  横向重心落在画面中部（单纯像素计数会被车身涂装、车间标识误触发，误判过 11–22 s 与
  1854–1861 s 两段），边界抽帧核对过
- 自动字幕 429 期间先用本地 Whisper（medium.en）兜底转过 661 条、也出过一版成片；
  拿到官方字幕后整片按官方字幕重做，Whisper 原文留档 `qLp-QJYiJCw.en.whisper-raw.srt`
- 批量翻译（每批 12 条）在本片出现整段串行错位（第 5 分钟附近中文整体前移一条），
  改为逐条翻译（batch 1）后消除；本地 llama-server 的前缀缓存让单条请求约 1.6 s，
  795 条约 20 分钟
- 全片为工厂巡线 + 演播室解说，无赞助口播、无广告段，时间轴与原片一致，未删段
- 与第 31 期 Cybercab 拆解构成“乘用车产线 → 重卡产线”的对照：同样看工位、连接工艺与
  合装顺序，Semi 多了电池箱结构件化、涂装线与驾驶室落装三个环节

