# YouTube-B

用 `uv` 管理虚拟环境与依赖的 YouTube 高清下载工作区，核心工具是 `yt-dlp`。

---

## 目录结构

```
YouTube-B/
├── pyproject.toml / uv.lock   # uv 依赖定义与锁定
├── .venv/                     # 虚拟环境（uv 生成，勿手动改）
├── yt-dlp.conf                # 项目级 yt-dlp 默认配置（必须保持 ASCII）
├── downloads/                 # 下载产物
├── subtitles/                 # 原语种字幕原件与合成结果
├── clips/                     # 自动高光切片产物（final/ 为可发布目录）
├── scripts/                   # 字幕重建、本地转写、翻译、自动切片等脚本
├── docs/                      # 策划文档与期数档案（docs/episodes/）
└── README.md
```

## 环境要求

| 依赖 | 版本 / 说明 |
|---|---|
| uv | 0.10.8（本机实测） |
| Python | 3.12（由 `.python-version` + uv 管理） |
| yt-dlp | 2026.10.21（`uv.lock` 锁定） |
| curl_cffi | 0.16.x（字幕请求的浏览器指纹模拟；yt-dlp 不支持 0.17.x） |
| faster-whisper | 1.x（原语种字幕缺失时的本地转写兜底） |
| ffmpeg | 8.1（需在 PATH 中，用于合并音视频、烧字幕） |
| node | v24（YouTube 的 JS 挑战求解，yt-dlp 默认只认 deno） |

首次使用或换机器：

```powershell
uv sync
uv run yt-dlp --version
ffmpeg -version
```

## 下载

```powershell
uv run yt-dlp "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

配置会自动生效：选最高画质、合并 MKV、保存到 `downloads/`，文件名为
`<标题> [<视频ID>].mkv`。`yt-dlp.conf` 不开启任何字幕写入，**原片始终无字幕**；
字幕在后期按“字幕规则”单独生成和匹配。

## 字幕规则（2026-10-26 起，长期有效）

所有从 YouTube 下载的视频，字幕统一按以下规则处理：

1. **只下载无字幕原片**：yt-dlp 只拉最高画质的视频/音频，不内嵌任何字幕；原片保持干净。
2. **字幕后期匹配**：字幕作为独立步骤生成并匹配，成品另存（如 `[中英字幕].mkv`），不覆盖原片。
3. **语序**：视频本身语言（原语种）在上，简体中文在下。
4. **只下载原语种字幕**：人工字幕优先，其次自动生成字幕；**不下载 YouTube 的中文自动翻译**。
5. **中文一律本地生成**：中文由本地大模型（Qwen3-30B-A3B，见下节）逐句翻译原语种字幕，
   与原语种按时间轴一一对应。
6. **画面已带中文硬字幕时**：不再叠加中文，只把原语种字幕叠在硬字幕上方，避免出现两行中文。
7. **兜底**：没有原语种字幕时，先用本地 Whisper 转写原语种，再走本地翻译。
8. **交付物**：无字幕原片 + 字幕成品（默认烧录，独立文件）+ `bilingual.srt`。

### 处理流程

```powershell
# 1. 最高画质下载（yt-dlp.conf 自动生效）
uv run yt-dlp "URL"

# 2. 只抓原语种字幕（把 en 换成视频原语种代码；不抓 zh-Hans）
uv run yt-dlp --skip-download --write-auto-subs --sub-langs "en" `
  --sub-format json3 -P subtitles -o "%(id)s.%(ext)s" --impersonate chrome "URL"

# 3. 原语种字幕缺失时，本地 Whisper 转写
uv run python scripts/transcribe.py

# 4. 生成原语种 ASS / SRT
uv run python scripts/build_subs.py --id <id> --prefix <id>. --margin-v 100

# 5. 本地大模型翻译，产出双语 SRT + ASS（原语种在上，中文在下）
uv run python scripts/translate_local.py "subtitles/<id>.bilingual.srt" `
  --prefix <id>.zh. --batch 12 --margin-v 100

# 6. 烧录字幕，输出独立成品（QSV 硬件加速，音轨直接复制；原片不动）
ffmpeg -i "downloads/<视频>.mkv" -vf "ass=subtitles/<id>.zh.bilingual.ass" `
  -c:v h264_qsv -global_quality 19 -preset slow -c:a copy `
  -map_metadata 0 "downloads/<视频> [中英字幕].mkv"
```

> 字幕位置：画面有中文硬字幕时，只烧原语种单语 ASS（`--margin-v 350`，避开底部 1–2 行硬字幕）；
> 画面干净时，烧本地翻译的双语 ASS（`--margin-v 100`，常规底部）。
> 画面底部有常驻会议横幅 / 图形时，用 `--margin-v 200` 把字幕抬到横幅上方。
> 60fps VFR 源（如 OCP session）烧录时加 `-fps_mode cfr -r 60`，避免 QSV 输出重复 DTS。
> 原语种不是英语时，用 `--top <语言代码>` 指定；`translate_local.py` 按原语种文本翻译成中文。
> 删除片中赞助口播：不要用 `concat` 滤镜把 4K 切成三段再拼（会缓冲整段画面导致内存爆掉）。
> 用 `select`/`aselect` 按时间区间剔除，再用 `setpts`/`asetpts` 减去被删时长，字幕按同一组
> 切点重映射（`.trim.srt` / `.trim.ass`）。重编码音轨时 `-global_quality` 必须限定为 `:v`，
> 否则 libopus 会报 `Quality-based encoding not supported`。
> 人工字幕（`--manual`）：先按句合并，再用 `scripts/translate_groups.py` 以“句组”为单位翻译，
> 避免模型把相邻碎片合并后整体错位；长句按 jieba 词边界切成 ≤2 行英文 + 2 行中文的显示 cue。
> 逐条碎片字幕（`--manual --raw`）不适合直接批量翻译，容易出现整段位移。

> 裁剪片头：先 `uv run python scripts/shift_subs.py subtitles/en.ass subtitles/en.trim.ass -3`，
> 再用 `-ss 3` 从原片重烧；此时音轨必须重编码（`-c:a libopus -b:a 160k`），不能用
> `-c:a copy`——输入 seek 下音频不会随视频一起裁掉，会导致音画相差 N 秒。

### 自动高光切片（2026-10-28 起）

从已完成的**双语 SRT** 与原片中自动切出 3–8 分钟的独立成片片段，完整规格见
[`docs/自动剪辑-高光切片方案.md`](docs/自动剪辑-高光切片方案.md)。

```powershell
# 1) 只分析：滑动窗口 + 本地模型提候选 + 确定性过滤，输出 analysis.json
uv run python scripts/auto_clip.py --srt "subtitles/<id>.zh.bilingual.srt" --analyze-only

# 2) 完整流程：分析 + 字幕钳位 + QSV 渲染 + ffprobe 验收
uv run python scripts/auto_clip.py --srt "subtitles/<id>.zh.bilingual.srt" `
  --video "downloads/<视频> [<id>].mkv" --max-clips 2

# 3) 只重渲染：复用已有 analysis.json，不再调用模型
uv run python scripts/auto_clip.py --srt ... --video ... --reuse-analysis

# 4) 手动覆盖某条切片起点（1 起始序号；时间吸附到包含该时刻的 cue 起点）
uv run python scripts/auto_clip.py --srt ... --video ... --reuse-analysis `
  --override-start "1=00:04:49.375"

