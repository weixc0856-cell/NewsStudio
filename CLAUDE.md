# 本项目长期规则（每期默认）

> 2026-10-29 固化。与 `README.md`、`docs/sync-contract.md` 冲突时，以本文件为准。

## 1. 每期默认交付：不做高光剪辑

- 每期默认**只交付三样**：无字幕原片、中英字幕成片（`[中英字幕].mkv`）、双语 SRT/ASS。
- **默认不运行** `auto_clip.py`、`generate_intro.py`、`assemble_highlights.py`、
  `merge_highlights.py`、`run_pipeline.py` 的高光/片头/合集阶段。
- 只有用户在当期明确要求“做高光/切片/合集/片头”时才做；否则不要主动补做。

## 2. 字幕规则

- 原片始终无字幕；字幕是独立后期步骤，成品另存 `[中英字幕].mkv`，不改原片。
- 只抓原语种字幕（人工优先，其次自动）；**不下载 YouTube 中文自动翻译**。
- 中文一律用本地 Qwen3-30B-A3B（`127.0.0.1:8080`，`LLM_API_KEY`）生成。
- 版式：原语种在上、简体中文在下；画面已有硬字幕时只叠原语种/中文单语并抬高
  （`MarginV` 按画面元素调整，底部有滚动条/台标时抬到其上方）。
- 人工字幕：先 `build_subs.py --manual` 按句合并，再用 `translate_groups.py` 按句组翻译；
  自动字幕：`build_subs.py` + `translate_local.py`（批量 12）。
- 烧录后必须验收：时长、音轨 MD5、head/tail 解码、抽帧看字幕位置。

## 3. 广告

- 成片中切除片中赞助口播，并用同一组切点重映射字幕；无广告则保持原时间轴。

## 4. 文档

- 每期在 `docs/episodes/epNN-*.md` 建档（三方验证、章节、简介模板、制作结果），
  并更新 `docs/episodes/制作记录-按期归档.md`、`docs/专栏策划-AI时代的基建.md`、
  README 的期数。
- 提交前跑 `uv run python -m unittest discover -s scripts -p "test_*.py"`。
