import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { existsSync } from "node:fs";
import test from "node:test";
import {
  C3_PROBE_TIMEOUT_MS,
  DEFAULT_PROBE_TIMEOUT_MS,
  OUTCOME_SCHEMA,
  RUNTIME_MATRIX,
  aggregateRepeatability,
  auditSessionMessages,
  buildProbeConfig,
  buildPromptRequest,
  buildReviewerPrompt,
  buildSmokePrompt,
  classifyLifecycle,
  diagnosticFromError,
  hasAuthoritativePromptResponse,
  inspectLifecycle,
  isPidAlive,
  normalizeStructuredResult,
  openCodeVersionCommand,
  probeTimeoutForCandidate,
  redactDiagnostic,
  runProbe,
  terminateOwnedProcessTree,
  validateOutcomeSchema,
  validateOutcomeSemantics,
  withIsolatedRuntimeEnvironment,
} from "../../scripts/opencode_structured_review_probe.mjs";

function successfulLifecycle(overrides = {}) {
  return {
    finish_reasons: ["stop"],
    finalization_voluntary: true,
    forced_finalization: false,
    read_search_tool_called: true,
    structured_output_present: true,
    successful_tool_result: true,
    ...overrides,
  };
}

function successfulTransport({ structured = { verdict: "PASS", blocking_findings: 0, report_markdown: "# Review" }, parts } = {}) {
  return async () => ({
    server: { close() {} },
    client: {
      session: {
        create: async () => ({ data: { id: "session-1" } }),
        prompt: async () => ({ data: {
          info: { id: "message-1", finish: "stop", time: { completed: 1 }, structured_output: structured, structured },
          parts: parts ?? [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
        } }),
        messages: async () => ({ data: [{
          info: { id: "message-1", finish: "stop", time: { completed: 1 }, structured_output: structured, structured },
          parts: parts ?? [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
        }] }),
      },
    },
  });
}

function controlConfig(overrides = {}) {
  return buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", ...overrides });
}

function runtimeFor(config) {
  return { opencode_version: config.expectedOpenCodeVersion, client_version: config.expectedClientVersion };
}

function transportWith({ create, cleanup }) {
  return async () => ({
    server: { cleanup },
    client: {
      session: {
        create,
        prompt: async () => ({ data: {
          info: { id: "message-1", finish: "stop", time: { completed: 1 }, structured_output: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Review" } },
          parts: [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
        } }),
        messages: async () => ({ data: [] }),
      },
    },
  });
}

test("frozen matrix accepts control, C1, C2, and C3", () => {
  assert.equal(RUNTIME_MATRIX.C1.runtimeVersion, "1.14.41");
  assert.equal(RUNTIME_MATRIX.C2.clientPackage, "@opencode/client");
  assert.equal(RUNTIME_MATRIX.C3.runtimeVersion, "1.18.31");
  assert.equal(RUNTIME_MATRIX.C3.clientPackage, "@opencode-ai/sdk");
  assert.equal(RUNTIME_MATRIX.C3.clientVersion, "1.18.31");
  assert.equal(RUNTIME_MATRIX.C3.transport, "official-sdk-v2");
  assert.equal(RUNTIME_MATRIX.C3.structuredField, "assistant.info.structured");
  assert.equal(controlConfig().expectedOpenCodeVersion, "1.18.31");
  const c1 = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C1", runtimeRoot: ".runtime/c1" });
  assert.equal(c1.expectedClientVersion, "1.14.41");
  const c3 = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  assert.equal(c3.expectedOpenCodeVersion, "1.18.31");
  assert.equal(c3.expectedClientVersion, "1.18.31");
  assert.throws(() => buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C4", runtimeRoot: ".runtime/c4" }), /Unlisted/);
  assert.throws(() => buildProbeConfig({ agent: "spec-reviewer", model: "other/model", directory: "." }), /frozen provider/);
});

test("qualification request preserves the fixed schema and production control transport", () => {
  const config = controlConfig();
  const request = buildPromptRequest(config, "session-1", buildReviewerPrompt());
  assert.deepEqual(request.body.model, { providerID: "opencode", modelID: "big-pickle" });
  assert.equal(request.body.format.type, "json_schema");
  assert.deepEqual(request.body.format.schema, OUTCOME_SCHEMA);
  assert.equal(request.body.format.retryCount, 2);
  assert.equal(normalizeStructuredResult("CONTROL", { structured_output: { verdict: "PASS" } }).value.verdict, "PASS");
});

test("C3 constructs official v2 flat prompt request and targets assistant.info.structured", () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  const request = buildPromptRequest(config, "session-1", buildReviewerPrompt());
  assert.equal(request.sessionID, "session-1");
  assert.equal(request.directory, config.directory);
  assert.equal(request.agent, "spec-reviewer");
  assert.deepEqual(request.model, { providerID: "opencode", modelID: "big-pickle" });
  assert.equal(request.format.type, "json_schema");
  assert.deepEqual(request.format.schema, OUTCOME_SCHEMA);
  assert.equal(request.format.retryCount, 2);
  assert.deepEqual(request.parts, [{ type: "text", text: buildReviewerPrompt() }]);
  assert.equal(request.path, undefined);
  assert.equal(request.body, undefined);

  const normalized = normalizeStructuredResult("C3", {
    structured: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Pass" },
    structured_output: { verdict: "BLOCK", blocking_findings: 1, report_markdown: "# Block" },
  });
  assert.equal(normalized.available, true);
  assert.equal(normalized.field, "assistant.info.structured");
  assert.deepEqual(normalized.value, { verdict: "PASS", blocking_findings: 0, report_markdown: "# Pass" });

  const noFallback = normalizeStructuredResult("C3", {
    structured_output: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Pass" },
  });
  assert.equal(noFallback.available, true);
  assert.equal(noFallback.value, undefined);
});

test("full and smoke prompts are fixed across candidates and models", () => {
  assert.equal(buildReviewerPrompt("C1", "opencode/big-pickle"), buildReviewerPrompt("C2", "opencode/mimo-v2.5-free"));
  assert.equal(buildReviewerPrompt("C1", "opencode/big-pickle"), buildReviewerPrompt("C3", "opencode/big-pickle"));
  assert.equal(buildSmokePrompt("C1"), buildSmokePrompt("C2"));
  assert.equal(buildSmokePrompt("C1"), buildSmokePrompt("C3"));
  assert.notEqual(buildReviewerPrompt(), buildSmokePrompt());
});

test("production reviewer roles remain discoverable", () => {
  assert.equal(existsSync(".opencode/agents/spec-reviewer.md"), true);
  assert.equal(existsSync(".opencode/agents/regression-reviewer.md"), true);
  assert.doesNotThrow(() => controlConfig({ agent: "regression-reviewer" }));
});

test("C1 uses only official assistant info.structured and C2 fails closed", () => {
  assert.deepEqual(normalizeStructuredResult("C1", { structured: { verdict: "PASS" } }), {
    available: true,
    field: "assistant.info.structured",
    value: { verdict: "PASS" },
  });
  const c2 = normalizeStructuredResult("C2", { structured: { verdict: "PASS" } });
  assert.equal(c2.available, false);
  assert.equal(c2.field, null);
});

test("fixed schema and semantic validation reject malformed machine values", () => {
  assert.equal(validateOutcomeSchema({ verdict: "PASS", blocking_findings: 0, report_markdown: "# Review" }).valid, true);
  assert.equal(validateOutcomeSchema({ verdict: "PASS", blocking_findings: -1, report_markdown: 2, prose: "PASS" }).valid, false);
  assert.equal(validateOutcomeSemantics({ verdict: "PASS", blocking_findings: 1 }).valid, false);
  assert.equal(validateOutcomeSemantics({ verdict: "BLOCK", blocking_findings: 0 }).valid, false);
});

test("lifecycle inspection requires a completed permitted repository tool", () => {
  const lifecycle = inspectLifecycle({ finalInfo: { finish: "stop", time: { completed: 1 } }, structuredOutput: {}, messages: [{ parts: [{ type: "tool", tool: "read", state: { status: "completed" } }] }] });
  assert.equal(lifecycle.successful_tool_result, true);
  assert.equal(classifyLifecycle({ lifecycle, schema: { valid: true }, semantics: { valid: true } }), "PASS_PROVEN");
  assert.equal(classifyLifecycle({ lifecycle: successfulLifecycle({ read_search_tool_called: false }), schema: { valid: true }, semantics: { valid: true } }), "FAIL_TOOL_CHOICE");
  assert.equal(classifyLifecycle({ lifecycle: successfulLifecycle({ successful_tool_result: false }), schema: { valid: true }, semantics: { valid: true } }), "FAIL_LIFECYCLE_AUDIT");
  assert.equal(classifyLifecycle({ lifecycle: successfulLifecycle({ finalization_voluntary: false }), schema: { valid: true }, semantics: { valid: true } }), "FAIL_LIFECYCLE_AUDIT");
});

test("same-attempt history is required when prompt response has no typed lifecycle", async () => {
  const audit = await auditSessionMessages({
    client: { session: { messages: async () => ({ data: [{ info: { id: "message-1" }, parts: [{ type: "tool", tool: "read", state: { status: "completed" } }] }] }) } },
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    finalInfo: { id: "message-1" },
    sessionId: "session-1",
  });
  assert.equal(audit.valid, true);
  assert.equal(audit.source, "session.messages");
});

test("audit retrieval failure, malformed history, and stale history fail closed", async () => {
  const args = { directory: "E:\\repo", promptMessage: { parts: [{ type: "text" }] }, finalInfo: { id: "message-1" }, sessionId: "session-1" };
  const failed = await auditSessionMessages({ ...args, client: { session: { messages: async () => { throw new Error("fetch failed"); } } } });
  const malformed = await auditSessionMessages({ ...args, client: { session: { messages: async () => ({ data: [{ parts: [null] }] }) } } });
  const stale = await auditSessionMessages({ ...args, client: { session: { messages: async () => ({ data: [{ info: { id: "old" }, parts: [] }] }) } } });
  assert.equal(failed.valid, false);
  assert.equal(malformed.valid, false);
  assert.equal(stale.valid, false);
});

test("runProbe classifies a full verified control lifecycle as PASS_PROVEN", async () => {
  const config = controlConfig();
  const result = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: successfulTransport() });
  assert.equal(result.classification, "PASS_PROVEN");
  assert.equal(result.lifecycle_audit_trustworthy, true);
  assert.equal(result.official_structured_machine_field, "response.data.info.structured_output");
});

test("runProbe maps absent machine result, schema violation, and semantic violation separately", async () => {
  const config = controlConfig();
  const absent = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: successfulTransport({ structured: null }) });
  const schema = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: successfulTransport({ structured: { verdict: "MAYBE", blocking_findings: 0, report_markdown: "x" } }) });
  const semantic = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: successfulTransport({ structured: { verdict: "PASS", blocking_findings: 1, report_markdown: "x" } }) });
  assert.equal(absent.classification, "FAIL_STRUCTURED_OUTPUT");
  assert.equal(schema.classification, "FAIL_SCHEMA");
  assert.equal(semantic.classification, "FAIL_SEMANTIC");
});

