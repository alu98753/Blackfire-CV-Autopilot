import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_START_SCRIPT = ROOT / "scripts" / "task_start.ps1"


class TaskStartBehavioralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt":
            raise unittest.SkipTest("task_start.ps1 requires Windows execution")

    def run_task_start(self, task="test-task", branch=None, env=None, cwd=ROOT):
        # Invoke powershell directly without an extra cmd.exe list2cmdline stripping layer
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(TASK_START_SCRIPT),
        ]
        if task is not None:
            args.extend(["-Task", str(task)])
        if branch is not None:
            args.extend(["-Branch", str(branch)])

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        return subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=run_env,
        )

    @staticmethod
    def parse_result(proc):
        lines = [line for line in (proc.stdout or "").splitlines() if line.strip()]
        if len(lines) != 1:
            raise AssertionError(f"Expected exactly one non-empty stdout line, got {len(lines)}:\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
        return json.loads(lines[0])

    @staticmethod
    def run_git(cwd, *args):
        res = subprocess.run(
            ["git", "-C", str(cwd)] + list(args),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Git command failed: git {' '.join(args)}\nstderr: {res.stderr}\nstdout: {res.stdout}")
        return res

    def make_fake_python_helper(self, path, code="READY", action="CREATED", python_version="Python 3.11.9", exit_code=0, extra_lines=0, malformed=False):
        lines = []
        if malformed:
            lines.append("not-json-content")
        else:
            payload = {
                "ok": (code == "READY"),
                "code": code,
                "message": f"Helper {code}",
                "action": action,
                "python_version": python_version,
            }
            lines.append(json.dumps(payload))
            for i in range(extra_lines):
                lines.append(json.dumps({"extra": i}))

        script_content = "\n".join([f"[Console]::Out.WriteLine('{line}')" for line in lines])
        script_content += f"\nexit {exit_code}\n"
        path.write_text(script_content, encoding="utf-8")

    def create_git_fixture(self, temp_dir, task_id="test-task", branch_name=None, stale_task_branch=False, missing_spec=False, mismatched_task_id=False):
        if branch_name is None:
            branch_name = task_id
        base = Path(temp_dir)
        origin_dir = base / "origin.git"
        main_dir = base / "BlackfireCrusade_tool"
        worktrees_dir = base / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)

        # 1. Bare remote origin
        self.run_git(base, "init", "--bare", str(origin_dir))

        # 2. Main clone
        self.run_git(base, "clone", str(origin_dir), str(main_dir))
        self.run_git(main_dir, "config", "user.name", "Test User")
        self.run_git(main_dir, "config", "user.email", "test@example.com")
        self.run_git(main_dir, "checkout", "-b", "main")

        # Initial commit on main
        init_file = main_dir / "README.md"
        init_file.write_text("# Test Repo\n", encoding="utf-8")
        self.run_git(main_dir, "add", "README.md")
        self.run_git(main_dir, "commit", "-m", "Initial commit on main")
        self.run_git(main_dir, "push", "-u", "origin", "main")

        # 3. Create task branch from main
        self.run_git(main_dir, "checkout", "-b", branch_name)
        task_docs_dir = main_dir / "docs" / "tasks" / task_id
        task_docs_dir.mkdir(parents=True, exist_ok=True)

        if not missing_spec:
            (task_docs_dir / "SPEC.md").write_text("# Test Spec\n", encoding="utf-8")

        task_id_in_json = "mismatched-id" if mismatched_task_id else task_id
        (task_docs_dir / "task.json").write_text(json.dumps({"id": task_id_in_json}), encoding="utf-8")

        self.run_git(main_dir, "add", "docs")
        self.run_git(main_dir, "commit", "-m", f"Add task artifacts for {task_id}")
        self.run_git(main_dir, "push", "-u", "origin", branch_name)

        # Switch back to main
        self.run_git(main_dir, "checkout", "main")

        if stale_task_branch:
            # Advance main on origin so task branch becomes stale
            adv_file = main_dir / "advance.txt"
            adv_file.write_text("advance main\n", encoding="utf-8")
            self.run_git(main_dir, "add", "advance.txt")
            self.run_git(main_dir, "commit", "-m", "Advance main to make task branch stale")
            self.run_git(main_dir, "push", "origin", "main")

        # Delete local task branch in main clone so local state is clean
        self.run_git(main_dir, "branch", "-D", branch_name)

        # Fake python helper
        fake_helper = base / "fake_bootstrap.ps1"
        self.make_fake_python_helper(fake_helper)

        return {
            "origin": origin_dir,
            "main": main_dir,
            "worktrees_root": worktrees_dir,
            "fake_helper": fake_helper,
        }

    def test_argument_validation_fails_with_invalid_argument(self):
        proc = self.run_task_start(task="INVALID_UPPERCASE")
        self.assertNotEqual(proc.returncode, 0)
        data = self.parse_result(proc)
        self.assertFalse(data["ok"])
        self.assertEqual(data["code"], "INVALID_ARGUMENT")

        proc2 = self.run_task_start(task="valid-task", branch="bad branch with spaces")
        self.assertNotEqual(proc2.returncode, 0)
        data2 = self.parse_result(proc2)
        self.assertFalse(data2["ok"])
        self.assertEqual(data2["code"], "INVALID_ARGUMENT")

    def test_canonical_main_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            missing_main = Path(temp) / "non_existent_main"
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(missing_main),
            }
            proc = self.run_task_start(task="test-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "CANONICAL_MAIN_MISSING")

    def test_happy_path_creates_canonical_worktree_and_returns_task_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="my-feature")
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="my-feature", env=env)
            self.assertEqual(proc.returncode, 0, f"stdout: {proc.stdout}\nstderr: {proc.stderr}")
            data = self.parse_result(proc)
            self.assertTrue(data["ok"])
            self.assertEqual(data["code"], "TASK_READY")
            self.assertEqual(data["action"], "CREATED")
            self.assertEqual(data["python_action"], "CREATED")
            self.assertEqual(data["python_version"], "Python 3.11.9")
            self.assertEqual(data["task"], "my-feature")
            self.assertEqual(data["branch"], "my-feature")

            expected_worktree = f["worktrees_root"] / "my-feature"
            self.assertTrue(expected_worktree.exists())
            self.assertTrue((expected_worktree / "docs" / "tasks" / "my-feature" / "SPEC.md").exists())

    def test_canonical_main_behind_fast_forwards_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="ff-task")
            # Make main behind origin/main locally by resetting main back 1 commit
            # First advance origin/main via temporary clone
            tmp_clone = Path(temp) / "tmp_clone"
            self.run_git(Path(temp), "clone", str(f["origin"]), str(tmp_clone))
            self.run_git(tmp_clone, "config", "user.name", "Test User")
            self.run_git(tmp_clone, "config", "user.email", "test@example.com")
            self.run_git(tmp_clone, "checkout", "main")
            (tmp_clone / "new_on_main.txt").write_text("main update\n", encoding="utf-8")
            self.run_git(tmp_clone, "add", "new_on_main.txt")
            self.run_git(tmp_clone, "commit", "-m", "Advance origin/main")
            self.run_git(tmp_clone, "push", "origin", "main")

            # Update task branch so it contains the new origin/main commit as ancestor
            self.run_git(tmp_clone, "checkout", "ff-task")
            self.run_git(tmp_clone, "rebase", "main")
            self.run_git(tmp_clone, "push", "--force", "origin", "ff-task")

            # Now f["main"] is behind origin/main
            main_before = self.run_git(f["main"], "rev-parse", "HEAD").stdout.strip()
            origin_main_now = self.run_git(tmp_clone, "rev-parse", "origin/main").stdout.strip()
            self.assertNotEqual(main_before, origin_main_now)

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="ff-task", env=env)
            self.assertEqual(proc.returncode, 0, f"stdout: {proc.stdout}\nstderr: {proc.stderr}")
            data = self.parse_result(proc)
            self.assertTrue(data["ok"])
            self.assertEqual(data["code"], "TASK_READY")

            main_after = self.run_git(f["main"], "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(main_after, origin_main_now)

    def test_canonical_main_dirty_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="dirty-main-task")
            (f["main"] / "untracked.txt").write_text("dirty\n", encoding="utf-8")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="dirty-main-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "CANONICAL_MAIN_DIRTY")
            # Verify no task worktree created
            self.assertFalse((f["worktrees_root"] / "dirty-main-task").exists())

    def test_canonical_main_wrong_branch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="wrong-branch-task")
            self.run_git(f["main"], "checkout", "-b", "other-branch")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="wrong-branch-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "CANONICAL_MAIN_WRONG_BRANCH")

    def test_canonical_main_diverged_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="diverged-main-task")
            # Advance remote origin/main via temporary clone
            tmp_clone = Path(temp) / "tmp_clone"
            self.run_git(Path(temp), "clone", str(f["origin"]), str(tmp_clone))
            self.run_git(tmp_clone, "config", "user.name", "Test User")
            self.run_git(tmp_clone, "config", "user.email", "test@example.com")
            self.run_git(tmp_clone, "checkout", "main")
            (tmp_clone / "remote_change.txt").write_text("remote\n", encoding="utf-8")
            self.run_git(tmp_clone, "add", "remote_change.txt")
            self.run_git(tmp_clone, "commit", "-m", "Remote commit on main")
            self.run_git(tmp_clone, "push", "origin", "main")

            # Create local unpushed commit on canonical main
            (f["main"] / "local_change.txt").write_text("local\n", encoding="utf-8")
            self.run_git(f["main"], "add", "local_change.txt")
            self.run_git(f["main"], "commit", "-m", "Local unpushed commit on main")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="diverged-main-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "CANONICAL_MAIN_DIVERGED")

    def test_missing_remote_task_branch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="existing-task")
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="non-existent-remote-branch", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "REMOTE_TASK_BRANCH_MISSING")

    def test_stale_task_branch_fails_closed_with_task_branch_stale_base(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="stale-task", stale_task_branch=True)
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="stale-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "TASK_BRANCH_STALE_BASE")

    def test_missing_remote_task_package_spec_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="pkg-missing", missing_spec=True)
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="pkg-missing", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "TASK_PACKAGE_MISSING")

    def test_mismatched_remote_task_json_id_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="mismatched-task", mismatched_task_id=True)
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="mismatched-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "TASK_PACKAGE_INVALID")

    def test_idempotent_reuse_of_existing_canonical_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="reuse-task")
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            # First run: CREATED
            proc1 = self.run_task_start(task="reuse-task", env=env)
            self.assertEqual(proc1.returncode, 0)
            data1 = self.parse_result(proc1)
            self.assertEqual(data1["action"], "CREATED")

            # Second run: REUSED
            proc2 = self.run_task_start(task="reuse-task", env=env)
            self.assertEqual(proc2.returncode, 0)
            data2 = self.parse_result(proc2)
            self.assertTrue(data2["ok"])
            self.assertEqual(data2["code"], "TASK_READY")
            self.assertEqual(data2["action"], "REUSED")

    def test_dirty_reused_worktree_fails_closed_and_preserves_wip(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="dirty-reuse-task")
            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc1 = self.run_task_start(task="dirty-reuse-task", env=env)
            self.assertEqual(proc1.returncode, 0)

            # Make task worktree dirty
            task_wt = f["worktrees_root"] / "dirty-reuse-task"
            dirty_file = task_wt / "wip.txt"
            dirty_file.write_text("work in progress\n", encoding="utf-8")

            proc2 = self.run_task_start(task="dirty-reuse-task", env=env)
            self.assertNotEqual(proc2.returncode, 0)
            data2 = self.parse_result(proc2)
            self.assertFalse(data2["ok"])
            self.assertEqual(data2["code"], "REUSED_TASK_WORKTREE_DIRTY")
            self.assertTrue(dirty_file.exists())

    def test_branch_owned_by_another_worktree_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="conflict-task")
            other_wt = Path(temp) / "other_wt"
            # Fetch remote branch in main clone first
            self.run_git(f["main"], "fetch", "origin")
            # Check out the branch in a different worktree
            self.run_git(f["main"], "worktree", "add", "-b", "conflict-task", str(other_wt), "origin/conflict-task")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="conflict-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "BRANCH_OWNED_ELSEWHERE")

    def test_canonical_path_exists_unregistered_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="unregistered-dir-task")
            target_path = f["worktrees_root"] / "unregistered-dir-task"
            target_path.mkdir(parents=True, exist_ok=True)
            (target_path / "some_stale_file.txt").write_text("residual", encoding="utf-8")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="unregistered-dir-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "WORKTREE_PATH_CONFLICT")
            self.assertTrue((target_path / "some_stale_file.txt").exists())

    def test_canonical_path_registered_to_wrong_branch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="wrong-reg-task")
            # Create another branch on origin via main clone
            self.run_git(f["main"], "checkout", "-b", "other-reg-branch")
            (f["main"] / "other.txt").write_text("other\n", encoding="utf-8")
            self.run_git(f["main"], "add", "other.txt")
            self.run_git(f["main"], "commit", "-m", "other branch commit")
            self.run_git(f["main"], "push", "origin", "other-reg-branch")
            self.run_git(f["main"], "checkout", "main")
            self.run_git(f["main"], "branch", "-D", "other-reg-branch")

            target_path = f["worktrees_root"] / "wrong-reg-task"
            self.run_git(f["main"], "worktree", "add", "-b", "other-reg-branch", str(target_path), "origin/other-reg-branch")

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="wrong-reg-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "WORKTREE_PATH_CONFLICT")

    def test_python_bootstrap_failure_preserves_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="py-fail-task")
            # Overwrite fake helper with exit code 15 CANONICAL_ENV_MISSING
            self.make_fake_python_helper(f["fake_helper"], code="CANONICAL_ENV_MISSING", exit_code=15)

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="py-fail-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "PYTHON_BOOTSTRAP_FAILED")

            # Worktree must be preserved!
            target_wt = f["worktrees_root"] / "py-fail-task"
            self.assertTrue(target_wt.exists())
            self.assertTrue((target_wt / "docs" / "tasks" / "py-fail-task" / "SPEC.md").exists())

    def test_python_bootstrap_malformed_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="py-malformed-task")
            self.make_fake_python_helper(f["fake_helper"], malformed=True, exit_code=0)

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="py-malformed-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "PYTHON_BOOTSTRAP_FAILED")

    def test_python_bootstrap_multiple_lines_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            f = self.create_git_fixture(temp, task_id="py-multiline-task")
            self.make_fake_python_helper(f["fake_helper"], extra_lines=2, exit_code=0)

            env = {
                "TASK_START_CANONICAL_MAIN_OVERRIDE": str(f["main"]),
                "TASK_START_WORKTREES_ROOT_OVERRIDE": str(f["worktrees_root"]),
                "TASK_START_PYTHON_HELPER": str(f["fake_helper"]),
            }
            proc = self.run_task_start(task="py-multiline-task", env=env)
            self.assertNotEqual(proc.returncode, 0)
            data = self.parse_result(proc)
            self.assertFalse(data["ok"])
            self.assertEqual(data["code"], "PYTHON_BOOTSTRAP_FAILED")


if __name__ == "__main__":
    unittest.main()
