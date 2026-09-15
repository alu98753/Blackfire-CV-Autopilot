import { execFile } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createOpencode } from "@opencode-ai/sdk";

const SCRIPT_DIRECTORY = dirname(fileURLToPath(import.meta.url));
const DEFAULT_OPEN_CODE_VERSION = "1.18.31";
const ISOLATED_DATABASE = ":memory:";
const MAX_DIAGNOSTIC_LENGTH = 600;
const ALLOWED_REVIEWER_AGENTS = new Set(["spec-reviewer", "regression-reviewer"]);
const READ_SEARCH_TOOLS = new Set(["read", "glob", "grep"]);

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

export function buildProbeConfig({ agent, model, directory, expectedOpenCodeVersion = DEFAULT_OPEN_CODE_VERSION }) {
  if (!ALLOWED_REVIEWER_AGENTS.has(agent)) {
    throw new Error("Probe agent must be spec-reviewer or regression-reviewer.");
  }
  if (typeof model !== "string" || !/^[^/\s]+\/[^/\s]+$/.test(model)) {
    throw new Error("Model must use provider/model form.");
  }
  if (typeof directory !== "string" || directory.trim().length === 0) {
    throw new Error("A repository directory is required.");
  }
  if (typeof expectedOpenCodeVersion !== "string" || expectedOpenCodeVersion.trim().length === 0) {
    throw new Error("An expected OpenCode version is required.");
  }

  const [provider, modelId] = model.split("/");
  return {
    agent,
    directory: resolve(directory),
    expectedOpenCodeVersion,
    model,
    modelId,
    provider,
    stateDatabase: ISOLATED_DATABASE,
  };
}

export function buildReviewerPrompt(agent) {
  const taskPath = "docs/tasks/opencode-structured-review-provider-compatibility";
  return [
    "Conduct a bounded, read-only review using your production reviewer contract.",
    `Read ${taskPath}/task.json, ${taskPath}/SPEC.md, and ${taskPath}/CONTEXT.md before finalizing.`,
    "Use at least one permitted repository read/search tool (read, glob, or grep) and wait for its successful result.",
    "Stop tool use once sufficient evidence is available; reserve a final assistant turn rather than consuming the maximum step budget.",
    "Do not edit files, execute shell commands, launch subagents, or use external tools.",
    `This is the live structured-output compatibility probe for the ${agent} production role.`,
  ].join("\n");
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

  const keys = Object.keys(payload);
  for (const required of OUTCOME_SCHEMA.required) {
    if (!(required in payload)) errors.push(`missing required property: ${required}`);
  }
  for (const key of keys) {
    if (!(key in OUTCOME_SCHEMA.properties)) errors.push(`additional property is not allowed: ${key}`);
  }
  if ("verdict" in payload && !["PASS", "BLOCK"].includes(payload.verdict)) {
    errors.push("verdict must be PASS or BLOCK");
  }
  if ("blocking_findings" in payload
    && (!Number.isInteger(payload.blocking_findings) || payload.blocking_findings < 0)) {
    errors.push("blocking_findings must be a non-negative integer");
  }
  if ("report_markdown" in payload && typeof payload.report_markdown !== "string") {
    errors.push("report_markdown must be a string");
  }
  return { valid: errors.length === 0, errors };
}

export function validateOutcomeSemantics(payload) {
  const errors = [];
  if (payload?.verdict === "PASS" && payload.blocking_findings !== 0) {
    errors.push("PASS requires blocking_findings to equal 0");
  }
  if (payload?.verdict === "BLOCK" && payload.blocking_findings < 1) {
    errors.push("BLOCK requires blocking_findings to be at least 1");
  }
  return { valid: errors.length === 0, errors };
}