test("C3 auditSessionMessages uses v2 flat parameters and rejects malformed/missing history", async () => {
  let calledWith;
  const mockClient = {
    session: {
      messages: async (params) => {
        calledWith = params;
        return { data: [{ info: { id: "msg-1" }, parts: [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }] }] };
      },
    },
  };
  const audit = await auditSessionMessages({
    client: mockClient,
    sessionId: "sess-v2",
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    finalInfo: { id: "msg-1" },
    candidate: "C3",
  });
  assert.equal(audit.valid, true);
  assert.equal(audit.source, "session.messages");
  assert.deepEqual(calledWith, { sessionID: "sess-v2", directory: "E:\\repo", throwOnError: true });

  const malformed = await auditSessionMessages({
    client: { session: { messages: async () => ({ data: [{ parts: [null] }] }) } },
    sessionId: "sess-v2",
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    finalInfo: { id: "msg-1" },
    candidate: "C3",
  });
  assert.equal(malformed.valid, false);

  const fetchFailed = await auditSessionMessages({
    client: { session: { messages: async () => { throw new Error("fetch failed"); } } },
    sessionId: "sess-v2",
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    finalInfo: { id: "msg-1" },
    candidate: "C3",
  });
  assert.equal(fetchFailed.valid, false);
});

test("runProbe classifies a full verified C3 lifecycle as PASS_PROVEN", async () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  let sessionCreateArgs;
  let promptArgs;
  const c3Transport = async () => ({
    server: { cleanup: async () => ({ proven: true }) },
    client: {
      session: {
        create: async (args) => {
          sessionCreateArgs = args;
          return { data: { id: "c3-session-1" } };
        },
        prompt: async (args) => {
          promptArgs = args;
          return {
            data: {
              info: {
                id: "msg-1",
                finish: "stop",
                time: { completed: 1 },
                structured: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Review" },
              },
              parts: [
                { type: "tool", tool: "read", state: { status: "completed" } },
                { type: "step-finish", reason: "stop" },
              ],
            },
          };
        },
        messages: async () => ({ data: [] }),
      },
    },
  });

  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: c3Transport,
  });

  assert.equal(result.classification, "PASS_PROVEN");
  assert.equal(result.lifecycle_audit_trustworthy, true);
  assert.equal(result.official_structured_machine_field, "assistant.info.structured");
  assert.equal(result.sdk_transport, "official-sdk-v2");
  assert.deepEqual(sessionCreateArgs, { directory: config.directory, throwOnError: true });
  assert.equal(promptArgs.sessionID, "c3-session-1");
  assert.equal(result.isolation_cleanup_proven, true);
});

