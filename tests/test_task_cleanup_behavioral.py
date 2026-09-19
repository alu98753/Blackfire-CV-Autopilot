import pytest
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

pytestmark = pytest.mark.ai_workflow

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "task_cleanup.ps1"

FAKE_GIT = r'''
import json, os, pathlib, sys
state = pathlib.Path(os.environ["FAKE_STATE"])
data = json.loads(state.read_text())
args = sys.argv[1:]
data.setdefault("calls", []).append({"cwd": os.getcwd(), "args": args})
if args[-2:] == ["status", "--porcelain"]:
    if os.environ.get("FAKE_DIRTY") == "1" and data["task"] in args: print(" M dirty.txt")
elif args[-3:] == ["worktree", "list", "--porcelain"]:
    if data.get("removed") and not data.get("post_ownership"): data["task_present"] = False
    for path, branch in [(data["main"], "main"), (data["task"], data["branch"])]:
        if path == data["task"] and not data.get("task_present", True): continue
        print(f"worktree {path}\nHEAD deadbeef\nbranch refs/heads/{branch}\n")
elif args[-2:] == ["fetch", "origin"]:
    if os.environ.get("FAKE_FETCH_STDERR") == "1": print("fetch progress", file=sys.stderr)
    if os.environ.get("FAKE_FETCH_FAIL") == "1": state.write_text(json.dumps(data)); sys.exit(7)
elif "show-ref" in args:
    if os.environ.get("FAKE_LOCAL_REF_FAIL") == "1": sys.exit(1)
elif "merge-base" in args:
    if os.environ.get("FAKE_UNMERGED") == "1": sys.exit(1)
elif "worktree" in args and "remove" in args:
    data["removed"] = True
    if os.environ.get("FAKE_REMOVE_FAIL") == "1": state.write_text(json.dumps(data)); sys.exit(1)
elif args[:2] == ["branch", "-d"]:
    data["local_deleted"] = True
    if os.environ.get("FAKE_LOCAL_DELETE_FAIL") == "1": state.write_text(json.dumps(data)); sys.exit(1)
elif args[:3] == ["push", "origin", "--delete"]:
    data["remote_deleted"] = True
    if os.environ.get("FAKE_REMOTE_STDERR") == "1": print("To https://example.invalid/repo.git", file=sys.stderr)
    if os.environ.get("FAKE_REMOTE_FAIL") == "1": print("fatal: remote failure", file=sys.stderr)
    if os.environ.get("FAKE_REMOTE_FAIL") == "1": state.write_text(json.dumps(data)); sys.exit(1)
state.write_text(json.dumps(data))
'''

FAKE_HELPER = r'''
$mode = $env:FAKE_HELPER_MODE
if ($mode -eq 'malformed') { Write-Output 'not-json'; exit 0 }
if ($mode -eq 'multiple') { Write-Output '{"code":"DETACHED"}'; Write-Output '{"code":"DETACHED"}'; exit 0 }
$code = if ($mode -eq 'wrong') { 'WRONG_TARGET' } else { 'DETACHED' }
Write-Output (ConvertTo-Json ([ordered]@{ code = $code; ok = ($code -eq 'DETACHED') }) -Compress)
'''