export function redactDiagnostic(value, limit = MAX_DIAGNOSTIC_LENGTH) {
  const text = String(value ?? "unknown error")
    .replace(/Bearer\s+[^\s,;]+/gi, "Bearer [REDACTED]")
    .replace(/\b(sk|pk|api)[_-][A-Za-z0-9_-]{8,}\b/gi, "[REDACTED]")
    .replace(/(api[_-]?key|token|password)\s*[=:]\s*[^\s,;]+/gi, "$1=[REDACTED]");
  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 3))}...`;
}

function toolParts(messages) {
  return messages.flatMap((message) => Array.isArray(message?.parts) ? message.parts : [])
    .filter((part) => part?.type === "tool");
}

function finishReasons(messages, finalInfo) {
  const reasons = [];
  if (typeof finalInfo?.finish === "string" && finalInfo.finish.length > 0) reasons.push(finalInfo.finish);
  for (const part of messages.flatMap((message) => Array.isArray(message?.parts) ? message.parts : [])) {
    if (part?.type === "step-finish" && typeof part.reason === "string" && part.reason.length > 0) {
      reasons.push(part.reason);
    }
  }
  return [...new Set(reasons)];
}

export function inspectLifecycle({ messages, finalInfo, structuredOutput }) {
  const calls = toolParts(messages);
  const allowedCalls = calls.filter((part) => READ_SEARCH_TOOLS.has(part.tool));
  const successfulAllowedResults = allowedCalls.filter((part) => part?.state?.status === "completed");
  const reasons = finishReasons(messages, finalInfo);
  const forced = reasons.some((reason) => /tool-calls|max[-_ ]?steps?|step[-_ ]?limit/i.test(reason));
  const completed = Boolean(finalInfo?.time?.completed) || reasons.length > 0;
  return {
    finish_reasons: reasons,
    finalization_voluntary: completed && !forced,
    forced_finalization: forced,
    read_search_tool_called: allowedCalls.length > 0,
    structured_output_present: structuredOutput !== undefined && structuredOutput !== null,
    successful_tool_result: successfulAllowedResults.length > 0,
  };
}

export function classifyLifecycle({ lifecycle, schema, semantics }) {
  if (!lifecycle.read_search_tool_called) return "FAIL_TOOL_CHOICE";
  if (!lifecycle.successful_tool_result) return "FAIL_TOOL_RESULT";
  if (!lifecycle.finalization_voluntary) return "FAIL_FINALIZATION";
  if (!lifecycle.structured_output_present) return "FAIL_MISSING_STRUCTURED_OUTPUT";
  if (!schema.valid || !semantics.valid) return "FAIL_SCHEMA";
  return "PASS_PROVEN";
}

export function classifyThrownError(error) {
  const detail = redactDiagnostic(error?.message ?? error);
  if (/tool[_ -]?choice|tool choice|unsupported tool/i.test(detail)) return "FAIL_TOOL_CHOICE";
  if (/fetch|network|econn|connection|timed out|timeout|http \d{3}|session\.(create|prompt)/i.test(detail)) {
    return "FAIL_TRANSPORT";
  }
  return "FAIL_INFRASTRUCTURE";
}

export async function createIsolatedOpenCode(createServer = createOpencode, environment = process.env) {
  const previous = environment.OPENCODE_DB;
  environment.OPENCODE_DB = ISOLATED_DATABASE;
  try {
    return await createServer({ hostname: "127.0.0.1", port: 0 });
  } finally {
    if (previous === undefined) delete environment.OPENCODE_DB;
    else environment.OPENCODE_DB = previous;
  }
}

function execFileText(command, args) {
  return new Promise((resolvePromise, reject) => {
    execFile(command, args, { encoding: "utf8", maxBuffer: 16 * 1024, timeout: 15_000, windowsHide: true },
      (error, stdout, stderr) => {
        if (error) {
          reject(new Error(`${error.message}; stderr=${redactDiagnostic(stderr, 240)}`));
          return;
        }
        resolvePromise(String(stdout).trim());
      });
  });
}

export function openCodeVersionCommand(platform = process.platform, commandShell = process.env.ComSpec ?? "cmd.exe") {
  if (platform === "win32") {
    return { command: commandShell, args: ["/d", "/s", "/c", "opencode --version < NUL"] };
  }
  return { command: "opencode", args: ["--version"] };
}

async function runtimeMetadata(commandRunner = execFileText) {
  const sdkPackage = JSON.parse(await readFile(resolve(SCRIPT_DIRECTORY, "../node_modules/@opencode-ai/sdk/package.json"), "utf8"));
  const versionCommand = openCodeVersionCommand();
  return {
    opencode_version: await commandRunner(versionCommand.command, versionCommand.args),
    sdk_version: sdkPackage.version,
  };
}

function evidenceBase(config, runtime) {
  return {
    attempt_kind: "live_production_reviewer",
    open_code_version: runtime.opencode_version,
    provider: config.provider,
    reviewer_role: config.agent,
    sdk_version: runtime.sdk_version,
    state_isolation: "OPENCODE_DB=:memory:",
    model: config.model,
  };
}

export async function runProbe(config, dependencies = {}) {
  const getRuntimeMetadata = dependencies.getRuntimeMetadata ?? runtimeMetadata;
  const createServer = dependencies.createServer ?? createOpencode;
  let server;
  let runtime = { opencode_version: "unavailable", sdk_version: "unavailable" };
  try {
    runtime = await getRuntimeMetadata();
    if (runtime.opencode_version !== config.expectedOpenCodeVersion) {
      throw new Error(`OpenCode version mismatch: expected ${config.expectedOpenCodeVersion}, got ${runtime.opencode_version}`);
    }
    const opencode = await createIsolatedOpenCode(createServer);
    server = opencode.server;
    const session = await opencode.client.session.create({
      query: { directory: config.directory },
      throwOnError: true,
    });
    const sessionId = session?.data?.id;
    if (typeof sessionId !== "string" || sessionId.length === 0) {
      throw new Error("OpenCode session.create returned no session id");
    }
    const promptResult = await opencode.client.session.prompt({
      ...buildPromptRequest(config, sessionId, buildReviewerPrompt(config.agent)),
      throwOnError: true,
    });
    const finalInfo = promptResult?.data?.info;
    if (!finalInfo || typeof finalInfo !== "object") {
      throw new Error("OpenCode session.prompt returned no assistant message info");
    }
    const promptMessage = { info: finalInfo, parts: promptResult?.data?.parts ?? [] };
    let messages = [promptMessage];
    try {
      const sessionMessages = await opencode.client.session.messages({
        path: { id: sessionId },
        query: { directory: config.directory },
        throwOnError: true,
      });
      if (Array.isArray(sessionMessages?.data)) messages = sessionMessages.data;
    } catch {
      // The prompt response still exposes its parts; do not turn a retrievable final response into a raw dump.
    }
    const structuredOutput = finalInfo.structured_output;
    const lifecycle = inspectLifecycle({ messages, finalInfo, structuredOutput });
    const schema = lifecycle.structured_output_present
      ? validateOutcomeSchema(structuredOutput)
      : { valid: false, errors: ["structured_output is missing"] };
    const semantics = schema.valid
      ? validateOutcomeSemantics(structuredOutput)
      : { valid: false, errors: [] };
    return {
      ...evidenceBase(config, runtime),
      lifecycle,
      schema_validation: schema,
      semantic_validation: semantics,
      classification: classifyLifecycle({ lifecycle, schema, semantics }),
    };
  } catch (error) {
    return {
      ...evidenceBase(config, runtime),
      lifecycle: {
        finish_reasons: [],
        finalization_voluntary: false,
        forced_finalization: false,
        read_search_tool_called: false,
        structured_output_present: false,
        successful_tool_result: false,
      },
      schema_validation: { valid: false, errors: [] },
      semantic_validation: { valid: false, errors: [] },
      classification: classifyThrownError(error),
      diagnostic: redactDiagnostic(error?.message ?? error),
    };
  } finally {
    server?.close();
  }
}

function argumentValue(args, name) {
  const index = args.indexOf(name);
  return index < 0 ? undefined : args[index + 1];
}

export function parseArguments(args) {
  if (args.includes("--help")) return { help: true };
  const config = buildProbeConfig({
    agent: argumentValue(args, "--agent"),
    directory: argumentValue(args, "--directory"),
    expectedOpenCodeVersion: argumentValue(args, "--expected-opencode-version") ?? DEFAULT_OPEN_CODE_VERSION,
    model: argumentValue(args, "--model"),
  });
  return { config, evidenceFile: argumentValue(args, "--evidence-file") };
}

async function main() {
  const parsed = parseArguments(process.argv.slice(2));
  if (parsed.help) {
    process.stdout.write("Usage: node scripts/opencode_structured_review_probe.mjs --agent spec-reviewer|regression-reviewer --model provider/model --directory <repo> [--evidence-file <path>]\n");
    return;
  }
  const evidence = await runProbe(parsed.config);
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
