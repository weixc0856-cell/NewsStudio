# 配音方案：CosyVoice 微服务 + 动态鸭音混音

> 状态：2026-10-28 已落地并验收（阶段 1–3）。主项目 `uv` 环境未安装任何 CosyVoice 依赖。

## 1. 架构（微服务解耦）

```text
YouTube-B（uv / Python 3.12）                独立 AI 服务层
┌─────────────────────────────┐              ┌──────────────────────────────┐
│ 下载 / 字幕 / auto_clip      │   HTTP       │ CosyVoice-Runtime             │
│ synthesize_dub.py  ─────────┼─────────────>│ 127.0.0.1:50000  (CPU 推理)   │
│ dub_mix.py（FFmpeg 滤镜）    │  <─ WAV ──── │ CosyVoice2-0.5B + wetext      │
└─────────────────────────────┘              └──────────────────────────────┘
                                              D:\AI\CosyVoice-Runtime（独立 venv）
```

- 主项目**不 import cosyvoice**，只通过 HTTP 调用。
- 服务端使用独立 Python 3.10 venv（`D:\AI\CosyVoice-Runtime\venv`），与 YouTube-B 的 `.venv` 互不可见。
- 语义分析与配音稿仍由 8080 端口的 `llama-server`（Qwen3-30B-A3B）负责。

## 2. 服务端

| 项 | 值 |
|---|---|
| 目录 | `D:\AI\CosyVoice-Runtime` |
| 启动 | `start_cosyvoice.bat`（或直接 `venv\Scripts\python.exe api_server.py`） |
| 监听 | `http://127.0.0.1:50000` |
| 模型 | zero-shot：`CosyVoice2-0.5B`；SFT 预置音色：`CosyVoice-300M-SFT`（均 CPU，fp32，12 线程） |
| 参考音频 | `assets\my_voice_5s.wav` + 同名 `.txt` 逐字稿（2026-10-28 已换成用户本人录音：3.35s / 24 kHz / 单声道） |
| 文本归一化 | wetext（本地 FST，见 §7） |

接口：

```text
GET  /health    -> 模型状态 / sample_rate / text_frontend / speakers / 统计
GET  /speakers  -> 预置音色列表（SFT 模型才有）
POST /tts       -> JSON {"text", "prompt_wav"?, "prompt_text"?, "speaker"?, "speed"?} -> audio/wav
POST /tts/upload -> multipart：text + prompt_wav 文件（也接受 speaker 字段）
```

响应为 16-bit PCM 单声道 WAV（CosyVoice2 为 24 kHz，300M-SFT 为 22.05 kHz），
响应头带 `X-Audio-Seconds`、`X-Synth-Seconds`。

### 2.1 两种音色模式

| 模式 | 启动脚本 | 模型 | 音色来源 |
|---|---|---|---|
| zero-shot 克隆 | `start_cosyvoice.bat` | `CosyVoice2-0.5B` | 参考音频 + 同名 `.txt` 逐字稿 |
| **SFT 预置音色** | `start_cosyvoice_sft.bat` | `CosyVoice-300M-SFT` | `spk2info.pt` 内置：中文女 / **中文男** / 日语男 / 粤语女 / 英文女 / 英文男 / 韩语女 |

- 两种模式共用 50000 端口，**同一时刻只能起一个**；Resource Manager 通过
  `rm.cosyvoice(preset_voice=True)` 自动选择 SFT 模型。
- 请求里带 `speaker` 就走 `inference_sft`，优先于 `prompt_wav`；未知音色返回 400
  并列出可用列表。
- **片头默认音色 = 中文女**（`generate_intro.DEFAULTS["voice_speaker"]`，2026-10-29 切换）；
  配音切片（`synthesize_dub.py`）默认仍走 zero-shot 克隆，两者互不影响。
- 模型只取 CPU 推理必需文件（llm/flow/hift/campplus/speech_tokenizer_v1/spk2info，约 2.2 GB），
  跳过 jit/trt 的 zip 与 fp32 onnx（完整包 5.36 GB）。
- SFT 模型慢一档：第 21 期 9.9 s 语音耗时 49.6 s（RTF 5.0，CosyVoice2 约 3.5）。

## 3. 配音稿契约

禁止把长文本直接丢给 TTS。每句一条，时间由 Python 计算，模型只出文字：

```json
[
  {"sentence_id": 1, "target_start_sec": 0.0, "max_duration_sec": 7.44,
   "text": "很多人以为算力瓶颈在显卡，但真正卡死云厂商的其实是 CPU。"}
]
```

**预算经验值**：CosyVoice2-0.5B CPU 实测语速约 **3.7–4.4 字/秒**，
同一句重新合成的时长波动可达 ±8%。因此 `最大时长 ≈ 字数 / 4.3 + 0.7s`，
不要按 6 字/秒估预算（4.5s 装不下 29 字，实测 7.5–8.1s）。

## 4. 三段流水线

```powershell
# 0) 生成配音稿（Qwen，只出文字；时间由脚本算）
uv run python scripts/make_dub_script.py `
  --result clips/<id>/result.json --clip 1 `
  --out dub/<id>/clip-01.script.json

# 1) 合成：逐句 HTTP -> WAV，ffprobe 校验，超预算 atempo 1.05~1.12x
uv run python scripts/synthesize_dub.py `
  --script dub/<id>/clip-01.script.json --out-dir dub/<id>/clip-01

# 2) 混音（独立测试/重混）：sidechain Ducking + 可选同程烧字幕
uv run python scripts/dub_mix.py `
  --video clips/<id>/final/<clip>.mp4 --dub dub/<id>/clip-01/track.wav `
  --out dub/<id>/clip-01.dubbed.mp4 --verify --dub-window 0.5:3 --dub-window 3.6:3

