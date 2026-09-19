import pytest
import subprocess
import unittest
from pathlib import Path

pytestmark = pytest.mark.ai_workflow


class StructuredReviewProbeDeterministicTests(unittest.TestCase):
    def test_node_probe_contract(self):
        repo_root = Path(__file__).resolve().parents[1]
        test_file = repo_root / "tests" / "workflow_scripts" / "opencode_structured_review_probe.test.mjs"
        result = subprocess.run(
            ["node", "--test", str(test_file)],
            cwd=repo_root,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
