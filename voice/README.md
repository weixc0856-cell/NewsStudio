# voice/

两段从源视频截出的干净人声（48 kHz / 16-bit WAV），与期数流水线无关。

| 文件 | 说明 |
|---|---|
| `INsXb8IRcNs_voice_594.60s_29.96s.wav` | 原始截取，立体声，前后 20 ms 淡入淡出 |
| `INsXb8IRcNs_voice_594.60s_29.96s_clean.wav` | 高通 + 降噪 + 限幅（−1 dB），立体声 |
| `INsXb8IRcNs_voice_594.60s_29.96s_dub.wav` | 配音母版（含背景音乐）：单声道，−16 LUFS，真峰值 −1 dBTP |
| `INsXb8IRcNs_voice_594.60s_29.96s_dub_nomusic.wav` | **配音母版·已去背景音乐**：Demucs 分离人声后同规格输出 |
| `npKK3E6wLzI_voice_35.63s_30.16s.wav` | 原始截取，立体声 |
| `npKK3E6wLzI_voice_35.63s_30.16s_clean.wav` | 同上 clean 处理 |
| `npKK3E6wLzI_voice_35.63s_30.16s_dub.wav` | 配音母版（含背景音乐）：单声道，−16 LUFS，真峰值 −1 dBTP |
| `npKK3E6wLzI_voice_35.63s_30.16s_dub_nomusic.wav` | **配音母版·已去背景音乐**：同上 |

- 源：唐诗欣赏·绝句 上 孙道临（`INsXb8IRcNs`，截 594.60 s 起 29.96 s）、
  张若虚《春江花月夜》雅坤朗诵（`npKK3E6wLzI`，截 35.63 s 起 30.16 s）。
- 切点都在停顿/音节间隙：第一段起于 1.47 s 静音之后、收在短停顿；第二段收在 1.14 s 停顿前。
- 母版处理链：`highpass=70` → `afftdn nr=10`（FFT 降噪）→ 单声道下混（0.5/0.5）
  → `loudnorm` 两遍测量 + 迭代微调至 −16.0 LUFS → 限幅真峰值 −1 dBTP。
  实测：第一段 −16.2 LUFS / −1.0 dBTP / LRA 11.2 LU；第二段 −16.2 LUFS / −1.0 dBTP / LRA 6.3 LU。
- 源音轨 `*.webm`（YouTube Opus 133–140 kbps）留作复查。

## 去背景音乐（2026-11-07）

两段素材的背景里都有持续的音乐（第一段约 162 Hz 基频及谐波，第二段约 246 Hz）。

- 工具：Demucs 4.1.0 `htdemucs`，`--two-stems=vocals`，CPU 推理（约 9 s/段）
- 结果：人声轨在停顿处的电平 —— 第一段 −125.7 dBFS、第二段 −74.4 dBFS（原素材对应位置分别是
  −48 dBFS 与 −52 dBFS 的音乐），即背景音乐基本清零；第二段仍残留约 −74 dBFS 的 246 Hz 单音，
  比语音低约 55 dB，正常听感下不可闻
- 母版处理链：Demucs 人声轨 → 重采样 48 kHz → 70 Hz 高通 → 单声道下混 →
  loudnorm 两遍 + 迭代至 −16.0 LUFS → 真峰值 −1 dBTP
