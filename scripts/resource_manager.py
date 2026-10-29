"""Single-task serial resource lifecycle for the 8 GB Intel Arc A750 box.

Hard rules (docs/资源调度-串行生命周期.md):

1. **One heavyweight process at a time.**  llama-server (Qwen3-30B-A3B),
   CosyVoice and FFmpeg/QSV never overlap.  ``assert_quiet()`` refuses to start
   a stage while another of them is alive.
2. **Health polling, never a blind sleep.**  ``/health`` is polled every second
   and the task starts the moment the model reports ready (llama.cpp returns
   status ok; CosyVoice returns ready / loading).
3. **Kill the whole tree.**  ``taskkill /F /T /PID``, then verify both the pid
   and the listening port are gone; then cool down 2 s so the Intel driver can
   release VRAM.  A plain ``terminate()`` is never used.
4. **Cleanup in ``finally``.**  ``ManagedService.__exit__`` always runs, so an
   exception, a Ctrl-C or a failed health check still leaves no zombie holding
   the GPU.
5. **One pipeline per machine.**  ``PipelineLock`` is an exclusive lock file.

Public API::

    with resource_manager.PipelineLock():
        with resource_manager.llama_server() as llm:
            ...  # 8080 is ready, nothing else heavy is running
        # llama-server tree is dead, port free, 2 s cooldown done
        with resource_manager.cosyvoice() as tts:
            ...
        with resource_manager.quiet_stage("qsv encode"):
            ...  # asserts no model process survived

``ResourceBusyError`` means another heavy process is alive; ``ServiceError``
means the service failed to become ready.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import psutil
import requests

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / ".runtime"
LOCK_PATH = RUNTIME_DIR / "pipeline.lock"
LOG_DIR = RUNTIME_DIR / "logs"

COOLDOWN_S = 2.0
TASKKILL = "taskkill.exe"
DEFAULT_HOST = "127.0.0.1"

FFMPEG_MARKERS = ("ffmpeg", "ffmpeg.exe")

LLAMA_BIN = Path(os.environ.get("LLAMA_SERVER_BIN", r"D:\AI\bin-sycl\llama-server.exe"))
LLAMA_MODEL = Path(os.environ.get(
    "LLAMA_MODEL_PATH", r"D:\AI\models\Qwen3-30B-A3B-Instruct-2507-Q4_K_M.gguf"))
LLAMA_PORT = int(os.environ.get("LLAMA_PORT", "8080"))
LLAMA_ALIAS = "Qwen3-30B-A3B-Instruct-2507-Q4_K_M"

COSY_DIR = Path(os.environ.get("COSYVOICE_DIR", r"D:\AI\CosyVoice-Runtime"))
COSY_PORT = int(os.environ.get("COSY_PORT", "50000"))
# SFT preset-voice runtime (CosyVoice-300M-SFT). Same port, same API, different model.
COSY_SFT_CLASS = os.environ.get("COSY_SFT_MODEL_CLASS", "CosyVoice")
COSY_SFT_DIRNAME = os.environ.get("COSY_SFT_MODEL_DIRNAME", "CosyVoice-300M-SFT")


# --------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------
def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [resource] {message}", flush=True)


# --------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------
class ResourceError(RuntimeError):
    """Base class for lifecycle failures."""


class ResourceBusyError(ResourceError):
    """A heavyweight process that must not overlap is still alive."""


class ServiceError(ResourceError):
    """The managed service never became healthy."""


# --------------------------------------------------------------------------
# process discovery
# --------------------------------------------------------------------------
@dataclass
class ProcInfo:
    pid: int
    name: str
    cmdline: str
    cwd: str = ""
    kind: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"pid": self.pid, "name": self.name, "kind": self.kind,
                "cmdline": self.cmdline[:300], "cwd": self.cwd}


def _process_cwd(proc: psutil.Process) -> str:
    try:
        return proc.cwd()
    except (psutil.Error, OSError):
        return ""


SHELLS = {"bash.exe", "sh.exe", "cmd.exe", "powershell.exe", "pwsh.exe",
          "conhost.exe", "nohup.exe", "wsl.exe", "git.exe", "node.exe"}
INTERPRETERS = {"python.exe", "pythonw.exe", "python", "python3.exe", "py.exe"}


def classify(name: str, cmdline: str, cwd: str = "") -> str | None:
    """Return the heavy kind for a process, or None.

    Only the process itself counts: a shell whose command *text* mentions
    ``llama-server`` must never be mistaken for the model server.
    """
    lower_name = name.lower()
    if lower_name in SHELLS:
        return None
    if "llama-server" in lower_name or lower_name in ("llama_server.exe",):
        return "llama"
    if lower_name in INTERPRETERS:
        tokens = [token.strip("\"'") for token in cmdline.split()]
        for token in tokens[1:]:
            base = token.replace("\\", "/").rsplit("/", 1)[-1].lower()
            if base in ("api_server.py",):
                return "cosyvoice"
        if "cosyvoice" in cwd.lower():
            return "cosyvoice"
        return None
    return None


def process_table() -> list[ProcInfo]:
    rows: list[ProcInfo] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            info = proc.info
            name = info.get("name") or ""
            cmdline = " ".join(info.get("cmdline") or [])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        cwd = _process_cwd(proc) if name.lower() in ("python.exe", "pythonw.exe") else ""
        rows.append(ProcInfo(pid=int(info["pid"]), name=name, cmdline=cmdline, cwd=cwd,
                             kind=classify(name, cmdline, cwd)))
    return rows


def find_heavy(kind: str | None = None) -> list[ProcInfo]:
    return [p for p in process_table()
            if p.kind is not None and (kind is None or p.kind == kind)]


def find_ffmpeg() -> list[ProcInfo]:
    return [p for p in process_table() if p.name.lower() in FFMPEG_MARKERS]


def pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        proc = psutil.Process(pid)
        return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError, ValueError):
        return False


def process_matches(pid: int, spec: "ServiceSpec") -> bool:
    """True when ``pid`` is the service the spec describes."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
        cmdline = " ".join(proc.cmdline())
    except (psutil.Error, OSError):
        return False
    cwd = _process_cwd(proc)
    if classify(name, cmdline, cwd) != spec.kind:
        return False
    haystack = f"{name} {cmdline} {cwd}".lower()
    return any(marker.lower() in haystack for marker in spec.markers)


