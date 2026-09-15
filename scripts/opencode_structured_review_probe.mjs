import { execFile } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve, delimiter } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const ISOLATED_DATABASE = ":memory:";
const MAX_DIAGNOSTIC_LENGTH = 600;
const ALLOWED_REVIEWER_AGENTS = new Set(["spec-reviewer", "regression-reviewer"]);
const ALLOWED_MODELS = new Set(["opencode/big-pickle", "opencode/mimo-v2.5-free"]);
const READ_SEARCH_TOOLS = new Set(["read", "glob", "grep"]);
const PHASE2_CLASSIFICATIONS = new Set([
  "PASS_PROVEN",
  "FAIL_TOOL_CHOICE",
  "FAIL_LIFECYCLE_AUDIT",
  "FAIL_STRUCTURED_OUTPUT",
  "FAIL_SCHEMA",
  "FAIL_SEMANTIC",
  "FAIL_INFRASTRUCTURE",
]);

export const RUNTIME_MATRIX = Object.freeze({
  CONTROL: Object.freeze({
    id: "CONTROL",
    runtimeVersion: "1.18.31",
    clientPackage: "@opencode-ai/sdk",
    clientVersion: "1.18.31",
    structuredField: "response.data.info.structured_output",
  }),
  C1: Object.freeze({
    id: "C1",
    runtimeVersion: "1.14.41",
    clientPackage: "@opencode-ai/sdk",
    clientVersion: "1.14.41",
    structuredField: "assistant.info.structured",
  }),
  C2: Object.freeze({
    id: "C2",
    runtimeVersion: "2.0.2",
    clientPackage: "@opencode/client",
    clientVersion: "2.0.2",
    structuredField: null,
  }),
});

export const OUTCOME_SCHEMA = {
  type: "object",
  additionalProperties: false,
  properties: {
    verdict: { type: "string", enum: ["PASS", "BLOCK"] },
    blocking_findings: { type: "integer", minimum: 0 },
    report_markdown: { type: "string" },
  },
  required: ["verdict", "blocking_findings", "report_markdown"],
};

const QUALIFICATION_PROMPT = [
  "Conduct a bounded, read-only review using your production reviewer contract.",
  "Read docs/tasks/opencode-structured-review-provider-compatibility/task.json, docs/tasks/opencode-structured-review-provider-compatibility/SPEC.md, and docs/tasks/opencode-structured-review-provider-compatibility/CONTEXT.md before finalizing.",
  "Use at least one permitted repository read/search tool (read, glob, or grep) and wait for its successful result.",
  "Stop tool use once sufficient evidence is available; reserve a final assistant turn rather than consuming the maximum step budget.",
  "Do not edit files, execute shell commands, launch subagents, or use external tools.",
].join("\n");

const SMOKE_PROMPT = [
  "Conduct a bounded, read-only compatibility smoke review using your production reviewer contract.",
  "Read docs/tasks/opencode-structured-review-provider-compatibility/task.json before finalizing.",
  "Use at least one permitted repository read/search tool (read, glob, or grep) and wait for its successful result.",
  "Stop tool use once sufficient evidence is available; reserve a final assistant turn rather than consuming the maximum step budget.",
  "Do not edit files, execute shell commands, launch subagents, or use external tools.",
].join("\n");

function matrixEntry(candidate) {
  const entry = RUNTIME_MATRIX[candidate];
  if (!entry) throw new Error(`Unlisted OpenCode runtime candidate: ${candidate}`);
  return entry;
}

export function buildProbeConfig({ agent, model, directory, candidate = "CONTROL", attemptKind = "qualifying", runtimeRoot }) {
  const runtime = matrixEntry(candidate);
  if (!ALLOWED_REVIEWER_AGENTS.has(agent)) {
    throw new Error("Probe agent must be spec-reviewer or regression-reviewer.");
  }
  if (!ALLOWED_MODELS.has(model)) {
    throw new Error("Model is not in the frozen provider/model matrix.");
  }
  if (typeof directory !== "string" || directory.trim().length === 0) {
    throw new Error("A repository directory is required.");
  }
  if (!new Set(["smoke", "qualifying", "confirmation"]).has(attemptKind)) {
    throw new Error("Attempt kind must be smoke, qualifying, or confirmation.");
  }
  if (candidate !== "CONTROL" && (typeof runtimeRoot !== "string" || runtimeRoot.trim().length === 0)) {
    throw new Error("Alternate runtimes require an isolated runtime root.");
  }

  const [provider, modelId] = model.split("/");
  return {
    agent,
    attemptKind,
    candidate,
    clientPackage: runtime.clientPackage,
    directory: resolve(directory),
    expectedClientVersion: runtime.clientVersion,
    expectedOpenCodeVersion: runtime.runtimeVersion,
    model,
    modelId,
    provider,
    runtimeRoot: runtimeRoot ? resolve(runtimeRoot) : undefined,
    stateDatabase: ISOLATED_DATABASE,
  };
}