# 5) 拼接已验收切片（独立脚本；硬切 + 字幕重映射 + 重新 ffprobe 验收）
uv run python scripts/merge_highlights.py --result clips/<id>/result.json
```

产物全部在 `clips/<id>/`：

| 路径 | 内容 |
|---|---|
| `analysis.json` | 每个窗口的 cue 范围、模型尝试、原始候选、淘汰/去重原因 |
| `result.json` | 终态、切片、逐项验收、`manual_overrides`、`merge` 结果 |
| `final/` | **仅**通过自动验收的 MP4（`<id>.highlight-NN.*.mp4` + `highlights-merged.mp4`） |
| `quarantine/` | 未通过验收的 MP4 + `.failed.json` |
| `work/` | 钳位后的 `clip-NN.srt/.ass`、`highlights-merged.srt/.ass`、FFmpeg 日志、窗口 Prompt |

- 模型只提候选（两个 cue ID + 标题 + 摘要）；时长门禁、归属、重叠去重、配额、字幕钳位、
  ffprobe 验收全部由 Python 确定性执行，任一淘汰都写入 JSON。
- 窗口默认 11 分钟、重叠 3.5 分钟；切片 3–8 分钟，优先 4–6 分钟；重叠率 > 0.4 判重；
  默认最多 2 条，候选不足不强行出片。
- 渲染 `-ss <起点> -i <原片> -t <时长>`，`h264_qsv` 视频 + AAC 音频；`-map_chapters -1`
  避免 MP4 生成多余的章节文本轨。
- 第 21 期基准：3 窗口全部成功，3 个原始候选中 1 个因重叠被去重、2 个通过验收；
  切片 1 按人工要求把起点从 04:55.609 覆盖到 04:49.375（cue 51），时长 372.369s；
  两条成片偏差 +24 / +23 ms，音频相对视频 −21.4 ms（AAC 编码器延迟，听感无差异）。
- 合集：`highlights-merged.mp4`，588.290s（预计 588.249s，+41 ms），2 段硬切，
  **非连续剪辑，中间跳过约 4m43s（282,431 ms）**；字幕 121 条，重映射后无溢出。
- 合集不直接拼接已烧录字幕的成片（会叠字），而是从源片按同一区间重新取流并只烧一次。
- 回归测试：`scripts/test_auto_clip.py`（12 项）+ `scripts/test_merge_highlights.py`（6 项）；
  严格解析器已对 `subtitles/` 下全部 41 个双语 SRT 验证，0 错误。

### 本地大模型翻译（Qwen3-30B-A3B）

按规则，中文字幕**不从 YouTube 下载**，统一用本地 llama.cpp 服务逐句翻译原语种字幕；
在线免费翻译（Google/MyMemory）容易限流且术语不准，仅作备选：

```powershell
# 等价于 start_server.bat 选模型 3 + 档位 3（16K），直接启动
D:\AI\bin-sycl\llama-server.exe -m "D:\AI\models\Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf" `
  --host 127.0.0.1 --port 8080 -dev SYCL0 -ngl 99 -c 16384 --parallel 1 `
  -b 256 -ub 128 -fa on --metrics --alias "Qwen3-30B-A3B-Instruct-2507-Q4_K_M,default" `
  --jinja --n-cpu-moe 48

# 逐批翻译英文 SRT，输出双语 SRT + ASS（英文在上、中文在下）
uv run python scripts/translate_local.py "subtitles/<id>.bilingual.srt" `
  --prefix <id>.zh. --batch 12 --margin-v 100
```

- 术语表在 `scripts/translate_local.py` 的 `SYSTEM` 提示里维护（默茨总理、黄仁勋、英伟达、中小企业）
- ASS 字体用 `Microsoft YaHei`，中文字形正常；`MarginV=100` 对应 1080p 常规底部
- 已知坑：ASS 换行是 `\N`，生成 Dialogue 时必须先分别转义上下两行再拼接；
  先拼接再转义会把 `\N` 变成字面反斜杠 + 字母 N（画面行尾会多一个 `\`）
- 已知坑：libass 不会在无空格的中文行内自动换行，长中文会从右侧被裁掉；
  `write_ass()` 的 `_wrap_cjk()` 会按标点优先、50 字上限插入 `\N` 硬断行；
  两行时按中点均分，`_safe_cut()` 避免把英文单词/缩写（如 Hyper NA）拆开

## yt-dlp.conf 逐项说明

| 配置 | 作用 | 为什么需要 |
|---|---|---|
| `--js-runtimes node` | 用 node 执行 YouTube 的 JS 挑战 | 不加时 n-challenge 解不开，YouTube 会少给格式（实测首轮列出时就缺格式） |
| `--remote-components ejs:github` | 启用 EJS 远程挑战求解脚本 | 仅启用 node 仍可能提示 challenge solver 缺失 |
| `-f bv*+ba/b` | 最佳视频流 + 最佳音频流 | 高清视频和音频在 YouTube 上是分离的，必须合并 |
| `-S res,fps,hdr:12,vcodec:vp9.2:vp9:av01:h264,acodec:opus:aac` | 排序优先级 | 同分辨率下优先高码率、宽解码支持的 VP9；音频优先 Opus |
| `-P downloads` | 输出目录 | 与项目源码分开 |
| `-o "%(title)s [%(id)s].%(ext)s"` | 文件名模板 | 带视频 ID，避免重名；含空格必须加引号 |
| `--merge-output-format mkv` | 强制 MKV 容器 | VP9 + Opus 放 MP4 兼容性差 |
| `--embed-metadata` | 写入标题等元数据 | 播放器里能显示正确标题 |
| `--retries 10` / `--fragment-retries 10` | 失败重试 | 长视频断流时自动续传 |
| `--concurrent-fragments 4` | 分片并发 | 加速 HLS/DASH 分片下载 |
| `--http-chunk-size 10M` | 加大 HTTP 分块 | 缓解 YouTube 对单请求的限速 |

> **配置编码限制**：Windows 下 yt-dlp 按系统编码（GBK）读取 `yt-dlp.conf`，
> 写中文注释会直接报 `Unable to parse "yt-dlp.conf": 'gbk' codec can't decode ...`。
> 该文件必须保持纯 ASCII。

## 本次下载记录（2026-10-26）

> 注：此节记录的是中文剪辑版（画面自带中文硬字幕）的处理过程。相关视频文件已于
> 2026-10-26 清理，仅保留处理记录与字幕文件；官方原版见下节。

来源：`https://www.youtube.com/watch?v=dIi3X6VJ3v8`
标题：德国总理对话黄仁勋：AI时代中国的优势，德国补得上吗？ — 24:08

实际选中的流：`271+251-20` → MKV，726 MB

| 项目 | 实际参数（ffprobe） |
|---|---|
| 分辨率 | 2560×1440，VP9，30fps |
| 音频 | Opus 48kHz 立体声，原始音轨（YouTube 元数据标记 en-US） |
| 时长 | 1448.26 秒 = 24:08 |
| 容器 | MKV，已嵌入元数据 |
| 整体码率 | ~4.2 Mbps |

**为什么是 1440p**：该视频 YouTube 端最高只提供到 1440p，无 4K/8K。
1440p 有三个候选流，选择依据：

| 格式 ID | 编码 | 码率 | 结论 |
|---|---|---|---|
| 271 | VP9 (webm) | 4075k | **选中**：同分辨率下码率最高，VP9 解码普及 |
| 400 | AV1 (mp4) | 3054k | 效率相当，但老设备软解更吃力 |
| 620 | VP9 (m3u8/HLS) | 标称 7779k | 标称值含多音轨开销，且为 Untested |

音频：`251-20`（Opus 126k）为 YouTube 标记的 original (default) 音轨；
`140-20` 是同一音轨的 AAC 版本（129k），按 Opus 优先规则未选。

### 中英字幕版（2026-10-26）

文件：`... [dIi3X6VJ3v8] [中英字幕].mkv`，771 MB（已剪掉前 3 秒）

| 项目 | 实际参数 |
|---|---|
| 视频 | H.264（QSV `-global_quality:v 19`），2560×1440，30fps |
| 音频 | Opus 48kHz 立体声（`libopus 160k` 重编码） |
| 时长 | 1445.25s（源 1448.26s − 3s），音视频均从 0 开始 |
| 字幕 | 英文单语 ASS（`MarginV=350`），烧录在画面中文硬字幕上方 |

字幕文件：`en.ass`（未剪）、`en.trim.ass`（剪后）、`bilingual.srt`（未剪）、
`bilingual.trimmed.srt`（剪后；中文行可按新规则用本地模型补译）。