test("runProbe with C3 maps missing structured, schema, and semantic failures", async () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  const makeTransport = (structured) => async () => ({
    server: { cleanup: async () => ({ proven: true }) },
    client: {
      session: {
        create: async () => ({ data: { id: "s1" } }),
        prompt: async () => ({
          data: {
            info: { id: "m1", finish: "stop", time: { completed: 1 }, structured },
            parts: [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
          },
        }),
        messages: async () => ({ data: [{
          info: { id: "m1", finish: "stop", time: { completed: 1 }, structured },
          parts: [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
        }] }),
      },
    },
  });

  const missing = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: makeTransport(undefined) });
  assert.equal(missing.classification, "FAIL_STRUCTURED_OUTPUT");

  const badSchema = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: makeTransport({ verdict: "INVALID" }) });
  assert.equal(badSchema.classification, "FAIL_SCHEMA");

  const badSemantics = await runProbe(config, { getRuntimeMetadata: async () => runtimeFor(config), createTransport: makeTransport({ verdict: "PASS", blocking_findings: 1, report_markdown: "x" }) });
  assert.equal(badSemantics.classification, "FAIL_SEMANTIC");
});

test("runtime/client mismatches, unavailable transport, and unavailable C2 adapter are infrastructure failures", async () => {
  const control = controlConfig();
  const mismatch = await runProbe(control, { getRuntimeMetadata: async () => ({ opencode_version: "1.14.41", client_version: "1.18.31" }) });
  const unavailable = await runProbe(control, { getRuntimeMetadata: async () => { throw new Error("runtime unavailable"); } });
  const c2 = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C2", runtimeRoot: ".runtime/c2" });
  const c2Result = await runProbe(c2, { getRuntimeMetadata: async () => runtimeFor(c2) });
  assert.equal(mismatch.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(unavailable.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(c2Result.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(c2Result.subreason, "STRUCTURED_ADAPTER_UNAVAILABLE");
});

test("isolated environment restores PATH and all caller state after success and exception", async () => {
  const environment = { PATH: "C:\\normal", OPENCODE_DB: "C:\\user.db", OPENCODE_CONFIG_DIR: "C:\\config", OPENCODE_DISABLE_AUTOUPDATE: "0" };
  await withIsolatedRuntimeEnvironment({ candidate: "C1", runtimeRoot: ".runtime/c1", environment }, async () => {
    assert.match(environment.PATH, /\.runtime/);
    assert.equal(environment.OPENCODE_DB, ":memory:");
    assert.equal(environment.OPENCODE_DISABLE_AUTOUPDATE, "1");
  });
  assert.deepEqual(environment, { PATH: "C:\\normal", OPENCODE_DB: "C:\\user.db", OPENCODE_CONFIG_DIR: "C:\\config", OPENCODE_DISABLE_AUTOUPDATE: "0" });
  await assert.rejects(() => withIsolatedRuntimeEnvironment({ candidate: "C1", runtimeRoot: ".runtime/c1", environment }, async () => { throw new Error("boom"); }), /boom/);
  assert.deepEqual(environment, { PATH: "C:\\normal", OPENCODE_DB: "C:\\user.db", OPENCODE_CONFIG_DIR: "C:\\config", OPENCODE_DISABLE_AUTOUPDATE: "0" });
});

test("owned Windows process-tree cleanup targets only the runner-created root", async () => {
  const child = new EventEmitter();
  child.pid = 4242;
  child.exitCode = null;
  let targeted;
  const result = await terminateOwnedProcessTree(child, {
    taskKill: async (pid) => {
      targeted = pid;
      child.exitCode = 0;
      child.emit("exit", 0);
    },
    waitForChildExit: async () => true,
  });
  assert.deepEqual(result, { proven: true, pid: 4242 });
  assert.equal(targeted, 4242);
});

test("probe runner cleans owned transport after normal completion and exception", async () => {
  const config = controlConfig();
  let normalCleanup = 0;
  const normal = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: transportWith({ create: async () => ({ data: { id: "session-1" } }), cleanup: async () => { normalCleanup += 1; return { proven: true }; } }),
  });
  let exceptionCleanup = 0;
  const exception = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: transportWith({ create: async () => { throw new Error("session failure"); }, cleanup: async () => { exceptionCleanup += 1; return { proven: true }; } }),
  });
  assert.equal(normal.classification, "PASS_PROVEN");
  assert.equal(exception.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(normal.isolation_cleanup_proven, true);
  assert.equal(exception.isolation_cleanup_proven, true);
  assert.equal(normalCleanup, 1);
  assert.equal(exceptionCleanup, 1);
});

