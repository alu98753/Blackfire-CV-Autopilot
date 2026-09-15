import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import test from "node:test";
import {
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
  inspectLifecycle,
  normalizeStructuredResult,
  openCodeVersionCommand,
  redactDiagnostic,
  runProbe,
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
        messages: async () => ({ data: [] }),
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

test("frozen matrix accepts only control, C1, and C2", () => {
  assert.equal(RUNTIME_MATRIX.C1.runtimeVersion, "1.14.41");
  assert.equal(RUNTIME_MATRIX.C2.clientPackage, "@opencode/client");
  assert.equal(controlConfig().expectedOpenCodeVersion, "1.18.31");
  const c1 = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C1", runtimeRoot: ".runtime/c1" });
  assert.equal(c1.expectedClientVersion, "1.14.41");
  assert.throws(() => buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: ".", candidate: "C3", runtimeRoot: ".runtime/c3" }), /Unlisted/);
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

test("full and smoke prompts are fixed across candidates and models", () => {
  assert.equal(buildReviewerPrompt("C1", "opencode/big-pickle"), buildReviewerPrompt("C2", "opencode/mimo-v2.5-free"));
  assert.equal(buildSmokePrompt("C1"), buildSmokePrompt("C2"));
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
