"""ComfyUI / FLUX client for editorial illustrations.

Generated images are illustrations, never evidence.  Factual visuals must come
from screenshots, official documents, public data or your own charts.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

import requests

DEFAULT_BASE_URL = "http://127.0.0.1:8188"
# ComfyUI 工作流 JSON：路径只写在本机 .env（NEWS_FLUX_WORKFLOW），仓库里留空
DEFAULT_WORKFLOW = Path(os.environ.get("NEWS_FLUX_WORKFLOW") or "workflows/flux3_t2i_api.json")
PLACEHOLDERS = ("positive_prompt", "width", "height", "seed", "steps", "cfg", "filename_prefix")


def server_ok(base_url: str = DEFAULT_BASE_URL, timeout: float = 3.0) -> bool:
    try:
        response = requests.get(f"{base_url.rstrip('/')}/system_stats", timeout=timeout)
        return response.status_code == 200
    except requests.RequestException:
        return False


def compile_workflow(workflow: dict[str, Any], *, prompt: str, width: int, height: int,
                     seed: int, steps: int, cfg: float, filename_prefix: str) -> dict[str, Any]:
    values = {
        "positive_prompt": prompt,
        "width": width,
        "height": height,
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "filename_prefix": filename_prefix,
    }

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            return {key: walk(value) for key, value in node.items()}
        if isinstance(node, list):
            return [walk(value) for value in node]
        if isinstance(node, str) and node.startswith("{{") and node.endswith("}}"):
            name = node[2:-2].strip()
            if name in values:
                return values[name]
        return node

    return walk(deepcopy(workflow))


def submit(workflow: dict[str, Any], base_url: str = DEFAULT_BASE_URL) -> str:
    client_id = uuid.uuid4().hex
    response = requests.post(f"{base_url.rstrip('/')}/prompt",
                             json={"prompt": workflow, "client_id": client_id}, timeout=30)
    response.raise_for_status()
    data = response.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI rejected the workflow: {data}")
    return prompt_id


def wait_for_image(prompt_id: str, base_url: str = DEFAULT_BASE_URL,
                   timeout_s: float = 300) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = requests.get(f"{base_url.rstrip('/')}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        history = response.json().get(prompt_id)
        if history:
            for node in history.get("outputs", {}).values():
                for image in node.get("images", []) or []:
                    return image
            status = history.get("status", {})
            raise RuntimeError(f"ComfyUI finished without an image: {status}")
        time.sleep(2)
    raise TimeoutError(f"ComfyUI did not finish within {timeout_s}s (prompt {prompt_id})")


def download_image(image: dict[str, Any], out: str | Path,
                   base_url: str = DEFAULT_BASE_URL) -> Path:
    params = {
        "filename": image.get("filename"),
        "subfolder": image.get("subfolder", ""),
        "type": image.get("type", "output"),
    }
    response = requests.get(f"{base_url.rstrip('/')}/view", params=params, timeout=120)
    response.raise_for_status()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(response.content)
    return path


def generate(*, prompt: str, out: str | Path, width: int = 1024, height: int = 576,
             seed: int | None = None, steps: int = 16, cfg: float = 1.0,
             workflow_path: str | Path | None = None, base_url: str = DEFAULT_BASE_URL,
             timeout_s: float = 300, dry_run: bool = False) -> dict[str, Any]:
    seed = int(seed if seed is not None else time.time_ns() % (2**31))
    wf_path = Path(workflow_path or os.environ.get("NEWS_FLUX_WORKFLOW") or DEFAULT_WORKFLOW)
    if not wf_path.is_file():
        raise FileNotFoundError(f"FLUX workflow not found: {wf_path}")
    workflow = json.loads(wf_path.read_text(encoding="utf-8"))
    compiled = compile_workflow(
        workflow,
        prompt=prompt,
        width=width,
        height=height,
        seed=seed,
        steps=steps,
        cfg=cfg,
        filename_prefix="news_illustration",
    )
    out_path = Path(out)
    meta = {
        "prompt": prompt, "width": width, "height": height, "seed": seed,
        "steps": steps, "cfg": cfg, "workflow": str(wf_path), "base_url": base_url,
        "kind": "illustration",
        "note": "Generated illustration. Not evidence; label it on screen.",
    }
    if dry_run:
        meta["dry_run"] = True
        out_path.with_suffix(out_path.suffix + ".workflow.json").write_text(
            json.dumps(compiled, ensure_ascii=False, indent=2), encoding="utf-8")
        return meta
    if not server_ok(base_url):
        raise RuntimeError(f"ComfyUI is not reachable at {base_url}; start it on 8188 first")
    prompt_id = submit(compiled, base_url=base_url)
    image = wait_for_image(prompt_id, base_url=base_url, timeout_s=timeout_s)
    download_image(image, out_path, base_url=base_url)
    meta["prompt_id"] = prompt_id
    meta["image"] = image
    out_path.with_suffix(out_path.suffix + ".json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
