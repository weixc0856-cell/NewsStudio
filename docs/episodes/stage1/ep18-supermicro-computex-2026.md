# 第 18 期：美超微 CEO 梁见后 Computex 2026 主题演讲 — 把数据中心拆成积木

- **状态**：已完成
- **信源**：Supermicro 官方频道，<https://www.youtube.com/watch?v=FLJHH3ZWEJo>
- **标题**：CEO Keynote @ Supermicro Innovate | Computex 2026
- **演讲**：梁见后（Charles Liang，Supermicro 创始人、董事长兼 CEO）；
  对谈环节由 Supermicro 首席营收官 Matthew “Matt” Thauberger（2026-05 上任）主持，
  嘉宾为 Arm 云 AI 执行副总裁 Mohamed Awad
- **规格**：51:58，1920×1080 29.97fps（VP9 + Opus，YouTube 最高画质 1080p30），
  YouTube 自动英文字幕（无人工字幕；成片画面另带英文直播硬字幕），2026-06-01 上传
- **建议标题**：`【AI基建·第18期】美超微梁见后 Computex 2026：把数据中心拆成积木，把上线时间压到几个月（中英双语·52 分钟）`
- **定位**：算力与系统集成篇。前 17 期大多在讲芯片、模型与机器人，本期讲“服务器和
  AI 数据中心到底怎么造、怎么快”：DCBBS 积木式方案、机架级集成、液冷与冷却液、
  产能与交付，以及 Arm 对谈里的“代理式 AI 让 CPU 重新吃重”。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 | Supermicro 官方 YouTube（主题演讲全程）、Supermicro 新闻室与 PR Newswire 新闻稿 |
| 财经 / 通讯社 | PR Newswire（Yonhap 转载）、Börse München EQS 转载、BigGo 财经、工商 / 经济日报系 |
| 技术媒体 | Tom's Hardware（经 Yahoo Tech 转载）、TechTimes、The Elec、电波新闻、e4ds、Performance-Intensive Computing |
| 中文媒体 | 智东西（zhiding.cn）、遠見（Global Views Monthly）、3c.yipee.cc、丰云学堂（SinoTrade） |
| 国际媒体 | Yonhap News、Naver News、德国 / 韩国 / 越南多语转载 |

结论：Supermicro 官方发布主题演讲，PR Newswire 同步发稿；Tom's Hardware、TechTimes、
The Elec、电波新闻、智东西、遠見等不同背景媒体对同一批关键事实（DCBBS 5 MW–1 GW、
Vera Rubin NVL72 配置、SMC PG25-A 冷却液、Arm AGI CPU 机架）做了独立报道与核查
→ **通过**。

> 注意：演讲中“新冷却液电阻抗高 1000 倍”的说法，Tom's Hardware 指出 Supermicro
> 未公布电导率、电阻率、介电强度，也未说明对照的基准冷却液，属待第三方验证的营销声明；
> 另有 2026-03-19 美国司法部起诉三名关联人士（含联合创始人 Wally Liaw）涉嫌走私
> 约 25 亿美元英伟达服务器至中国的案件，Supermicro 本身不是被告，但已让相关人员休假并
> 配合调查。两者不影响选品，但简介或置顶评论宜提示“对照阅读”。

### 验证链接（留档）

- 官方视频：<https://www.youtube.com/watch?v=FLJHH3ZWEJo>
- 官方新闻稿（PR Newswire / Yonhap 转载）：<https://m-en.yna.co.kr/view/RPR20260601008600353?section=press-release/index>
- Tom's Hardware（Yahoo Tech 转载）：<https://tech.yahoo.com/computing/articles/supermicro-shows-off-vera-rubin-120207862.html>
- TechTimes（冷却液声明与独立验证）：<https://www.techtimes.com/articles/317621/20260602/supermicro-claims-1000x-impedance-coolant-ai-racks-computex-independent-testing-pending.htm>
- 智东西（DCBBS 5 MW–1 GW）：<https://cooperation.zhiding.cn/2026/0608/3190030.shtml>
- 遠見（新冷却液）：<https://www.gvm.com.tw/article/130568>
- BigGo 财经（Vera Rubin / 1 GW AI 工厂）：<https://finance.biggo.com.tw/news/a_d9kZ4BmHHDnbgyXpiI>
- The Elec（Arm AGI CPU 机架与 Vera Rubin DCBBS）：<https://www.thelec.net/news/articleView.html?idxno=11024>
- 电波新闻（5 MW 到 1 GW）：<https://dempa-digital.com/article/717388>
- e4ds（Computex 2026 端到端战略）：<https://e4ds.com/sub_view.asp?ch=11&t=0&idx=22650&c=1&ti=t>
- 3c.yipee.cc（DCBBS 蓝图）：<https://3c.yipee.cc/340465/>
- PR Newswire 韩国转载（Naver）：<https://n.news.naver.com/mnews/article/092/0002425304>
- Matt Thauberger 任命公告（Business Wire，2026-05-14）：<https://www.businesswire.com/news/home/20260514709915/en/Supermicro-Appoints-Matthew-Thauberger-as-Chief-Revenue-Officer>

