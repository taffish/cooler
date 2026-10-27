"""Fresh-container offline WebAgg checks; wrapper/browser checks remain separate."""
import argparse
import contextlib
import hashlib
import importlib.util
import importlib.machinery
import io
import os
from pathlib import Path
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import unittest.mock

spec = importlib.util.spec_from_file_location("core_smoke", "/opt/cooler/share/cooler_smoke.py")
core = importlib.util.module_from_spec(spec)
spec.loader.exec_module(core)


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def read_until(proc, lines, marker, timeout):
    deadline = time.monotonic() + timeout
    with selectors.DefaultSelector() as sel:
        sel.register(proc.stdout, selectors.EVENT_READ)
        while time.monotonic() < deadline:
            if marker in "".join(lines):
                return
            for key, event in sel.select(0.05):
                block = os.read(key.fd, 65536)
                if not block:
                    raise AssertionError("child ended before " + marker + "\n" + "".join(lines))
                lines.append(block.decode())
            if proc.poll() is not None and marker not in "".join(lines):
                raise AssertionError("child failed: " + "".join(lines))
    raise AssertionError("timeout waiting for " + marker + "\n" + "".join(lines))


def start(root):
    src = root / "input with spaces.cool"
    core.tiny(src)
    number = free_port()
    lines = []
    proc = subprocess.Popen(["cooler-gui", str(src), "chr1:0-60", "--port", str(number),
                             "--host-port", "18765", "--label", "two words",
                             "--scale", "linear"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    read_until(proc, lines, "Session files are temporary", 3)
    text = "".join(lines)
    assert "Cooler GUI is starting. two words" in text
    assert "Open: http://127.0.0.1:18765/1" in text
    assert "ssh -N -L 18765:127.0.0.1:18765" in text and "Ctrl-C" in text
    log = Path(next(x.split(": ", 1)[1] for x in text.splitlines() if x.startswith("Internal log: ")))
    assert log.parent.stat().st_mode & 0o777 == 0o700
    return proc, lines, number, log.parent


def stop(proc, lines, number, session, sig=signal.SIGTERM, expected=143):
    proc.send_signal(sig)
    tail, _ = proc.communicate(timeout=15)
    lines.append(tail.decode())
    text = "".join(lines)
    assert proc.returncode == expected, text
    assert "stopping (" in text and "stopped; session files removed." in text
    assert not session.exists(), session
    with socket.socket() as sock:
        assert sock.connect_ex(("127.0.0.1", number)) != 0
    return text


def session_check(root, mode):
    proc, lines, number, session = start(root)
    try:
        if mode == "interrupt":
            assert "GUI is ready." not in "".join(lines)
            stop(proc, lines, number, session, signal.SIGINT, 130)
            return
        read_until(proc, lines, "Cooler GUI is ready.", 60)
        text = "".join(lines)
        assert text.index("GUI is starting.") < text.index("GUI is ready.")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f"http://127.0.0.1:{number}/1") as response:
            assert b"mpl.js" in response.read()
        if mode == "failure":
            children = Path(f"/proc/{proc.pid}/task/{proc.pid}/children").read_text().split()
            assert len(children) == 1, children
            child = int(children[0])
            assert child > 1
            os.kill(child, signal.SIGKILL)
            tail, _ = proc.communicate(timeout=15)
            lines.append(tail.decode())
            text = "".join(lines)
            # A killed child can lose its socket before waitpid observes exit.
            # Both supervision paths must fail closed and clean this session.
            assert proc.returncode != 0 and any(message in text for message in (
                "WebAgg child exited unexpectedly", "WebAgg lost its owned listening socket")), text
            assert not session.exists()
            with socket.socket() as sock:
                assert sock.connect_ex(("127.0.0.1", number)) != 0
        else:
            for kind, signature in (("png", b"\x89PNG\r\n\x1a\n"), ("svg", b"<?xml"),
                                    ("pdf", b"%PDF"), ("jpeg", b"\xff\xd8"),
                                    ("eps", b"%!PS"), ("ps", b"%!PS"),
                                    ("gif", b"GIF"), ("tif", b"II"),
                                    ("webp", b"RIFF"), ("avif", b""), ("raw", b"")):
                print("GUI export stage=" + kind, flush=True)
                with opener.open(f"http://127.0.0.1:{number}/1/download.{kind}") as response:
                    artifact = response.read()
                assert len(artifact) > 500 and artifact.startswith(signature)
            # Upstream advertises PGF, but its stream cannot contain raster data.
            # The documented unsupported export must not terminate the viewer.
            try:
                opener.open(f"http://127.0.0.1:{number}/1/download.pgf")
            except urllib.error.HTTPError as error:
                assert error.code == 500
            else:
                raise AssertionError("PGF unexpectedly available; revisit its documented boundary")
            with opener.open(f"http://127.0.0.1:{number}/1") as response:
                assert b"mpl.js" in response.read()
            stop(proc, lines, number, session)
    except BaseException:
        log = session / "webagg.log"
        if log.exists():
            print(log.read_text(errors="replace")[-10000:], flush=True)
        if proc.poll() is None:
            proc.terminate()
        tail, _ = proc.communicate(timeout=15)
        print(("".join(lines) + tail.decode())[-10000:], flush=True)
        raise
    finally:
        if proc.poll() is None:
            proc.terminate()
            proc.communicate(timeout=15)


def invalid(root):
    helper = importlib.machinery.SourceFileLoader("cooler_gui_probe", "/opt/cooler/bin/cooler-gui").load_module()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        fdroot = Path(f"/proc/{os.getpid()}/fd")
        live = list(fdroot.iterdir())
        # Model a non-listening descriptor that vanished just after enumeration.
        with unittest.mock.patch.object(Path, "iterdir", return_value=iter(live + [fdroot / "2147483647"])):
            assert helper.owns_listener(os.getpid(), listener.getsockname()[1])
    assert "WebAgg" in core.run("cooler-gui", "--help")
    for args in (["missing.cool", "chr1"], [], ["--unknown"],
                 ["missing.cool", "chr1", "--port", "0"]):
        assert "error:" in core.run("cooler-gui", *args, expected=1)
    src = root / "tiny.cool"
    core.tiny(src)
    for sig in (signal.SIGINT, signal.SIGTERM):
        class InterruptedOutput(io.StringIO):
            fired = False
            writing = False

            def write(self, value):
                if self.writing:
                    raise RuntimeError("reentrant output regression")
                self.writing = True
                try:
                    if not self.fired and "GUI is starting." in value:
                        self.fired = True
                        os.kill(os.getpid(), sig)
                    return super().write(value)
                finally:
                    self.writing = False

        output = InterruptedOutput()
        before = src.read_bytes()
        with unittest.mock.patch.object(sys, "argv", ["cooler-gui", str(src), "chr1",
                                                      "--port", str(free_port())]), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = helper.main()
        text = output.getvalue()
        assert output.fired and code == 128 + sig, text
        assert "reentrant" not in text and "stopping (" in text, text
        assert "stopped; session files removed." in text
        log = Path(next(line.split(": ", 1)[1] for line in text.splitlines()
                        if line.startswith("Internal log: ")))
        assert not log.parent.exists() and src.read_bytes() == before
    for args in (["--ready-timeout", "nan"], ["--label", "line\nbreak"]):
        assert "error:" in core.run("cooler-gui", src, "chr1", *args, expected=1)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        number = listener.getsockname()[1]
        assert "cannot bind" in core.run("cooler-gui", src, "chr1", "--port", number, expected=1)
        assert listener.fileno() >= 0
    text = core.run("cooler-gui", src, "missing-chromosome", expected=1)
    assert "WebAgg child exited unexpectedly" in text and "session files removed" in text


def output_check(root):
    """Use real closed pipe consumers with the installed helper and WebAgg."""
    helper = importlib.machinery.SourceFileLoader("cooler_output_probe", "/opt/cooler/bin/cooler-gui").load_module()
    src = root / "input with spaces.cool"
    core.tiny(src)
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    old = root / "old-recovery"
    old.mkdir()
    (old / "keep").write_bytes(b"unrelated recovery data")
    # Fail the first announcement before WebAgg may be created. Use pipes,
    # not /dev/full: Apptainer's contained /dev deliberately omits that device.
    for kind in ("stdout", "both"):
        prior = set(Path("/tmp").glob("cooler-gui-*"))
        number = free_port()
        reader, writer = os.pipe()
        os.close(reader)
        sink = os.fdopen(writer, "wb")
        with sink:
            result = subprocess.run(["cooler-gui", str(src), "chr1", "--port", str(number)],
                                    stdout=sink, stderr=sink if kind == "both" else subprocess.PIPE, timeout=15)
        assert result.returncode == 1, (kind, result.returncode, result.stderr)
        if kind == "stdout":
            assert b"startup output is unavailable" in result.stderr
            assert b"Exception ignored" not in result.stderr
        assert set(Path("/tmp").glob("cooler-gui-*")) == prior
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", number)) != 0
        print(f"PASS gui-output first-write {kind} exit=1 no-residue", flush=True)
    cases = [("startup", "stdout", None, 1),
             ("ready", "stdout", signal.SIGINT, 130),
             ("ready", "stdout", signal.SIGTERM, 143),
             ("ready", "both", signal.SIGINT, 130),
             ("ready", "both", signal.SIGTERM, 143),
             ("failure", "stderr", None, 1)]
    for stage, closed, sig, expected in cases:
        number = free_port()
        lines = []
        session = None
        owned = []
        proc = subprocess.Popen(["cooler-gui", str(src), "chr1:0-60", "--port", str(number),
                                 "--scale", "linear"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            read_until(proc, lines, "Session files are temporary", 3)
            text = "".join(lines)
            session = Path(next(x.split(": ", 1)[1] for x in text.splitlines()
                                if x.startswith("Internal log: "))).parent
            assert session.parent == Path("/tmp") and session.name.startswith("cooler-gui-")
            assert session.stat().st_mode & 0o777 == 0o700
            if stage != "startup":
                read_until(proc, lines, "Cooler GUI is ready.", 60)
                owned = [int(x) for x in Path(f"/proc/{proc.pid}/task/{proc.pid}/children").read_text().split()]
                assert len(owned) == 1 and owned[0] > 1 and os.getpgid(owned[0]) == owned[0]
                assert helper.owns_listener(owned[0], number)
            else:
                assert "GUI is ready." not in "".join(lines)
            if closed in ("stdout", "both"):
                proc.stdout.close()
            if closed in ("stderr", "both"):
                proc.stderr.close()
            if stage == "failure":
                os.kill(owned[0], signal.SIGKILL)
            elif sig:
                proc.send_signal(sig)
            assert proc.wait(timeout=75 if stage == "startup" else 15) == expected
            assert not session.exists(), session
            assert all(not Path(f"/proc/{pid}").exists() for pid in owned), owned
            with socket.socket() as sock:
                assert sock.connect_ex(("127.0.0.1", number)) != 0
            assert hashlib.sha256(src.read_bytes()).hexdigest() == before
            assert (old / "keep").read_bytes() == b"unrelated recovery data"
            for stream in (proc.stdout, proc.stderr):
                if not stream.closed:
                    tail = stream.read().decode(errors="replace")
                    assert "BrokenPipeError" not in tail and "Exception ignored" not in tail, tail
            print(f"PASS gui-output {stage} {closed} {sig} exit={expected} no-residue", flush=True)
        finally:
            # Failure diagnostics reclaim only this test's registered session.
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=15)
            for pid in owned:
                if Path(f"/proc/{pid}").exists() and os.getpgid(pid) == pid:
                    os.killpg(pid, signal.SIGKILL)
            for stream in (proc.stdout, proc.stderr):
                stream.close()
            if session is not None and session.exists():
                shutil.rmtree(session)


p = argparse.ArgumentParser()
p.add_argument("mode", choices=("service", "interrupt", "failure", "invalid", "output"))
a = p.parse_args()
with tempfile.TemporaryDirectory(prefix="cooler-gui-smoke-", dir="/tmp") as tmp:
    root = Path(tmp)
    if a.mode == "invalid":
        invalid(root)
    elif a.mode == "output":
        output_check(root)
    else:
        session_check(root, a.mode)
print("PASS gui-" + a.mode, flush=True)
