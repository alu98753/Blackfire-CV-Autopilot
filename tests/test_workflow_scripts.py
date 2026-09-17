import json
import os
import subprocess
import tempfile
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
        self.assertIn("createOpencodeClient({ baseUrl, throwOnError: true, fetch: transport.fetch })", text)
        self.assertNotIn("session.create({ directory, throwOnError", text)
        prompt_options = text.split("session.prompt({", 1)[1].split("});", 1)[0]
        self.assertNotIn("throwOnError", prompt_options)

    def test_transport_diagnostic_attributes_nested_cause_and_redacts_bounds(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { transportDiagnostic } from "
            f"'{probe.as_uri()}';"
            "const cause=Object.assign(new Error('Bearer secret-value ' + 'x'.repeat(900)),{name:'SocketError',code:'ECONNRESET'});"
            "const error=Object.assign(new TypeError('fetch failed'),{cause});"
            "console.log(JSON.stringify(transportDiagnostic('session.prompt',error)));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        value = json.loads(result.stdout)
        self.assertEqual(value["operation"], "session.prompt")
        self.assertEqual(value["name"], "TypeError")
        self.assertEqual(value["message"], "fetch failed")
        self.assertEqual(value["cause_name"], "SocketError")
        self.assertEqual(value["cause_code"], "ECONNRESET")
        self.assertLessEqual(len(value["cause_message"]), 600)
        self.assertNotIn("secret-value", value["cause_message"])

    def test_bounded_operation_timeout_success_and_rejection(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { runBoundedOperation } from "
            f"'{probe.as_uri()}';"
            "const never=await runBoundedOperation('session.prompt',20,()=>new Promise(()=>{})).catch(error=>({name:error.name,operation:error.operation}));"
            "const success=await runBoundedOperation('session.create',50,async()=> 'ok');"
            "const rejected=await runBoundedOperation('event.subscribe',50,async()=>{const cause=Object.assign(new Error('reset'),{code:'ECONNRESET'});throw Object.assign(new TypeError('fetch failed'),{cause});}).catch(error=>({name:error.name,operation:error.operation,cause:error.cause.code}));"
            "console.log(JSON.stringify({never,success,rejected}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertEqual(value["never"], {"name": "TimeoutError", "operation": "session.prompt"})
        self.assertEqual(value["success"], "ok")
        self.assertEqual(value["rejected"], {"name": "TypeError", "operation": "event.subscribe", "cause": "ECONNRESET"})

    def test_reviewer_prompt_uses_repository_ai_execution_budget(self):
        text = (self.root / "scripts" / "opencode_structured_review.mjs").read_text(encoding="utf-8")
        self.assertIn("REVIEWER_AI_EXECUTION_DEADLINE_MS = 480_000", text)
        self.assertIn("runBoundedOperation(operation, REVIEWER_AI_EXECUTION_DEADLINE_MS", text)
        self.assertNotIn("runBoundedOperation(operation, 180000", text)

    def test_timeout_hierarchy_keeps_outer_gate_margin(self):
        gate = (self.root / "scripts" / "ai_gate.ps1").read_text(encoding="utf-8-sig")
        adapter = (self.root / "scripts" / "opencode_structured_review.mjs").read_text(encoding="utf-8")
        self.assertIn("[int]$ReviewTimeoutSeconds = 540", gate)
        self.assertIn("REVIEWER_AI_EXECUTION_DEADLINE_MS = 480_000", adapter)
        self.assertIn("REVIEWER_TRANSPORT_TIMEOUT_MS = 510_000", adapter)
        self.assertGreater(540, 510)
        self.assertGreater(510_000, 480_000)

    def test_reviewer_transport_uses_owned_dispatcher_and_bounded_cleanup(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { createReviewerTransport, closeReviewerTransport, REVIEWER_AI_EXECUTION_DEADLINE_MS, REVIEWER_TRANSPORT_TIMEOUT_MS } from "
            f"'{probe.as_uri()}';"
            "const calls=[]; class FakeAgent { constructor(options){this.options=options;this.closed=0;this.destroyed=0;} close(){this.closed++;return Promise.resolve();} destroy(){this.destroyed++;} }"
            "const transport=createReviewerTransport({AgentClass:FakeAgent,fetchImpl:(input,init)=>{calls.push({input,init});return Promise.resolve('ok');}});"
            "const controller=new AbortController(); await transport.fetch(new Request('http://127.0.0.1/'),{signal:controller.signal}); const safe=await closeReviewerTransport(transport,25);"
            "console.log(JSON.stringify({timeout:transport.agent.options.headersTimeout,bodyTimeout:transport.agent.options.bodyTimeout,reviewer:REVIEWER_AI_EXECUTION_DEADLINE_MS,dispatcher:calls[0].init.dispatcher===transport.agent,signal:calls[0].init.signal===controller.signal,safe,closed:transport.agent.closed,destroyed:transport.agent.destroyed}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertGreater(value["timeout"], value["reviewer"])
        self.assertGreater(value["bodyTimeout"], value["reviewer"])
        self.assertTrue(value["dispatcher"])
        self.assertTrue(value["signal"])
        self.assertTrue(value["safe"])
        self.assertEqual(value["closed"], 1)
        self.assertEqual(value["destroyed"], 0)
        self.assertIn('fetch: transport.fetch', (self.root / "scripts" / "opencode_structured_review.mjs").read_text(encoding="utf-8"))

    def test_reviewer_transport_accepts_node_global_request(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import http from 'node:http';"
            "import { createReviewerTransport, closeReviewerTransport } from "
            f"'{probe.as_uri()}';"
            "const server=http.createServer((request,response)=>{response.end('ok');});"
            "await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));"
            "const port=server.address().port; const controller=new AbortController();"
            "const request=new Request('http://127.0.0.1:'+port+'/',{signal:controller.signal});"
            "const transport=createReviewerTransport();"
            "const response=await transport.fetch(request,{signal:controller.signal});"
            "const body=await response.text(); const closed=await closeReviewerTransport(transport,1000);"
            "await new Promise(resolve=>server.close(resolve));"
            "console.log(JSON.stringify({ok:response.ok,status:response.status,body,closed}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertTrue(value["ok"])
        self.assertEqual(value["status"], 200)
        self.assertEqual(value["body"], "ok")
        self.assertTrue(value["closed"])

    def test_reviewer_transport_preserves_abort_behavior(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import http from 'node:http';"
            "import { createReviewerTransport, closeReviewerTransport } from "
            f"'{probe.as_uri()}';"
            "const server=http.createServer((_request,_response)=>{});"
            "await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));"
            "const port=server.address().port; const controller=new AbortController();"
            "const transport=createReviewerTransport();"
            "const request=new Request('http://127.0.0.1:'+port+'/',{signal:controller.signal});"
            "const pending=transport.fetch(request,{signal:controller.signal}).then(()=>({aborted:false})).catch(error=>({aborted:true,name:error.name,message:error.message}));"
            "setTimeout(()=>controller.abort(),25);"
            "const result=await Promise.race([pending,new Promise(resolve=>setTimeout(()=>resolve({timeout:true}),1000))]);"
            "const closed=await closeReviewerTransport(transport,1000);"
            "await new Promise(resolve=>server.close(resolve));"
            "console.log(JSON.stringify({result,closed,ownedAgent:transport.agent?.constructor?.name==='Agent'}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertTrue(value["result"]["aborted"])
        self.assertNotEqual(value["result"].get("name"), "TimeoutError")
        self.assertTrue(value["closed"])
        self.assertTrue(value["ownedAgent"])

    def test_reviewer_transport_failure_cleanup_destroys_stuck_agent(self):
        probe = self.root / "scripts" / "opencode_structured_review.mjs"
        script = (
            "import { createReviewerTransport, closeReviewerTransport } from "
            f"'{probe.as_uri()}';"
            "class StuckAgent { constructor(){this.destroyed=0;} close(){return new Promise(()=>{});} destroy(){this.destroyed++;} }"
            "const transport=createReviewerTransport({AgentClass:StuckAgent,fetchImpl:async()=>{throw new Error('fetch failed');}});"
            "let failure; try { await transport.fetch(new Request('http://127.0.0.1/')); } catch(error) { failure=error.message; }"
            "const safe=await closeReviewerTransport(transport,10); console.log(JSON.stringify({failure,safe,destroyed:transport.agent.destroyed}));"
        )
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, timeout=5, check=True)
        value = json.loads(result.stdout)
        self.assertEqual(value["failure"], "fetch failed")
        self.assertFalse(value["safe"])
        self.assertEqual(value["destroyed"], 1)

    def test_classified_envelope_owns_exit_boundary(self):
        adapter = (self.root / "scripts" / "opencode_structured_review.mjs").read_text(encoding="utf-8")
        gate = (self.root / "scripts" / "ai_gate.ps1").read_text(encoding="utf-8")
        self.assertIn('classification: "STRUCTURED_TRANSPORT_FAILED"', adapter)
        self.assertIn('if (failure) { process.stdout.write', adapter)
        self.assertNotIn('if (failure) { process.stdout.write(JSON.stringify({ schema_version: 1, agent, model, classification: "STRUCTURED_TRANSPORT_FAILED", diagnostic: transportDiagnostic(failure.operation ?? operation, failure), cleanup }) + "\\n"); process.exitCode = 1; }', adapter)
        self.assertIn("$env = if (-not $res.TimedOut) { Read-Envelope $res.StdOut } else { $null }", gate)
        self.assertNotIn("$res.ExitCode -eq 0) { Read-Envelope", gate)

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

    def run_cleanup_helper(self, worktree, canonical, *extra):
        helper = self.root / "scripts" / "worktree_cleanup_safety.ps1"
        arguments = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(helper), "-WorktreePath", str(worktree),
            "-CanonicalEnvironmentPath", str(canonical), *extra,
        ]
        command = subprocess.list2cmdline(arguments) + " < NUL"
        return subprocess.run(
            ["cmd.exe", "/d", "/s", "/c", command],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    @staticmethod
    def helper_result(result):
        output = (result.stdout or "").strip().splitlines()
        if not output:
            raise AssertionError(result.stdout + result.stderr)
        return json.loads(output[-1])

    @staticmethod
    def make_worktree(root):
        worktree = root / "task-worktree"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: administrative-marker", encoding="utf-8")
        return worktree

    @staticmethod
    def make_junction(link, target):
        result = subprocess.run(
            ["cmd.exe", "/d", "/s", "/c", f'mklink /J "{link}" "{target}"'],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise unittest.SkipTest(f"junction fixture unavailable: {result.stdout}{result.stderr}")

    def test_cleanup_accepts_and_detaches_exact_junction_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree = self.make_worktree(root)
            canonical = root / "canonical-env"
            canonical.mkdir()
            (canonical / "sentinel.txt").write_text("keep", encoding="utf-8")
            self.make_junction(worktree / ".venv", canonical)

            result = self.run_cleanup_helper(worktree, Path(str(canonical).upper()) / "")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.helper_result(result)["code"], "EXPECTED_JUNCTION")

            result = self.run_cleanup_helper(worktree, canonical, "-Detach")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(self.helper_result(result)["code"], "DETACHED")
            self.assertFalse((worktree / ".venv").exists())
            self.assertEqual((canonical / "sentinel.txt").read_text(encoding="utf-8"), "keep")

    def test_cleanup_fail_closed_classifications(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            canonical = root / "canonical"
            canonical.mkdir()

            missing = root / "missing-worktree"
            missing.mkdir()
            (missing / ".git").write_text("marker", encoding="utf-8")
            result = self.run_cleanup_helper(missing, canonical)
            self.assertEqual(self.helper_result(result)["code"], "MISSING_VENV")

            physical = root / "physical-worktree"
            physical.mkdir()
            (physical / ".git").write_text("marker", encoding="utf-8")
            (physical / ".venv").mkdir()
            result = self.run_cleanup_helper(physical, canonical)
            self.assertEqual(self.helper_result(result)["code"], "PHYSICAL_DIRECTORY")
            self.assertTrue((physical / ".venv").exists())

            wrong = root / "wrong-target"
            wrong.mkdir()
            (wrong / ".git").write_text("marker", encoding="utf-8")
            wrong_target = root / "other-env"
            wrong_target.mkdir()
            self.make_junction(wrong / ".venv", wrong_target)
            result = self.run_cleanup_helper(wrong, canonical)
            self.assertEqual(self.helper_result(result)["code"], "WRONG_TARGET")
            self.assertTrue((wrong / ".venv").exists())

    def test_cleanup_classifies_partial_removal_without_force(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partial = root / "partial-worktree"
            partial.mkdir()
            result = self.run_cleanup_helper(partial, root / "canonical")
            self.assertEqual(self.helper_result(result)["code"], "PARTIAL_REMOVAL_REQUIRES_STALE_PROOF")
            helper_text = (self.root / "scripts" / "worktree_cleanup_safety.ps1").read_text(encoding="utf-8")
            self.assertNotIn("worktree remove --force", helper_text.lower())
            self.assertNotIn("worktree prune", helper_text.lower())

    def test_cleanup_rejects_directory_symlink_as_unsupported_reparse(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            worktree = self.make_worktree(root)
            canonical = root / "canonical"
            canonical.mkdir()
            try:
                os.symlink(canonical, worktree / ".venv", target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                raise unittest.SkipTest(f"symbolic-link fixture unavailable: {error}")
            result = self.run_cleanup_helper(worktree, canonical)
            self.assertEqual(self.helper_result(result)["code"], "UNSUPPORTED_REPARSE")
            self.assertTrue((worktree / ".venv").is_symlink())

    def test_cleanup_contract_keeps_remove_and_prune_ownership_in_workflow(self):
        helper = (self.root / "scripts" / "worktree_cleanup_safety.ps1").read_text(encoding="utf-8")
        completion = (self.root / ".agents" / "skills" / "branch_completion_workflow" / "SKILL.md").read_text(encoding="utf-8")
        architecture = (self.root / "docs" / "architecture" / "ai_development_workflow.md").read_text(encoding="utf-8")
        self.assertIn("-Detach", completion)
        self.assertIn("git worktree remove <path>", completion)
        self.assertIn("git worktree prune --verbose", completion)
        self.assertIn("Live or dirty", completion)
        self.assertIn("unrelated worktrees", completion)
        self.assertLess(completion.index("-Detach"), completion.index("git worktree remove <path>"))
        self.assertNotIn("worktree remove --force", helper.lower())
        self.assertNotIn("worktree prune", helper.lower())
        self.assertIn("worktree_cleanup_safety.ps1", architecture)


if __name__ == "__main__":
    unittest.main()
