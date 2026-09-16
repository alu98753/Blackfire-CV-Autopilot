import json
import subprocess
import unittest
from pathlib import Path


class WorkflowScriptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]

    def test_gate_uses_structured_adapter_and_keeps_external_states(self):
        text = (self.root / "scripts" / "ai_gate.ps1").read_text(encoding="utf-8-sig")
        self.assertIn("opencode_structured_review.mjs", text)
        self.assertIn("VALID_PASS", text)
        self.assertIn("VALID_BLOCK", text)
        self.assertIn("VERIFICATION_UNAVAILABLE", text)
        self.assertNotIn("Get-FinalAssistantMessageFromStructuredJson", text)
        self.assertNotIn("Get-CanonicalReviewPayload", text)
        self.assertNotIn("Test-ReviewVerdictStructure", text)

    def test_adapter_validates_exact_machine_contract(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { validateSchema, validateSemantics } from "
            f"'{probe.as_uri()}';"
            "console.log(JSON.stringify(["
            "validateSchema({verdict:'PASS',blocking_findings:0,report_markdown:'ok'}),"
            "validateSchema({verdict:'PASS',blocking_findings:1,report_markdown:'bad'}),"
            "validateSemantics({verdict:'BLOCK',blocking_findings:0,report_markdown:'bad'})]));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        values = json.loads(result.stdout)
        self.assertTrue(values[0]["valid"])
        self.assertTrue(values[1]["valid"])
        self.assertFalse(values[2]["valid"])

    def test_lifecycle_event_order_is_not_synthesized_from_prompt_parts(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { lifecycleCompletionBoundary } from "
            f"'{probe.as_uri()}';"
            "const tool=(name,messageID='m2',sessionID='s',status='completed')=>({type:'tool',messageID,sessionID,tool:name,state:{status}});"
            "const end=(messageID='m2',sessionID='s')=>({type:'step-finish',messageID,sessionID,reason:'tool-calls'});"
            "const prompt=[{messageID:'m2',type:'tool',tool:'StructuredOutput',state:{status:'completed'}}];"
            "const structured={verdict:'PASS',blocking_findings:0,report_markdown:'ok'};"
            "console.log(JSON.stringify(["
            "lifecycleCompletionBoundary({events:[tool('read','m1'),tool('StructuredOutput'),end()],sessionID:'s',messageID:'m2',promptParts:prompt,structured}),"
            "lifecycleCompletionBoundary({events:[tool('StructuredOutput','m1'),end('m1')],sessionID:'s',messageID:'m2',promptParts:prompt,structured}),"
            "lifecycleCompletionBoundary({events:[tool('StructuredOutput'),end('m1')],sessionID:'s',messageID:'m2',promptParts:prompt,structured}),"
            "lifecycleCompletionBoundary({events:[tool('read','m1',null),tool('StructuredOutput'),end()],sessionID:'s',messageID:'m2',promptParts:prompt,structured}),"
            "lifecycleCompletionBoundary({events:[tool('read','m1'),tool('StructuredOutput'),end()],sessionID:'s',messageID:'m2',promptParts:prompt,structured})]));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        values = json.loads(result.stdout)
        self.assertTrue(values[0]["complete"])
        self.assertTrue(values[0]["lifecycle"]["grounding_before_structured"])
        self.assertFalse(values[1]["complete"])
        self.assertFalse(values[2]["complete"])
        self.assertFalse(values[3]["complete"])
        self.assertTrue(values[4]["complete"])

    def test_windows_workflow_harness(self):
        harness = self.root / "tests" / "workflow_scripts" / "Invoke-WorkflowScriptHarness.ps1"
        command = f'cmd.exe /d /s /c "chcp 65001 >nul && powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{harness}" < NUL"'
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, shell=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Workflow script harness:", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
