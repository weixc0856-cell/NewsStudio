# 协作契约：更新指令、提交规范与按期交付

> 状态：2026-10-29 落地，第 21 期（c88l8daXiv4）验收后固化
> 适用：本仓库所有人机协作（Claude Code / 其他 AI / 人工协作者）
> 关联：`docs/资源调度-串行生命周期.md`、`docs/片头语与工程化导读规范.md`、
> `docs/自动剪辑-高光切片方案.md`、`docs/配音方案-CosyVoice.md`

---

## 1. 这份契约解决什么问题

过去几轮返工的共同原因不是能力不足，而是**指令边界含糊**：一句“再优化一下切片”，
既没说改哪个模块，也没说什么不能动，结果改动溢出到已验收的片头、海报或成片路径。

本契约把每次同步收敛成三件事：

1. **四段式更新指令**——让 AI 知道目标、输入、禁区、交付标准；
2. **Git 提交规范**——一次提交只做一件事，历史可回溯；
3. **按期交付模板**——每期跑完填一次，人和 AI 看同一张表。

---

## 2. 四段式更新指令模板

以后每次让 AI 改东西，统一用下面四段，缺一段就容易跑偏。

```text
【更新目标】
对 [模块 / 第 XX 期] 进行 [具体动作]。

【输入资产】
基于：
- 视频：downloads/xxx.mkv
- 字幕：subtitles/xxx.zh.bilingual.srt
- （如有）已有 analysis.json / copy.json

【变更约束】（必须严格遵守）
1. 架构约束：单任务串行生命周期（Resource Manager）、静态海报（60fps CFR）、
   转场 B（0.1s 卡片淡化 + 200ms 音频淡化）。
2. 边界约束：dependent_start 独立句门禁、时长 180s~420s、标题去重、不引入新依赖。
3. 范围约束：只改 [明确列出的文件/模块]，其余生产配置与已验收文件保持不变。

【期望交付】
1. 关键 diff 摘要
2. 离线验证结果（如有）
3. 最终验收指标（音视频时长差、解码报错、进程/显存清理审计）
4. 明确写出「未改动」的部分
```

### 2.1 各段的填写要点

| 段 | 必须写清楚 | 反例 |
|---|---|---|
| 更新目标 | 动作 + 对象 + 是否接入生产（离线预览 vs 正式渲染） | “优化一下片头” |
| 输入资产 | 精确到 `downloads/`、`subtitles/`、`clips/<id>/` 下的文件 | “用上次那个视频” |
| 变更约束 | 架构 / 边界 / 范围三层，范围段要点名文件或目录 | “别乱改” |
| 期望交付 | 四项都要，尤其第 3 项验收指标和第 4 项“未改动清单” | “跑通就行” |

### 2.2 约束段的固定措辞（建议原样引用）

- **架构约束**：`单任务串行生命周期（Resource Manager）、麦肯锡橙白双栏海报（静态单帧 60fps CFR）、转场 B（0.1s 卡片淡化 + 200ms 音频淡化）`
- **边界约束**：`dependent_start 独立句门禁、时长 180–420 s（硬上限 600 s，配置见 result.json.config）、标题去重、不引入新依赖`
- **范围约束**：`只改 <文件列表>，其余生产配置与已验收文件保持不变`
- **字幕约束**：`原片保留无字幕母版；交付版只烧原文字幕 + 本地 Qwen 翻译中文（原文在上、中文在下）`
- **广告约束**：`最终字幕版中切除赞助口播，并重新对齐切片/合集字幕时间轴`

### 2.3 示例：第 22 期（下一期直接套用）

```text
【更新目标】
生成第 22 期高光切片与合集。

【输入资产】
- 视频：downloads/xxxx.mkv
- 字幕：subtitles/xxxx.zh.bilingual.srt

【变更约束】
1. 严格复用现有架构：Resource Manager 串行、静态海报、转场 B、TTS 年份归一化、
   dependent_start + 标题去重。
2. 不修改 auto_clip 核心选择逻辑以外的代码，不引入新依赖。
3. 生产路径只写 clips/xxxx/，不触碰第 21 期任何文件。

【期望交付】
完整跑通后给出：片头时长与验收、两条切片起止与标题、
合集总时长与 A/V 差、资源清理记录。
```

