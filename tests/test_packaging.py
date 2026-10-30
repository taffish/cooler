"""Deterministic packaging regressions; native wrapper tests are separate."""
import contextlib
import importlib.machinery
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
gui = importlib.machinery.SourceFileLoader("gui_test", str(ROOT / "docker/cooler-gui")).load_module()
smoke = importlib.machinery.SourceFileLoader("smoke_test", str(ROOT / "docker/cooler_smoke.py")).load_module()


class VersionTests(unittest.TestCase):
    def test_exact_output_and_status(self):
        cases = [(0, "cooler, version 0.12.1\n", True),
                 (9, "cooler, version 0.12.1\n", False), (0, "", False),
                 (0, "cooler, version 0.11.0\n", False),
                 (0, "cooler, version 0.12.1-extra\n", False),
                 (0, "\ncooler, version 0.12.1\n", False),
                 (0, "cooler, version 0.12.1\nextra\n", False)]
        for code, text, passed in cases:
            with self.subTest(code=code, text=text), \
                 mock.patch.dict(sys.modules, cooler=types.SimpleNamespace(__version__="0.12.1")), \
                 mock.patch.object(smoke.subprocess, "run", return_value=types.SimpleNamespace(returncode=code, stdout=text)):
                if passed:
                    smoke.version_check()
                else:
                    with self.assertRaises(AssertionError):
                        smoke.version_check()