# --------------------------------------------------------------------------
# ports
# --------------------------------------------------------------------------
def port_owner(port: int) -> int | None:
    try:
        for conn in psutil.net_connections(kind="tcp"):
            if (conn.status == psutil.CONN_LISTEN and conn.laddr
                    and conn.laddr.port == port and conn.pid):
                return int(conn.pid)
    except (psutil.Error, OSError):
        pass
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             f"(Get-NetTCPConnection -State Listen -LocalPort {port} "
             "-ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"],
            capture_output=True, text=True, timeout=20, errors="replace")
        text = out.stdout.strip()
        return int(text) if text.isdigit() else None
    except (subprocess.SubprocessError, ValueError):
        return None


def wait_port_free(port: int, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_owner(port) is None:
            return True
        time.sleep(interval)
    return port_owner(port) is None


def wait_port_open(port: int, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_owner(port) is not None:
            return True
        time.sleep(interval)
    return port_owner(port) is not None


# --------------------------------------------------------------------------
# kill trees
# --------------------------------------------------------------------------
def kill_tree(pid: int, *, timeout: float = 15.0) -> dict[str, Any]:
    """taskkill /F /T the tree, then verify; psutil fallback for stragglers."""
    result: dict[str, Any] = {"pid": pid, "taskkill_rc": None, "remaining": [],
                              "already_gone": False, "seconds": 0.0}
    started = time.monotonic()
    if not pid_alive(pid):
        result["already_gone"] = True
        return result
    descendants: list[int] = []
    try:
        descendants = [int(c.pid) for c in psutil.Process(pid).children(recursive=True)]
    except (psutil.Error, OSError):
        pass
    try:
        cp = subprocess.run([TASKKILL, "/F", "/T", "/PID", str(pid)],
                            capture_output=True, text=True, errors="replace", timeout=30)
        result["taskkill_rc"] = cp.returncode
    except (subprocess.SubprocessError, OSError) as exc:
        result["taskkill_error"] = str(exc)
    deadline = started + timeout
    while time.monotonic() < deadline:
        alive = [p for p in [pid, *descendants] if pid_alive(p)]
        if not alive:
            break
        for straggler in alive:
            try:
                psutil.Process(straggler).kill()
            except (psutil.Error, OSError):
                pass
        time.sleep(0.1)
    result["remaining"] = [p for p in [pid, *descendants] if pid_alive(p)]
    result["seconds"] = round(time.monotonic() - started, 3)
    return result


# --------------------------------------------------------------------------
# VRAM accounting (Intel Arc has no nvidia-smi; use the Windows GPU counters)
# --------------------------------------------------------------------------
def gpu_memory_by_pid(timeout: float = 25.0) -> dict[int, int]:
    """Dedicated GPU memory in MiB per pid, from Windows performance counters."""
    script = (
        "Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUProcessMemory "
        "| Where-Object { $_.DedicatedUsage -gt 0 } "
        "| ForEach-Object { \"$($_.Name)|$($_.DedicatedUsage)\" }"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=timeout, errors="replace")
    except (subprocess.SubprocessError, OSError):
        return {}
    mem: dict[int, int] = {}
    for line in out.stdout.splitlines():
        name, _, usage = line.strip().partition("|")
        if not name.startswith("pid_") or not usage.isdigit():
            continue
        try:
            pid = int(name.split("_")[1])
        except (IndexError, ValueError):
            continue
        mem[pid] = round(int(usage) / (1024 * 1024))
    return mem


# --------------------------------------------------------------------------
# exclusivity guards
# --------------------------------------------------------------------------
def describe(procs: list[ProcInfo]) -> str:
    return ", ".join(f"{p.name}#{p.pid}({p.kind})" for p in procs)


def assert_quiet(*, allow_kind: str | None = None, context: str = "stage") -> None:
    """Raise unless at most the allowed service kind is running."""
    heavy = find_heavy()
    allowed = [p for p in heavy if allow_kind and p.kind == allow_kind]
    offenders = [p for p in heavy if p not in allowed]
    if allow_kind and len(allowed) > 1:
        offenders = heavy
    if offenders:
        raise ResourceBusyError(
            f"{context}: refusing to start -- other heavyweight process(es) alive: "
            f"{describe(offenders)}. Run `uv run python scripts/run_pipeline.py --cleanup`.")
    if allowed:
        log(f"{context}: exclusive slot granted ({allow_kind} already running, "
            f"pid {allowed[0].pid})")


def cleanup_all(*, cooldown_s: float = COOLDOWN_S) -> list[dict[str, Any]]:
    """Kill every heavy process (models first, then ffmpeg) and cool down."""
    report: list[dict[str, Any]] = []
    for proc in find_heavy():
        log(f"清理 isolate {proc.kind}: {proc.name}#{proc.pid}")
        report.append(kill_tree(proc.pid))
    for proc in find_ffmpeg():
        log(f"清理 isolate ffmpeg: {proc.name}#{proc.pid}")
        report.append(kill_tree(proc.pid))
    if report:
        if cooldown_s > 0:
            log(f"冷却中 {cooldown_s:.1f}s")
            time.sleep(cooldown_s)
        log("清理 done")
    left = find_heavy()
    if left:
        raise ResourceBusyError(f"cleanup incomplete: {describe(left)}")
    return report


# --------------------------------------------------------------------------
# service specs
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class ServiceSpec:
    name: str
    kind: str
    cmd: tuple[str, ...]
    port: int
    markers: tuple[str, ...]
    cwd: Path | None = None
    env: dict[str, str] | None = None
    log_name: str = ""
    startup_timeout_s: float = 600.0
    poll_interval_s: float = 1.0

    @property
    def health_url(self) -> str:
        return f"http://{DEFAULT_HOST}:{self.port}/health"

    @property
    def base_url(self) -> str:
        return f"http://{DEFAULT_HOST}:{self.port}"


def llama_spec(*, port: int | None = None, model_path: Path | None = None,
               bin_path: Path | None = None, ctx: int = 16384,
               n_cpu_moe: int = 48) -> ServiceSpec:
    exe = Path(bin_path or LLAMA_BIN)
    model = Path(model_path or LLAMA_MODEL)
    sport = int(port or LLAMA_PORT)
    cmd = (
        str(exe), "-m", str(model),
        "--host", DEFAULT_HOST, "--port", str(sport),
        "-dev", "SYCL0", "-ngl", "99", "-c", str(ctx), "--parallel", "1",
        "-b", "256", "-ub", "128", "-fa", "on", "--metrics",
        "--alias", f"{LLAMA_ALIAS},default",
        "--jinja", "--n-cpu-moe", str(n_cpu_moe),
    )
    return ServiceSpec(name="llama-server", kind="llama", cmd=cmd, port=sport,
                       markers=("llama-server",), log_name="llama-server",
                       startup_timeout_s=900.0, poll_interval_s=1.0)


def cosyvoice_spec(*, port: int | None = None, cwd: Path | None = None,
                   preset_voice: bool = False) -> ServiceSpec:
    root = Path(cwd or COSY_DIR)
    sport = int(port or COSY_PORT)
    python = root / "venv" / "Scripts" / "python.exe"
    env = {
        "COSY_MODEL_CLASS": "CosyVoice2",
        "COSY_MODEL_DIR": str(root / "pretrained_models" / "CosyVoice2-0.5B"),
        "COSY_PROMPT_WAV": str(root / "assets" / "my_voice_5s.wav"),
        "COSY_WETEXT_DIR": str(root / "assets" / "wetext"),
        "COSY_CPU_THREADS": "12",
        "COSY_HOST": DEFAULT_HOST,
        "COSY_PORT": str(sport),
        "PYTHONUNBUFFERED": "1",
        "PYTHONUTF8": "1",
    }
    if preset_voice:
        # CosyVoice-300M-SFT: preset speakers, no reference audio needed.
        env["COSY_MODEL_CLASS"] = COSY_SFT_CLASS
        env["COSY_MODEL_DIR"] = str(root / "pretrained_models" / COSY_SFT_DIRNAME)
    return ServiceSpec(name="cosyvoice", kind="cosyvoice",
                       cmd=(str(python), str(root / "api_server.py")),
                       port=sport, markers=("api_server.py", "cosyvoice"),
                       cwd=root, env=env, log_name="cosyvoice",
                       startup_timeout_s=300.0, poll_interval_s=0.5)


# --------------------------------------------------------------------------
# health
# --------------------------------------------------------------------------
READY_STATUSES = {"ok", "ready", "healthy", "up"}
FATAL_STATUSES = {"error", "failed", "dead"}


def health_state(status_code: int, body: str) -> tuple[str, dict[str, Any] | None]:
    """Classify a /health response as ready / loading / fatal."""
    payload: dict[str, Any] | None = None
    try:
        parsed = json.loads(body)
        payload = parsed if isinstance(parsed, dict) else None
    except (ValueError, TypeError):
        payload = None
    status = str((payload or {}).get("status", "")).lower()
    if status_code == 200 and (status in READY_STATUSES or status == ""):
        return "ready", payload
    if status in FATAL_STATUSES:
        return "fatal", payload
    if status_code >= 500 and payload and (payload.get("error") or {}).get("code"):
        message = str((payload.get("error") or {}).get("message", ""))
        if "loading" not in message.lower():
            return "fatal", payload
    return "loading", payload


def probe_health(url: str, timeout: float = 5.0) -> tuple[str, dict[str, Any] | None, str]:
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:
        return "loading", None, str(exc)[:200]
    state, payload = health_state(resp.status_code, resp.text)
    return state, payload, resp.text[:200]


# --------------------------------------------------------------------------
# managed service
# --------------------------------------------------------------------------
def _log_tail(path: Path, lines: int = 12) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return " | ".join(text[-lines:])


class ManagedService:
    """Start (or adopt) one service, then guarantee it is dead and cooled down.

    Use as a context manager.  The exit path runs even when the body raises;
    that is the whole point -- no stage may leave VRAM allocated.
    """

    def __init__(self, spec: ServiceSpec, *, adopt: bool = True,
                 cooldown_s: float | None = None, measure_vram: bool = False,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.spec = spec
        self.adopt = adopt
        self.cooldown_s = COOLDOWN_S if cooldown_s is None else float(cooldown_s)
        self.measure_vram = measure_vram
        self._sleep = sleep
        self.pid: int | None = None
        self.adopted = False
        self.health: dict[str, Any] | None = None
        self.log_path = LOG_DIR / f"{spec.log_name or spec.name}.log"
        self.vram_mb: int | None = None
        self.stopped = False
        self._proc: subprocess.Popen[str] | None = None
        self._log_fh: Any = None

    # -- context protocol ------------------------------------------------
    def __enter__(self) -> "ManagedService":
        assert_quiet(allow_kind=self.spec.kind, context=self.spec.name)
        owner = port_owner(self.spec.port)
        if owner is None:
            same_kind = find_heavy(self.spec.kind)
            if same_kind:
                raise ResourceBusyError(
                    f"{self.spec.name}: another {self.spec.kind} process is already "
                    f"running on a different port ({describe(same_kind)}); only one "
                    f"heavyweight process is allowed. Run `run_pipeline.py --cleanup`.")
        if owner:
            if not self.adopt:
                raise ResourceBusyError(
                    f"{self.spec.name}: port {self.spec.port} already used by pid {owner}")
            if not process_matches(owner, self.spec):
                raise ResourceBusyError(
                    f"{self.spec.name}: port {self.spec.port} is held by an unrelated "
                    f"pid {owner}; kill it first")
            self.pid = owner
            self.adopted = True
            log(f"{self.spec.name}: 已启动 (adopted pid {owner}, port {self.spec.port})")
        else:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self._log_fh = open(self.log_path, "a", encoding="utf-8", errors="replace")
            self._log_fh.write(f"\n=== {datetime.now().isoformat()} "
                               f"{self.spec.name} ===\n")
            self._log_fh.flush()
            env = {**os.environ, **(self.spec.env or {})}
            flags = 0
            if os.name == "nt":
                flags = (getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                         | getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log(f"{self.spec.name}: 已启动 (spawning, port {self.spec.port})")
            try:
                self._proc = subprocess.Popen(
                    list(self.spec.cmd), cwd=str(self.spec.cwd) if self.spec.cwd else None,
                    env=env, stdout=self._log_fh, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL, creationflags=flags, text=True)
            except OSError as exc:
                self._close_log()
                raise ServiceError(f"{self.spec.name}: could not start: {exc}") from exc
            self.pid = self._proc.pid
            log(f"{self.spec.name}: pid {self.pid}, waiting for health at "
                f"{self.spec.health_url}")
        try:
            self.health = self._wait_ready()
        except BaseException:
            try:
                self.stop(reason="startup failed")
            except Exception as cleanup_exc:       # keep the original failure
                log(f"{self.spec.name}: cleanup after startup failure failed: "
                    f"{cleanup_exc}")
            raise
        log(f"{self.spec.name}: 已完成 health check "
            f"({(self.health or {}).get('model_class') or (self.health or {}).get('status')})")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        try:
            self.stop(reason="stage finished" if exc is None else "stage failed")
        except Exception as cleanup_exc:
            if exc is not None:                     # do not mask the stage error
                log(f"{self.spec.name}: cleanup failed while handling "
                    f"{exc_type.__name__ if exc_type else 'error'}: {cleanup_exc}")
            else:
                raise
        return False

    # -- health ----------------------------------------------------------
    def _wait_ready(self) -> dict[str, Any]:
        deadline = time.monotonic() + self.spec.startup_timeout_s
        last = "no response"
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                raise ServiceError(
                    f"{self.spec.name} exited with code {self._proc.returncode} before "
                    f"becoming ready. log: {_log_tail(self.log_path)}")
            state, payload, detail = probe_health(self.spec.health_url)
            if state == "ready":
                return payload or {"status": "ok"}
            if state == "fatal":
                raise ServiceError(f"{self.spec.name} reported a fatal error: {detail}")
            last = detail
            self._sleep(self.spec.poll_interval_s)
        raise ServiceError(
            f"{self.spec.name} not ready at {self.spec.health_url} after "
            f"{self.spec.startup_timeout_s:.0f}s ({last}). "
            f"log: {_log_tail(self.log_path)}")

    # -- teardown --------------------------------------------------------
    def stop(self, *, reason: str = "stop") -> dict[str, Any] | None:
        if self.stopped or self.pid is None:
            return None
        self.stopped = True
        pid = self.pid
        if self.measure_vram:
            self.vram_mb = gpu_memory_by_pid().get(pid)
        log(f"{self.spec.name}: 清理 (reason: {reason}, pid {pid}, "
            f"vram {self.vram_mb if self.vram_mb is not None else '?'} MiB)")
        result = kill_tree(pid)
        # A launcher (e.g. the uv venv trampoline) can leave the real listener
        # in a detached child; kill whatever still owns the port.
        owner = port_owner(self.spec.port)
        if owner and owner != pid and process_matches(owner, self.spec):
            log(f"{self.spec.name}: killing detached listener {owner}")
            kill_tree(owner)
        freed = wait_port_free(self.spec.port, timeout=10.0)
        if self._proc is not None:
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        self._close_log()
        if result["remaining"]:
            raise ResourceBusyError(
                f"{self.spec.name}: pid(s) {result['remaining']} survived taskkill")
        if not freed:
            leftover = port_owner(self.spec.port)
            raise ResourceBusyError(
                f"{self.spec.name}: port {self.spec.port} still held by pid {leftover}")
        if self.cooldown_s > 0:
            log(f"{self.spec.name}: 冷却中 {self.cooldown_s:.1f}s")
            self._sleep(self.cooldown_s)
        log(f"{self.spec.name}: 已清理 (pid {pid} gone, port {self.spec.port} free)")
        return result

    def _close_log(self) -> None:
        if self._log_fh is not None:
            try:
                self._log_fh.close()
            except OSError:
                pass
            self._log_fh = None


def llama_server(**kwargs: Any) -> ManagedService:
    spec_kwargs = {k: kwargs.pop(k) for k in ("port", "model_path", "bin_path", "ctx",
                                              "n_cpu_moe") if k in kwargs}
    return ManagedService(llama_spec(**spec_kwargs), measure_vram=True, **kwargs)


def cosyvoice(**kwargs: Any) -> ManagedService:
    spec_kwargs = {k: kwargs.pop(k) for k in ("port", "cwd", "preset_voice") if k in kwargs}
    return ManagedService(cosyvoice_spec(**spec_kwargs), measure_vram=False, **kwargs)


# --------------------------------------------------------------------------
# quiet stages (no model may be alive)
# --------------------------------------------------------------------------
class quiet_stage:
    """Context for FFmpeg/QSV work: no model, and it stays dead afterwards."""

    def __init__(self, name: str, *, check_ffmpeg_exit: bool = False) -> None:
        self.name = name
        self.check_ffmpeg_exit = check_ffmpeg_exit

    def __enter__(self) -> "quiet_stage":
        assert_quiet(context=self.name)
        log(f"{self.name}: 已确认无模型进程，QSV/编码窗口独占")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if self.check_ffmpeg_exit:
            for proc in find_ffmpeg():
                log(f"{self.name}: killing leftover ffmpeg {proc.pid}")
                kill_tree(proc.pid)
        remaining = find_heavy()
        if remaining:
            log(f"{self.name}: WARNING model process appeared mid-stage: "
                f"{describe(remaining)}")
        else:
            log(f"{self.name}: 已清理 (no model process alive)")
        return False


# --------------------------------------------------------------------------
# pipeline lock
# --------------------------------------------------------------------------
class PipelineLock:
    """Exclusive lock file: one four-stage pipeline per machine at a time."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or LOCK_PATH)
        self.owned = False

    def __enter__(self) -> "PipelineLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                info = self.read()
                holder = int(info.get("pid") or 0)
                if holder and pid_alive(holder):
                    raise ResourceBusyError(
                        f"another pipeline is running (pid {holder}, started "
                        f"{info.get('started_at')}); refusing to interleave")
                log(f"removing stale lock (pid {holder} is gone)")
                try:
                    self.path.unlink()
                except OSError:
                    pass
                continue
            payload = {"pid": os.getpid(),
                       "started_at": datetime.now().isoformat(timespec="seconds")}
            os.write(fd, json.dumps(payload).encode("utf-8"))
            os.close(fd)
            self.owned = True
            log(f"pipeline lock acquired ({self.path.name}, pid {os.getpid()})")
            return self
        raise ResourceBusyError(f"could not acquire {self.path}")

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if self.owned:
            info = self.read()
            if int(info.get("pid") or 0) == os.getpid():
                try:
                    self.path.unlink()
                except OSError:
                    pass
            self.owned = False
            log("pipeline lock released")
        return False

    def read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}


# --------------------------------------------------------------------------
# status report
# --------------------------------------------------------------------------
def status(*, include_lock: bool = True) -> dict[str, Any]:
    heavy = find_heavy()
    vram = gpu_memory_by_pid()
    report: dict[str, Any] = {
        "heavy": [{**p.as_dict(), "vram_mb": vram.get(p.pid)} for p in heavy],
        "ffmpeg": [p.as_dict() for p in find_ffmpeg()],
        "ports": {port: port_owner(port) for port in (LLAMA_PORT, COSY_PORT)},
    }
    if include_lock:
        report["lock"] = PipelineLock().read()
    return report