处理过程：

1. 英文源：YouTube 自动字幕（`en` json3，1984 个词块），脚本重建为 298 条句级 cue；
   期间字幕端点持续 429，改用 `curl_cffi` 指纹模拟后抢到一次。
2. 中文源：画面本身已有 1–2 行中文硬字幕，按规则不再叠加中文，只把英文放在其上方。
   `bilingual.srt` 中未生成中文行；如需中文，按新规则用本地模型翻译补全。
3. 烧录：`ass` 滤镜 + `h264_qsv`，24 分钟视频约 3 分钟完成；抽帧 60s/300s/1100s/1400s
   确认英文始终位于中文上方，英文换行时向上扩展、不重叠。
4. 裁剪：先确认 3 秒处没有关键帧（GOP 约 8 秒），流拷贝会切到 0 或 8.3 秒，因此从原片
   重新烧录；`scripts/shift_subs.py` 把 ASS/SRT 整体前移 3 秒，`-ss 3` 输入 seek 后两条流
   都从 0 开始。注意 `-c:a copy` 在输入 seek 下不裁音频、只保留原始时间戳，会造成 3 秒
   音画不同步，必须改为重编码音轨（`libopus`）。
5. 校验：输出首帧与源片第 3 秒逐帧比对一致；输出 57s 的字幕对应源片 60s，确认整体平移正确。

### 官方原版（2026-10-26 补）

上面那个中文版是二手剪辑（自带中文硬字幕和片头包装）。官方原始上传来自德国联邦经济与能源部：

- 链接：`https://www.youtube.com/watch?v=PCroCEAGQ7g`
- 标题：Fireside Talk: Chancellor Merz and Jensen Huang | Invest in Germany Summit 2026
- 规格：58:15，1920×1080 60fps，VP9 + Opus，1.09 GB，无硬字幕
- 结构：开头约 23 分钟是直播等待画面和峰会开场演讲，对谈位于 **22:55–47:02**
- 注：完整 58:15 原版文件已清理；保留下面切出的无字幕对谈片段和双语成品

对谈片段（无损流拷贝，未重编码）：

- 文件：`Fireside Talk - Chancellor Merz and Jensen Huang [PCroCEAGQ7g] [对谈片段].mkv`，581 MB
- 切点：1374.767s → 2822.483s（24:07.7），音视频起点均为 0；音频互相关 0ms、相关度 1.0
- 字幕：274 条 cue。英文来自 YouTube 自动字幕；中文由本地 Qwen3-30B-A3B 逐句翻译
  （`scripts/translate_local.py`，274/274 有译文、0 缺译），已烧录为双语成片：
  `Fireside Talk - Chancellor Merz and Jensen Huang [PCroCEAGQ7g] [对谈片段] [中英字幕].mkv`
  （861 MB，H.264 1080p60 + Opus，24:07.7，英文在上、中文在下）
- 字幕文件：`PCroCEAGQ7g.talk.en.ass`（英文单语）、
  `PCroCEAGQ7g.talk.zh.bilingual.srt` / `.ass`（双语，`MarginV=100`，Microsoft YaHei）
- 按规则未下载 YouTube 的中文字幕，中文由本地模型翻译；翻译约 8 分钟，
  其中一批返回行数不符，脚本自动降级为逐条重试后补全

字幕脚本新增参数：`--id` 指定视频、`--prefix` 输出前缀、`--start/--end` 截取区间并自动平移、
`--margin-v` 调整底部留白。注意 `--id` 与 `--prefix` 不可省，否则多视频共存时会选错字幕源。

**完整性校验**（均已执行，无报错）：

```powershell
# 参数
ffprobe -v error -show_entries format=duration,size,bit_rate -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels -of default=noprint_wrappers=1 "downloads/<文件名>.mkv"

# 头部 60 秒解码
ffmpeg -v error -i "downloads/<文件名>.mkv" -t 60 -f null -

# 尾部 30 秒解码（确认文件尾完整、未截断）
ffmpeg -v error -sseof -30 -i "downloads/<文件名>.mkv" -f null -
```

## GTC Berlin 2026 主题演讲（2026-10-26）

官方源：NVIDIA 频道，`https://www.youtube.com/watch?v=v-NGxyPjcrE`
标题：NVIDIA GTC Berlin 2026 Keynote With CEO Jensen Huang（2026-10-23 上传，1:31:59，英）

- 画质：最高 4K60。可选 VP9 315（8.38 Mbps，5.39 GiB）与 AV1 401（4.49 Mbps，2.95 GiB）。
  YouTube 限速下单连接约 0.4–1.3 MB/s，VP9 预计 3.5 小时，故选用 AV1（约 1 小时，画质接近）。
- 原片：`NVIDIA GTC Berlin 2026 Keynote With CEO Jensen Huang [v-NGxyPjcrE].mkv`，
  3.0 GB，AV1 3840×2160 60fps + Opus，5518.98s，**无字幕**。
- 字幕：只抓英文原语种（auto captions json3，1022 条 cue）；中文由本地 Qwen3-30B-A3B
  逐句翻译（1022/1022，0 缺译），术语表补充 token→词元、AI factory→AI 工厂等。
- 成品：`... [v-NGxyPjcrE] [中英字幕].mkv`，3.5 GB，**双语字幕已烧录进画面**
  （AV1 QSV medium、`global_quality 24`，约 35 分钟），英文在上、中文在下，
  任何播放器直接可见。
- 说明：先做过一版“无损封装 ASS 字幕轨”，但测试播放器不显示（不支持 MKV/ASS 轨或默认标记），
  因此改为硬字幕。编码实测：av1_qsv medium 约 3× 实时（约 35 分钟）、slow 约 47 分钟，
  h264_qsv slow 约 92 分钟。
- 字幕文件：`v-NGxyPjcrE.en.ass`（英文单语）、`v-NGxyPjcrE.zh.bilingual.srt/.ass`（双语）。

## AMD Advancing AI 2026 主题演讲（2026-10-27）

官方源：AMD 频道，`https://www.youtube.com/watch?v=crEztVjfAPM`
标题：Advancing AI 2026 | Build What's Next with @AMD（2026-07-23，2:13:50，英）

- 选品：通过三方验证（AMD Newsroom、Yahoo Finance / TheStreet、EE Times、36Kr、
  StockAnalysis 等），完整记录见 `docs/专栏策划-AI时代的基建.md` 第十节
- 画质：最高 1080p30；选用 HLS VP9 高码率流（约 2.47 Mbps，2.4 GB）
- 原片：`... [crEztVjfAPM].mkv`，2.4 GB，VP9 1920×1080 29.97fps + Opus，**无字幕**
- 字幕：**官方人工英文字幕**（2078 条事件，按句末标点合并为 1420 条 cue）；
  中文由本地 Qwen3-30B-A3B 翻译（1420/1420，1 条单独补译），术语含 Helios、ROCm、EPYC 等
- 成品：`... [crEztVjfAPM] [中英字幕].mkv`，2.2 GB，H.264 1080p + Opus，
  **硬字幕**（英文在上、中文在下），烧录约 13 分钟
- 字幕文件：`crEztVjfAPM.en.ass`（英文单语）、`crEztVjfAPM.zh.bilingual.srt/.ass`（双语）
- 人工字幕处理：新增 `--manual` 模式，按人工 cue 时间轴处理，并在句末标点处合并、
  130 字 / 8 秒限长，避免长句被硬切导致翻译补全

## Intel Computex Keynote 2026（2026-10-27）

官方源：Intel 频道，`https://www.youtube.com/watch?v=7HvrdXjdlU8`
标题：Intel Computex Keynote 2026（2026-06-02，1:06:14，英，陈立武）

- 选品：通过三方验证（Intel Newsroom、Nasdaq、TrendForce、Futurum、CRN、Gadgets Now 等），
  记录见 `docs/episodes/ep04-intel-computex-2026.md`