### 2.4 示例：第 21 期本轮重切（已执行，可作参照）

```text
【更新目标】
对第 21 期（c88l8daXiv4）重切两条高光起点与标题，并重出合集。

【输入资产】
- 视频：downloads/c88l8daXiv4.mkv
- 字幕：subtitles/c88l8daXiv4.zh.bilingual.srt
- 已有：clips/c88l8daXiv4/analysis.json、intro/ 已验收片头

【变更约束】
1. 架构约束：串行生命周期、静态海报 60fps CFR、转场 B。
2. 边界约束：dependent_start 门禁、时长区间、标题去重、不引入新依赖。
3. 范围约束：只改 scripts/auto_clip.py、scripts/assemble_highlights.py 与对应测试；
   片头复用，不重做 TTS，不动第 21 期以外的任何期次。

【期望交付】
diff 摘要、离线验证、成片时长差与资源审计、未改动清单。
```

结果：clip1 起点 → cue 56，clip2 起点 → cue 204，clip2 标题改为「GPU闲置成本高于CPU」，
合集 654.908 s，142 项测试通过。

---

## 3. 快速口令（高频场景一句话）

| 场景 | 说法 |
|---|---|
| 只改模板不跑片 | 「只更新 `assets/templates/intro.html`，用第 21 期数据离线渲染预览，不接入生产。」 |
| 只重渲某一期 | 「按当前 HEAD 规则重跑第 XX 期，片头复用已验收版本，只重渲切片+合集。」 |
| 回滚某次改动 | 「回退到 commit `xxxxx`，生产媒体文件保持不动。」 |
| 同步新规则给后续期 | 「后续所有期次默认启用：dependent_start 门禁 + 标题去重 + 静态海报 + 转场 B。」 |
| 只查不改 | 「只做审计：列出当前成片规格、时长差、残留进程，不做任何写入。」 |

---

## 4. Git 提交规范

### 4.1 前缀

沿用现有单动词前缀，固定五类：

| 前缀 | 使用场景 | 示例 |
|---|---|---|
| `pipeline:` | 流水线整体行为、片头、拼接、资源管理 | `pipeline: switch intro to dual-column poster` |
| `auto_clip:` | 高光选择、边界、标题、重试逻辑 | `auto_clip: add dependent_start gate and title dedup` |
| `assets:` | 模板、样式、静态资源 | `assets: refine poster safe-area and insight card` |
| `epXX:` | 某一期正式交付物 | `ep21: release verified dual highlights and 10m54s reel` |
| `test:` | 纯测试相关 | `test: adapt assertions to current ep21 artifacts` |
| `docs:` | 仅文档（补充类） | `docs: add sync contract` |

### 4.2 粒度与格式

- 一条 commit 只做一件事；跨模块的改动拆开提交。
- 第一行 ≤ 72 字符，动词开头，不加句号。
- 正文用 `*` 列要点，写清“改了什么”和“验收结果”，不写“优化了一下”。
- **媒体文件不入库**：`*.mp4`、`*.mkv`、`*.wav` 等大体积产物由 `.gitignore` 拦截；
  提交前用 `git diff --cached --numstat` 确认没有二进制。

示例（第 21 期重切）：

```text
auto_clip: add dependent_start gate, title deduplication, and recut ep21 highlights to clean independent boundaries

* DEPENDENT_START: treat relative-clause / continuation markers (...) as filler-level penalty
* title deduplication: pass existing titles into prompt + ensure_unique_titles fallback
* ep21 recut: clip1 start → cue 56, clip2 start → cue 204
* clip2 title changed to "GPU闲置成本高于CPU" (no longer collides with clip1)
* adaptive tests for current artifacts; 142 tests green
```

---

## 5. 按期交付模板

每期跑通后复制填空，放进 `docs/episodes/epXX-*.md` 的「制作结果」或直接发群。

