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
├── docs/                      # 策划文档与期数档案（docs/episodes/stage1|stage2/）
├── episodes_registry.json     # 极简查重索引（只读这个，不遍历历史档案）
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

### 自动高光切片与片头合集（2026-10-28 起，2026-10-29 改为可选）

> **默认关闭**：从 2026-10-29 起，每期默认**不做**高光切片与片头合集，只交付
> 无字幕原片 + 中英字幕成片 + 双语 SRT。只有用户明确要求时才运行下面的切片 / 片头 / 合集流程。
> 规则同步写在仓库根目录 `CLAUDE.md`。

从已完成的**双语 SRT** 与原片中自动切出 45–90 秒（优先 50–70 秒）的独立论点片段，再拼成
「独立片头 → 高光 1 → 短转场 → … → 高光 N」的 16:9 横屏合集（目标约 5 分钟）。完整规格见
[`docs/自动剪辑-高光切片方案.md`](docs/自动剪辑-高光切片方案.md)；
片头视觉与 5W1H 文案规范见
[`docs/片头语与工程化导读规范.md`](docs/片头语与工程化导读规范.md)；
配音链路见 [`docs/配音方案-CosyVoice.md`](docs/配音方案-CosyVoice.md)。

```powershell
# 1) 只分析：滑动窗口 + 本地模型提候选 + 确定性过滤，输出 analysis.json
uv run python scripts/auto_clip.py --srt "subtitles/<id>.zh.bilingual.srt" --analyze-only

# 2) 完整流程：分析 + 字幕钳位 + QSV 渲染 + ffprobe 验收
uv run python scripts/auto_clip.py --srt "subtitles/<id>.zh.bilingual.srt" `
  --video "downloads/<视频> [<id>].mkv"

# 3) 只重渲染：复用已有 analysis.json，不再调用模型
uv run python scripts/auto_clip.py --srt ... --video ... --reuse-analysis

# 4) 修正第 1 条切片起点（吸附到包含该时刻的 cue 起点；--fix-start 是简写）
uv run python scripts/auto_clip.py --srt ... --video ... --reuse-analysis `
  --fix-start 04:49.375
# 或显式指定序号：--override-start "1=00:04:49.375"

# 5) 旧版硬切合集（不含片头；保留用于对比与回归）
uv run python scripts/merge_highlights.py --result clips/<id>/result.json

# 6) 独立片头：本地 Qwen 5W1H 文案 + 麦肯锡橙白双栏海报 + CosyVoice（10–20 秒，目标 12–18）
uv run python scripts/generate_intro.py --video-id <id> `
  --title "CPU 成为新瓶颈：2026 年的数据中心（Dylan Patel / SemiAnalysis）" `
  --summary "AI 推理把 CPU 推成瓶颈……" `
  --series "AI 基建 / 第 21 期" --speaker "DYLAN PATEL / SEMIANALYSIS" `
  --source "SemiAnalysis × Daytona" --stamp "FIELD RECORD / 2026" `
  --stamp-right "2026 / DATACENTER · CPU" --index 021

# 6a) 只预览/复用文案（不调用 TTS、不渲染）
uv run python scripts/generate_intro.py --video-id <id> `
  --title ... --summary ... --copy-only
uv run python scripts/generate_intro.py --video-id <id> `
  --copy-json clips/<id>/intro/copy.json `
  --series "AI 基建 / 第 21 期" --speaker "DYLAN PATEL / SEMIANALYSIS" `
  --source "SemiAnalysis × Daytona" --stamp "FIELD RECORD / 2026" `
  --stamp-right "2026 / DATACENTER · CPU" --index 021

# 7) 最终合集：片头 → 切片 1 → 0.3 s 黑场（dip-to-black）→ 切片 2
uv run python scripts/assemble_highlights.py --video-id <id>
```

### 四阶段串行流水线（2026-10-28 起，推荐入口）

流水线自己按阶段启停 llama-server 与 CosyVoice，任何时刻只有一个重量级进程；
模型用完立刻 `taskkill /F /T` 杀进程树，验证端口释放后冷却 2 秒再进入下一阶段。
规格与异常处理见 [`docs/资源调度-串行生命周期.md`](docs/资源调度-串行生命周期.md)。

```powershell
# 四阶段：LLM 高光规划+5W1H 文案 → TTS → 视觉卡片 → QSV 渲染+合集
uv run python scripts/run_pipeline.py --video-id <id> `
  --srt "subtitles/<id>.zh.bilingual.srt" `
  --title "..." --summary "..." --series "AI 基建 / 第 21 期" `
  --speaker "DYLAN PATEL / SEMIANALYSIS" --source "SemiAnalysis × Daytona" `
  --stamp "FIELD RECORD / 2026" --stamp-right "2026 / DATACENTER · CPU" `
  --index 021 --reuse-analysis