test("probe timeout cleans owned transport without a live model call", async () => {
  const config = controlConfig();
  let cleanupCalls = 0;
  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    probeTimeoutMs: 5,
    createTransport: transportWith({
      create: async () => new Promise(() => {}),
      cleanup: async () => { cleanupCalls += 1; return { proven: true }; },
    }),
  });
  assert.equal(result.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(result.subreason, "PROBE_TIMEOUT");
  assert.equal(result.isolation_cleanup_proven, true);
  assert.equal(cleanupCalls, 1);
});

test("cleanup failure fails closed and still restores caller environment", async () => {
  const config = controlConfig();
  const environment = { PATH: "C:\\normal", OPENCODE_DB: "C:\\user.db", OPENCODE_DISABLE_AUTOUPDATE: "0" };
  const result = await runProbe(config, {
    environment,
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: transportWith({
      create: async () => ({ data: { id: "session-1" } }),
      cleanup: async () => ({ proven: false, diagnostic: "tree still alive" }),
    }),
  });
  assert.equal(result.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(result.subreason, "ISOLATION_CLEANUP_UNSAFE");
  assert.deepEqual(environment, { PATH: "C:\\normal", OPENCODE_DB: "C:\\user.db", OPENCODE_DISABLE_AUTOUPDATE: "0" });
});

test("repeatability requires exactly spec, regression, spec, regression PASS attempts and ignores smoke", () => {
  const route = (role, kind = "qualifying", classification = "PASS_PROVEN") => ({ attempt_kind: kind, reviewer_role: role, classification, matrix_candidate: "C1", open_code_version: "1.14.41", client_package: "@opencode-ai/sdk", client_version: "1.14.41", provider: "opencode", model: "big-pickle" });
  const passes = [route("regression-reviewer", "smoke"), route("spec-reviewer"), route("regression-reviewer"), route("spec-reviewer", "confirmation"), route("regression-reviewer", "confirmation")];
  assert.equal(aggregateRepeatability(passes).stable, true);
  assert.equal(aggregateRepeatability([...passes.slice(0, 4), route("regression-reviewer", "confirmation", "FAIL_SCHEMA")]).stable, false);
});

test("diagnostics are bounded, redact credentials, and Windows version check is non-interactive", () => {
  const diagnostic = redactDiagnostic(`Bearer secret-value api_key=example-secret sk_abcdefghijk ${"x".repeat(800)}`);
  assert.ok(diagnostic.length <= 600);
  assert.doesNotMatch(diagnostic, /secret-value|example-secret|sk_abcdefghijk/);
  assert.match(diagnosticFromError({ status: 401, token: "secret-value" }), /REDACTED/);
  assert.deepEqual(openCodeVersionCommand("win32", "C:\\Windows\\System32\\cmd.exe"), { command: "C:\\Windows\\System32\\cmd.exe", args: ["/d", "/s", "/c", "opencode --version < NUL"] });
});

test("child exits before taskkill -> cleanup proven", async () => {
  const child = new EventEmitter();
  child.pid = 9001;
  child.exitCode = 0;
  let taskKillCalled = false;
  const result = await terminateOwnedProcessTree(child, {
    isPidAlive: () => false,
    checkDescendants: async () => [],
    taskKill: async () => { taskKillCalled = true; },
  });
  assert.deepEqual(result, { proven: true, pid: 9001 });
  assert.equal(taskKillCalled, false);
});

test("taskkill reports PID not found but tree is already gone -> cleanup proven", async () => {
  const child = new EventEmitter();
  child.pid = 9002;
  child.exitCode = null;
  const result = await terminateOwnedProcessTree(child, {
    isPidAlive: () => false,
    checkDescendants: async () => [],
    taskKill: async () => {
      throw new Error("Command failed: taskkill /PID 9002 /T /F: 錯誤: 找不到處理程序 9002");
    },
    waitForChildExit: async () => true,
  });
  assert.deepEqual(result, { proven: true, pid: 9002 });
});

test("owned descendant remains -> cleanup not proven", async () => {
  const child = new EventEmitter();
  child.pid = 9003;
  child.exitCode = 0;
  const result = await terminateOwnedProcessTree(child, {
    isPidAlive: () => false,
    checkDescendants: async () => [9004],
    taskKill: async () => {},
    retryTaskKill: async () => {},
    waitForChildExit: async () => true,
  });
  assert.equal(result.proven, false);
  assert.match(result.diagnostic, /9004/);
});

test("cleanup retry removes remaining owned tree -> cleanup proven", async () => {
  const child = new EventEmitter();
  child.pid = 9005;
  child.exitCode = null;
  let descendants = [9006];
  let retried = false;
  const result = await terminateOwnedProcessTree(child, {
    isPidAlive: () => false,
    checkDescendants: async () => descendants,
    taskKill: async () => {},
    retryTaskKill: async () => {
      retried = true;
      descendants = [];
    },
    waitForChildExit: async () => true,
  });
  assert.deepEqual(result, { proven: true, pid: 9005 });
  assert.equal(retried, true);
});

test("reviewer FAIL_LIFECYCLE_AUDIT is preserved when cleanup succeeds", async () => {
  const config = buildProbeConfig({ agent: "regression-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  const transport = async () => ({
    server: { cleanup: async () => ({ proven: true, pid: 1111 }) },
    client: {
      session: {
        create: async () => ({ data: { id: "s-fail-audit" } }),
        prompt: async () => ({
          data: {
            info: { id: "m-1", finish: "step-limit", structured: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Done" } },
            parts: [
              { type: "tool", tool: "read", state: { status: "completed" } },
              { type: "step-finish", reason: "step-limit" },
            ],
          },
        }),
        messages: async () => ({ data: [] }),
      },
    },
  });
  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: transport,
  });
  assert.equal(result.classification, "FAIL_LIFECYCLE_AUDIT");
  assert.equal(result.subreason, "STEP_BUDGET_EXHAUSTED");
  assert.equal(result.isolation_cleanup_proven, true);
  assert.equal(result.owned_process_tree_pid, 1111);
});