## 内容结构

| 时间 | 环节 |
|---|---|
| 00:00 | 开场短片：Built to Accelerate |
| 01:44 | 梁见后登场：AI 革命才刚刚开始 |
| 03:48 | 核心命题：时间是钱，上线时间就是收入 |
| 06:43 | 积木式方案：为什么能比别人快 |
| 08:58 | 已交付的液冷数据中心：5 个月，再到 3 个月 |
| 09:57 | 全平台矩阵：X15 / H15 / N15 / A15 与 Arm AGI |
| 11:20 | GPU 机架：GB300 / B300 出货 8000+ 机架，Vera Rubin NVL72 送样 |
| 17:07 | 产能与交付：营收 150 → 220 → 400 亿美元，600 万平方英尺 |
| 19:16 | 现场机架：Vera Rubin NVL72、供电与散热 |
| 23:54 | 新冷却液：号称 1000 倍电阻抗 |
| 25:52 | 上线与运维：CPO、SONiC、SuperCloud、驻场服务 |
| 33:20 | 对谈 Arm：代理式 AI 让 CPU 重新吃重（Mohamed Awad） |
| 39:23 | Arm AGI CPU：能效、机架密度与产能 |
| 47:04 | 收尾：DCBBS 的四段时间账 |

## 简介模板（可直接粘贴）

**一句话提炼**：梁见后把 AI 数据中心的竞争重新定义成一道时间方程——上市时间、部署时间、
上线时间之和，就是客户开始赚钱的时间。DCBBS 的做法是把服务器、供电、散热、网络、
软件全部拆成预验证的“积木”，以 L11/L12 整机架交付，把行业惯常的 12–18 个月
压到 4–7 个月。

**为什么今天还值得看**

- **一笔算给客户看的时间账**：数据中心晚一个月上线，损失的不只是电费，而是整个业务窗口。
  梁见后把“time to market + time to deploy + time to online = time to make money”
  讲成了全场的主线。
- **积木式工程学的具体拆法**：从主板、机箱、电源、机架到 CDU、冷却塔和 SuperCloud 软件，
  哪些复用、哪些预验证、为什么整机架出货能省掉现场集成。
- **液冷与冷却液的争议点**：DLC-2、CDU、冷板、歧管都讲得很细，但“1000 倍电阻抗”的
  冷却液声明尚无第三方数据，Tom's Hardware 已明确指出缺少对比基准。
- **一组可核对的规模数字**：9 个月出货 8000+ 个 GPU 机架、全球 600 万平方英尺产能、
  营收 150 → 220 → 400 亿美元，以及 Vera Rubin NVL72 已送样、Rubin HGX 与 Vera CPU 排队。
- **Arm 的视角**：Mohamed Awad 解释代理式 AI 为什么让 CPU 从“管理加速器”变成
  “自己发起工作负载”，以及 Arm AGI CPU 想拿下企业本地部署与新兴云的市场。
- **时效说明**：演讲录制于 2026-06-01（Computex 2026），配置、产能与财务数字以当时口径为准。

**时间戳导航**

```
00:00 开场短片：Built to Accelerate
01:44 梁见后登场：AI 革命才刚刚开始
03:48 时间是钱：上线时间就是收入
06:43 积木式方案：为什么能比别人快
08:58 液冷数据中心：5 个月，再到 3 个月
09:57 全平台矩阵：X15 / H15 / N15 / A15 与 Arm AGI
11:20 GPU 机架：8000+ 机架与 Vera Rubin NVL72
17:07 产能与交付：600 万平方英尺
19:16 现场机架：Vera Rubin NVL72、供电与散热
23:54 新冷却液：号称 1000 倍电阻抗
25:52 上线与运维：CPO、SONiC、SuperCloud
33:20 对谈 Arm：代理式 AI 让 CPU 重新吃重
39:23 Arm AGI CPU：能效与机架密度
47:04 收尾：DCBBS 的四段时间账
```

