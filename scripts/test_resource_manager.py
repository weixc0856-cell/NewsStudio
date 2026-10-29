"""Tests for scripts/resource_manager.py (stdlib unittest + psutil).

Run:
    .venv/Scripts/python.exe scripts/test_resource_manager.py

The fake service is a real child process that serves /health and spawns a
grandchild, so ``taskkill /F /T`` is exercised for real -- no mocks on the
kill path.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import resource_manager as rm  # noqa: E402

FAKE_SERVER = '''
import http.server, json, subprocess, sys
port = int(sys.argv[1])
pid_file = sys.argv[2]
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(180)"])
open(pid_file, "w").write(str(child.pid))

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()
'''


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def wait_file(path: Path, timeout: float = 15.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            text = path.read_text().strip()
            if text:
                return int(text)
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    raise AssertionError(f"{path} was never written")


class CleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="rm-test-")
        self.dir = Path(self.tmp.name)
        self.pids: list[int] = []
        # The developer machine may have llama-server up; unit tests must not
        # depend on that state, so the real scan is neutralised by default.
        self.patcher = mock.patch.object(rm, "find_heavy", return_value=[])
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.addCleanup(self._kill_leftovers)
        self.addCleanup(self.tmp.cleanup)

    def _kill_leftovers(self) -> None:
        for pid in self.pids:
            try:
                rm.kill_tree(pid, timeout=5.0)
            except Exception:
                pass

    def spec(self, port: int, name: str = "fake") -> rm.ServiceSpec:
        script = self.dir / "api_server.py"
        script.write_text(FAKE_SERVER, encoding="utf-8")
        pid_file = self.dir / f"{name}.pid"
        return rm.ServiceSpec(
            name=name, kind="cosyvoice",
            cmd=(sys.executable, str(script), str(port), str(pid_file)),
            port=port, markers=("api_server.py",), log_name=f"test-{name}",
            startup_timeout_s=30.0, poll_interval_s=0.05)

    # -- health classification ------------------------------------------
    def test_health_state(self) -> None:
        self.assertEqual(rm.health_state(200, '{"status":"ok"}')[0], "ready")
        self.assertEqual(rm.health_state(200, '{"status":"ready"}')[0], "ready")
        self.assertEqual(rm.health_state(200, "")[0], "ready")
        self.assertEqual(
            rm.health_state(503, '{"error":{"code":503,"message":"Loading model"}}')[0],
            "loading")
        self.assertEqual(rm.health_state(500, '{"status":"error"}')[0], "fatal")

    # -- lifecycle -------------------------------------------------------
    def test_start_health_poll_and_kill_tree(self) -> None:
        port = free_port()
        pid_file = self.dir / "fake.pid"
        spec = self.spec(port)
        with rm.ManagedService(spec, cooldown_s=0.0) as svc:
            self.assertIsNotNone(svc.pid)
            self.assertTrue(rm.pid_alive(svc.pid))
            self.assertEqual(svc.health, {"status": "ok"})
            grandchild = wait_file(pid_file)
            self.pids.append(grandchild)
            self.assertTrue(rm.pid_alive(grandchild))
            # the venv python is a launcher: the listener is its child
            listener = rm.port_owner(port)
            self.assertIsNotNone(listener)
            self.assertTrue(rm.pid_alive(listener))
        self.assertFalse(rm.pid_alive(svc.pid))
        self.assertFalse(rm.pid_alive(grandchild))
        self.assertIsNone(rm.port_owner(port))

    def test_exception_still_kills_the_tree(self) -> None:
        port = free_port()
        spec = self.spec(port, "boom")
        with self.assertRaises(RuntimeError):
            with rm.ManagedService(spec, cooldown_s=0.0) as svc:
                pid = svc.pid
                raise RuntimeError("stage blew up")
        self.assertFalse(rm.pid_alive(pid))
        self.assertIsNone(rm.port_owner(port))

    def test_adopts_then_kills_matching_service(self) -> None:
        import subprocess
        port = free_port()
        spec = self.spec(port, "adopt")
        pid_file = self.dir / "adopt.pid"
        proc = subprocess.Popen(list(spec.cmd))
        self.pids.append(proc.pid)
        self.assertTrue(rm.wait_port_open(port, timeout=15))
        with rm.ManagedService(spec, cooldown_s=0.0) as svc:
            self.assertTrue(svc.adopted)
            self.assertEqual(svc.pid, rm.port_owner(port))
        self.assertFalse(rm.pid_alive(proc.pid))
        self.assertIsNone(rm.port_owner(port))
        self.assertTrue(pid_file.exists())

    def test_refuses_foreign_process_on_the_port(self) -> None:
        import http.server
        import threading
        port = free_port()
        server = http.server.HTTPServer(("127.0.0.1", port), http.server.BaseHTTPRequestHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        spec = self.spec(port, "foreign")
        try:
            with self.assertRaises(rm.ResourceBusyError):
                with rm.ManagedService(spec, cooldown_s=0.0):
                    pass
            self.assertIsNotNone(rm.port_owner(port))
        finally:
            server.shutdown()
            server.server_close()

    def test_refuses_a_second_service_of_the_same_kind(self) -> None:
        port = free_port()
        spec = self.spec(port, "second")
        other = rm.ProcInfo(pid=333, name="python.exe",
                            cmdline="python.exe api_server.py", kind="cosyvoice")
        with mock.patch.object(rm, "find_heavy", return_value=[other]):
            with self.assertRaises(rm.ResourceBusyError):
                with rm.ManagedService(spec, cooldown_s=0.0):
                    pass

    def test_cooldown_runs_after_kill(self) -> None:
        port = free_port()
        spec = self.spec(port, "cooldown")
        sleeps: list[float] = []
        with rm.ManagedService(spec, cooldown_s=0.4,
                               sleep=lambda seconds: sleeps.append(seconds)) as svc:
            pass
        self.assertIn(0.4, sleeps)
        self.assertFalse(rm.pid_alive(svc.pid))

    # -- kill_tree -------------------------------------------------------
    def test_kill_tree_parent_and_grandchild(self) -> None:
        pid_file = self.dir / "direct.pid"
        code = (
            "import subprocess, sys, time\n"
            f"child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(180)'])\n"
            f"open(r'{pid_file}', 'w').write(str(child.pid))\n"
            "time.sleep(180)\n"
        )
        import subprocess
        parent = subprocess.Popen([sys.executable, "-c", code])
        self.pids.append(parent.pid)
        grandchild = wait_file(pid_file)
        self.pids.append(grandchild)
        result = rm.kill_tree(parent.pid)
        self.assertEqual(result["remaining"], [])
        self.assertFalse(rm.pid_alive(grandchild))

    # -- exclusivity -----------------------------------------------------
    def test_assert_quiet_allows_only_one_kind(self) -> None:
        llama = rm.ProcInfo(pid=111, name="llama-server.exe", cmdline="", kind="llama")
        cosy = rm.ProcInfo(pid=222, name="python.exe", cmdline="api_server.py",
                           kind="cosyvoice")
        with mock.patch.object(rm, "find_heavy", return_value=[llama]):
            rm.assert_quiet(allow_kind="llama")
            with self.assertRaises(rm.ResourceBusyError):
                rm.assert_quiet()
        with mock.patch.object(rm, "find_heavy", return_value=[llama, cosy]):
            with self.assertRaises(rm.ResourceBusyError):
                rm.assert_quiet(allow_kind="llama")

    def test_shell_mentioning_the_marker_is_not_heavy(self) -> None:
        self.assertIsNone(rm.classify(
            "bash.exe", "bash.exe -c 'llama-server.exe -m model.gguf'"))
        self.assertIsNone(rm.classify(
            "python.exe", "python.exe -c \"print('api_server.py')\""))
        self.assertEqual(rm.classify("llama-server.exe", "llama-server.exe -m x"),
                         "llama")
        self.assertEqual(rm.classify("python.exe", "python.exe api_server.py"),
                         "cosyvoice")

    # -- lock ------------------------------------------------------------
    def test_pipeline_lock_is_exclusive(self) -> None:
        path = self.dir / "pipeline.lock"
        with rm.PipelineLock(path):
            with self.assertRaises(rm.ResourceBusyError):
                with rm.PipelineLock(path):
                    pass
        with rm.PipelineLock(path):
            self.assertTrue(path.exists())
        self.assertFalse(path.exists())

    def test_stale_lock_is_replaced(self) -> None:
        path = self.dir / "pipeline.lock"
        path.write_text(json.dumps({"pid": 999_999, "started_at": "x"}), encoding="utf-8")
        with rm.PipelineLock(path) as lock:
            self.assertTrue(lock.owned)
            self.assertEqual(json.loads(path.read_text())["pid"], os.getpid())


class CosyVoiceSpecTests(unittest.TestCase):
    def test_default_spec_is_zero_shot_cosyvoice2(self) -> None:
        spec = rm.cosyvoice_spec()
        self.assertEqual(spec.env["COSY_MODEL_CLASS"], "CosyVoice2")
        self.assertIn("CosyVoice2-0.5B", spec.env["COSY_MODEL_DIR"])

    def test_preset_voice_spec_switches_to_sft_model(self) -> None:
        spec = rm.cosyvoice_spec(preset_voice=True)
        self.assertEqual(spec.env["COSY_MODEL_CLASS"], "CosyVoice")
        self.assertIn("CosyVoice-300M-SFT", spec.env["COSY_MODEL_DIR"])
        self.assertEqual(spec.port, 50000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