test("cleanup failure legitimately overrides reviewer result", async () => {
  const config = buildProbeConfig({ agent: "regression-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  const transport = async () => ({
    server: { cleanup: async () => ({ proven: false, diagnostic: "owned descendant remains" }) },
    client: {
      session: {
        create: async () => ({ data: { id: "s-fail-cleanup" } }),
        prompt: async () => ({
          data: {
            info: { id: "m-1", finish: "stop", time: { completed: 1 }, structured: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Done" } },
            parts: [{ type: "tool", tool: "read", state: { status: "completed" } }, { type: "step-finish", reason: "stop" }],
          },
        }),
        messages: async () => ({ data: [] }),
      },
    },
  });
  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: transport,
  });
  assert.equal(result.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(result.subreason, "ISOLATION_CLEANUP_UNSAFE");
  assert.match(result.diagnostic, /owned descendant remains/);
});

test("stdout and stderr stream cleanup releases stream handles", () => {
  const stdout = new EventEmitter();
  let stdoutDestroyed = false;
  stdout.destroy = () => { stdoutDestroyed = true; };
  const stderr = new EventEmitter();
  let stderrDestroyed = false;
  stderr.destroy = () => { stderrDestroyed = true; };
  stdout.removeAllListeners();
  stderr.removeAllListeners();
  stdout.destroy();
  stderr.destroy();
  assert.equal(stdoutDestroyed, true);
  assert.equal(stderrDestroyed, true);
});