```markdown
### 【同步】第 XX 期高光切片与合集交付

**版本状态**
测试全部通过（XXX/XXX），资源审计 0 残留（llama / CosyVoice / FFmpeg 已释放）。

**交付物一览**
| 类型 | 路径 | 关键指标 |
|------|------|----------|
| 片头 | `clips/[ID]/intro/intro.mp4` | X.XX s，60fps，静态海报，读音已归一化 |
| 切片 01 | `clips/[ID]/final/[ID].highlight-01.[标题].mp4` | XX s，起点为独立主谓句 |
| 切片 02 | `clips/[ID]/final/[ID].highlight-02.[标题].mp4` | XX s，标题已去重 |
| 最终合集 | `clips/[ID]/final/[ID].highlights-merged.mp4` | XX s，转场 B，A/V 差 ≤ 30ms |

**关键边界确认**
- 起点均无 `dependent_start` 语法依赖
- 标题唯一，文件名无冲突
- 右下角安全区已避开平台时长遮挡
- 资源清理：端口空、无残留进程、pipeline lock 已释放
```

### 5.1 第 21 期填写结果（参照样例）

| 类型 | 路径 | 关键指标 |
|---|---|---|
| 片头 | `clips/c88l8daXiv4/intro/intro.mp4` | 8.95 s（配音 8.51 s），60 fps，静态海报 |
| 切片 01 | `clips/c88l8daXiv4/final/c88l8daXiv4.highlight-01.CPU成AI新瓶颈.mp4` | 344.399 s，起点 cue 56 |
| 切片 02 | `clips/c88l8daXiv4/final/c88l8daXiv4.highlight-02.GPU闲置成本高于CPU.mp4` | 300.955 s，起点 cue 204，标题已去重 |
| 最终合集 | `clips/c88l8daXiv4/final/c88l8daXiv4.highlights-merged.mp4` | 654.908 s，h264 1080p60 + aac，A/V 差 21 ms |

残差：`654.908 − 654.769 = 0.139 s`（容差 1.5 s）。

---

## 6. 验收指标口径

所有期次按同一口径验收，避免“差不多就行了”。

| 指标 | 口径 | 阈值 |
|---|---|---|
| 切片时长 | `end_ms − start_ms` | 45–90 s（优先 50–70 s）；硬上限 90 s |
| 单集切片数 | 选中切片数 | 3–5 条 |
| 合集总长 | 片头 + 切片 + 转场 | 约 5 分钟（4–6 分钟） |
| 合集时长差 | `actual_duration_ms − expected_duration_ms` | ≤ 1500 ms |
| A/V 差 | 容器内音轨与视频轨时长差 | ≤ 30 ms |
| 解码 | `ffmpeg -v error -i <file> -f null -` 无输出 | 0 条报错 |
| 规格 | 1920×1080、60 fps CFR、h264 + aac | 与模板一致 |
| 片头 | 静态海报单帧，10–20 s（目标 12–16 s，**提示项**） | 音视频差 ≤ 60 ms；超窗只告警 |
| 资源 | llama / CosyVoice / FFmpeg 进程、8080/50000 端口、pipeline lock | 全部为 0 |
| 测试 | `python -m unittest discover -s scripts -p "test_*.py"` | 全绿（当前 154 通过 / 1 skipped） |
| 字幕 | 原文在上、中文在下；无字幕母版保留 | 人工抽检 3 处 |

> 交付报告里必须写「未改动」的部分。没有这一条，就等于没有范围约束。

---

## 7. 与现有文档的分工

| 文档 | 管什么 |
|---|---|
| 本文件 | 怎么下指令、怎么提交、怎么交付 |
| `资源调度-串行生命周期.md` | 什么时候只能有一个重量级进程 |
| `片头语与工程化导读规范.md` | 片头文案、视觉、模板占位符 |
| `自动剪辑-高光切片方案.md` | 选段算法、门禁、重试、装配 |
| `配音方案-CosyVoice.md` | TTS、音色、时长修复 |
| `docs/episodes/` | 每期的选题与制作结果归档 |
