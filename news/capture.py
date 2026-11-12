"""Browser capture and typographic cards (headless Chrome/Edge, no Playwright)."""
from __future__ import annotations

import html
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

def _install_roots() -> tuple[str, ...]:
    """Program-files roots from the environment (no hardcoded drive letters)."""
    keys = ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")
    roots = [os.environ.get(k, "").strip() for k in keys]
    return tuple(r for r in roots if r)


BROWSERS = [
    str(Path(root) / rel)
    for root in _install_roots()
    for rel in (r"Google\Chrome\Application\chrome.exe",
                r"Microsoft\Edge\Application\msedge.exe")
]

CARD_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8">
<style>
  html,body {{ margin:0; width:{width}px; height:{height}px; background:#0b0e13; }}
  body {{ font-family: Arial, "Microsoft YaHei", sans-serif; color:#f5f5f5; }}
  .rail {{ position:absolute; left:0; top:0; width:10px; height:100%; background:#ff5500; }}
  .wrap {{ position:absolute; left:96px; right:96px; top:96px; bottom:280px;
           display:flex; flex-direction:column; justify-content:space-between; }}
  .eyebrow {{ font-family: Consolas, monospace; letter-spacing:.18em; font-size:20px;
              color:#ff5500; text-transform:uppercase; }}
  .title {{ font-size:64px; line-height:1.12; font-weight:700; letter-spacing:-.01em; }}
  .sub {{ font-size:28px; line-height:1.4; color:#b9c2cc; }}
  .sources {{ font-family: Consolas, monospace; font-size:20px; color:#87919c;
              line-height:1.5; border-top:1px solid #2a313a; padding-top:20px; }}
  .quote {{ font-size:54px; line-height:1.22; font-weight:600; }}
  .attribution {{ font-size:26px; color:#ff5500; letter-spacing:.08em; }}
  .index {{ position:absolute; right:96px; bottom:260px; font-family:Consolas,monospace;
            font-size:18px; color:#5e6873; letter-spacing:.16em; }}
</style></head>
<body><div class="rail"></div><div class="wrap">
  {body}
</div><div class="index">{index}</div></body></html>
"""


def find_browser(explicit: str | None = None) -> Path | None:
    for candidate in [explicit, os.environ.get("NEWS_BROWSER"), *BROWSERS]:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    for name in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    return None


def _run_browser(url: str, out: Path, width: int, height: int, wait_ms: int,
                 browser: Path | None, timeout_s: float = 45.0) -> dict[str, Any]:
    exe = find_browser(str(browser) if browser else None)
    if exe is None:
        raise RuntimeError("no Chrome/Edge found; set NEWS_BROWSER")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="news-chrome-") as profile:
        cmd = [
            str(exe), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={width},{height}",
            f"--user-data-dir={profile}", f"--virtual-time-budget={max(1000, wait_ms)}",
            "--no-first-run", "--no-default-browser-check", "--disable-extensions",
            "--disable-background-networking", "--disable-sync",
            "--disable-features=Translate,MediaRouter,OptimizationHints",
            f"--screenshot={out.resolve().as_posix()}", url,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True)
        try:
            _, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
            raise RuntimeError(f"browser timed out after {timeout_s:.0f}s: {url}")
    if not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError(f"browser produced no screenshot: {out}\n{(stderr or '')[-800:]}")
    return {"browser": str(exe), "bytes": out.stat().st_size, "url": url}


def screenshot_url(url: str, out: str | Path, *, width: int = 1920, height: int = 1080,
                   wait_ms: int = 6000, browser: str | None = None,
                   timeout_s: float = 45.0) -> dict[str, Any]:
    """Capture the viewport of a public page.

    This is deliberately a viewport capture: it does not bypass paywalls,
    logins or robots rules.  Full-page/element capture can be added with
    Playwright later, but is not required for the first episodes.
    """
    return _run_browser(url, Path(out), width, height, wait_ms,
                        Path(browser) if browser else None, timeout_s=timeout_s)


def render_html_to_png(html_text: str, out: str | Path, *, width: int = 1920,
                       height: int = 1080, work_dir: str | Path | None = None,
                       browser: str | None = None) -> dict[str, Any]:
    out_path = Path(out)
    work_root = Path(work_dir) if work_dir else None
    if work_root is not None:
        work_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="news-card-", dir=work_root) as tmp:
        page = Path(tmp) / "card.html"
        page.write_text(html_text, encoding="utf-8")
        return _run_browser(page.resolve().as_uri(), out_path, width, height, 1500,
                            Path(browser) if browser else None)


def source_card_html(*, title: str, subtitle: str, sources: list[str], index: str = "",
                     width: int = 1920, height: int = 1080) -> str:
    src = "<br>".join(html.escape(s) for s in sources if s)
    body = (
        '<div class="eyebrow">Evidence desk · source card</div>'
        f'<div class="title">{html.escape(title)}</div>'
        f'<div class="sub">{html.escape(subtitle)}</div>'
        f'<div class="sources">{src or "SOURCES: see description"}</div>'
    )
    return CARD_TEMPLATE.format(width=width, height=height, body=body,
                                index=html.escape(index))


def quote_card_html(*, text: str, attribution: str, index: str = "",
                    width: int = 1920, height: int = 1080) -> str:
    body = (
        '<div class="eyebrow">Quoted material · verify in context</div>'
        f'<div><div class="quote">{html.escape(text)}</div>'
        f'<div class="attribution" style="margin-top:36px">{html.escape(attribution)}</div></div>'
        '<div class="sources">Source card · see description for links</div>'
    )
    return CARD_TEMPLATE.format(width=width, height=height, body=body,
                                index=html.escape(index))


def render_segment_card(segment: dict[str, Any], out: str | Path, *,
                        width: int = 1920, height: int = 1080,
                        index: str = "", work_dir: str | Path | None = None,
                        browser: str | None = None) -> dict[str, Any]:
    if segment.get("type") == "quote":
        html_text = quote_card_html(
            text=segment.get("text_en") or "",
            attribution=segment.get("attribution") or "",
            index=index, width=width, height=height,
        )
    else:
        html_text = source_card_html(
            title=segment.get("title") or "",
            subtitle=segment.get("subtitle") or "",
            sources=segment.get("sources") or [],
            index=index, width=width, height=height,
        )
    return render_html_to_png(html_text, out, width=width, height=height,
                              work_dir=work_dir, browser=browser)


def capture_coverage(pack, out_dir: str | Path, *, limit: int = 3,
                     width: int = 1920, height: int = 1080, wait_ms: int = 6000,
                     browser: str | None = None) -> list[dict[str, Any]]:
    """Capture one viewport screenshot per coverage item."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for idx, item in enumerate(pack.coverage[:limit], start=1):
        target = out / f"shot-{idx:02d}.png"
        try:
            info = screenshot_url(item.url, target, width=width, height=height,
                                  wait_ms=wait_ms, browser=browser)
        except Exception as exc:  # keep going; the editor can retry one URL
            results.append({"publisher": item.publisher, "headline": item.headline,
                            "out": str(target), "error": str(exc)})
            continue
        results.append({**info, "publisher": item.publisher,
                        "headline": item.headline, "out": str(target)})
    return results