test("isPidAlive accurately detects running and non-existent PIDs", () => {
  assert.equal(isPidAlive(process.pid), true);
  assert.equal(isPidAlive(9999999), false);
  assert.equal(isPidAlive(-1), false);
  assert.equal(isPidAlive(0), false);
});

test("probeTimeoutForCandidate assigns 480s to C3 and preserves 40s default for CONTROL, C1, and C2", () => {
  assert.equal(C3_PROBE_TIMEOUT_MS, 480_000);
  assert.equal(DEFAULT_PROBE_TIMEOUT_MS, 40_000);
  assert.equal(probeTimeoutForCandidate("C3"), 480_000);
  assert.equal(probeTimeoutForCandidate("CONTROL"), 40_000);
  assert.equal(probeTimeoutForCandidate("C1"), 40_000);
  assert.equal(probeTimeoutForCandidate("C2"), 40_000);
});

test("C3 probe runner respects injected probeTimeoutMs override", async () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  let cleanupCalls = 0;
  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    probeTimeoutMs: 5,
    createTransport: async () => ({
      server: { cleanup: async () => { cleanupCalls += 1; return { proven: true }; } },
      client: {
        session: {
          create: async () => new Promise(() => {}),
        },
      },
    }),
  });
  assert.equal(result.classification, "FAIL_INFRASTRUCTURE");
  assert.equal(result.subreason, "PROBE_TIMEOUT");
  assert.equal(cleanupCalls, 1);
});

