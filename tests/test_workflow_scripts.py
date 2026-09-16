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

    def test_lifecycle_authority_uses_prompt_identity_and_grounding_only(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { qualifyAttempt } from "
            f"'{probe.as_uri()}';"
            "const tool=(name,messageID='m2',sessionID='s',status='completed')=>({type:'tool',messageID,sessionID,tool:name,state:{status}});"
            "const structured={verdict:'PASS',blocking_findings:0,report_markdown:'ok'};"
            "console.log(JSON.stringify(["
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',structured}}),"
            "qualifyAttempt({events:[tool('StructuredOutput','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',structured}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'wrong',info:{id:'m2',sessionID:'s',structured}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',structured}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s'}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',structured:{verdict:'BLOCK',blocking_findings:0,report_markdown:'bad'}}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',finish:'tool-calls',structured}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',structured:{verdict:'MAYBE',blocking_findings:0,report_markdown:'bad'}}}),"
            "qualifyAttempt({events:[tool('read','m1')],sessionID:'s',info:{id:'m2',sessionID:'s',structured:{verdict:'BLOCK',blocking_findings:1,report_markdown:'bad'}}})]));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        values = json.loads(result.stdout)
        self.assertEqual(values[0]["classification"], "VALID_PASS")
        self.assertEqual(values[1]["classification"], "GROUNDING_FAILED")
        self.assertEqual(values[2]["classification"], "STRUCTURED_TRANSPORT_FAILED")
        self.assertEqual(values[3]["classification"], "STRUCTURED_TRANSPORT_FAILED")
        self.assertEqual(values[4]["classification"], "STRUCTURED_OUTPUT_MISSING")
        self.assertEqual(values[5]["classification"], "SEMANTIC_CONTRADICTION")
        self.assertEqual(values[6]["classification"], "VALID_PASS")
        self.assertEqual(values[7]["classification"], "SCHEMA_INVALID")
        self.assertEqual(values[8]["classification"], "VALID_BLOCK")

    def test_adapter_client_throw_on_error_is_configuration_not_prompt_input(self):
        text = (self.root / "scripts" / "opencode_structured_review.mjs").read_text(encoding="utf-8")
        self.assertIn("createOpencodeClient({ baseUrl: await waitForServer(server), throwOnError: true })", text)
        self.assertNotIn("session.create({ directory, throwOnError", text)
        prompt_options = text.split("session.prompt({", 1)[1].split("});", 1)[0]
        self.assertNotIn("throwOnError", prompt_options)

    def test_windows_opencode_launcher_uses_cmd_shim_safely(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { buildServerLaunch } from "
            f"'{probe.as_uri()}';"
            "console.log(JSON.stringify([buildServerLaunch('win32','cmd.exe'), buildServerLaunch('linux')]));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        windows, unix = json.loads(result.stdout)
        self.assertEqual(windows["executable"], "cmd.exe")
        self.assertEqual(windows["args"][:3], ["/d", "/s", "/c"])
        self.assertIn("opencode serve", windows["args"][3])
        self.assertIn("< NUL", windows["args"][3])
        self.assertEqual(unix["executable"], "opencode")
        self.assertNotIn("AppData", windows["args"][3])

    def test_event_consumer_settlement_is_bounded_and_subprocess_exits(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { settleEventConsumer } from "
            f"'{probe.as_uri()}';"
            "const controller=new AbortController();"
            "const safe=await settleEventConsumer({consumer:Promise.resolve(),stream:{return:async()=>({done:true})},abortController:controller,timeoutMs:25});"
            "const unsafe=await settleEventConsumer({consumer:new Promise(()=>{}),stream:{return:async()=>({done:true})},abortController:new AbortController(),timeoutMs:25});"
            "console.log(JSON.stringify({safe,unsafe,aborted:controller.signal.aborted}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertTrue(value["safe"])
        self.assertFalse(value["unsafe"])
        self.assertTrue(value["aborted"])

    def test_windows_process_tree_cleanup_closes_owned_pipes(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { spawn } from 'node:child_process';"
            "import { stopServer } from "
            f"'{probe.as_uri()}';"
            "const server=spawn('cmd.exe',['/d','/s','/c','node -e \"process.stdout.write(\\'live\\');setInterval(()=>{},1000)\"'],{stdio:['ignore','pipe','pipe'],windowsHide:true});"
            "await new Promise(r=>setTimeout(r,100));"
            "console.log(JSON.stringify(await stopServer(server,{platform:'win32',timeoutMs:2000})));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=10, check=True)
        value = json.loads(result.stdout)
        self.assertTrue(value["safe"])
        self.assertTrue(value["tree_termination_confirmed"])
        self.assertTrue(value["stdout_closed"])
        self.assertTrue(value["stderr_closed"])

    def test_windows_workflow_harness(self):
        harness = self.root / "tests" / "workflow_scripts" / "Invoke-WorkflowScriptHarness.ps1"
        command = f'cmd.exe /d /s /c "chcp 65001 >nul && powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{harness}" < NUL"'
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, shell=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Workflow script harness:", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