# 3) 生产接入：auto_clip 在同一遍 QSV 渲染里完成字幕烧录 + 鸭音
uv run python scripts/auto_clip.py --srt ... --video ... --reuse-analysis `
  --dub-dir dub/<id>/clip-01-tracks     # 目录内放 clip-01.wav、clip-02.wav
```

> 片头导读（`scripts/generate_intro.py`）复用同一 `/tts` 接口与固定参考音色；
> 文案由本地 Qwen（8080）按 5W1H 生成 3 句口播 + 画面标题/副标题，画面是
> `assets/templates/intro.html` 的 state 0/1 两个确定性状态；口播超 9.5s 时
> Qwen 会压缩重写并重新合成。见 `docs/片头语与工程化导读规范.md`。

`synthesize_dub.py` 产出：

| 文件 | 内容 |
|---|---|
| `sentence-NN.raw.wav` | 原始合成 |
| `sentence-NN.wav` | 通过/变速后的最终分段 |
| `track.wav` | 按 `target_start_sec` 对齐的整条导读轨 |
| `manifest.json` | 每句 raw/final 时长、tempo、状态（OK / FIT / OVER） |

任一 OVER（1.12x 后仍超预算）时退出码为 1；确认可用 `--allow-over` 才继续。

## 5. 混音参数

- `sidechaincompress`：导读为 sidechain，英文原声为主输入。
- 阈值按导读实测电平自动标定（`--duck-target-db`，默认 −19.5），
  目标衰减约 16 dB（原声约剩 15%）。
- `attack=15 ms / release=400 ms`，导读结束 0.4s 内平滑恢复。
- 导读响度自动归一化：`--dub-target-db -20`（按整条导读实测均值补增益，0.25×–4× 夹取），
  `alimiter=0.95` 防削波；换不同录音设备不需要手调。
- 原声全部保留，不做静音、不做整段压低。

## 6. 验收记录（2026-10-28）

| 阶段 | 结果 |
|---|---|
| 1 服务化 | `status=ready`，device=cpu，text_frontend=wetext，模型加载 10.0s |
| 1 合成 | 中英混合句 → 6.72s WAV（24 kHz 单声道），RTF 3.46；CAM++ 音色余弦 **0.837** |
| 2 时长校验 | 句 1 raw 7.48s → tempo 1.05 → 7.12s（预算 7.44）FIT；句 2 raw 7.32s ≤ 8.0s OK |
| 2 音色 | 分段输出与参考音频余弦 **0.812**（官方示例音色） |
| 用户音色 | 本人 3.35s 录音 → 克隆余弦 **0.865**，分段 **0.846**；ASR 复核与输入文本一致 |
| 用户音色·时长 | 同两句话无需变速：6.24s / 7.24s（预算 7.44 / 8.00） |
| 用户音色·混音 | 导读归一化后 −20.9 dB，鸭音 15.5–21.0 dB，结束后偏差 0.0 dB |
| 3 鸭音 | 导读窗内原声衰减 **14.6–21.6 dB**（约剩 8–19%），导读结束后偏差 **0.0 dB** |
| 3 电平 | 片头导读 −23.7 dB vs 原声 −34.3 dB（+10.6 dB 主导）；60s 处 −29.5 vs −30.0 |
| 3 时长 | 成片 372.416s vs 原片 372.393s（+23 ms，与无配音渲染一致） |
| 3 集成 | `auto_clip --dub-dir` 单遍完成烧字幕 + 鸭音：366.170s（目标 366.135s，+35 ms），验收通过；`result.json` = SUCCESS，clip-02 无导读时自动走原链路 |
| 3 集成电平 | 片头 −23.7 dB、导读结束 16.5s 处 −33.0 dB、60s 处 −32.1 dB（与原片一致） |
| SFT 片头（2026-10-29） | 中文男：raw 9.892s → tempo 1.15× → 8.605s，窗口 9071ms，增益 ×2.95 归一到 −20 dB，峰值约 −2.1 dB |
| 女声片头（2026-10-29） | 中文女：新文案 raw 8.557s → 加 0.6s 前导 → 9.157s；语音起点 0.58s，首词 −19.4 dB；计划窗口 9407ms |

回归测试：`test_auto_clip.py`（12）、`test_merge_highlights.py`（6）、`test_dub_mix.py`（8）。

## 7. 运行时的本地补丁与坑

1. **wetext 需要登录 token**：`snapshot_download("pengzhendong/wetext")` 报
   `Authentication token does not exist`。改为从 ModelScope 文件接口下 4 个 FST 到
   `assets\wetext\`，并给 `cosyvoice/cli/frontend.py` 打补丁支持 `COSY_WETEXT_DIR`。
   重新下载用 `fetch_wetext_fst.py`（带退避重试，接口会限流）。
2. **pyworld 无 Windows wheel**：仅在训练侧使用，`dataset/processor.py` 已改为可选导入。
3. **openai-whisper 构建需要旧 setuptools**：`setuptools<81` + `--no-build-isolation`。
4. **缺失依赖**：`gdown`、`pyarrow`、`python-multipart` 已补进 `requirements-runtime.txt`。
5. **CPU 性能**：RTF ≈ 3.4–3.9（12 线程），一句 7 秒导读约 25 秒合成；
   导读稿应控制在 2–4 句、总时长 12–18 秒。
6. **时长波动**：同一句重复合成 ±8%，预算要给余量；确定性校验不能省。

## 8. 明确不做

- 不整段配音，只做片头短导读。
- 不用外部混音库，只用 FFmpeg 原生滤镜。
- 不在主项目 `uv` 环境安装 CosyVoice 依赖。
- 不跳过 ffprobe 时长校验直接混音。