test("inspectLifecycle treats finish=tool-calls with completed tool and structured output as voluntary, not forced", () => {
  const lifecycle = inspectLifecycle({
    messages: [
      {
        parts: [
          { type: "tool", tool: "read", state: { status: "completed" } },
          { type: "step-finish", reason: "tool-calls" },
        ],
      },
    ],
    finalInfo: { id: "m-tc", finish: "tool-calls", time: { completed: 1 } },
    structuredOutput: { verdict: "PASS", blocking_findings: 0, report_markdown: "# OK" },
  });
  assert.equal(lifecycle.forced_finalization, false);
  assert.equal(lifecycle.finalization_voluntary, true);
  assert.equal(lifecycle.read_search_tool_called, true);
  assert.equal(lifecycle.successful_tool_result, true);
  assert.equal(lifecycle.structured_output_present, true);
  assert.deepEqual(lifecycle.finish_reasons, ["tool-calls"]);
});

test("inspectLifecycle treats finish=stop as voluntary", () => {
  const lifecycle = inspectLifecycle({
    messages: [
      {
        parts: [
          { type: "tool", tool: "grep", state: { status: "completed" } },
          { type: "step-finish", reason: "stop" },
        ],
      },
    ],
    finalInfo: { id: "m-stop", finish: "stop", time: { completed: 1 } },
    structuredOutput: { verdict: "PASS", blocking_findings: 0, report_markdown: "# OK" },
  });
  assert.equal(lifecycle.forced_finalization, false);
  assert.equal(lifecycle.finalization_voluntary, true);
});

test("inspectLifecycle treats typed step-limit signal as forced finalization", () => {
  const lifecycle = inspectLifecycle({
    messages: [
      {
        parts: [
          { type: "tool", tool: "read", state: { status: "completed" } },
          { type: "step-finish", reason: "step-limit" },
        ],
      },
    ],
    finalInfo: { id: "m-limit", finish: "step-limit", time: { completed: 1 } },
    structuredOutput: { verdict: "PASS", blocking_findings: 0, report_markdown: "# OK" },
  });
  assert.equal(lifecycle.forced_finalization, true);
  assert.equal(lifecycle.finalization_voluntary, false);
});