@unittest.skipUnless(sys.platform == "linux", "container helper requires Linux /tmp and procfs")
class SessionTests(unittest.TestCase):
    def test_initialization_failure_retains_recovery_diagnostic(self):
        with tempfile.TemporaryDirectory() as fixture:
            src = Path(fixture) / "in.cool"
            src.write_bytes(b"input")
            allocated = []
            real_open, real_mkdtemp = os.open, tempfile.mkdtemp
            def allocate(*args, **kwargs):
                name = real_mkdtemp(*args, **kwargs)
                allocated.append(Path(name))
                return name
            def deny_owned_open(path, *args, **kwargs):
                if str(path).startswith("cooler-gui-"):
                    raise PermissionError("injected initial fd failure")
                return real_open(path, *args, **kwargs)
            stream = io.StringIO()
            handlers = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
            with mock.patch.object(gui.os, "open", side_effect=deny_owned_open), \
                 mock.patch.object(gui.tempfile, "mkdtemp", side_effect=allocate), \
                 mock.patch.object(sys, "argv", ["cooler-gui", str(src), "chr1", "--port", "65321"]), \
                 contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                code = gui.main()
            self.assertEqual(code, 1)
            self.assertEqual(len(allocated), 1)
            self.assertTrue(allocated[0].is_dir())
            self.assertIn("recovery directory: " + str(allocated[0]), stream.getvalue())
            self.assertNotIn("session files removed", stream.getvalue())
            self.assertTrue(all(signal.getsignal(s) == h for s, h in handlers.items()))
            self.assertEqual(src.read_bytes(), b"input")
            allocated[0].rmdir()

    def test_normal_idempotent_external_symlink(self):
        with tempfile.TemporaryDirectory() as elsewhere:
            sentinel = Path(elsewhere) / "keep"
            sentinel.write_bytes(b"outside")
            session = gui.Session()
            try:
                (session.root / "external").symlink_to(elsewhere)
                (session.root / "webagg.log").symlink_to(sentinel)
                with self.assertRaises(OSError):
                    session.tail()
                session.cleanup()
                session.cleanup()
                self.assertEqual(sentinel.read_bytes(), b"outside")
                self.assertFalse(session.root.exists())
            finally:
                session.close()

    def test_replaced_root_and_recovery(self):
        for replacement in ("symlink", "directory"):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as elsewhere:
                sentinel = Path(elsewhere) / "keep"
                sentinel.write_bytes(b"outside")
                session = gui.Session()
                old = session.root.with_name(session.root.name + "-recovery")
                try:
                    (session.root / "webagg.log").write_text("owned log")
                    session.root.rename(old)
                    if replacement == "symlink":
                        session.root.symlink_to(elsewhere)
                    else:
                        session.root.mkdir()
                        (session.root / "keep").write_bytes(b"foreign")
                    with self.assertRaises(OSError):
                        session.cleanup()
                    with self.assertRaises(OSError):
                        session.tail()
                    self.assertEqual((old / "webagg.log").read_text(), "owned log")
                    self.assertEqual(sentinel.read_bytes(), b"outside")
                    if replacement == "symlink":
                        session.root.unlink()
                    else:
                        self.assertEqual((session.root / "keep").read_bytes(), b"foreign")
                        (session.root / "keep").unlink()
                        session.root.rmdir()
                    old.rename(session.root)
                    session.cleanup()
                finally:
                    session.close()

    def test_parent_identity_and_deletion_failure(self):
        session = gui.Session()
        try:
            (session.root / "keep").write_text("owned")
            with mock.patch.object(gui.os, "lstat", return_value=types.SimpleNamespace(st_dev=-1, st_ino=-1)):
                with self.assertRaises(OSError):
                    session.cleanup()
            with mock.patch.object(gui.os, "unlink", side_effect=PermissionError("injected deletion failure")):
                with self.assertRaises(PermissionError):
                    session.cleanup()
            self.assertEqual((session.root / "keep").read_text(), "owned")
            session.cleanup()
        finally:
            session.close()

    def test_race_after_listing_is_not_path_following(self):
        session = gui.Session()
        old = session.root.with_name(session.root.name + "-recovery")
        real_listdir = os.listdir
        with tempfile.TemporaryDirectory() as elsewhere:
            (Path(elsewhere) / "keep").write_text("outside")
            (session.root / "owned").write_text("ours")
            def replaced(fd):
                result = real_listdir(fd)
                session.root.rename(old)
                session.root.symlink_to(elsewhere)
                return result
            try:
                with mock.patch.object(gui.os, "listdir", side_effect=replaced):
                    with self.assertRaises(OSError):
                        session.cleanup()
                self.assertEqual((old / "owned").read_text(), "ours")
                self.assertEqual((Path(elsewhere) / "keep").read_text(), "outside")
                session.root.unlink()
                old.rename(session.root)
                session.cleanup()
            finally:
                session.close()

    def test_cleanup_error_never_claims_success(self):
        for failure in ("wait", "delete"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as fixture:
                src = Path(fixture) / "in.cool"
                src.write_bytes(b"input")
                sessions = []
                real_session = gui.Session
                def allocate():
                    s = real_session()
                    sessions.append(s)
                    return s
                fake = mock.Mock(pid=12345)
                fake.poll.return_value = None
                fake.wait.side_effect = subprocess.TimeoutExpired("fake child", 4) if failure == "wait" else None
                def popen(*args, **kwargs):
                    os.kill(os.getpid(), signal.SIGTERM)
                    return fake
                stream = io.StringIO()
                old = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
                with mock.patch.object(gui, "Session", side_effect=allocate), \
                     mock.patch.object(gui.subprocess, "Popen", side_effect=popen), \
                     mock.patch.object(gui.os, "killpg"), \
                     mock.patch.object(sys, "argv", ["cooler-gui", str(src), "chr1", "--port", "65321"]), \
                     contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                    if failure == "delete":
                        with mock.patch.object(real_session, "cleanup", side_effect=PermissionError("cannot delete")):
                            code = gui.main()
                    else:
                        code = gui.main()
                self.assertEqual(code, 143)
                self.assertNotIn("stopped; session files removed", stream.getvalue())
                self.assertIn("recovery directory:", stream.getvalue())
                self.assertTrue(sessions[0].root.is_dir())
                self.assertEqual(src.read_bytes(), b"input")
                self.assertTrue(all(signal.getsignal(s) == h for s, h in old.items()))
                # The fixture created no actual child; safely reclaim its kept root.
                import shutil
                shutil.rmtree(sessions[0].root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
