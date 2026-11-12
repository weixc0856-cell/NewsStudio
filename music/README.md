# music/

与本仓库期数流水线无关的独立素材。

| 文件 | 规格 | 说明 |
|---|---|---|
| `We Never - 若如初見 (Instrumental) [zBGTEvt5Fbg].mkv` | H.264 1920×1080 60fps + Opus，152.18 s，52.0 MiB | 视频成品 |
| `We Never - 若如初見 (Instrumental).opus` | Opus 48k 立体声 148k，2.7 MiB | 音频无损抽取（音频包 MD5 与 MKV 内音轨一致） |
| `We Never - 若如初見 (Instrumental).m4a` | AAC 48k 立体声 256k，4.9 MiB | 兼容版（车载/手机/老播放器） |
| `We Never - 若如初見 (Instrumental).wav` | PCM 48k 16-bit 立体声，27.9 MiB | 剪辑/DAW 用的无压缩容器（内容仍来自 148k Opus，不增加音质） |

- 来源：<https://www.youtube.com/watch?v=zBGTEvt5Fbg>（TimTaka Music，2026-10-04 上传；2026-11-06 下载）
- 选 `312+251`：1080p60 最高码率视频（HLS 变体，约 2.8 Mbps）+ Opus 150k 音频。
- 该 HLS 变体有 30 个包缺 PTS，直接封装 MKV/MP4 都会失败或产生非单调 DTS：
  最终用 **视频 QSV 重编码（`-global_quality:v 18`）+ 音频原样复制**，head/tail 解码无报错。
- 音频抽取：`.opus` 从源 Opus 流直接复制（MD5 `6d2e5689e1ddd540eac8332aab1dfe32`，与 MKV 音轨一致）；
  标签 `title` / `artist=ZHENLOE` / `composer=Xiao Yang`。`.m4a` 为 AAC 转码版。
- 纯音乐（Instrumental），无对白、无字幕轨：不生成字幕、不做翻译与烧录。
