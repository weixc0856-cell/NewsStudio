# 第 31 期：特斯拉 Cybercab 工程拆解——25 个工位造一台无人出租车

- **状态**：已完成
- **信源**：Munro Live 频道，<https://www.youtube.com/watch?v=UIrK8oStl-0>
- **标题**：Tesla Cybercab Deep Dive: Inside the Engineering with Lars Moravy and Team
- **规格**：1:26:41（5201.6 s），源最高 4K24，现场英文原声，2026-10-26 发布
- **建议标题**：`【AI基建·第31期】特斯拉 Cybercab 工程拆解：25 个工位造一台无人出租车，电池包还提前给 LFP 留了位置（中英双语·87分钟）`
- **定位**：汽车篇的「制造侧」——不讲算法、不讲芯片，讲一台为无人驾驶专门设计的车怎么被造出来：
  取消涂装车间、模块化 Unboxed 装配、25 个工位、钢壳 4680 电池包自评 A-。与第 22 期
  Waymo（算力账）互补：一边算芯片，一边算产线与 BOM。

## 三方验证（The Multi-Publisher Rule）

| 类型 | 发布者 |
|---|---|
| 官方 | Munro Live 频道（视频本体，Munro & Associates 媒体部门）；特斯拉方面由车辆工程副总裁 Lars Moravy、Cybercab 总工程师 Eric Earley 出镜 |
| 财经媒体 | Business Insider Markets《Tesla Says Cybercab Factory Is So Efficient It Doesn't Need to Run Every Day》；Benzinga |
| 技术媒体 | Teslarati（两篇：电池包结构与「无人预料的问题」）；The Next Web《Tesla built the Cybercab's battery pack with room for cheaper LFP cells》；Yahoo Autos |
| 国际媒体 | 中文：汽车之家车家号（产线 25 工位两篇）、新浪《Cybercab 工厂探访》、42 号车库系；韩文：AutoHerald；北欧：Teknikveckan；塞尔维亚：Benchmark |
| 社区 | Cybertruck Owners Club 论坛专帖 |

结论：Munro Live 发布原始视频，英文垂直媒体、财经媒体、中文/韩文/北欧汽车媒体各自独立拆解同一次
探访，核心数据（25 工位、约 80% 自动化、88S6P 钢壳包、无涂装车间）互相印证 → **通过**。
视频由 Munro Live 自制，未被单一机构垄断版权。

> 口径提示：多家报道把电池工程负责人写作 Robert Sumpf、把车队规模写作 463 或 544 台，
> 数字存在出入。本期只采信片中人物亲口说出的数字，转述部分在字幕里不额外补充。

## 内容结构（按内容自拟，原视频无官方章节）

| 时间 | 环节 |
|---|---|
| 00:00 | 开场：Giga Texas 车间，Lars Moravy / Eric Earley / Hector 带看，先讲为什么要「拆开造」 |
| 02:32 | Unboxed 的由来：为什么把车做成几个能独立装配的大模块 |
| 06:02 | 前舱模块：热管理、驱动单元、逆变器装成一个可整体更换的单元 |
| 20:02 | 产线全貌：Unboxed 架构与 25 个工位 |
| 25:20 | 电池包：88S6P 4680、钢壳、四个独立灌封模块 |
| 33:32 | 电池包自评 A-：非结构/半结构包，对比 Model Y 的 D |
| 44:10 | 热管理：第三代热泵 |
| 47:22 | 逆变器与电子件：12V/48V 兼容 |
| 51:19 | 电机与减速器：前驱、11:1 齿比 |
| 57:30 | 取消涂装车间：面板与颜色怎么解决 |
| 01:01:11 | 总装：所有 Unboxed 模块在这里合拢 |
| 01:08:03 | 充电与补能设施 |
| 01:16:24 | Optimus 与人形机器人：给无人车插枪、未来维护分工 |
| 01:19:06 | 规模、制造哲学与「为什么别人做不到」 |
| 01:25:07 | 收尾：什么时候能拿到一台 Cybercab |