- 画质：最高 1080p60；选用 HLS VP9 高码率流（约 2.29 Mbps，1.1 GB）
- 原片：`Intel Computex Keynote 2026 [7HvrdXjdlU8].mkv`，1.1 GB，
  VP9 1920×1080 59.94fps + Opus，**无字幕**
- 字幕：YouTube 自动英文（700 条 cue），本地 Qwen 翻译 700/700；
  术语补充 Intel→英特尔、Lip-Bu→立武/陈立武、Xeon→至强、McLaren→迈凯伦
- 成品：`... [7HvrdXjdlU8] [中英字幕].mkv`，4.1 GB，H.264 1080p60 + Opus，
  **硬字幕**（英文在上、中文在下），烧录约 20 分钟
- AV1 版：`... [7HvrdXjdlU8] [中英字幕][AV1].mkv`，2.2 GB（4.63 Mbps），
  比 H.264 版小约 47%，两版并存
- 字幕文件：`7HvrdXjdlU8.zh.bilingual.srt/.ass`、`7HvrdXjdlU8.en.ass`

## Google Cloud Next '26 Opening Keynote（2026-10-27）

官方源：Google Cloud 频道，`https://www.youtube.com/watch?v=11PBno-cJ1g`
标题：Google Cloud Next '26 Opening Keynote（2026-04-22，1:38:58，英）

- 选品：通过三方验证（Google Cloud Blog、CIO.com、SiliconANGLE、ITPro、Futurum、
  澎湃新闻、证券时报等），完整记录见 `docs/episodes/ep05-google-cloud-next-26.md`
- 画质：最高 1080p30，无 4K；选用格式 616（VP9，标称 5.07 Mbps，实际约 2.53 Mbps）
  + 251（Opus），实测 616 虽标 Premium 但可正常取流
- 原片：`Google Cloud Next '26 Opening Keynote [11PBno-cJ1g].mkv`，1.79 GB，
  VP9 1920×1080 29.97fps + Opus 48kHz 立体声，1:38:58，**无字幕**
- 字幕：**官方人工英文字幕**（`en-j3PyPqV-e1s`，1833 条事件按句合并为 964 条 cue）；
  中文由本地 Qwen3-30B-A3B 翻译 964/964，2 条跨 cue 尾句人工补齐
- 成品：`... [11PBno-cJ1g] [中英字幕].mkv`，1.78 GB，H.264 1080p + Opus，
  **硬字幕**（英文在上、中文在下），QSV 烧录 7 分 49 秒
- 字幕文件：`11PBno-cJ1g.zh.bilingual.srt/.ass`、`11PBno-cJ1g.en-j3PyPqV-e1s.ass`
- 人工字幕处理：`clean()` 清理 `SPEAKER N:` / 姓名标签与音效标签；
  `merge_manual_cues()` 在 1.5 秒以上停顿处断句；`write_ass()` 新增 `_wrap_cjk()`，
  按标点优先、50 字上限硬断行，解决 libass 不自动换行导致的长中文裁切

## State of GPT（2026-10-27）

官方源：Microsoft Developer 频道，`https://www.youtube.com/watch?v=bZQun8Y4L2A`
标题：State of GPT | BRK216HFS（Andrej Karpathy / Microsoft Build 2023，42:40，英）

- 选品：通过三方验证（Microsoft Build / Karpathy 官方幻灯片、GitHub 镜像、Glasp 转录、
  TheMind、Lawrence Wu、澎湃 / 机器之心、B 站双语版等），记录见
  `docs/episodes/ep06-state-of-gpt.md`
- 画质：最高 1080p30；格式 616（VP9，标称 5.24 Mbps）+ 251-8（Opus 107k 原声）
- 注意：该视频带 8 条自动配音音轨（de / es / fr / hi / id / it / ja / pl），
  必须显式指定 `251-8`，裸 `251` 会报 `Requested format is not available`
- 原片：`State of GPT ｜ BRK216HFS [bZQun8Y4L2A].mkv`，469.8 MB，
  VP9 1920×1080 29.97fps + Opus，42:40，**无字幕**
- 字幕：官方人工英文 `en-US`（1133 条事件 → 464 条 cue）；
  中文由本地 Qwen3-30B-A3B 翻译 464/464
- 成品：`... [中英字幕].mkv`，492.0 MB，H.264 1080p + Opus，
  **硬字幕**（英上中下），QSV 烧录 3 分 11 秒
- 字幕文件：`bZQun8Y4L2A.zh.bilingual.srt/.ass`、`bZQun8Y4L2A.en-US.ass`
- 定位：2023 年经典演讲，作为“基础篇”；简介中已写明“为什么今天还值得看”
  （训练管线、LLM 心智模型、方法分层三层参考价值），并注明产品与数字以 2023 年为准

## 黄仁勋 × Cadence（CadenceLIVE Silicon Valley 2024，2026-10-27）

官方源：Cadence Design Systems 频道，`https://www.youtube.com/watch?v=YUrlLq2CuGM`
标题：Anirudh Devgan and Jensen Huang - CadenceLIVE Silicon Valley 2024 - Fireside Chat（28:57，英）

- 选品：通过三方验证（Cadence 官方、SemiWiki、EDN、Cambrian AI、每日经济新闻、
  东方财富、Infobae 等），记录见 `docs/episodes/ep07-cadence-jensen-huang-2024.md`
- 画质：最高 1080p30，仅 H.264（无 VP9 / AV1）；选用 `270+251`（实际约 1.20 Mbps）
- 原片：`Anirudh Devgan and Jensen Huang - CadenceLIVE Silicon Valley 2024 - Fireside Chat [YUrlLq2CuGM].mkv`，
  247.9 MB，H.264 1080p + Opus，28:57，**无字幕**
- 字幕：**无人工字幕**，使用 YouTube 自动英文（json3，260 条句级 cue）；
  自动字幕无标点、全小写，已修正 `Jensen Wong → Jensen Huang`、`Jansen → Jensen`、
  跨 cue 拆开的 `Blackwell`、`Eda → EDA`
- 中文：本地 Qwen 翻译 260/260
- 成品：`... [中英字幕].mkv`，387.2 MB，H.264 1080p + Opus，
  **硬字幕**（英上中下），QSV 烧录 2 分 29 秒
- 字幕文件：`YUrlLq2CuGM.zh.bilingual.srt/.ass`、`YUrlLq2CuGM.en.ass`
- 定位：产业对谈篇，讲 Blackwell 背后的 Palladium 仿真、加速计算对抗反摩尔定律、
  数字生物学与人形机器人；简介已写明“为什么今天还值得看”

## NVIDIA GTC Studio × Schneider Electric（2026-10-27）

官方源：NVIDIA 官方频道，`https://www.youtube.com/watch?v=lBNHFR41GgY`
标题：NVIDIA GTC Studio with Insights from Schneider Electric（17:04，英）

- 选品：通过三方验证（NVIDIA 官方、Schneider Electric Newsroom、Frank's World、
  Data Center Frontier、AutomationWorld、赛迪网等），记录见
  `docs/episodes/ep08-gtc-studio-schneider-electric.md`
- 画质：最高 1440p30；选用 VP9 `271+251`（实际约 4.86 Mbps）
- 原片：`NVIDIA GTC Studio with Insights from Schneider Electric [lBNHFR41GgY].mkv`，
  593.3 MB，VP9 2560×1440 + Opus，17:04，**无字幕**
- 字幕：**无人工字幕**，使用 YouTube 自动英文（json3，234 条句级 cue）；
  这期自动字幕带标点与大小写，质量较好
- 中文：本地 Qwen 翻译 234/234
- 成品：`... [中英字幕].mkv`，637.4 MB，H.264 1440p + Opus，
  **硬字幕**（英上中下），QSV 烧录 2 分 13 秒
- 字幕文件：`lBNHFR41GgY.zh.bilingual.srt/.ass`、`lBNHFR41GgY.en.ass`
- 定位：能源与电力层短篇访谈；Pankaj Sharma 谈 AI 工厂的电力、电网与可持续能源；
  简介已按访谈内容整理 10 个时间戳

