import assert from "node:assert/strict";
import test from "node:test";
import {
  OUTCOME_SCHEMA,
  auditSessionMessages,
  buildProbeConfig,
  buildPromptRequest,
  classifyLifecycle,
  createIsolatedOpenCode,
  inspectLifecycle,
  openCodeVersionCommand,
  redactDiagnostic,
  runProbe,
  validateOutcomeSchema,
  validateOutcomeSemantics,
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

test("probe config and SDK prompt request preserve the pinned reviewer contract", () => {
  const config = buildProbeConfig({
    agent: "spec-reviewer",
    model: "opencode/big-pickle",
    directory: ".",
  });
  const request = buildPromptRequest(config, "session-1", "review now");

  assert.equal(config.provider, "opencode");
  assert.equal(config.modelId, "big-pickle");
  assert.equal(config.expectedOpenCodeVersion, "1.18.31");
  assert.equal(config.stateDatabase, ":memory:");
  assert.equal(request.path.id, "session-1");
  assert.deepEqual(request.body.model, { providerID: "opencode", modelID: "big-pickle" });
  assert.equal(request.body.format.type, "json_schema");
  assert.deepEqual(request.body.format.schema, OUTCOME_SCHEMA);
  assert.equal(request.body.format.retryCount, 2);
});

test("fixed schema accepts only the reviewer outcome shape", () => {
  assert.deepEqual(validateOutcomeSchema({
    verdict: "PASS",
    blocking_findings: 0,
    report_markdown: "# Spec Review",
  }), { valid: true, errors: [] });

  const invalid = validateOutcomeSchema({
    verdict: "PASS",
    blocking_findings: -1,
    report_markdown: 2,
    reconstructed_verdict: "PASS",
  });
  assert.equal(invalid.valid, false);
  assert.match(invalid.errors.join("\n"), /additional property/);
  assert.match(invalid.errors.join("\n"), /non-negative integer/);
  assert.match(invalid.errors.join("\n"), /must be a string/);
});

test("semantic validation enforces PASS and BLOCK cross-fields", () => {
  assert.deepEqual(validateOutcomeSemantics({ verdict: "PASS", blocking_findings: 0 }), { valid: true, errors: [] });
  assert.deepEqual(validateOutcomeSemantics({ verdict: "BLOCK", blocking_findings: 1 }), { valid: true, errors: [] });
  assert.equal(validateOutcomeSemantics({ verdict: "PASS", blocking_findings: 1 }).valid, false);
  assert.equal(validateOutcomeSemantics({ verdict: "BLOCK", blocking_findings: 0 }).valid, false);
});

test("lifecycle inspection requires a completed repository read/search tool result", () => {
  const lifecycle = inspectLifecycle({
    finalInfo: { finish: "stop", time: { completed: 1 } },
    structuredOutput: { verdict: "PASS" },
    messages: [{
      parts: [
        { type: "tool", tool: "read", state: { status: "completed" } },
        { type: "step-finish", reason: "stop" },
      ],
    }],
  });
  assert.equal(lifecycle.read_search_tool_called, true);
  assert.equal(lifecycle.successful_tool_result, true);
  assert.equal(lifecycle.finalization_voluntary, true);

  const noResult = inspectLifecycle({
    finalInfo: { finish: "stop", time: { completed: 1 } },
    structuredOutput: {},
    messages: [{ parts: [{ type: "tool", tool: "read", state: { status: "error" } }] }],
  });
  assert.equal(noResult.successful_tool_result, false);
});

test("successful session-message retrieval is the authoritative lifecycle audit", async () => {
  const audit = await auditSessionMessages({
    client: {
      session: {
        messages: async () => ({ data: [{ parts: [{ type: "tool", tool: "read", state: { status: "completed" } }] }] }),
      },
    },
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    sessionId: "session-1",
  });
  assert.equal(audit.valid, true);
  assert.equal(audit.source, "session.messages");
  assert.equal(audit.messages[0].parts[0].state.status, "completed");
});

test("session-message retrieval failure fails closed instead of becoming FAIL_TOOL_CHOICE", async () => {
  const config = buildProbeConfig({ agent: "spec-reviewer", model: "opencode/big-pickle", directory: "." });
  const result = await runProbe(config, {
    getRuntimeMetadata: async () => ({ opencode_version: "1.18.31", sdk_version: "1.18.31" }),
    createServer: async () => ({
      server: { close() {} },
      client: {
        session: {
          create: async () => ({ data: { id: "session-1" } }),
          prompt: async () => ({ data: { info: { finish: "stop", time: { completed: 1 } }, parts: [{ type: "text" }] } }),
          messages: async () => { throw new Error("fetch failed"); },
        },
      },
    }),
  });
  assert.equal(result.classification, "FAIL_LIFECYCLE_AUDIT");
  assert.match(result.diagnostic, /session\.messages failed/);
});

test("malformed session-message response fails closed", async () => {
  const audit = await auditSessionMessages({
    client: { session: { messages: async () => ({ data: [{ parts: [null] }] }) } },
    directory: "E:\\repo",
    promptMessage: { parts: [{ type: "text" }] },
    sessionId: "session-1",
  });
  assert.equal(audit.valid, false);
  assert.equal(audit.classification, "FAIL_LIFECYCLE_AUDIT");
  assert.match(audit.diagnostic, /unusable response shape/);
});

test("missing and malformed structured output have deterministic classifications", () => {
  const missing = classifyLifecycle({
    lifecycle: successfulLifecycle({ structured_output_present: false }),
    schema: { valid: false, errors: ["structured_output is missing"] },
    semantics: { valid: false, errors: [] },
  });
  assert.equal(missing, "FAIL_MISSING_STRUCTURED_OUTPUT");

  const malformedSchema = validateOutcomeSchema({
    verdict: "MAYBE",
    blocking_findings: 0,
    report_markdown: "report",
  });
  const malformed = classifyLifecycle({
    lifecycle: successfulLifecycle(),
    schema: malformedSchema,
    semantics: { valid: true, errors: [] },
  });
  assert.equal(malformed, "FAIL_SCHEMA");
});

test("diagnostics are bounded and redact credential-like values", () => {
  const diagnostic = redactDiagnostic(`Bearer secret-value api_key=example-secret sk_abcdefghijk ${"x".repeat(800)}`);
  assert.ok(diagnostic.length <= 600);
  assert.doesNotMatch(diagnostic, /secret-value|example-secret|sk_abcdefghijk/);
  assert.match(diagnostic, /REDACTED/);
});

test("OpenCode server creation uses an isolated memory database and restores caller state", async () => {
  const environment = { OPENCODE_DB: "C:\\user-state\\opencode.db" };
  let observed;
  const server = await createIsolatedOpenCode(async () => {
    observed = environment.OPENCODE_DB;
    return { client: {}, server: { close() {} } };
  }, environment);

  assert.equal(observed, ":memory:");
  assert.equal(environment.OPENCODE_DB, "C:\\user-state\\opencode.db");
  assert.equal(typeof server.server.close, "function");
});

test("version probe uses the Windows non-interactive command wrapper without changing production version policy", () => {
  assert.deepEqual(openCodeVersionCommand("win32", "C:\\Windows\\System32\\cmd.exe"), {
    command: "C:\\Windows\\System32\\cmd.exe",
    args: ["/d", "/s", "/c", "opencode --version < NUL"],
  });
  assert.deepEqual(openCodeVersionCommand("linux"), { command: "opencode", args: ["--version"] });
});