## 简介模板（可直接粘贴）

**一句话提炼**：Munro Live 走进 Giga Texas，让特斯拉车辆工程副总裁 Lars Moravy 带着团队
把 Cybercab 从外到内拆了一遍——为无人驾驶专门设计的车，最后拼的不是算力，是产线：
25 个工位、取消涂装车间、钢壳 4680 电池包自评 A-，还提前给更便宜的 LFP 留了位置。

**时间戳导航**

```
00:00  为什么要「拆开造」
02:32  Unboxed 的由来
06:02  前舱模块：热管理 + 驱动 + 逆变器一体
20:02  产线全貌：25 个工位
25:20  电池包：88S6P、钢壳、四个灌封模块
33:32  自评 A-：为什么敢把 Model Y 评为 D
44:10  第三代热泵
47:22  逆变器：12V/48V 兼容
51:19  电机与减速器：11:1 齿比
57:30  没有涂装车间的车怎么上色
01:01:11  总装：模块合拢
01:08:03  充电设施
01:16:24  Optimus 来插枪
01:19:06  规模与制造哲学
```

**出处与致谢**：原视频来自 Munro Live（<https://www.youtube.com/watch?v=UIrK8oStl-0>），
本片中英字幕由 YouTube 英文自动字幕整理、经术语统一后由本地 Qwen3-30B-A3B 翻译，
仅供学习交流，版权归原权利人所有。

## 制作结果

- **原片**：`downloads/Tesla Cybercab Deep Dive： Inside the Engineering with Lars Moravy and Team [UIrK8oStl-0].mkv`，
  2,387,197,482 字节（2.22 GiB），H.264 1920×1080 24fps + Opus 48 kHz 立体声，1:26:41.6，
  **无字幕、画面无硬字幕**
- **字幕**：YouTube 英文自动字幕（`en-orig` json3）1442 条句级 cue；产品名规范化
  （`cyber cab / cybercab → Cybercab`、`cybertruck → Cybertruck`、`optimus → Optimus`）后，
  由本地 Qwen3-30B-A3B 按每批 12 条翻译 1442/1442，零空译；译后再统一
  `Lars / Eric / Hector`（原文混用音译与英文）、`unboxed` 的六种译法统一为 `Unboxed`、
  `奥拓马斯 → Optimus`
- **成片**：`downloads/… [中英字幕].mkv`，4,290,423,130 字节（4.00 GiB），H.264 1920×1080 24fps
  + Opus 原音轨（直接复制），6.6 Mbps，1:26:41.6，**硬字幕**（英上中下，1442 条，`MarginV=100`），
  QSV 烧录 5 分 08 秒（16.9×）
- **字幕文件**：`UIrK8oStl-0.zh.bilingual.srt/.ass`（双语，成片用）、`UIrK8oStl-0.en-orig.ass`（英文）
- **校验**：时长与原片一致（5201.621 s）；音轨包数据 MD5 与原片相同
  （`9744ded5cffa5f335c3683cbf54a6aa7`）；head/tail 解码无报错；抽帧确认字幕位置正常
  （英文在上、中文在下，避开左下角 MUNRO LIVE 台标）

## 备注

- 源最高 4K24（VP9 5.66 GiB）。按第 30 期的既有做法，交付取 1080p 而非 4K：选用 H.264
  `137+251`（3.56 Mbps，2.16 GiB），比 4K 省一半以上体积，烧录后仍是 1080p24 的常规交付规格。
- 术语统一：`拉尔斯/埃里克/赫克托` 一律改回 `Lars / Eric / Hector`；`unboxed` 的几种译法
  （未封装 / 无框 / 开箱即装 / 未包装）统一为 `Unboxed`；产品名统一 `Cybercab / Cybertruck / Optimus`。