# 资源侧运维
uv run python scripts/run_pipeline.py --status     # 模型进程 / 端口 / 显存
uv run python scripts/run_pipeline.py --cleanup    # 杀掉所有模型 / ffmpeg 进程树
```

- `--reanalyze` 强制重跑阶段 1 的高光候选提取；`--render-clips` 在阶段 4
  先渲染切片；`--skip-assembly` 只出片头；`--max-voice-repairs` 控制超窗重写次数。
- 阶段 2 默认逐句合成 + 句间 400 ms 停顿，超窗只告警；只有显式开启
  `enforce_duration_window` 时才走 `atempo ≤ 1.15` / Qwen 压缩重写（同一套“一次一个进程”规则）。
- 阶段 4 开编前会再断言没有模型进程存活；`assemble_highlights.py` 也有同样的门禁。
- 阶段记录写在 `clips/<id>/pipeline.json`（状态、耗时、服务、错误、资源审计）。
- **合集拼接**：片头、黑场、切片先归一化（60 fps CFR / 1920×1080 / yuv420p /
  AAC 48k / 统一 video timescale），再用 concat demuxer `-c copy` 流拷贝拼接；
  只有无法流拷贝时才重编码（`--mode filter` 保留旧路径）。
  第 21 期实测：14.7 s、峰值 ffmpeg RSS 236 MB、系统内存 31%，对比旧 filter 路径
  437 s / 47 GB RSS / 100% 内存。

产物全部在 `clips/<id>/`：

| 路径 | 内容 |
|---|---|
| `analysis.json` | 每个窗口的 cue 范围、模型尝试、原始候选、淘汰/去重原因 |
| `result.json` | 终态、切片、逐项验收、`manual_overrides`、`merge` / `intro` / `assembly` |
| `intro/` | 独立片头：`intro.html`、`intro.png`、`keyframe-0.png`、`copy.{json,prompt.txt,response.json}`、`copy_rewrite.*`、`narration.*.wav`、`intro.mp4`、`intro.json` |
| `final/` | **仅**通过自动验收的 MP4（`<id>.highlight-NN.*.mp4`、`<id>.highlights-merged.mp4`；`highlights-merged.mp4` 为旧版无片头合集） |
| `quarantine/` | 未通过验收的 MP4 + `.failed.json` |
| `work/` | 钳位后的 `clip-NN.srt/.ass`、`assembly.srt/.ass`、转场卡、FFmpeg 日志、窗口 Prompt |

- 模型只提候选（两个 cue ID + 标题 + 摘要）；时长门禁、归属、重叠去重、配额、字幕钳位、
  ffprobe 验收全部由 Python 确定性执行，任一淘汰都写入 JSON。
- 窗口默认 5 分钟、重叠 1 分钟；切片 45–90 秒，优先 50–70 秒；重叠率 > 0.4 判重；
  合集预算 330 秒（片头 + 切片 + 转场），候选不足不强行出片。
- 渲染 `-ss <起点> -i <原片> -t <时长>`，`h264_qsv` 视频 + AAC 音频；`-map_chapters -1`
  避免 MP4 生成多余的章节文本轨。
- 合集不直接拼接已烧录字幕的成片（会叠字），而是从源片按同一区间重新取流并只烧一次。
- **文案本地生成（5W1H）**：本地 Qwen（`llama-server` 8080）低温度写 5–6 句口语导读
  （60–95 字，5W1H 讲清楚），并给出 12–18 字大标题与出处副标题；
  禁用营销词。`--copy-json` 复用已验收文案，`--copy-only` 只预览，
  `--copy-source args` 改用手写文案。整条链路不调用任何云端模型或视频生成模型。
- **画面（麦肯锡橙白双栏海报）**：`assets/templates/intro.html` 固定版式
  （纯白底、6px #ff5500 顶条、左栏中英标题、右栏 KEY ENGINEERING INSIGHTS 卡片、
  底部四列信源矩阵），Python 只替换占位符；静态单帧、60 fps CFR、无动效滤镜。
  无 Playwright / Remotion / 新依赖。
- **配音与时长**：CosyVoice 预置「中文女」，按句合成并在句间插入 400 ms 数字静音，
  前导 600 ms；不做 atempo 压缩。片头 10–20 秒为提示区间（advisory），超出只告警。
  第 21 期当前片头 17.10 s（60 fps，音视频差 21 ms），可单独播放与验收。
- **片头床音**：片头期间混入与片头等长（约 17 s）的原片音频（15%），最后 0.4 秒淡出；
  切片 1 以 100% 原声接上，避免片头成为纯静音卡。
- **转场**：无字 dip-to-black。前段最后 0.15 s 淡出到纯黑，300 ms 纯黑静音，后段前 0.15 s
  从黑场淡入；音频在交界处做 200 ms 淡出/淡入。视频仍以流拷贝拼接，只有交界小片重编码。
- **字幕时间轴**：片头之后才出现第一条字幕；第二段从「片头 + 切片 1 + 转场」重新计时，
  全程相对时间，禁止沿用原视频绝对时间戳。
- 第 21 期合集非连续：中间跳过 4m43s（282431 ms），`result.json` 的
  `assembly.skipped_human` / `note` 已标注。
- 验证样本、实测时长/同步数据与合集跳过标注见
  [`docs/自动剪辑-高光切片方案.md`](docs/自动剪辑-高光切片方案.md) 第 13 节。
- 回归测试：`test_auto_clip.py`（12）+ `test_merge_highlights.py`（6）+
  `test_dub_mix.py`（8）+ `test_generate_intro.py`（26）+
  `test_assemble_highlights.py`（14）+ `test_resource_manager.py`（12）+
  `test_run_pipeline.py`（8）+ `test_concat_assembly.py`（7），共 **93 项**；
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

## 期数档案

README 只保留项目通用用法；每一期的选题、三方验证、内容结构、简介模板与制作结果在
`docs/episodes/`，按阶段存放：

- `docs/episodes/stage1/`：第 1–30 期完整档案（已封存），索引见
  [`stage1/STAGE1_EPISODES.md`](docs/episodes/stage1/STAGE1_EPISODES.md)，
  复盘见 [`stage1/STAGE1_SUMMARY.md`](docs/episodes/stage1/STAGE1_SUMMARY.md)
- `docs/episodes/stage2/`：第 31 期起的新档案
- **查重与校验只读根目录 [`episodes_registry.json`](episodes_registry.json)**：
  每条记录含 id / title / core_entity / event / url / tags，**不要全文读取历史期数档案**
- README 迁出的下载/编码/校验细节：`docs/episodes/制作记录-按期归档.md`
- 专栏整体策划：`docs/专栏策划-AI时代的基建.md`

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