## 800 VDC AI Factories（OCP Global Summit 2026，2026-10-27）

官方源：Open Compute Project 频道，`https://www.youtube.com/watch?v=4ywmp2XSuiU`
标题：800 VDC AI Factories From Architecture Alignment to Industry Deployment（20:53，英）
讲者：Mike Tu、Jared Huntington（NVIDIA）

- 选品：通过三方验证（OCP 官方、NVIDIA 博客、Data Center News Asia、Network World、
  Dell'Oro、财联社等），记录见 `docs/episodes/ep09-800vdc-ai-factories.md`
- 画质：最高 1080p60；选用 VP9 `617+251`（标称 1997k，实际约 0.53 Mbps，静态幻灯片文字清晰）
- 原片：`800 VDC AI Factories From Architecture Alignment to Industry Deployment [4ywmp2XSuiU].mkv`，
  79.0 MB，VP9 1080p60 + Opus，20:52，**无字幕**
- 字幕：YouTube 自动英文（268 条句级 cue）；中文 Qwen 翻译 268/268，
  800 VDC 统一（模型初译混用“800 伏 / 800V 直流电”，已纠正 18 处）
- 成品：`... [中英字幕].mkv`，180.1 MB，H.264 1080p60 CFR + Opus，
  **硬字幕**（英上中下），MarginV=200（避开底部 OCP 横幅），烧录 2 分 55 秒
- 注意：源是 60fps VFR，首版 QSV 输出有重复 DTS；重烧时加 `-fps_mode cfr -r 60`，警告归零
- 字幕文件：`4ywmp2XSuiU.zh.bilingual.srt/.ass`、`4ywmp2XSuiU.en.ass`

## 黄仁勋 × 美国两党政策中心（AI 与能源，2026-10-27）

官方源：Bipartisan Policy Center 频道，`https://www.youtube.com/watch?v=doJDuLMnaWc`
标题：A Conversation with NVIDIA CEO Jensen Huang – The Future of AI and Energy（1:02:20，英）

- 选品：通过三方验证（BPC 官方、C-SPAN、Internet Archive、Axios、E&E News、
  Utility Dive、POLITICO Pro 等），记录见 `docs/episodes/ep10-bpc-jensen-huang-ai-energy.md`
- 画质：最高 1080p30；选用 VP9 `616+251`（实际约 1.86 Mbps）
- 原片：`A Conversation with NVIDIA CEO Jensen Huang – The Future of AI and Energy [doJDuLMnaWc].mkv`，
  827.6 MB，VP9 1080p30 + Opus，62:20，**无字幕**
- 字幕：YouTube 自动英文（793 条句级 cue）；中文 Qwen 翻译 793/793
- 修正：2 条跨 cue 尾句漏译、620–624 错位（中文整体提前一条），已人工重新对齐
- 成品：`... [中英字幕].mkv`，993.4 MB，H.264 1080p30 CFR + Opus，
  **硬字幕**（英上中下），烧录 4 分 30 秒
- 字幕文件：`doJDuLMnaWc.zh.bilingual.srt/.ass`、`doJDuLMnaWc.en.ass`
- 定位：政策与能源篇，补上华盛顿视角；简介已写明“为什么今天还值得看”

## PhysicsX × AWS（物理 AI / 汽车空气动力学，2026-10-27）

官方源：AWS Events 频道，`https://www.youtube.com/watch?v=z8i0qatIucE`
标题：AWS re:Invent 2025 - PhysicsX: Scaling Physics AI for Automotive Aerodynamics (STP109)（17:10，英）
讲者：James Leahy（PhysicsX 首席研究科学家）

- 选品：通过三方验证（AWS 官方与案例、IAA Mobility 同题演讲、AI Business、CDFAM、
  Business Times 等），记录见 `docs/episodes/ep11-physicsx-aws-aerodynamics.md`
- 画质：最高 1080p30，仅 H.264；270（HLS）时间戳异常，改用 137（DASH）+ 251
- 原片：`AWS re:Invent 2025 - PhysicsX: Scaling Physics AI for Automotive Aerodynamics (STP109) [z8i0qatIucE].mkv`，
  101.1 MB，H.264 1080p30 + Opus，17:10，**无字幕**
- 字幕：**官方人工英文** `en-eEY6OEpapPo`（392 事件 → 190 条 cue）；
  中文 Qwen 翻译 190/190；行首 `- ` 说话人标记已在 `clean()` 清理
- 成品：`... [中英字幕].mkv`，132.2 MB，H.264 1080p30 CFR + Opus，
  **硬字幕**（英上中下），烧录 1 分 20 秒
- 字幕文件：`z8i0qatIucE.zh.bilingual.srt/.ass`、`z8i0qatIucE.en-eEY6OEpapPo.ass`
- 定位：工业 AI / 物理 AI 应用篇；大型物理模型替代/加速传统 CFD，已在主要车企落地

## CNBC 独家：ASML 4 亿美元 High-NA 光刻机（2026-10-27）

官方源：CNBC 频道，`https://www.youtube.com/watch?v=1JkzrR-hznE`
标题：How ASML Makes Chips Faster With Its New $400 Million High NA Machine（17:25，英）

- 选品：通过三方验证（CNBC 原始独家、Reuters/CGTN、Benzinga、TrendForce、DIGITIMES、
  36Kr、钛媒体等），记录见 `docs/episodes/ep12-cnbc-asml-high-na.md`
- 画质：最高 1080p24；选用 VP9 `616+251-11`（实际约 2.24 Mbps）
- 注意：视频带 11 条自动配音音轨，必须显式指定原声 `251-11`，裸 `251` 不可用
- 原片：`How ASML Makes Chips Faster With Its New $400 Million High NA Machine [1JkzrR-hznE].mkv`，
  279.5 MB，VP9 1080p24 + Opus，17:25，**无字幕**
- 字幕：**官方人工英文** `en`（399 事件 → 198 条 cue）；中文 Qwen 翻译 198/198；
  修正官方字幕两处小错（Assia Haddou、CNBC）
- 成品：`... [中英字幕].mkv`，421.1 MB，H.264 1080p24 CFR + Opus，
  **硬字幕**（英上中下），烧录 1 分 07 秒
- 字幕文件：`1JkzrR-hznE.zh.bilingual.srt/.ass`、`1JkzrR-hznE.en.ass`
- 定位：半导体上游篇；High-NA EUV 的造价、客户采用节奏、中国/关税与 Hyper-NA

## UC Berkeley EECS：EUV 光刻的历史与路线图（2026-10-27）

官方源：UC Berkeley EECS 频道，`https://www.youtube.com/watch?v=qGy0GK0PMwc`
标题：Tony Yen and Ronald Goossens - EUV: Lithography: History, Latest Results, Technology Roadmap
（原片 83:05，成片 69:59，英）
讲者：Tony Yen（ASML 技术开发中心 VP）、Ronald Goossens（前 ASML 计算光刻高级总监）

- 选品：通过三方验证（Berkeley 官方、Stanford/Purdue/MIT 同讲者讲座、Class Central、
  SEMI 讲者简介等），记录见 `docs/episodes/ep13-berkeley-euv-lithography.md`
- 画质：最高 1080p30，仅 H.264；选用 `270+251-16`，实际约 0.65 Mbps
- 注意：视频带 17 条自动配音音轨，必须显式指定原声 `251-16`
- 原片：`Tony Yen and Ronald Goossens - EUV： Lithography： History, Latest Results, Technology Roadmap [qGy0GK0PMwc].mkv`，
  385.5 MB，H.264 1080p30 + Opus，83:05，**无字幕**
- **裁切**：前 13:06 是静态标题页、无讲话；成片从 13:06 起裁切为 69:59，完整原片保留
- 字幕：**官方人工英文**（1285 事件 → 889 条 cue）；中文 Qwen 翻译 889/889
- 成品：`... [中英字幕].mkv`，492.0 MB，H.264 1080p30 CFR + Opus 160k，
  **硬字幕**（英上中下），烧录 4 分 54 秒
