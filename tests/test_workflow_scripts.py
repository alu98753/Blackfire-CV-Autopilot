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

    def test_node_workflow_contract_derives_spec_from_package_json(self):
        contract = self.root / "scripts" / "node_workflow_contract.ps1"
        contract_text = contract.read_text(encoding="utf-8")
        self.assertNotIn("$NodeEngineRequiredSpec", contract_text)

        test_dir = self.root / ".runtime" / "test_engine_ssot_fixture"
        test_dir.mkdir(parents=True, exist_ok=True)
        try:
            # 1. Custom version in package.json (>=22.0)
            custom_pkg = {"name": "fixture", "engines": {"node": ">=22.0"}}
            (test_dir / "package.json").write_text(json.dumps(custom_pkg), encoding="utf-8")

            # Prove Get-RequiredNodeEngineSpec extracts exact string from package.json
            ps_get_spec = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Get-RequiredNodeEngineSpec -RepoRoot \'{test_dir}\'"'
            res_spec = subprocess.run(f'cmd.exe /d /s /c "{ps_get_spec}"', cwd=self.root, capture_output=True, text=True)
            self.assertEqual(res_spec.returncode, 0, res_spec.stdout + res_spec.stderr)
            self.assertEqual(res_spec.stdout.strip(), ">=22.0")

            # Under >=22.0, 20.11.1 must fail
            ps_fail = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Assert-NodeSupportedVersion -Version \'20.11.1\' -RepoRoot \'{test_dir}\'"'
            res_fail = subprocess.run(f'cmd.exe /d /s /c "{ps_fail}"', cwd=self.root, capture_output=True, text=True)
            self.assertNotEqual(res_fail.returncode, 0)
            self.assertIn(">=22.0", res_fail.stdout + res_fail.stderr)

            # Under >=22.0, 22.1.0 must pass
            ps_pass = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Assert-NodeSupportedVersion -Version \'22.1.0\' -RepoRoot \'{test_dir}\'"'
            res_pass = subprocess.run(f'cmd.exe /d /s /c "{ps_pass}"', cwd=self.root, capture_output=True, text=True)
            self.assertEqual(res_pass.returncode, 0, res_pass.stdout + res_pass.stderr)

            # 2. Missing engines.node fails closed
            (test_dir / "package.json").write_text(json.dumps({"name": "fixture"}), encoding="utf-8")
            ps_missing = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Get-RequiredNodeEngineSpec -RepoRoot \'{test_dir}\'"'
            res_missing = subprocess.run(f'cmd.exe /d /s /c "{ps_missing}"', cwd=self.root, capture_output=True, text=True)
            self.assertNotEqual(res_missing.returncode, 0)
            self.assertIn("missing a valid 'engines.node'", res_missing.stdout + res_missing.stderr)

            # 3. Malformed engines.node syntax fails closed
            (test_dir / "package.json").write_text(json.dumps({"name": "fixture", "engines": {"node": "unsupported_syntax"}}), encoding="utf-8")
            ps_malformed = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Assert-NodeSupportedVersion -Version \'24.19.0\' -RepoRoot \'{test_dir}\'"'
            res_malformed = subprocess.run(f'cmd.exe /d /s /c "{ps_malformed}"', cwd=self.root, capture_output=True, text=True)
            self.assertNotEqual(res_malformed.returncode, 0)
            self.assertIn("Unsupported or malformed 'engines.node' specification", res_malformed.stdout + res_malformed.stderr)
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

        # 4. Repository worktree package.json contract
        repo_pkg = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
        repo_engine = repo_pkg["engines"]["node"]
        self.assertEqual(repo_engine, ">=18.17")
        ps_repo_valid = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Assert-NodeSupportedVersion \'24.19.0\'; Assert-NodeSupportedVersion \'v18.17.0\'"'
        res_repo_valid = subprocess.run(f'cmd.exe /d /s /c "{ps_repo_valid}"', cwd=self.root, capture_output=True, text=True)
        self.assertEqual(res_repo_valid.returncode, 0, res_repo_valid.stdout + res_repo_valid.stderr)

        ps_repo_invalid = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; Assert-NodeSupportedVersion \'18.16.0\'"'
        res_repo_invalid = subprocess.run(f'cmd.exe /d /s /c "{ps_repo_invalid}"', cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(res_repo_invalid.returncode, 0)
        self.assertIn("Unsupported Node.js version", res_repo_invalid.stdout + res_repo_invalid.stderr)

    def test_node_workflow_readiness_probe_package_boundary(self):
        script = "import('undici').then(() => import('@opencode-ai/sdk/v2')).then(() => console.log('BOUNDARY_OK'));"
        result = subprocess.run(["node", "--input-type=module", "-e", script], cwd=self.root, capture_output=True, text=True, check=True)
        self.assertIn("BOUNDARY_OK", result.stdout)

    def test_node_workflow_readiness_reports_unbootstrapped_directory(self):
        contract = self.root / "scripts" / "node_workflow_contract.ps1"
        test_dir = self.root / ".runtime" / "test_unbootstrapped_fixture"
        test_dir.mkdir(parents=True, exist_ok=True)
        try:
            (test_dir / "package.json").write_text(json.dumps({"name": "fixture", "engines": {"node": ">=18.17"}}), encoding="utf-8")
            (test_dir / "package-lock.json").write_text("{}", encoding="utf-8")
            ps_cmd = f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ". \'{contract}\'; $r = Test-NodeWorkflowDependencies -RepoRoot \'{test_dir}\'; [pscustomobject]@{{ Ready = $r.Ready; Reason = $r.Reason; Remediation = $r.Remediation }} | ConvertTo-Json -Compress"'
            result = subprocess.run(f'cmd.exe /d /s /c "{ps_cmd}"', cwd=self.root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            data = json.loads(result.stdout.strip())
            self.assertFalse(data["Ready"])
            self.assertIn("bootstrap_node_workflow_deps.ps1", data["Remediation"])
        finally:
            import shutil
            shutil.rmtree(test_dir, ignore_errors=True)

    def test_gate_and_readiness_contracts_do_not_mutate_dependencies(self):
        gate_text = (self.root / "scripts" / "ai_gate.ps1").read_text(encoding="utf-8")
        contract_text = (self.root / "scripts" / "node_workflow_contract.ps1").read_text(encoding="utf-8")
        self.assertNotIn("npm install", gate_text)
        self.assertNotIn("npm ci", gate_text)
        # Verify readiness contract does not invoke npm commands to mutate environment
        self.assertNotIn("& npm", contract_text)
        self.assertNotIn("npm install", contract_text)
        self.assertNotIn("npm.cmd", contract_text)

    def test_bootstrap_node_workflow_deps_contract(self):
        bootstrap_text = (self.root / "scripts" / "bootstrap_node_workflow_deps.ps1").read_text(encoding="utf-8")
        self.assertIn("npm ci", bootstrap_text)
        self.assertNotIn("npm install ", bootstrap_text)
        self.assertIn("Get-RequiredNodeEngineSpec", bootstrap_text)
        self.assertIn("Assert-NodeSupportedVersion", bootstrap_text)
        self.assertIn("Assert-NodeWorkflowDependenciesReady", bootstrap_text)

    def test_gate_reviewer_override_does_not_bypass_node_readiness(self):
        gate_text = (self.root / "scripts" / "ai_gate.ps1").read_text(encoding="utf-8")
        self.assertIn("if (-not $_SkipNodeReadinessCheck) {", gate_text)
        self.assertNotIn("if ($_ReviewerExecutableOverride) { if ($_NodeVersionOverride) { Assert-NodeSupportedVersion", gate_text)

    def test_windows_workflow_harness(self):
        harness = self.root / "tests" / "workflow_scripts" / "Invoke-WorkflowScriptHarness.ps1"
        command = f'cmd.exe /d /s /c "chcp 65001 >nul && powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{harness}" < NUL"'
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, shell=True, timeout=240)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Workflow script harness:", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