export function buildReviewerPrompt() {
  return QUALIFICATION_PROMPT;
}

export function buildSmokePrompt() {
  return SMOKE_PROMPT;
}

export function buildPromptRequest(config, sessionId, prompt) {
  return {
    path: { id: sessionId },
    query: { directory: config.directory },
    body: {
      agent: config.agent,
      model: { providerID: config.provider, modelID: config.modelId },
      parts: [{ type: "text", text: prompt }],
      format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 },
    },
  };
}

export function validateOutcomeSchema(payload) {
  const errors = [];
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
    return { valid: false, errors: ["structured_output must be an object"] };
  }
  for (const required of OUTCOME_SCHEMA.required) {
    if (!(required in payload)) errors.push(`missing required property: ${required}`);
  }
  for (const key of Object.keys(payload)) {
    if (!(key in OUTCOME_SCHEMA.properties)) errors.push(`additional property is not allowed: ${key}`);
  }
  if ("verdict" in payload && !["PASS", "BLOCK"].includes(payload.verdict)) errors.push("verdict must be PASS or BLOCK");
  if ("blocking_findings" in payload && (!Number.isInteger(payload.blocking_findings) || payload.blocking_findings < 0)) {
    errors.push("blocking_findings must be a non-negative integer");
  }
  if ("report_markdown" in payload && typeof payload.report_markdown !== "string") errors.push("report_markdown must be a string");
  return { valid: errors.length === 0, errors };
}

export function validateOutcomeSemantics(payload) {
  const errors = [];
  if (payload?.verdict === "PASS" && payload.blocking_findings !== 0) errors.push("PASS requires blocking_findings to equal 0");
  if (payload?.verdict === "BLOCK" && payload.blocking_findings < 1) errors.push("BLOCK requires blocking_findings to be at least 1");
  return { valid: errors.length === 0, errors };
}

