import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "task_package_resolver.ps1"


class TaskPackageResolverTests(unittest.TestCase):
    def run_ps(self, code, cwd):
        return subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", code], cwd=cwd, text=True, capture_output=True)

    def test_real_fixture_classifications(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            active = root / "docs" / "tasks" / "active"
            archive = root / "docs" / "tasks" / "archive" / "2026"
            (active / "live").mkdir(parents=True)
            (active / "live" / "SPEC.md").write_text("# live", encoding="utf-8")
            (active / "live" / "task.json").write_text('{"id":"live"}', encoding="utf-8")
            (active / "broken").mkdir(parents=True)
            (active / "broken" / "task.json").write_text('{"id":"wrong"}', encoding="utf-8")
            (archive / "old").mkdir(parents=True)
            (archive / "old" / "SPEC.md").write_text("# old", encoding="utf-8")
            (archive / "old" / "task.json").write_text('{"id":"old"}', encoding="utf-8")
            (archive / "ambiguous").mkdir(parents=True)
            (root / "docs" / "tasks" / "archive" / "2025" / "ambiguous").mkdir(parents=True)
            code = ". '{0}'; 'live','missing','old','broken','ambiguous' | % {{ (Resolve-TaskPackage -Task $_ -RepoRoot '{1}').Classification }}".format(RESOLVER, root)
            result = self.run_ps(code, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.split(), ["ACTIVE", "MISSING", "ARCHIVED", "MALFORMED", "AMBIGUOUS_ARCHIVE"])

    def test_contract_has_canonical_active_path_and_resolver_outcomes(self):
        text = RESOLVER.read_text(encoding="utf-8")
        self.assertIn('docs/tasks/active/$Task', text)
        for classification in ("ACTIVE", "ARCHIVED", "MISSING", "MALFORMED", "AMBIGUOUS_ARCHIVE"):
            self.assertIn(classification, text)

    def test_active_resolution_is_required_by_workflow_callers(self):
        for name in ("task_start.ps1", "ai_scout.ps1", "ai_gate.ps1"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("task_package_resolver.ps1", text)
            self.assertIn("Get-TaskPackageGitPath", text) if name == "task_start.ps1" else self.assertIn("Resolve-TaskPackage", text)


if __name__ == "__main__":
    unittest.main()