**出处与致谢**：原视频来自 Supermicro 官方频道
（<https://www.youtube.com/watch?v=FLJHH3ZWEJo>），本片中英字幕由 YouTube 自动英文字幕
翻译整理，仅供学习交流，版权归原权利人所有。

> 注：画面下方的英文为原片自带的自动字幕，个别专有名词存在识别错误；
> 本片中文按校正后的英文翻译，专名以中文字幕为准。

## 制作结果

- **原片**：`CEO Keynote @ Supermicro Innovate │ Computex 2026 [FLJHH3ZWEJo].mkv`，
  1.06 GiB（1,139,471,023 字节），VP9 1920×1080 29.97fps + Opus 48kHz 立体声，
  3117.96s（51:58），整体码率 2.92 Mbps，无内嵌字幕
- **字幕**：YouTube 自动英文（json3，2517 个事件合并为 589 条句级 cue）；中文由本地
  Qwen3-30B-A3B 逐条翻译 589/589（1 个批次返回 10/12 行，脚本自动降级为逐条重试后补全，
  0 缺译）；自动字幕专名错误在翻译前修正，译文另做了人工抽查修正（`CRO` 误译“首席风险官”、
  两处 `Supermicro` 误译“英伟达”、`Graviton` 因果句、`indoor CDU`、`SONiC` 等）
- **成片**：`CEO Keynote @ Supermicro Innovate │ Computex 2026 [FLJHH3ZWEJo] [中英字幕].mkv`，
  1.30 GiB（1,398,160,573 字节），H.264（QSV `-global_quality:v 19`）1920×1080 29.97fps + Opus 48kHz
  立体声（原音轨复制），3117.96s（51:58）；
  **画面原带英文直播硬字幕**，按规则不叠加英文，成片只在其上方叠简体中文
  （`MarginV=260`，Microsoft YaHei），QSV 烧录约 3.3 分钟
- **字幕文件**：`subtitles/FLJHH3ZWEJo.en.ass`（英文单语）、
  `subtitles/FLJHH3ZWEJo.zh.bilingual.srt` / `subtitles/FLJHH3ZWEJo.zh.bilingual.ass`
  （英上中下，完整双语存档，`MarginV=100`）、`subtitles/FLJHH3ZWEJo.zh.ass`
  （仅中文，成片烧录用，`MarginV=260`）
- **校验**：成片 3117.961s，与源片一致；head 60s / tail 30s 解码均无报错；
  抽帧 0:30 / 5:00 / 23:59 / 36:32 / 49:10 确认中文位于英文硬字幕上方（间距约一行，
  无重叠），长句按标点换行、未被裁切；输出 29.97fps CFR（25746/859），Opus 48kHz
  立体声原音轨复制

## 备注

- 该视频只有自动英文字幕，无人工字幕；自动字幕的专名错误已在生成双语前修正
  （`Sugon → Supermicro`、`Meradoobin 72 / MVR 72 → Vera Rubin NVL72`、
  `DCBPS / DC BBS → DCBBS`、`authentic AI → agentic AI`、`HGI → AGI`、
  `AR workloads → AI workloads`、`PLC → DLC`、`1.6 terabit sheet → switch` 等）
- 片中没有赞助口播，无需删段，成片即全片
- 最高画质为 1080p30（YouTube 端无 4K/60fps）；VP9 f616 + Opus 251-20
- “1000 倍电阻抗”与“吉瓦级数据中心 5 个月 / 3 个月建成”均为演讲中的单方说法；
  Supermicro 新闻室另有“5 个月建成 1 兆瓦（1 MW）液冷数据中心”的标题口径，
  引用时注意 MW 与 GW 的区别
- 与第 4 期（Intel Computex 2026）、第 9 期（800 VDC AI 工厂）可形成“整机与电力”
  的互文：芯片之外，机架、供电、散热和交付节拍同样是算力扩张的瓶颈
