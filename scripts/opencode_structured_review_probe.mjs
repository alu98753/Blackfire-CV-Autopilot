import { execFile, spawn } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve, delimiter } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const ISOLATED_DATABASE = ":memory:";
const MAX_DIAGNOSTIC_LENGTH = 600;
export const DEFAULT_PROBE_TIMEOUT_MS = 40_000;
export const C3_PROBE_TIMEOUT_MS = 480_000;
export const PROBE_TIMEOUT_MS = DEFAULT_PROBE_TIMEOUT_MS;
const CLEANUP_TIMEOUT_MS = 5_000;
const SERVER_STARTUP_TIMEOUT_MS = 10_000;

export function probeTimeoutForCandidate(candidate) {
  if (candidate === "C3") return C3_PROBE_TIMEOUT_MS;
  return DEFAULT_PROBE_TIMEOUT_MS;
}
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
  C3: Object.freeze({
    id: "C3",
    runtimeVersion: "1.18.31",
    clientPackage: "@opencode-ai/sdk",
    clientVersion: "1.18.31",
    transport: "official-sdk-v2",
    structuredField: "assistant.info.structured",
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
  if (candidate !== "CONTROL" && candidate !== "C3" && (typeof runtimeRoot !== "string" || runtimeRoot.trim().length === 0)) {
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
  if (config.candidate === "C3") {
    return {
      sessionID: sessionId,
      directory: config.directory,
      agent: config.agent,
      model: { providerID: config.provider, modelID: config.modelId },
      parts: [{ type: "text", text: prompt }],
      format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 },
    };
  }
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
  if (candidate === "C1" || candidate === "C3") return { available: true, field: runtime.structuredField, value: finalInfo?.structured };
  return {
    available: false,
    field: null,
    diagnostic: "v2.0.2 @opencode/client session.prompt has no official JSON-schema structured-result transport",
  };
}

function toolParts(messages) {
  return messages.flatMap((message) => Array.isArray(message?.parts) ? message.parts : []).filter((part) => part?.type === "tool");
}

export function hasAuthoritativePromptResponse({ promptMessage, finalInfo, structuredOutput, sessionId } = {}) {
  if (!promptMessage || typeof promptMessage !== "object") return false;
  if (!finalInfo || typeof finalInfo !== "object") return false;
  if (typeof finalInfo.id !== "string" || finalInfo.id.length === 0) return false;
  if (promptMessage.info && promptMessage.info !== finalInfo && promptMessage.info.id !== finalInfo.id) return false;
  if (typeof sessionId === "string" && sessionId.length > 0) {
    const sessionMatch = finalInfo.sessionID ?? finalInfo.sessionId;
    if (typeof sessionMatch === "string" && sessionMatch !== sessionId) return false;
  }
  if (structuredOutput === undefined || structuredOutput === null) return false;

  const parts = promptMessage.parts;
  if (!Array.isArray(parts) || parts.length === 0) return false;
  const validParts = parts.every((part) => part && typeof part === "object" && typeof part.type === "string");
  if (!validParts) return false;

  const hasSuccessfulTool = parts.some(
    (part) => part.type === "tool" && READ_SEARCH_TOOLS.has(part.tool) && part.state?.status === "completed",
  );
  const hasStepFinish = parts.some(
    (part) => part.type === "step-finish" && typeof part.reason === "string" && part.reason.length > 0,
  );
  return hasSuccessfulTool && hasStepFinish;
}

export async function auditSessionMessages({
  client,
  sessionId,
  directory,
  promptMessage,
  finalInfo,
  candidate = "CONTROL",
  structuredOutput,
}) {
  if (hasAuthoritativePromptResponse({ promptMessage, finalInfo, structuredOutput, sessionId })) {
    return { valid: true, source: "prompt-response", messages: [promptMessage] };
  }
  let response;
  try {
    if (candidate === "C3") {
      response = await client.session.messages({ sessionID: sessionId, directory, throwOnError: true });
    } else {
      response = await client.session.messages({ path: { id: sessionId }, query: { directory }, throwOnError: true });
    }
  } catch (error) {
    return { valid: false, source: "session.messages", diagnostic: redactDiagnostic(`session.messages failed: ${error?.message ?? error}`) };
  }
  const messages = response?.data;
  const finalId = finalInfo?.id;
  const validShape = Array.isArray(messages) && messages.every((message) => message && typeof message === "object"
    && Array.isArray(message.parts) && message.parts.every((part) => part && typeof part === "object" && typeof part.type === "string"));
  const containsSameFinal = validShape && typeof finalId === "string" && messages.some((message) => message.info?.id === finalId);
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
  const forced = reasons.some((reason) => /max[-_ ]?steps?|step[-_ ]?limit|step[-_ ]?budget/i.test(reason));
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

function infrastructureEvidence(config, runtime, diagnostic, subreason) {
  return {
    ...evidenceBase(config, runtime),
    classification: "FAIL_INFRASTRUCTURE",
    diagnostic: redactDiagnostic(diagnostic),
    subreason,
    lifecycle: emptyLifecycle(),
    schema_validation: { valid: false, errors: [] },
    semantic_validation: { valid: false, errors: [] },
  };
}

function evidenceBase(config, runtime) {
  const entry = matrixEntry(config.candidate);
  const base = {
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
  if (entry.transport) {
    base.sdk_transport = entry.transport;
  }
  return base;
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

function waitForExit(child, timeoutMs = CLEANUP_TIMEOUT_MS) {
  if (child?.exitCode !== null && child?.exitCode !== undefined) return Promise.resolve(true);
  return new Promise((resolvePromise) => {
    const timer = setTimeout(() => resolvePromise(false), timeoutMs);
    child.once("exit", () => {
      clearTimeout(timer);
      resolvePromise(true);
    });
  });
}

export function isPidAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

async function taskKillProcessTree(pid, commandRunner = execFileText) {
  const commandShell = process.env.ComSpec ?? "cmd.exe";
  await commandRunner(commandShell, ["/d", "/s", "/c", `taskkill /PID ${pid} /T /F < NUL`]);
}

export async function terminateOwnedProcessTree(child, dependencies = {}) {
  const pid = child?.pid;
  if (!Number.isInteger(pid) || pid <= 0) {
    return { proven: false, diagnostic: "probe runner did not receive an owned process-tree root" };
  }

  const checkPidAlive = dependencies.isPidAlive ?? isPidAlive;
  const checkDescendants = dependencies.checkDescendants ?? (() => []);
  const taskKill = dependencies.taskKill ?? taskKillProcessTree;
  const retryTaskKill = dependencies.retryTaskKill ?? taskKill;
  const waitForChildExit = dependencies.waitForChildExit ?? waitForExit;
  const timeoutMs = dependencies.cleanupTimeoutMs ?? CLEANUP_TIMEOUT_MS;

  let descendants = await checkDescendants(pid);
  if ((child.exitCode !== null && child.exitCode !== undefined) && !checkPidAlive(pid) && descendants.length === 0) {
    return { proven: true, pid };
  }

  try {
    child.kill?.();
  } catch {}

  let taskKillError = null;
  try {
    await taskKill(pid);
  } catch (error) {
    taskKillError = error;
  }

  await waitForChildExit(child, Math.min(2000, timeoutMs)).catch(() => false);
  let rootAlive = checkPidAlive(pid);
  descendants = await checkDescendants(pid);

  if (!rootAlive && descendants.length === 0) {
    return { proven: true, pid };
  }

  try {
    await retryTaskKill(pid);
  } catch (error) {
    taskKillError = error;
  }

  await waitForChildExit(child, Math.min(1000, timeoutMs)).catch(() => false);
  rootAlive = checkPidAlive(pid);
  descendants = await checkDescendants(pid);

  if (!rootAlive && descendants.length === 0) {
    return { proven: true, pid };
  }

  if (descendants.length > 0) {
    return { proven: false, diagnostic: `owned descendant processes [${descendants.join(", ")}] remained after cleanup` };
  }

  if (rootAlive) {
    return { proven: false, diagnostic: `owned process tree root ${pid} did not exit after taskkill` };
  }

  return {
    proven: false,
    diagnostic: taskKillError ? `owned process tree cleanup failed: ${diagnosticFromError(taskKillError)}` : `owned process tree ${pid} state could not be proven`,
  };
}

function waitForServerAddress(child, timeoutMs) {
  return new Promise((resolvePromise, reject) => {
    let output = "";
    const timer = setTimeout(() => reject(new Error(`Timeout waiting for owned server to start after ${timeoutMs}ms`)), timeoutMs);
    const settle = (callback, value) => {
      clearTimeout(timer);
      child.stdout?.off("data", onOutput);
      child.stderr?.off("data", onOutput);
      child.off("exit", onExit);
      child.stdout?.resume();
      child.stderr?.resume();
      callback(value);
    };
    const onOutput = (chunk) => {
      output = redactDiagnostic(`${output}${chunk}`.slice(-MAX_DIAGNOSTIC_LENGTH));
      const line = output.split(/\r?\n/).find((entry) => entry.startsWith("opencode server listening"));
      const match = line?.match(/on\s+(https?:\/\/[^\s]+)/);
      if (match) settle(resolvePromise, match[1]);
    };
    const onExit = (code) => settle(reject, new Error(`owned OpenCode server exited with code ${code}: ${output}`));
    child.stdout?.on("data", onOutput);
    child.stderr?.on("data", onOutput);
    child.once("exit", onExit);
  });
}

class ProbeTimeoutError extends Error {
  constructor(timeoutMs) {
    super(`probe runner timeout after ${timeoutMs}ms`);
  }
}

async function runWithinDeadline(operation, timeoutMs) {
  let timer;
  const operationPromise = Promise.resolve().then(operation);
  operationPromise.catch(() => { });
  try {
    return await Promise.race([
      operationPromise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new ProbeTimeoutError(timeoutMs)), timeoutMs); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
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
  const commandShell = process.env.ComSpec ?? "cmd.exe";
  const child = spawn(commandShell, ["/d", "/s", "/c", "opencode serve --hostname=127.0.0.1 --port=0 < NUL"], {
    detached: true,
    env: { ...process.env, OPENCODE_CONFIG_CONTENT: "{}" },
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  try {
    const baseUrl = await waitForServerAddress(child, SERVER_STARTUP_TIMEOUT_MS);
    return {
      client: sdk.createOpencodeClient({ baseUrl }),
      server: {
        cleanup: () => terminateOwnedProcessTree(child),
      },
    };
  } catch (error) {
    await terminateOwnedProcessTree(child);
    throw error;
  }
}

async function createC3Transport() {
  const sdkV2 = await import("@opencode-ai/sdk/v2");
  const { default: launch } = await import("cross-spawn");
  const child = launch("opencode", ["serve", "--hostname=127.0.0.1", "--port=0"], {
    env: { ...process.env, OPENCODE_DB: ":memory:", OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_CONFIG_CONTENT: "{}" },
    stdio: ["ignore", "pipe", "pipe"],
  });
  try {
    const baseUrl = await waitForServerAddress(child, SERVER_STARTUP_TIMEOUT_MS);
    return {
      client: sdkV2.createOpencodeClient({ baseUrl }),
      server: {
        cleanup: async () => {
          child.stdout?.destroy();
          child.stderr?.destroy();
          return await terminateOwnedProcessTree(child);
        },
      },
    };
  } catch (error) {
    await terminateOwnedProcessTree(child);
    throw error;
  }
}

async function cleanupTransport(transport) {
  if (!transport?.server) return { proven: true };
  try {
    if (typeof transport.server.cleanup === "function") return await transport.server.cleanup();
    await transport.server.close?.();
    return { proven: true };
  } catch (error) {
    return { proven: false, diagnostic: `probe transport cleanup failed: ${diagnosticFromError(error)}` };
  }
}

export async function runProbe(config, dependencies = {}) {
  const getRuntimeMetadata = dependencies.getRuntimeMetadata ?? ((candidate) => runtimeMetadata(candidate));
  const defaultTransport = config.candidate === "C3" ? createC3Transport : createC1Transport;
  const createTransport = dependencies.createTransport ?? defaultTransport;
  let runtime = { opencode_version: "unavailable", client_version: "unavailable" };
  try {
    const environment = dependencies.environment ?? process.env;
    runtime = await withIsolatedRuntimeEnvironment({ ...config, environment }, async () => getRuntimeMetadata(config));
    if (!validateRuntimeMetadata(config, runtime)) return infrastructureEvidence(config, runtime, "exact runtime/client version mismatch", "VERSION_MISMATCH");
    const adapter = normalizeStructuredResult(config.candidate, {});
    if (!adapter.available) {
      return infrastructureEvidence(config, runtime, adapter.diagnostic, "STRUCTURED_ADAPTER_UNAVAILABLE");
    }
    return await withIsolatedRuntimeEnvironment({ ...config, environment }, async () => {
      let opencode;
      let evidence;
      try {
        opencode = await createTransport(config);
        evidence = await runWithinDeadline(async () => {
          const createArgs = config.candidate === "C3"
            ? { directory: config.directory, throwOnError: true }
            : { query: { directory: config.directory }, throwOnError: true };
          const session = await opencode.client.session.create(createArgs);
          const sessionId = session?.data?.id;
          if (typeof sessionId !== "string" || sessionId.length === 0) throw new Error("OpenCode session.create returned no session id");
          const prompt = config.attemptKind === "smoke" ? buildSmokePrompt() : buildReviewerPrompt();
          const promptResult = await opencode.client.session.prompt({ ...buildPromptRequest(config, sessionId, prompt), throwOnError: true });
          const finalInfo = promptResult?.data?.info;
          if (!finalInfo || typeof finalInfo !== "object") throw new Error("OpenCode session.prompt returned no assistant message info");
          const promptMessage = { info: finalInfo, parts: promptResult?.data?.parts ?? [] };
          const normalized = normalizeStructuredResult(config.candidate, finalInfo);
          const audit = await auditSessionMessages({
            client: opencode.client,
            directory: config.directory,
            finalInfo,
            promptMessage,
            sessionId,
            candidate: config.candidate,
            structuredOutput: normalized.value,
          });
          if (!audit.valid) return { ...evidenceBase(config, runtime), lifecycle_audit_source: audit.source, lifecycle_audit_trustworthy: false, lifecycle: emptyLifecycle(), schema_validation: { valid: false, errors: [] }, semantic_validation: { valid: false, errors: [] }, classification: "FAIL_LIFECYCLE_AUDIT", diagnostic: audit.diagnostic, subreason: "AUDIT_UNTRUSTWORTHY" };
          const lifecycle = inspectLifecycle({ messages: audit.messages, finalInfo, structuredOutput: normalized.value });
          const schema = lifecycle.structured_output_present ? validateOutcomeSchema(normalized.value) : { valid: false, errors: ["structured result is missing"] };
          const semantics = schema.valid ? validateOutcomeSemantics(normalized.value) : { valid: false, errors: [] };
          const classification = classifyLifecycle({ lifecycle, schema, semantics });
          const evidenceResult = {
            ...evidenceBase(config, runtime),
            lifecycle_audit_source: audit.source,
            lifecycle_audit_trustworthy: true,
            official_structured_machine_field: normalized.field,
            lifecycle,
            schema_validation: schema,
            semantic_validation: semantics,
            classification,
          };
          if (classification === "FAIL_LIFECYCLE_AUDIT") {
            if (lifecycle.forced_finalization || !lifecycle.finalization_voluntary) {
              evidenceResult.subreason = "STEP_BUDGET_EXHAUSTED";
              evidenceResult.diagnostic = "model did not voluntarily finalize before step budget exhaustion";
            } else if (!lifecycle.successful_tool_result) {
              evidenceResult.subreason = "TOOL_RESULT_FAILED";
              evidenceResult.diagnostic = "read/search tool was called but did not return a successful completed result";
            }
          }
          return evidenceResult;
        }, dependencies.probeTimeoutMs ?? probeTimeoutForCandidate(config.candidate));
      } catch (error) {
        evidence = error instanceof ProbeTimeoutError
          ? infrastructureEvidence(config, runtime, error.message, "PROBE_TIMEOUT")
          : infrastructureEvidence(config, runtime, diagnosticFromError(error), "RUNTIME_OR_TRANSPORT_FAILURE");
      } finally {
        const cleanup = await cleanupTransport(opencode);
        if (evidence) {
          evidence.isolation_cleanup_proven = cleanup.proven;
          evidence.owned_process_tree_pid = cleanup.pid ?? null;
        }
        if (!cleanup.proven) evidence = infrastructureEvidence(config, runtime, cleanup.diagnostic, "ISOLATION_CLEANUP_UNSAFE");
      }
      return evidence;
    });
  } catch (error) {
    return infrastructureEvidence(config, runtime, diagnosticFromError(error), "RUNTIME_OR_TRANSPORT_FAILURE");
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
