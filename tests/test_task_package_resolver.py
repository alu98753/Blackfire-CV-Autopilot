import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "scripts" / "task_package_resolver.ps1"


class TaskPackageResolverTests(unittest.TestCase):
    def run_ps(self, code, cwd):
        return subprocess.run(["pwsh", "-NoProfile", "-File", "-", code], cwd=cwd, text=True, capture_output=True)

    def test_contract_has_canonical_active_path_and_classifications(self):
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