- 裁切烧录：`-ss 786.39` + 字幕前移 786.39s + 音轨重编码；
  libopus 必须用 `-global_quality:v 19`，否则会报 `Quality-based encoding not supported`
- 字幕文件：`qGy0GK0PMwc.zh.bilingual.srt/.ass`（完整时间轴）、
  `qGy0GK0PMwc.zh.bilingual.trimmed.srt/.ass`（成片用）、`qGy0GK0PMwc.en-j3PyPqV-e1s.ass`

## 扎克伯格谈 AI、开源与 Orion（Tiff In Tech，2026-10-27）

官方源：Tiff In Tech 频道，`https://www.youtube.com/watch?v=VuSozCGlMoE`
标题：Mark Zuckerberg On The Future of AI, His Programming Days, and Orion AR（12:07，英）

- 选品：通过三方验证（Tiff In Tech 原始访谈、The Verge、Reuters、Business Insider、
  36Kr、钛媒体、极客公园、智东西等），记录见 `docs/episodes/ep14-zuckerberg-tiff-in-tech.md`
- 画质：最高 4K24；选用 VP9 `313+251-11`（实际约 10.05 Mbps）
- 注意：视频带 11 条自动配音音轨，必须显式指定原声 `251-11`
- 原片：`Mark Zuckerberg On The Future of AI, His Programming Days, and Orion AR [VuSozCGlMoE].mkv`，
  870.8 MB，VP9 4K24 + Opus，12:07，**无字幕**
- 字幕：YouTube 自动英文（131 条句级 cue）；中文 Qwen 翻译 131/131；
  修正 Quest 3S / Ray-Ban / Reels / Meta AI 等识别错误
- 成品：`... [中英字幕].mkv`，743.0 MB，H.264 4K24 CFR + Opus，
  **硬字幕**（英上中下），烧录 3 分 00 秒
- 字幕文件：`VuSozCGlMoE.zh.bilingual.srt/.ass`、`VuSozCGlMoE.en.ass`
- 注意：片头几秒原生英文叠字与低位字幕有重叠，之后无冲突
- 定位：消费 AI / AR 平台篇；开源 Llama、Orion、AR 取代手机

## NVIDIA GTC 2025：通用机器人圆桌（2026-10-27）

官方源：NVIDIA Developer 频道，`https://www.youtube.com/watch?v=BmD22FNOAY4`
标题：A New Era for Generalist Robotics: The Rise of Humanoids | NVIDIA GTC 2025（61:58，英）
嘉宾：Bernt Børnich（1X）、Aaron Saunders（Boston Dynamics）、Deepak Pathak（Skild AI）、
Jim Fan（NVIDIA）、Pras Velagapudi（Agility Robotics）；主持 Tiffany Janzen

- 选品：通过三方验证（NVIDIA 官方、The Robot Report、The Verge、TechCrunch、
  腾讯新闻、今日头条等），记录见 `docs/episodes/ep15-gtc-humanoids-panel.md`
- 画质：最高 1080p30，仅 H.264；选用 DASH `137+251`（实际约 1.35 Mbps）
- 原片：`A New Era for Generalist Robotics： The Rise of Humanoids ｜ NVIDIA GTC 2025 [BmD22FNOAY4].mkv`，
  597.7 MB，H.264 1080p30 + Opus，61:58，**无字幕**
- 字幕：YouTube 自动英文（792 条句级 cue）；中文 Qwen 翻译 792/792；
  8 个批次失败后逐条重试，修正 `already`、`scaling law`、Agility、Atlas、hot 等误译
- 成品：`... [中英字幕].mkv`，1191.8 MB，H.264 1080p30 CFR + Opus，
  **硬字幕**（英上中下），烧录 4 分 42 秒
- 字幕文件：`BmD22FNOAY4.zh.bilingual.srt/.ass`、`BmD22FNOAY4.en.ass`
- 定位：物理 AI / 机器人圆桌；数据金字塔、跨具身、扩展定律与 5–10 年时间表

## 黄仁勋 CES 2025 访谈（Tiff In Tech，2026-10-27）

官方源：Tiff In Tech 频道，`https://www.youtube.com/watch?v=Z_DR1_zhmCU`
标题：NVIDIA CEO Jensen Huang on Robotics, AI, And The Next Big Emerging Technologies（13:26，英）

- 选品：通过三方验证（Tiff In Tech 原始访谈、证券时报、21 世纪经济报道、东方财富、
  新浪科技、CNBC、China Daily、BusinessKorea 等），记录见
  `docs/episodes/ep16-jensen-huang-ces2025-tiff.md`
- 画质：最高 1080p24；选用 VP9 `616+251-5`（实际约 2.10 Mbps）
- 注意：视频带 5 条自动配音音轨，必须显式指定原声 `251-5`
- 原片：`NVIDIA CEO Jensen Huang on Robotics, AI, And The Next Big Emerging Technologies [Z_DR1_zhmCU].mkv`，
  202.3 MB，VP9 1080p24 + Opus，13:26，**无字幕**
- 字幕：YouTube 自动英文（128 条句级 cue）；中文 Qwen 翻译 128/128；
  修正 NVIDIA / Cosmos / Isaac GR00T / Jensen / Omniverse 等识别错误，以及 basic science、
  Chad GPT、I'm asking your questions 等误译
- 成品：`... [中英字幕].mkv`，248.5 MB，H.264 1080p24 CFR + Opus，
  **硬字幕**（英上中下），烧录 53 秒
- 字幕文件：`Z_DR1_zhmCU.zh.bilingual.srt/.ass`、`Z_DR1_zhmCU.en.ass`
- 注意：片头 0:05 原生英文叠字与低位字幕短暂重叠
- 定位：物理 AI / 机器人篇；Cosmos、Omniverse、Isaac GR00T、DRIVE 与 Toyota

## Figure 创始人 Brett Adcock × Sourcery（2026-10-27）

官方源：Sourcery with Molly O'Shea 频道，`https://www.youtube.com/watch?v=g1ESjEGG1SM`
标题：The $10 Trillion Bet on Humanoid Robots | Figure Founder Brett Adcock（2026-04-30，33:00，英）

- 选品：通过三方验证（PANews 全文编译、BigGo 摘要、Podscan / Quicklets / TeaHose 转录，
  Forbes、Interesting Engineering、财联社等独立报道与核查），记录见
  `docs/episodes/ep17-figure-brett-adcock-sourcery.md`
- 画质：最高 4K30；选用 VP9 `313+251-16`（标称 15.9 Mbps，3.71 GiB）
- 原片：`The $10 Trillion Bet on Humanoid Robots ｜ Figure Founder Brett Adcock [g1ESjEGG1SM].mkv`，
  3.71 GiB，VP9 3840×2160 29.97fps + Opus 48kHz 立体声，33:00，**无字幕**
- 字幕：YouTube 自动英文（json3，1112 个事件 → 534 条句级 cue）；中文 Qwen 翻译 534/534，
  1 条因批次合并缺失已补译；修正 `Finger→Figure`、`bot queue→BotQ`、`Harkin Cover→Hark and Cover`、
  `Sorcery→Sourcery`、`figure one/two/three→Figure 01/02/03` 等识别错误
- 剪辑：删除两段赞助口播（原片 684.28–774.32s、1358.24–1464.20s），
  `select`/`aselect` + `setpts` 重映射；成片 1784.06s（29:44），字幕剩 494 条
- 成品：`... [中英字幕].mkv`，3.30 GiB，H.264 3840×2160 29.97fps CFR + Opus 160k，
  **硬字幕**（英上中下），QSV 烧录约 9 分钟
- 字幕文件：`g1ESjEGG1SM.zh.bilingual.trim.srt/.trim.ass`（成片）、
  `g1ESjEGG1SM.zh.bilingual.srt/.ass`（完整版）、`g1ESjEGG1SM.en.ass`