export function redactDiagnostic(value, limit = MAX_DIAGNOSTIC_LENGTH) {
  const text = String(value ?? "unknown error")
    .replace(/Bearer\s+[^\s,;]+/gi, "Bearer [REDACTED]")
    .replace(/\b(sk|pk|api)[_-][A-Za-z0-9_-]{8,}\b/gi, "[REDACTED]")
    .replace(/(["']?(?:api[_-]?key|token|password)["']?\s*[:=]\s*["']?)[^\s,;"}]+/gi, "$1[REDACTED]");
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 3))}...`;
}

export function diagnosticFromError(error) {
  if (typeof error?.message === "string" && error.message.length > 0) return redactDiagnostic(error.message);
  try {
    return redactDiagnostic(JSON.stringify(error));
  } catch {
    return redactDiagnostic(error);
  }
}

export function normalizeStructuredResult(candidate, finalInfo) {
  const runtime = matrixEntry(candidate);
  if (candidate === "CONTROL") return { available: true, field: runtime.structuredField, value: finalInfo?.structured_output };
  if (candidate === "C1") return { available: true, field: runtime.structuredField, value: finalInfo?.structured };
  return {
    available: false,
    field: null,
    diagnostic: "v2.0.2 @opencode/client session.prompt has no official JSON-schema structured-result transport",
  };
}

function toolParts(messages) {
  return messages.flatMap((message) => Array.isArray(message?.parts) ? message.parts : []).filter((part) => part?.type === "tool");
}

function hasUsablePromptParts(promptMessage) {
  const parts = promptMessage?.parts;
  if (!Array.isArray(parts) || parts.length === 0
    || !parts.every((part) => part && typeof part === "object" && typeof part.type === "string")) return false;
  return parts.some((part) => part.type === "tool" && READ_SEARCH_TOOLS.has(part.tool) && part.state?.status === "completed")
    && parts.some((part) => part.type === "step-finish" && typeof part.reason === "string");
}

export async function auditSessionMessages({ client, sessionId, directory, promptMessage, finalInfo }) {
  if (hasUsablePromptParts(promptMessage)) {
    return { valid: true, source: "prompt-response", messages: [promptMessage] };
  }
  let response;
  try {
    response = await client.session.messages({ path: { id: sessionId }, query: { directory }, throwOnError: true });
  } catch (error) {
    return { valid: false, source: "session.messages", diagnostic: redactDiagnostic(`session.messages failed: ${error?.message ?? error}`) };
  }
  const messages = response?.data;
  const finalId = finalInfo?.id;
  const validShape = Array.isArray(messages) && messages.every((message) => message && typeof message === "object"
    && Array.isArray(message.parts) && message.parts.every((part) => part && typeof part === "object" && typeof part.type === "string"));
  const containsSameFinal = typeof finalId === "string" && messages.some((message) => message.info?.id === finalId);
  if (!validShape || !containsSameFinal) {
    return { valid: false, source: "session.messages", diagnostic: "session.messages returned incomplete same-attempt lifecycle evidence" };
  }
  return { valid: true, source: "session.messages", messages };
}

function finishReasons(messages, finalInfo) {
  const reasons = [];
  if (typeof finalInfo?.finish === "string" && finalInfo.finish.length > 0) reasons.push(finalInfo.finish);
  for (const part of messages.flatMap((message) => Array.isArray(message?.parts) ? message.parts : [])) {
    if (part?.type === "step-finish" && typeof part.reason === "string" && part.reason.length > 0) reasons.push(part.reason);
  }
  return [...new Set(reasons)];
}

export function inspectLifecycle({ messages, finalInfo, structuredOutput }) {
  const calls = toolParts(messages);
  const allowedCalls = calls.filter((part) => READ_SEARCH_TOOLS.has(part.tool));
  const reasons = finishReasons(messages, finalInfo);
  const forced = reasons.some((reason) => /tool-calls|max[-_ ]?steps?|step[-_ ]?limit/i.test(reason));
  return {
    finish_reasons: reasons,
    finalization_voluntary: (Boolean(finalInfo?.time?.completed) || reasons.length > 0) && !forced,
    forced_finalization: forced,
    read_search_tool_called: allowedCalls.length > 0,
    successful_tool_result: allowedCalls.some((part) => part?.state?.status === "completed"),
    structured_output_present: structuredOutput !== undefined && structuredOutput !== null,
  };
}

export function classifyLifecycle({ lifecycle, schema, semantics }) {
  if (!lifecycle.read_search_tool_called) return "FAIL_TOOL_CHOICE";
  if (!lifecycle.successful_tool_result || !lifecycle.finalization_voluntary) return "FAIL_LIFECYCLE_AUDIT";
  if (!lifecycle.structured_output_present) return "FAIL_STRUCTURED_OUTPUT";
  if (!schema.valid) return "FAIL_SCHEMA";
  if (!semantics.valid) return "FAIL_SEMANTIC";
  return "PASS_PROVEN";
}

function emptyLifecycle() {
  return { finish_reasons: [], finalization_voluntary: false, forced_finalization: false, read_search_tool_called: false, successful_tool_result: false, structured_output_present: false };
}

function evidenceBase(config, runtime) {
  return {
    attempt_kind: config.attemptKind,
    client_package: config.clientPackage,
    client_version: runtime.client_version,
    isolation_method: "isolated runtime root + OPENCODE_DB=:memory: + restored PATH/environment",
    matrix_candidate: config.candidate,
    model: config.model,
    open_code_version: runtime.opencode_version,
    provider: config.provider,
    reviewer_role: config.agent,
  };
}

export function validateRuntimeMetadata(config, runtime) {
  return runtime?.opencode_version === config.expectedOpenCodeVersion && runtime?.client_version === config.expectedClientVersion;
}

export async function withIsolatedRuntimeEnvironment({ candidate, runtimeRoot, environment = process.env }, operation) {
  const previous = Object.fromEntries(["PATH", "OPENCODE_DB", "OPENCODE_DISABLE_AUTOUPDATE"].map((key) => [key, environment[key]]));
  environment.OPENCODE_DB = ISOLATED_DATABASE;
  environment.OPENCODE_DISABLE_AUTOUPDATE = "1";
  if (candidate !== "CONTROL" && runtimeRoot) environment.PATH = `${resolve(runtimeRoot, "node_modules", ".bin")}${delimiter}${previous.PATH ?? ""}`;
  try {
    return await operation();
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete environment[key];
      else environment[key] = value;
    }
  }
}

function execFileText(command, args, environment = process.env) {
  return new Promise((resolvePromise, reject) => {
    execFile(command, args, { encoding: "utf8", env: environment, maxBuffer: 16 * 1024, timeout: 15_000, windowsHide: true }, (error, stdout, stderr) => {
      if (error) return reject(new Error(`${error.message}; stderr=${redactDiagnostic(stderr, 240)}`));
      resolvePromise(String(stdout).trim());
    });
  });
}

export function openCodeVersionCommand(platform = process.platform, commandShell = process.env.ComSpec ?? "cmd.exe") {
  return platform === "win32"
    ? { command: commandShell, args: ["/d", "/s", "/c", "opencode --version < NUL"] }
    : { command: "opencode", args: ["--version"] };
}

async function runtimeMetadata(config, commandRunner = execFileText, environment = process.env) {
  const packagePath = config.runtimeRoot
    ? resolve(config.runtimeRoot, "node_modules", ...config.clientPackage.split("/"), "package.json")
    : resolve(SCRIPT_DIRECTORY, "../node_modules", ...config.clientPackage.split("/"), "package.json");
  const clientPackage = JSON.parse(await readFile(packagePath, "utf8"));
  const command = openCodeVersionCommand();
  return { opencode_version: await commandRunner(command.command, command.args, environment), client_version: clientPackage.version };
}

async function createC1Transport(config) {
  const sdk = await import(pathToFileURL(resolve(config.runtimeRoot, "node_modules", "@opencode-ai", "sdk", "dist", "index.js")).href);
  return sdk.createOpencode({ hostname: "127.0.0.1", port: 0, timeout: 30_000 });
}

export async function runProbe(config, dependencies = {}) {
  const getRuntimeMetadata = dependencies.getRuntimeMetadata ?? ((candidate) => runtimeMetadata(candidate));
  const createTransport = dependencies.createTransport ?? createC1Transport;
  let runtime = { opencode_version: "unavailable", client_version: "unavailable" };
  try {
    runtime = await withIsolatedRuntimeEnvironment(config, async () => getRuntimeMetadata(config));
    if (!validateRuntimeMetadata(config, runtime)) {
      return { ...evidenceBase(config, runtime), classification: "FAIL_INFRASTRUCTURE", diagnostic: "exact runtime/client version mismatch", subreason: "VERSION_MISMATCH", lifecycle: emptyLifecycle(), schema_validation: { valid: false, errors: [] }, semantic_validation: { valid: false, errors: [] } };
    }
    const adapter = normalizeStructuredResult(config.candidate, {});
    if (!adapter.available) {
      return { ...evidenceBase(config, runtime), classification: "FAIL_INFRASTRUCTURE", diagnostic: adapter.diagnostic, subreason: "STRUCTURED_ADAPTER_UNAVAILABLE", lifecycle: emptyLifecycle(), schema_validation: { valid: false, errors: [] }, semantic_validation: { valid: false, errors: [] } };
    }
    return await withIsolatedRuntimeEnvironment(config, async () => {
      const opencode = await createTransport(config);
      try {
        const session = await opencode.client.session.create({ query: { directory: config.directory }, throwOnError: true });
        const sessionId = session?.data?.id;
        if (typeof sessionId !== "string" || sessionId.length === 0) throw new Error("OpenCode session.create returned no session id");
        const prompt = config.attemptKind === "smoke" ? buildSmokePrompt() : buildReviewerPrompt();
        const promptResult = await opencode.client.session.prompt({ ...buildPromptRequest(config, sessionId, prompt), throwOnError: true });
        const finalInfo = promptResult?.data?.info;
        if (!finalInfo || typeof finalInfo !== "object") throw new Error("OpenCode session.prompt returned no assistant message info");
        const promptMessage = { info: finalInfo, parts: promptResult?.data?.parts ?? [] };
        const audit = await auditSessionMessages({ client: opencode.client, directory: config.directory, finalInfo, promptMessage, sessionId });
        if (!audit.valid) return { ...evidenceBase(config, runtime), lifecycle_audit_source: audit.source, lifecycle_audit_trustworthy: false, lifecycle: emptyLifecycle(), schema_validation: { valid: false, errors: [] }, semantic_validation: { valid: false, errors: [] }, classification: "FAIL_LIFECYCLE_AUDIT", diagnostic: audit.diagnostic, subreason: "AUDIT_UNTRUSTWORTHY" };
        const normalized = normalizeStructuredResult(config.candidate, finalInfo);
        const lifecycle = inspectLifecycle({ messages: audit.messages, finalInfo, structuredOutput: normalized.value });
        const schema = lifecycle.structured_output_present ? validateOutcomeSchema(normalized.value) : { valid: false, errors: ["structured result is missing"] };
        const semantics = schema.valid ? validateOutcomeSemantics(normalized.value) : { valid: false, errors: [] };
        return { ...evidenceBase(config, runtime), lifecycle_audit_source: audit.source, lifecycle_audit_trustworthy: true, official_structured_machine_field: normalized.field, lifecycle, schema_validation: schema, semantic_validation: semantics, classification: classifyLifecycle({ lifecycle, schema, semantics }) };
      } finally {
        await opencode.server?.close?.();
      }
    });
  } catch (error) {
    return { ...evidenceBase(config, runtime), classification: "FAIL_INFRASTRUCTURE", diagnostic: diagnosticFromError(error), subreason: "RUNTIME_OR_TRANSPORT_FAILURE", lifecycle: emptyLifecycle(), schema_validation: { valid: false, errors: [] }, semantic_validation: { valid: false, errors: [] } };
  }
}

export function aggregateRepeatability(attempts) {
  const qualifying = attempts.filter((attempt) => attempt.attempt_kind !== "smoke");
  if (qualifying.length !== 4) return { stable: false, reason: "requires exactly four qualifying attempts" };
  const expectedRoles = ["spec-reviewer", "regression-reviewer", "spec-reviewer", "regression-reviewer"];
  const first = qualifying[0];
  const sameRoute = qualifying.every((attempt, index) => attempt.reviewer_role === expectedRoles[index]
    && attempt.matrix_candidate === first.matrix_candidate && attempt.open_code_version === first.open_code_version
    && attempt.client_package === first.client_package && attempt.client_version === first.client_version
    && attempt.provider === first.provider && attempt.model === first.model);
  return { stable: sameRoute && qualifying.every((attempt) => attempt.classification === "PASS_PROVEN"), reason: sameRoute ? undefined : "attempts must share the exact route and required role order" };
}

function argumentValue(args, name) {
  const index = args.indexOf(name);
  return index < 0 ? undefined : args[index + 1];
}

export function parseArguments(args) {
  if (args.includes("--help")) return { help: true };
  return {
    config: buildProbeConfig({ agent: argumentValue(args, "--agent"), attemptKind: argumentValue(args, "--attempt-kind") ?? "qualifying", candidate: argumentValue(args, "--candidate") ?? "CONTROL", directory: argumentValue(args, "--directory"), model: argumentValue(args, "--model"), runtimeRoot: argumentValue(args, "--runtime-root") }),
    evidenceFile: argumentValue(args, "--evidence-file"),
  };
}

async function main() {
  const parsed = parseArguments(process.argv.slice(2));
  if (parsed.help) {
    process.stdout.write("Usage: node scripts/opencode_structured_review_probe.mjs --candidate CONTROL|C1|C2 --agent spec-reviewer|regression-reviewer --attempt-kind smoke|qualifying|confirmation --model opencode/big-pickle|opencode/mimo-v2.5-free --directory <repo> [--runtime-root <isolated-root>] [--evidence-file <path>]\n");
    return;
  }
  const evidence = await runProbe(parsed.config);
  if (!PHASE2_CLASSIFICATIONS.has(evidence.classification)) throw new Error("invalid Phase 2 classification");
  const serialized = `${JSON.stringify(evidence, null, 2)}\n`;
  if (parsed.evidenceFile) await writeFile(resolve(parsed.evidenceFile), serialized, "utf8");
  process.stdout.write(serialized);
  process.exitCode = evidence.classification === "PASS_PROVEN" ? 0 : 2;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  main().catch((error) => {
    process.stderr.write(`STRUCTURED_REVIEW_PROBE_ERROR: ${redactDiagnostic(error?.message ?? error)}\n`);
    process.exitCode = 1;
  });
}
