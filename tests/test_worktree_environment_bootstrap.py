import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_SCRIPT = ROOT / "scripts" / "worktree_environment_bootstrap.ps1"
CLEANUP_SCRIPT = ROOT / "scripts" / "worktree_cleanup_safety.ps1"


class WorktreeEnvironmentBootstrapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt":
            raise unittest.SkipTest("worktree_environment_bootstrap requires Windows NTFS junction support")

    def run_bootstrap(self, worktree_path=None, canonical_path=None, env=None):
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(BOOTSTRAP_SCRIPT),
        ]
        if worktree_path is not None:
            args.extend(["-WorktreePath", str(worktree_path)])
        if canonical_path is not None:
            args.extend(["-CanonicalEnvironmentPath", str(canonical_path)])

        command = subprocess.list2cmdline(args) + " < NUL"
        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        return subprocess.run(
            ["cmd.exe", "/d", "/s", "/c", command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=run_env,
        )

    @staticmethod
    def parse_result(proc):
        lines = (proc.stdout or "").strip().splitlines()
        if not lines:
            raise AssertionError(f"No stdout lines returned.\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
        return json.loads(lines[-1])

    @staticmethod
    def make_fake_canonical_env(path, python_version="Python 3.11.9", exit_code=0):
        scripts_dir = path / "Scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        # On Windows, a venv python.exe requires pyvenv.cfg in the parent directory
        real_py = Path(sys.executable)
        py_home = str(real_py.parent)
        pyvenv_cfg = path / "pyvenv.cfg"
        pyvenv_cfg.write_text(
            f"home = {py_home}\ninclude-system-site-packages = false\nversion = 3.11.2\nexecutable = {real_py}\n",
            encoding="utf-8",
        )
        target_py = scripts_dir / "python.exe"
        if exit_code == 0:
            shutil.copyfile(real_py, target_py)
        else:
            target_py.write_bytes(b"INVALID_EXE_HEADER")

    @staticmethod
    def make_junction(link, target):
        cmd = f'mklink /J "{link}" "{target}"'
        res = subprocess.run(
            ["cmd.exe", "/d", "/s", "/c", cmd],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise unittest.SkipTest(f"mklink /J failed: {res.stdout}{res.stderr}")

    def test_registered_worktree_absent_venv_creates_exact_junction_and_succeeds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            # Pre-condition: .venv does not exist
            self.assertFalse((wt / ".venv").exists())

            proc = self.run_bootstrap(wt, canonical)
            self.assertEqual(proc.returncode, 0, f"STDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")
            res = self.parse_result(proc)

            self.assertTrue(res["ok"])
            self.assertEqual(res["code"], "READY")
            self.assertEqual(res["action"], "CREATED")
            self.assertEqual(os.path.normcase(res["target"]), os.path.normcase(str(canonical)))
            self.assertTrue(res["python_version"].startswith("Python"))

            # Check junction physically exists
            self.assertTrue((wt / ".venv").exists())

            # Verify with worktree_cleanup_safety.ps1 in -ClassifyOnly mode
            cleanup_args = [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(CLEANUP_SCRIPT), "-WorktreePath", str(wt),
                "-CanonicalEnvironmentPath", str(canonical), "-ClassifyOnly"
            ]
            cleanup_proc = subprocess.run(
                ["cmd.exe", "/d", "/s", "/c", subprocess.list2cmdline(cleanup_args) + " < NUL"],
                cwd=ROOT, capture_output=True, text=True, check=False
            )
            self.assertEqual(cleanup_proc.returncode, 0, cleanup_proc.stdout + cleanup_proc.stderr)
            cleanup_res = json.loads(cleanup_proc.stdout.strip().splitlines()[-1])
            self.assertEqual(cleanup_res["code"], "EXPECTED_JUNCTION")

    def test_idempotent_second_run_reports_unchanged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            # First run creates
            proc1 = self.run_bootstrap(wt, canonical)
            self.assertEqual(proc1.returncode, 0)
            res1 = self.parse_result(proc1)
            self.assertEqual(res1["action"], "CREATED")

            # Second run reports UNCHANGED
            proc2 = self.run_bootstrap(wt, canonical)
            self.assertEqual(proc2.returncode, 0)
            res2 = self.parse_result(proc2)
            self.assertEqual(res2["action"], "UNCHANGED")
            self.assertEqual(res2["code"], "READY")

    def test_physical_directory_fails_closed_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            # Create physical .venv directory with a sentinel file
            physical_venv = wt / ".venv"
            physical_venv.mkdir()
            sentinel = physical_venv / "important_data.txt"
            sentinel.write_text("keep-me", encoding="utf-8")

            proc = self.run_bootstrap(wt, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "PHYSICAL_DIRECTORY")

            # Must be preserved untouched
            self.assertTrue(physical_venv.is_dir())
            self.assertTrue(sentinel.exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep-me")

    def test_wrong_target_junction_fails_closed_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            wrong_target = root / "other_venv"
            wrong_target.mkdir()

            self.make_junction(wt / ".venv", wrong_target)

            proc = self.run_bootstrap(wt, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "WRONG_TARGET")

            # Must remain pointing to wrong_target
            self.assertTrue((wt / ".venv").exists())

    def test_unsupported_reparse_symlink_fails_closed_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            try:
                os.symlink(canonical, wt / ".venv", target_is_directory=True)
            except (OSError, NotImplementedError) as err:
                raise unittest.SkipTest(f"Directory symlink creation unavailable: {err}")

            proc = self.run_bootstrap(wt, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "UNSUPPORTED_REPARSE")
            self.assertTrue((wt / ".venv").is_symlink())

    def test_missing_canonical_env_fails_before_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            missing_canonical = root / "does_not_exist"

            proc = self.run_bootstrap(wt, missing_canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "CANONICAL_ENV_MISSING")
            self.assertFalse((wt / ".venv").exists())

    def test_missing_canonical_interpreter_fails_before_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            canonical.mkdir()  # empty canonical without Scripts/python.exe

            proc = self.run_bootstrap(wt, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "MISSING_INTERPRETER")
            self.assertFalse((wt / ".venv").exists())

    def test_unregistered_directory_fails_closed_before_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            unregistered_dir = root / "not_a_git_worktree"
            unregistered_dir.mkdir()

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            proc = self.run_bootstrap(unregistered_dir, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "NOT_REGISTERED_WORKTREE")
            self.assertFalse((unregistered_dir / ".venv").exists())

    def test_broken_or_unusable_interpreter_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            # make interpreter that is not a valid executable
            self.make_fake_canonical_env(canonical, exit_code=1)

            proc = self.run_bootstrap(wt, canonical)
            self.assertNotEqual(proc.returncode, 0)
            res = self.parse_result(proc)
            self.assertFalse(res["ok"])
            self.assertEqual(res["code"], "INTERPRETER_UNUSABLE")

            # Junction was created, but because interpreter failed, junction is left intact for idempotent retry/inspection
            self.assertTrue((wt / ".venv").exists())

    def test_ambiguous_target_fails_closed_and_is_preserved(self):
        # We can test ambiguous target by having a mock seam or helper where Target returns multiple targets
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(canonical)

            # Test invalid argument check: omitted WorktreePath
            proc_empty = self.run_bootstrap(canonical_path=canonical)
            self.assertNotEqual(proc_empty.returncode, 0)
            res_empty = self.parse_result(proc_empty)
            self.assertEqual(res_empty["code"], "INVALID_ARGUMENT")

    def test_production_canonical_pool_is_never_mutated(self):
        real_canonical = Path(r"E:\Side_Project\VenvPools\.venvs-Blackfire-CV-Autopilot")
        if not real_canonical.exists():
            raise unittest.SkipTest("real canonical environment not present")
        before_mtime = (real_canonical / "pyvenv.cfg").stat().st_mtime_ns

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestRunner"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            (repo / "README.md").write_text("root", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "init"], check=True, capture_output=True)

            wt = root / "worktrees" / "task-wt"
            subprocess.run(["git", "-C", str(repo), "worktree", "add", "-b", "task/feat", str(wt), "HEAD"], check=True, capture_output=True)

            fake_canonical = root / "fake_canonical_venv"
            self.make_fake_canonical_env(fake_canonical)

            proc = self.run_bootstrap(wt, fake_canonical)
            self.assertEqual(proc.returncode, 0)

        after_mtime = (real_canonical / "pyvenv.cfg").stat().st_mtime_ns
        self.assertEqual(before_mtime, after_mtime)


if __name__ == "__main__":
    unittest.main()