- 注意：画面底部有常驻赞助商 logo 条（MERGE / public / VCX / TURING / deel），属节目包装，
  未遮挡；删除的是口播段落
- 定位：物理 AI 商业化篇，接第 15、16 期；从技术路线与产品叙事落到产能、故障率与资本

## Supermicro CEO 梁见后 Computex 2026（2026-10-27）

- 来源：`https://www.youtube.com/watch?v=FLJHH3ZWEJo`，Supermicro 官方频道
- 标题：CEO Keynote @ Supermicro Innovate | Computex 2026，51:58，2026-06-01 上传
- 原片：`CEO Keynote @ Supermicro Innovate │ Computex 2026 [FLJHH3ZWEJo].mkv`，
  1.06 GiB，VP9 1920×1080 29.97fps + Opus 48kHz 立体声，**无内嵌字幕**
- 字幕：YouTube 自动英文（json3，2517 个事件 → 589 条句级 cue）；中文 Qwen 589/589，
  1 个批次行数不符后逐条重试补全
- **画面自带英文直播硬字幕**：按“不叠加同语种”的规则，成片不再烧英文，只在硬字幕上方
  叠简体中文（`MarginV=260`）；完整双语 SRT / ASS 单独存档
- 成品：`... [中英字幕].mkv`，1.30 GiB（1,398,160,573 字节），H.264 1080p29.97 + Opus 原音轨，
  51:58，硬字幕（原英文 + 上方中文），QSV 烧录约 3.3 分钟
- 字幕文件：`FLJHH3ZWEJo.en.ass`（英文）、`FLJHH3ZWEJo.zh.bilingual.srt/.ass`
  （英上中下存档）、`FLJHH3ZWEJo.zh.ass`（仅中文，成片用）
- 专名修正：`Sugon → Supermicro`、`Meradoobin/MVR 72 → Vera Rubin NVL72`、
  `DCBPS/DC BBS → DCBBS`、`authentic AI → agentic AI`、`HGI → AGI`、`AR workloads → AI workloads`、
  `PLC → DLC`、`1.6 terabit sheet → switch`；译文抽查另修正 `CRO`、两处 `Supermicro`、
  `Graviton` 因果句、`indoor CDU`、`SONiC`
- 定位：系统集成 / 液冷篇，接第 4 期 Intel Computex 与第 9 期 800 VDC AI 工厂

## 西门子 CES 2026 主题演讲：工业 AI 革命（2026-10-28）

- 来源：`https://www.youtube.com/watch?v=R4Wm6YdoZSs`，Siemens 官方频道
- 标题：The Industrial AI Revolution: Siemens Keynote at CES 2026，1:02:01，2026-01-07 上传
- 原片：`The Industrial AI Revolution： Siemens Keynote at CES 2026 [R4Wm6YdoZSs].mkv`，
  1.21 GiB（1,296,101,164 字节），VP9 1920×1080 29.97fps + Opus 48kHz 立体声，**无内嵌字幕、画面无硬字幕**
- 字幕：YouTube 人工英文（json3，1096 条 cue；`--manual --raw` 保留原始断句，
  合并为 694 条，句组翻译后合并为 620 条句级 cue，再按词边界切成 785 条显示 cue）；中文 785/785
- 成品：`... [中英字幕].mkv`，1.35 GiB（1,449,043,840 字节），H.264 1080p29.97 + Opus 原音轨，
  1:02:01，硬字幕（英上中下，`MarginV=100`），QSV 烧录约 4.3 分钟
- 字幕文件：`R4Wm6YdoZSs.en.ass`（英文）、`R4Wm6YdoZSs.zh.bilingual.srt/.ass`
  （英上中下，成片用）
- 专名修正：`Spark → SPARC`、`Arc → ARC`、`Siemens accelerator marketplace → Xcelerator`、
  `simulate the science → simulate the scenario` 等
- 定位：工业数字化 / 工业 AI 篇，接第 9 期 800 VDC 与第 18 期 Supermicro DCBBS

## Figure 首次公开总部与工厂（Sourcery，2026-10-28）

- 来源：`https://www.youtube.com/watch?v=ch_UM_JJU9w`，Sourcery with Molly O'Shea 频道
- 标题：Figure's First Full HQ Tour: From the Lab to the Factory Floor，1:12:20，2026-05-01 上传
- 原片：`Figure's First Full HQ Tour： From the Lab to the Factory Floor [ch_UM_JJU9w].mkv`，
  8.62 GiB（9,250,834,090 字节），VP9 3840×2160 29.97fps + Opus 48kHz 立体声，**无内嵌字幕、画面无硬字幕**
- 字幕：YouTube 自动英文（json3，4745 个事件 → 1377 条 cue）；删除两段赞助口播后重映射为
  1335 条，中文 Qwen 翻译；底部常驻赞助商 logo 条属节目包装，未处理
- 剪辑：删除原片 20:45.200–22:14.960（Brex/Turing）与 52:41.359–54:27.440
  （VCX/Public/Merge/Deel），成片整体前移
- 成品：`... [中英字幕].mkv`，10.84 GiB（11,644,398,901 字节），H.264 2160p29.97 + Opus 160k，
  69:04，硬字幕（英上中下，`MarginV=100`），QSV 烧录约 21.8 分钟
- 字幕文件：`ch_UM_JJU9w.zh.trim.bilingual.srt/.ass`（成片用）、
  `ch_UM_JJU9w.bilingual.srt/.ass`（完整英文版，含广告段）
- 专名修正：`figure 3/three → Figure 03`、`robot Q/quarters → BotQ`、`Sorcery → Sourcery`、
  `Arch Republic → Archer public`、`helix → Helix` 等
- 定位：物理 AI / 具身智能工程与制造篇，接第 17 期 Figure 访谈

## Dylan Patel：2026 年的数据中心（Daytona，2026-10-28）

- 来源：`https://www.youtube.com/watch?v=c88l8daXiv4`，Daytona 官方频道
  （Daytona Compute Conference，旧金山 Chase Center，2026-03-09 现场录制）
- 标题：Dylan Patel (SemiAnalysis): The Datacenter in 2026: CPUs, RL Environments &
  Agent-Driven Workloads，25:04，2026-04-07 上传
- 选品：通过三方验证（Daytona 原始视频、SemiAnalysis 同主题报告、HPCwire、TrendForce、
  WCCFtech、知乎 / 腾讯新闻中文编译、Intel/AMD 财报侧证），记录见
  `docs/episodes/ep21-dylan-patel-datacenter-2026.md`
- 画质：最高 1080p60；选用 VP9 `303+251`（实际约 2.01 Mbps，383.96 MiB）
- 原片：`Dylan Patel (SemiAnalysis)： The Datacenter in 2026： CPUs, RL Environments & Agent-Driven Workloads [c88l8daXiv4].mkv`，
  402,612,121 字节（383.96 MiB），VP9 1920×1080 59.94fps + Opus 48kHz 立体声，
  25:04，**无字幕、画面无硬字幕**
- 字幕：YouTube 自动英文（json3，1531 个事件 → 317 条句级 cue）；中文由本地
  Qwen3-30B-A3B 逐条翻译 317/317，0 缺译；专名修正 `o1`、`GPT-5.4`、`Opus 4.6`、
  `neoclouds`、`hyperscalers`、`vCPUs`、`CoreWeave`、`Trainium 3`、`TPU v7`、
  `AllReduce`、`Ray` 等
- 成片：`... [中英字幕].mkv`，761,804,264 字节（726.5 MiB），H.264 1080p59.94 CFR
  + Opus 原音轨（直接复制），25:04，**硬字幕**（英上中下，`MarginV=100`），
  QSV 烧录 3 分 52 秒
- 校验：时长与原片一致；音轨 MD5 与原片相同；head/tail 解码无报错；抽帧确认底部无裁切
- 字幕文件：`c88l8daXiv4.zh.bilingual.srt/.ass`（双语，成片用，317 条）、
  `c88l8daXiv4.en.ass`（英文）