test("complete prompt-response lifecycle is authoritative without calling session.messages", async () => {
  let messagesCalled = false;
  const audit = await auditSessionMessages({
    client: {
      session: {
        messages: async () => {
          messagesCalled = true;
          return { data: [] };
        },
      },
    },
    sessionId: "sess-authoritative",
    directory: "E:\\repo",
    promptMessage: {
      info: { id: "msg-auth", sessionID: "sess-authoritative" },
      parts: [
        { type: "tool", tool: "read", state: { status: "completed" } },
        { type: "step-finish", reason: "tool-calls" },
      ],
    },
    finalInfo: { id: "msg-auth", sessionID: "sess-authoritative" },
    candidate: "C3",
    structuredOutput: { verdict: "PASS", blocking_findings: 0, report_markdown: "# OK" },
  });
  assert.equal(audit.valid, true);
  assert.equal(audit.source, "prompt-response");
  assert.equal(messagesCalled, false);
});

test("incomplete prompt-response falls back to session.messages", async () => {
  let messagesCalled = false;
  const audit = await auditSessionMessages({
    client: {
      session: {
        messages: async () => {
          messagesCalled = true;
          return {
            data: [
              {
                info: { id: "msg-fallback" },
                parts: [
                  { type: "tool", tool: "read", state: { status: "completed" } },
                  { type: "step-finish", reason: "stop" },
                ],
              },
            ],
          };
        },
      },
    },
    sessionId: "sess-fallback",
    directory: "E:\\repo",
    promptMessage: {
      info: { id: "msg-fallback" },
      parts: [{ type: "text", text: "no tool call here" }],
    },
    finalInfo: { id: "msg-fallback" },
    candidate: "C3",
    structuredOutput: null,
  });
  assert.equal(messagesCalled, true);
  assert.equal(audit.valid, true);
  assert.equal(audit.source, "session.messages");
});

test("session.messages decoder failure fails closed without salvage", async () => {
  const audit = await auditSessionMessages({
    client: {
      session: {
        messages: async () => {
          throw new Error('Expected OutputFormatJsonSchema, got {"type":"json_schema"}');
        },
      },
    },
    sessionId: "sess-decoder-fail",
    directory: "E:\\repo",
    promptMessage: {
      info: { id: "msg-fail" },
      parts: [{ type: "text" }],
    },
    finalInfo: { id: "msg-fail" },
    candidate: "C3",
    structuredOutput: null,
  });
  assert.equal(audit.valid, false);
  assert.equal(audit.source, "session.messages");
  assert.match(audit.diagnostic, /OutputFormatJsonSchema/);
});

test("session.messages rejects stale message without same final id", async () => {
  const audit = await auditSessionMessages({
    client: {
      session: {
        messages: async () => ({
          data: [
            {
              info: { id: "stale-id-from-prior-session" },
              parts: [
                { type: "tool", tool: "read", state: { status: "completed" } },
                { type: "step-finish", reason: "stop" },
              ],
            },
          ],
        }),
      },
    },
    sessionId: "sess-stale",
    directory: "E:\\repo",
    promptMessage: {
      info: { id: "current-msg-id" },
      parts: [{ type: "text" }],
    },
    finalInfo: { id: "current-msg-id" },
    candidate: "C3",
    structuredOutput: null,
  });
  assert.equal(audit.valid, false);
  assert.equal(audit.source, "session.messages");
  assert.match(audit.diagnostic, /incomplete same-attempt lifecycle evidence/);
});

test("runProbe with finish=tool-calls and complete prompt lifecycle classifies as PASS_PROVEN", async () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3" });
  const c3ToolCallsTransport = async () => ({
    server: { cleanup: async () => ({ proven: true }) },
    client: {
      session: {
        create: async () => ({ data: { id: "c3-session-tc" } }),
        prompt: async () => ({
          data: {
            info: {
              id: "msg-tc",
              finish: "tool-calls",
              time: { completed: 1 },
              structured: { verdict: "PASS", blocking_findings: 0, report_markdown: "# Done" },
            },
            parts: [
              { type: "tool", tool: "read", state: { status: "completed" } },
              { type: "step-finish", reason: "tool-calls" },
            ],
          },
        }),
        messages: async () => { throw new Error("must not be called"); },
      },
    },
  });

  const result = await runProbe(config, {
    getRuntimeMetadata: async () => runtimeFor(config),
    createTransport: c3ToolCallsTransport,
  });
  assert.equal(result.classification, "PASS_PROVEN");
  assert.equal(result.lifecycle_audit_source, "prompt-response");
  assert.equal(result.lifecycle_audit_trustworthy, true);
  assert.equal(result.lifecycle.forced_finalization, false);
  assert.equal(result.lifecycle.finalization_voluntary, true);
});
