"""Four-stage, one-heavy-process-at-a-time pipeline.

    stage 1  LLM      highlight planning (auto_clip --analyze-only, optional)
                      + 5W1H intro copy                 <- llama-server only
    stage 2  TTS      CosyVoice narration + 6.0-9.5 s audit  <- CosyVoice only
    stage 3  PICTURE  two deterministic 1920x1080 keyframes <- no model, no GPU
    stage 4  MEDIA    QSV intro render, optional clip render, final assembly

Every service is opened with ``resource_manager.ManagedService``: health-poll
until ready, run the stage, ``taskkill /F /T`` the whole tree, verify the port
is free, then cool down 2 s.  Stage 4 refuses to start while any model process
is alive.  The lock file guarantees one pipeline per machine.

Usage:
    uv run python scripts/run_pipeline.py --video-id c88l8daXiv4 `
        --srt subtitles/c88l8daXiv4.zh.bilingual.srt `
        --title "..." --summary "..." --series "AI 基建 / 第 21 期" `
        --speaker "DYLAN PATEL / SEMIANALYSIS" --source "SemiAnalysis × Daytona" `
        --stamp "FIELD RECORD / 2026" --stamp-right "2026 / DATACENTER · CPU" `
        --index 021 --reuse-analysis

    uv run python scripts/run_pipeline.py --status
    uv run python scripts/run_pipeline.py --cleanup
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import assemble_highlights as ah  # noqa: E402
import generate_intro as gi  # noqa: E402
import resource_manager as rm  # noqa: E402

ROOT = gi.ROOT

STAGES: tuple[tuple[int, str, str], ...] = (
    (1, "LLM", "文本理解与高光规划（LLM 独占）"),
    (2, "TTS", "语音合成与时间审计（TTS 独占）"),
    (3, "PICTURE", "视觉卡片生成（零显存）"),
    (4, "MEDIA", "媒体渲染与成片装配（FFmpeg/QSV 独占）"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


# --------------------------------------------------------------------------
# stage bookkeeping
# --------------------------------------------------------------------------
@dataclass
class StageRecord:
    index: int
    key: str
    title: str
    status: str = "PENDING"          # PENDING / RUNNING / SUCCESS / FAILED / SKIPPED
    service: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    seconds: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Pipeline:
    """Writes clips/<id>/pipeline.json after every transition (crash-safe)."""

    def __init__(self, video_id: str, state_path: Path | None) -> None:
        self.video_id = video_id
        self.state_path = state_path
        self.records = [StageRecord(*stage) for stage in STAGES]
        self.status = "RUNNING"
        self.started_at = now_iso()
        self.finished_at: str | None = None
        self.error: str | None = None
        self.resource_audit: dict[str, Any] | None = None
        self.persist()

    def persist(self) -> None:
        if self.state_path is None:
            return
        payload = {
            "schema_version": 1,
            "video_id": self.video_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "stages": [asdict(record) for record in self.records],
            "resource_audit": self.resource_audit,
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        tmp.replace(self.state_path)

    def stage(self, index: int, service: str,
              fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        record = self.records[index - 1]
        record.status = "RUNNING"
        record.service = service
        record.started_at = now_iso()
        self.persist()
        rm.log(f"stage {index}/4 {record.key} 已启动 — {record.title}")
        started = time.monotonic()
        try:
            detail = fn()
        except BaseException as exc:
            record.status = "FAILED"
            record.error = f"{type(exc).__name__}: {exc}"
            record.seconds = round(time.monotonic() - started, 2)
            record.finished_at = now_iso()
            self.status = "FAILED"
            self.error = record.error
            self.finished_at = now_iso()
            self.persist()
            rm.log(f"stage {index}/4 {record.key} 失败 — {record.error}")
            raise
        record.detail = detail if isinstance(detail, dict) else {}
        record.status = "SUCCESS"
        record.seconds = round(time.monotonic() - started, 2)
        record.finished_at = now_iso()
        self.persist()
        rm.log(f"stage {index}/4 {record.key} 已完成 ({record.seconds:.1f}s)")
        return record.detail

    def finish(self, audit: dict[str, Any] | None = None) -> None:
        self.resource_audit = audit
        if self.status == "RUNNING":
            self.status = "SUCCESS"
        self.finished_at = now_iso()
        self.persist()


# --------------------------------------------------------------------------
# the four stages
# --------------------------------------------------------------------------
def run_intro_stages(args: argparse.Namespace, cfg: dict[str, Any], intro_dir: Path,
                     *, pipeline: Pipeline | None = None,
                     analysis_hook: Callable[[], dict[str, Any]] | None = None,
                     media_hook: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
                     max_voice_repairs: int = 2) -> dict[str, Any]:
    """Run stages 1-3 and the intro part of stage 4.  Raises on failure."""
    pipeline = pipeline or Pipeline(args.video_id, None)
    chrome = gi.chrome_block(args, cfg)
    state: dict[str, Any] = {"copy": None, "copy_info": None, "voice": None,
                             "timeline": None, "picture": None, "intro": None}

    def stage_llm() -> dict[str, Any]:
        detail: dict[str, Any] = {}
        # llama-server is the only heavy process alive in this block.
        with rm.llama_server():
            if analysis_hook is not None:
                detail["analysis"] = analysis_hook()
            result = gi.stage_copy(
                out_dir=intro_dir, cfg=cfg, title=args.title, summary=args.summary,
                copy_json=args.copy_json, copy_source=args.copy_source,
                spoken_text=args.spoken_text, screen_title=args.screen_title,
                screen_subtitle=args.screen_subtitle)
            state["copy"] = result["copy"]
            state["copy_info"] = result["info"]
            detail["copy"] = result["copy"]
            detail["model"] = result["info"].get("model")
        return detail

    def stage_tts() -> dict[str, Any]:
        repairs: list[dict[str, Any]] = []
        while True:
            try:
                # CosyVoice is the only heavy process alive in this block.
                with rm.cosyvoice(preset_voice=bool(cfg.get("voice_speaker"))):
                    result = gi.stage_voice(out_dir=intro_dir, cfg=cfg,
                                            text=state["copy"]["intro_spoken_text"],
                                            voice_wav=args.voice_wav)
                break
            except gi.VoiceWindowError as exc:
                if len(repairs) >= max_voice_repairs:
                    raise
                repair = {"attempt": len(repairs) + 1, "voice_ms": exc.voice_ms,
                          "raw_seconds": exc.raw_seconds, "tempo": exc.tempo,
                          "error": str(exc)}
                repairs.append(repair)
                rm.log(f"voice does not fit ({exc}); reopening the LLM window for a "
                       f"shorter line (repair {len(repairs)}/{max_voice_repairs})")
                # TTS is already dead here; the LLM window comes after it.
                with rm.llama_server():
                    rewritten = gi.stage_rewrite(out_dir=intro_dir, cfg=cfg,
                                                 copy=state["copy"])
                state["copy"] = rewritten["copy"]
                state["copy_info"] = gi.save_copy(intro_dir, state["copy_info"],
                                                  rewritten["copy"])
        state["voice"] = result["voice"]
        state["timeline"] = result["timeline"]
        return {"narration": result["voice"], "timeline": result["timeline"],
                "repairs": repairs}

    def stage_picture() -> dict[str, Any]:
        with rm.quiet_stage("stage 3 picture"):
            frames = gi.stage_picture(out_dir=intro_dir, cfg=cfg, copy=state["copy"],
                                      chrome=chrome, renderer=args.renderer,
                                      browser_arg=args.browser)
        state["picture"] = frames
        return frames["payload"]

    def stage_media() -> dict[str, Any]:
        detail: dict[str, Any] = {}
        with rm.quiet_stage("stage 4 media"):
            record = gi.stage_render(
                video_id=args.video_id, out_dir=intro_dir, cfg=cfg,
                copy=state["copy"], copy_info=state["copy_info"], chrome=chrome,
                frames_info=state["picture"], voice_info=state["voice"],
                timeline=state["timeline"])
            state["intro"] = record
            detail["intro"] = {"status": record["status"],
                               "path": record["path"],
                               "duration_ms": record["duration_ms"]}
            if media_hook is not None:
                detail["media"] = media_hook(state)
        return detail

    intro_dir.mkdir(parents=True, exist_ok=True)
    pipeline.stage(1, "llama-server", stage_llm)
    pipeline.stage(2, "cosyvoice", stage_tts)
    pipeline.stage(3, "none", stage_picture)
    pipeline.stage(4, "ffmpeg/qsv", stage_media)
    return state


# --------------------------------------------------------------------------
# full pipeline: analysis -> intro -> assembly
# --------------------------------------------------------------------------
def _analysis_hook(args: argparse.Namespace, cfg: dict[str, Any],
                   clips_dir: Path) -> Callable[[], dict[str, Any]]:
    def run() -> dict[str, Any]:
        analysis_path = clips_dir / "analysis.json"
        if not args.reanalyze and analysis_path.exists():
            rm.log(f"reuse {rel(analysis_path)} (no extra LLM pass)")
            return {"status": "REUSED", "path": rel(analysis_path)}
        if not args.srt:
            raise gi.StageError("analysis.json is missing and --srt was not provided")
        srt = resolve(args.srt)
        cmd = [sys.executable, str(ROOT / "scripts" / "auto_clip.py"),
               "--srt", str(srt), "--video-id", args.video_id,
               "--analyze-only", "--base", str(cfg["llm_base"])]
        if args.video:
            cmd += ["--video", str(resolve(args.video))]
        rm.log("highlight planning: auto_clip --analyze-only (LLM window exclusive)")
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=3600)
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "").strip()[-600:]
            raise gi.StageError(f"auto_clip analysis failed (exit "
                                f"{proc.returncode}): {tail}")
        return {"status": "ANALYZED", "path": rel(analysis_path)}
    return run


def _media_hook(args: argparse.Namespace, clips_dir: Path) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def run(_state: dict[str, Any]) -> dict[str, Any]:
        detail: dict[str, Any] = {}
        if args.render_clips:
            if not args.srt:
                raise gi.StageError("--render-clips needs --srt")
            cmd = [sys.executable, str(ROOT / "scripts" / "auto_clip.py"),
                   "--srt", str(resolve(args.srt)), "--video-id", args.video_id,
                   "--reuse-analysis"]
            if args.video:
                cmd += ["--video", str(resolve(args.video))]
            rm.log("clip render: auto_clip --reuse-analysis (QSV, same window as assembly)")
            proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=14400)
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()[-800:]
                raise gi.StageError(f"clip render failed (exit {proc.returncode}): {tail}")
            detail["clips"] = "RENDERED"
        if args.skip_assembly:
            detail["assembly"] = "SKIPPED"
            return detail
        result_path = clips_dir / "result.json"
        if not result_path.exists():
            raise gi.StageError(f"{rel(result_path)} missing; cannot assemble")
        asm_argv = ["--video-id", args.video_id]
        if args.video:
            asm_argv += ["--source", str(resolve(args.video))]
        if args.browser:
            asm_argv += ["--browser", args.browser]
        asm_argv += ["--renderer", args.renderer]
        rm.log("final assembly: intro -> highlight 1 -> title card -> highlight 2")
        rc = ah.run(ah.parse_args(asm_argv))
        if rc != 0:
            raise gi.StageError(f"assemble_highlights returned {rc}")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assembly = result.get("assembly") or {}
        detail["assembly"] = {"status": assembly.get("status"),
                              "output": assembly.get("output"),
                              "duration_ms": assembly.get("actual_duration_ms")}
        return detail
    return run


def intro_only(args: argparse.Namespace, cfg: dict[str, Any], intro_dir: Path) -> int:
    """Entry point for ``generate_intro.py --stage all`` (serial, managed)."""
    with rm.PipelineLock():
        pipeline = Pipeline(args.video_id, intro_dir / "pipeline.json")
        try:
            run_intro_stages(args, cfg, intro_dir, pipeline=pipeline)
            pipeline.finish(_final_audit(pipeline))
        except Exception as exc:
            rm.log(f"intro pipeline failed: {exc}")
            pipeline.finish(_final_audit(pipeline))
            return 1
    return 0


def _final_audit(pipeline: Pipeline | None = None) -> dict[str, Any]:
    """No model may survive the pipeline; kill stragglers and report."""
    leftovers = rm.find_heavy()
    if leftovers:
        rm.log(f"final audit: killing leftover model process(es): {rm.describe(leftovers)}")
        rm.cleanup_all()
    # The lock is still held at audit time; recording its pid would look like
    # a leftover, so the audit reports only processes/ports.
    audit = rm.status(include_lock=False)
    if pipeline is not None:
        pipeline.resource_audit = audit
    rm.log("final audit: " + (f"heavy={len(audit['heavy'])} "
                              f"ffmpeg={len(audit['ffmpeg'])} "
                              f"ports={audit['ports']}"))
    return audit


def run_pipeline(args: argparse.Namespace, cfg: dict[str, Any]) -> int:
    video_id = args.video_id
    clips_dir = resolve(args.clips_dir) if args.clips_dir else ROOT / "clips" / video_id
    intro_dir = resolve(args.out) if args.out else clips_dir / "intro"
    clips_dir.mkdir(parents=True, exist_ok=True)

    with rm.PipelineLock():
        pipeline = Pipeline(video_id, clips_dir / "pipeline.json")
        try:
            run_intro_stages(
                args, cfg, intro_dir, pipeline=pipeline,
                analysis_hook=_analysis_hook(args, cfg, clips_dir),
                media_hook=_media_hook(args, clips_dir),
                max_voice_repairs=args.max_voice_repairs)
        except Exception as exc:
            rm.log(f"pipeline failed: {exc}")
            audit = _final_audit(pipeline)
            pipeline.finish(audit)
            return 1
        audit = _final_audit(pipeline)
        pipeline.finish(audit)

    stages = {record.key: record.status for record in pipeline.records}
    rm.log("pipeline SUCCESS: " + ", ".join(f"{k}={v}" for k, v in stages.items()))
    final = (pipeline.records[-1].detail.get("media") or {}).get("assembly") or {}
    if final.get("output"):
        rm.log(f"final reel: {final['output']}")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Four-stage serial pipeline: LLM -> TTS -> picture -> QSV")
    gi.add_intro_arguments(ap)
    ap.add_argument("--srt", default=None, help="bilingual SRT for highlight planning")
    ap.add_argument("--video", default=None, help="source video (default: result.json)")
    ap.add_argument("--clips-dir", default=None, help="default clips/<video-id>")
    ap.add_argument("--reanalyze", action="store_true",
                    help="rerun the highlight planning even if analysis.json exists")
    ap.add_argument("--render-clips", action="store_true",
                    help="stage 4: also render the highlight clips with QSV")
    ap.add_argument("--skip-assembly", action="store_true",
                    help="stage 4: build the intro only, skip the final reel")
    ap.add_argument("--max-voice-repairs", type=int, default=2,
                    help="LLM rewrite cycles allowed when TTS overflows the window")
    ap.add_argument("--cleanup", action="store_true",
                    help="kill every llama-server / CosyVoice / ffmpeg tree and exit")
    ap.add_argument("--status", action="store_true",
                    help="print heavyweight processes, ports and VRAM, then exit")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not args.video_id and not (args.cleanup or args.status):
        print("config error: --video-id is required", file=sys.stderr)
        return 2

    if args.cleanup:
        report = rm.cleanup_all()
        print(json.dumps({"killed": report, "status": rm.status()},
                         ensure_ascii=False, indent=2))
        return 0
    if args.status:
        print(json.dumps(rm.status(), ensure_ascii=False, indent=2))
        return 0

    cfg = gi.build_cfg(args)
    if not (cfg["min_duration_ms"] < cfg["max_duration_ms"]):
        print("config error: max-duration-ms must exceed min-duration-ms", file=sys.stderr)
        return 2
    try:
        return run_pipeline(args, cfg)
    except rm.ResourceBusyError as exc:
        rm.log(f"resource conflict: {exc}")
        return 3
    except Exception as exc:
        rm.log(f"pipeline error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