- 定位：算力基础设施篇，接第 9 期 800 VDC 与第 18 期 DCBBS：电力 → 机架 → CPU

## Waymo：Compute in Motion（Hot Chips 2026，2026-10-28）

- 来源：`https://www.youtube.com/watch?v=3X6NN1csAF4`，Hot Chips 2026 官方频道
  （HC38，斯坦福纪念礼堂，2026-08-24 下午主题演讲）
- 标题：HC2026-K: Compute in Motion: Challenges of Autonomous Driving，1:04:03，2026-09-09 上传
- 讲者：Daniel Rosenband（Waymo 计算负责人），主持 Cliff Young（Google）
- 选品：通过三方验证（Hot Chips 官方视频、Waymo 官方博客、ServeTheHome、SiliconANGLE、
  Design News、AI Business、36Kr / OFweek、MK、Axios、TeslAnt 口径对照），记录见
  `docs/episodes/ep22-waymo-hot-chips-2026.md`
- 画质：最高 1080p60；选用 VP9 `303+251-20`（实际约 0.62 Mbps，344.9 MiB）
- 原片：`HC2026-K： Compute in Motion： Challenges of Autonomous Driving [3X6NN1csAF4].mkv`，
  361,654,866 字节（344.9 MiB），VP9 1920×1080 59.94fps + Opus 48kHz 立体声，
  1:04:03，**无字幕、画面无硬字幕**，但讲者/问答镜头的底部有会议横幅
- 字幕：YouTube 自动英文（json3，3025 个事件 → 810 条句级 cue）；中文由本地
  Qwen3-30B-A3B 翻译；专名修正 `Whimo → Waymo`、`Hot Ships → Hot Chips`、`Ohigh → Ojai`、
  `Ionic 5 → Ioniq 5`、`lightars/LAR → lidar`、`tops → TOPS`、`connets → CNNs`、
  `codeesign/codees → co-design`、`Sabish and Peter → Sabareesh and Pieter` 等
- 成片：`... [中英字幕].mkv`，1,156,316,283 字节（1.08 GiB），H.264 1080p59.94 CFR
  + Opus 原音轨（直接复制），1:04:03，**硬字幕**（英上中下；幻灯片 `MarginV=100`，会议镜头 `MarginV=260`），
  QSV 烧录 9 分 24 秒
- 校验：时长与原片一致；音轨 MD5 与原片相同；head/tail 解码无报错；抽帧确认幻灯片低位、会议镜头高位
- 字幕文件：`3X6NN1csAF4.zh.bilingual.srt/.ass`（双语，成片用）、`3X6NN1csAF4.en.ass`（英文）
- 定位：车规算力 / 物理 AI 篇，接第 21 期（CPU 成为 AI 新瓶颈）：数据中心 → 车内；
  与第 17、20 期 Figure 系列形成“物理 AI 商业化 + 工程实现”的对照

## ICRA 2026 机器人学习四讲（2026-10-28）

- 来源：`https://www.youtube.com/watch?v=a9f2rqxACHQ`，IEEE Robotics and Automation Society 官方频道
  （ICRA 2026，维也纳，2026-06-04 上午“Robot Learning, Planning & Foundation Models”主题报告场）
- 标题：ICRA 2026 Keynote 5 - Robot Learning & Models，1:25:30，2026-10-06 上传
- 讲者：David Hsu（NUS）、Stefanie Tellex（Brown）、Noémie Jaquier（KTH）、
  Paolo Robuffo Giordano（IRISA / Inria）；主持 Karinne Ramirez-Amaro（Chalmers）
- 选品：通过三方验证（ICRA 2026 官方 keynote 日程、IEEE RAS 官方视频、Habr / AIRI 现场报道、
  四位讲者的学校主页与论文），记录见 `docs/episodes/ep23-icra2026-robot-learning.md`
- 画质：最高 1080p24；选用 VP9 `248+251`（实际约 0.78 Mbps，约 477 MiB）
- 原片：`ICRA 2026 Keynote 5 - Robot Learning & Models [a9f2rqxACHQ].mkv`，
  577,930,702 字节（551.2 MiB），VP9 1920×1080 23.976fps + Opus，1:25:30，
  **无字幕、画面无硬字幕**，幻灯片底部有 IEEE RAS 红色页脚
- 字幕：YouTube 自动英文（json3，4437 个事件 → 1015 条句级 cue）；中文由本地
  Qwen3-30B-A3B 按每批 12 条翻译 1015/1015；批量翻译出现若干局部错位，已按原文重排；
  专名修正 `Karin Ramirez Samaro → Karinne Ramirez-Amaro`、`David Hu → David Hsu`、
  `Stephanie Telix → Stefanie Tellex`、`No Jlair → Noémie Jaquier`、
  `Paulo Robufo Jordano → Paolo Robuffo Giordano`、`lrenchian → Lagrangian` 等
- 成片：`... [中英字幕].mkv`，1,190,197,453 字节（1.11 GiB），H.264 1080p23.976 CFR
  + Opus 原音轨（直接复制），1:25:30，**硬字幕**（英上中下，`MarginV=230`，
  避开底部 IEEE RAS 页脚），QSV 烧录 5 分 06 秒
- 校验：时长与原片一致；音轨 MD5 与原片相同；head/tail 解码无报错；抽帧确认字幕在红色页脚上方
- 字幕文件：`a9f2rqxACHQ.zh.bilingual.srt/.ass`（双语，成片用，1015 条）、
  `a9f2rqxACHQ.en.ass`（英文）
- 定位：机器人学习 / 物理 AI 理论篇，接第 17、20 期 Figure 与第 22 期 Waymo：
  从工程实现回到“开放世界决策、语言编程、几何归纳偏置、内在鲁棒性”四个研究问题

## 常用变体

只列格式、不下载：

```powershell
uv run yt-dlp -F "URL"
```

要 1080p H.264 + AAC 的高兼容 MP4（适合投放、剪辑、老设备）：

```powershell
uv run yt-dlp -f "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/b" `
  --merge-output-format mp4 "URL"
```

抓原语种字幕并嵌入容器（中文不抓，按规则由本地模型翻译）：

```powershell
uv run yt-dlp --write-auto-subs --sub-langs "en" --embed-subs "URL"
```

只下载音频：

```powershell
uv run yt-dlp -x --audio-format opus "URL"
```

## 排错记录

| 现象 | 原因 | 处理 |
|---|---|---|
| `Unable to parse "yt-dlp.conf": 'gbk' codec ...` | 配置文件含非 ASCII 字符 | 注释改英文，保持纯 ASCII |
| 格式列表缺少高清项 / `n challenge solving failed` | 没有可用的 JS 运行时或挑战求解脚本 | `--js-runtimes node` + `--remote-components ejs:github` |
| 下载速度忽高忽低（9 MB/s → 300 KB/s） | YouTube 服务端对单请求限速，不是断线 | 已加 `--http-chunk-size 10M`；可结合 `--concurrent-fragments` |
| 控制台标题显示乱码（但文件名正常） | 终端 GBK 输出编码 | 仅影响显示，可 `chcp 65001` 或设 `PYTHONIOENCODING=utf-8` |
| 网络受限时无法访问 YouTube | 代理 | 在配置里加 `--proxy http://127.0.0.1:端口`，或设环境变量 |
| HLS 流合并报 `Invalid argument` | HLS 时间戳异常 | 改用同分辨率 DASH 流（如 137 DASH 替代 270 HLS） |
| `libopus: Quality-based encoding not supported` | `-global_quality` 同时作用于音频 | 改用 `-global_quality:v 19`，音频单独 `-b:a 160k` |

## 说明

- 下载速度受 YouTube 端限速影响，长视频耗时不代表连接断开：可看
  `downloads/*.part` 的大小和修改时间是否在变化。
- 中断后重新执行同一命令会自动续传（`.part` 文件保留）。
- 下载内容仅供个人学习、研究使用，请遵守平台条款与版权规定。