class TaskCleanupBehavioralTests(unittest.TestCase):
    def run_wrapper(self, *, cwd_kind="other", delete_remote=False, topology_main_matches=True, **flags):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            canonical = root / "BlackfireCrusade_tool"
            main = canonical if topology_main_matches else root / "other-main"
            task, other = root / "task", root / "other"
            for path in (canonical, main, task, other): path.mkdir(exist_ok=True)
            common_dir = canonical / ".git"; common_dir.mkdir()
            state = root / "state.json"
            state.write_text(json.dumps({"main": str(main), "task": str(task), "branch": "task/fixture", "task_present": True, "post_ownership": bool(flags.get("post_ownership"))}), encoding="utf-8")
            fake_py = root / "fake_git.py"; fake_py.write_text(FAKE_GIT, encoding="utf-8")
            fake_cmd = root / "fake_git.cmd"; fake_cmd.write_text(f'@"{sys.executable}" "{fake_py}" %*\n', encoding="utf-8")
            helper = root / "helper.ps1"; helper.write_text(FAKE_HELPER, encoding="utf-8")
            cwd = {"main": main, "task": task, "task-child": task / "scripts", "other": other}[cwd_kind]
            if cwd_kind == "task-child": cwd.mkdir()
            env = os.environ.copy()
            env.update({"TASK_CLEANUP_GIT_EXE": str(fake_cmd), "TASK_CLEANUP_HELPER": str(helper), "TASK_CLEANUP_COMMON_DIR_OVERRIDE": str(common_dir), "FAKE_STATE": str(state)})
            for key, value in flags.items(): env["FAKE_" + key.upper()] = "1" if value is True else str(value)
            args = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WRAPPER), "-Task", "task"]
            if delete_remote: args.append("-DeleteRemoteBranch")
            command = subprocess.list2cmdline(args) + " < NUL"
            return subprocess.run(["cmd.exe", "/d", "/s", "/c", command], cwd=cwd, env=env, capture_output=True, text=True, timeout=30), json.loads(state.read_text())

    def test_happy_local_and_explicit_remote_ordering(self):
        result, state = self.run_wrapper()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(state.get("remote_deleted", False))
        result, state = self.run_wrapper(delete_remote=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state["remote_deleted"])
        names = [" ".join(c["args"]) for c in state["calls"]]
        self.assertLess(next(i for i, x in enumerate(names) if x.startswith("branch -d")), next(i for i, x in enumerate(names) if x.startswith("push origin --delete")))

    def test_successful_remote_delete_with_stderr_is_success(self):
        result, state = self.run_wrapper(delete_remote=True, remote_stderr=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state["remote_deleted"])
        self.assertIn("TASK CLEANUP SUCCEEDED", result.stdout)

    def test_failed_remote_delete_preserves_stderr_and_local_success(self):
        result, state = self.run_wrapper(delete_remote=True, remote_fail=True)
        self.assertEqual(result.returncode, 2)
        self.assertTrue(state["local_deleted"])
        self.assertTrue(state["remote_deleted"])
        self.assertIn("LOCAL", result.stderr)
        self.assertIn("SUCCEEDED", result.stderr)
        self.assertIn("fatal: remote failure", result.stderr)

    def test_successful_fetch_with_stderr_continues(self):
        result, state = self.run_wrapper(fetch_stderr=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(state["local_deleted"])

    def test_non_main_launch_and_cwd_containment_protection(self):
        result, state = self.run_wrapper(cwd_kind="other")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(os.path.normcase(c["cwd"]) == os.path.normcase(state["main"]) for c in state["calls"] if "remove" in c["args"]))
        self.assertTrue(all(os.path.normcase(c["cwd"]) != os.path.normcase(str(ROOT)) for c in state["calls"] if "remove" in c["args"]))
        for cwd_kind in ("task", "task-child"):
            result, state = self.run_wrapper(cwd_kind=cwd_kind)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(state.get("removed", False))

    def test_main_branch_at_noncanonical_path_fails_closed(self):
        result, state = self.run_wrapper(topology_main_matches=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(state.get("removed", False))
        self.assertFalse(state.get("local_deleted", False))
        self.assertFalse(state.get("remote_deleted", False))

    def test_failures_stop_destructive_sequence(self):
        cases = (("dirty", {"dirty": True}), ("unmerged", {"unmerged": True}), ("fetch", {"fetch_fail": True}), ("malformed", {"helper_mode": "malformed"}), ("multiple", {"helper_mode": "multiple"}), ("wrong", {"helper_mode": "wrong"}), ("remove", {"remove_fail": True}), ("post", {"post_ownership": True}), ("local", {"local_delete_fail": True}))
        for label, flags in cases:
            result, state = self.run_wrapper(delete_remote=True, **flags)
            self.assertNotEqual(result.returncode, 0, label)
            calls = [" ".join(c["args"]) for c in state["calls"]]
            if label in ("dirty", "unmerged", "fetch", "malformed", "multiple", "wrong"):
                self.assertFalse(any("worktree remove" in x for x in calls), label)
            if label in ("remove", "post", "local"):
                self.assertFalse(state.get("remote_deleted", False))

if __name__ == "__main__":
    unittest.main()
