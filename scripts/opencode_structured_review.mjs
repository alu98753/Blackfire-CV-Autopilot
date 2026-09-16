import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { spawn } from "node:child_process";

export const OUTCOME_SCHEMA = {
  type: "object", additionalProperties: false,
  properties: {
    verdict: { type: "string", enum: ["PASS", "BLOCK"] },
    blocking_findings: { type: "integer", minimum: 0 },
    report_markdown: { type: "string" },
  },
  required: ["verdict", "blocking_findings", "report_markdown"],
};
const TOOLS = new Set(["read", "glob", "grep"]);
const LIMIT = 600;

export function validateSchema(value) {
  const errors = [];
  if (!value || typeof value !== "object" || Array.isArray(value)) return { valid: false, errors: ["structured result must be an object"] };
  for (const key of OUTCOME_SCHEMA.required) if (!(key in value)) errors.push(`missing required property: ${key}`);
  for (const key of Object.keys(value)) if (!OUTCOME_SCHEMA.properties[key]) errors.push(`additional property is not allowed: ${key}`);
  if ("verdict" in value && !["PASS", "BLOCK"].includes(value.verdict)) errors.push("verdict must be PASS or BLOCK");
  if ("blocking_findings" in value && (!Number.isInteger(value.blocking_findings) || value.blocking_findings < 0)) errors.push("blocking_findings must be a non-negative integer");
  if ("report_markdown" in value && typeof value.report_markdown !== "string") errors.push("report_markdown must be a string");
  return { valid: errors.length === 0, errors };
}

export function validateSemantics(value) {
  const errors = [];
  if (value?.verdict === "PASS" && value.blocking_findings !== 0) errors.push("PASS requires blocking_findings == 0");
  if (value?.verdict === "BLOCK" && value.blocking_findings < 1) errors.push("BLOCK requires blocking_findings >= 1");
  return { valid: errors.length === 0, errors };
}

export function qualifyLifecycle({ parts, events, sessionID, messageID, structured }) {
  // `events` is the only chronology source. Prompt response parts are used
  // for final-message identity and structured payload confirmation only.
  const ordered = events.filter((part) => part?.sessionID === sessionID);
  const repoTools = ordered.filter((part) => part?.type === "tool" && TOOLS.has(part.tool));
  const finalPart = (part) => part?.messageID === messageID;
  const structuredIndex = ordered.findIndex((part) => finalPart(part) && part?.type === "tool" && part.tool === "StructuredOutput" && part.state?.status === "completed");
  const groundingIndex = repoTools.findIndex((part) => part.state?.status === "completed");
  const finalMessageIdentity = typeof messageID === "string" && parts.length > 0 && parts.every((part) => !part.messageID || part.messageID === messageID);
  return {
    source: "typed-event-and-prompt-response", session_id: sessionID, message_id: messageID ?? null,
    final_message_identity: finalMessageIdentity, terminal_step: ordered.some((part) => finalPart(part) && part.type === "step-finish"),
    repository_tool_called: repoTools.length > 0, completed_repository_tool: groundingIndex >= 0,
    structured_output_completed: structuredIndex >= 0, final_structured_message_identity: structuredIndex >= 0, grounding_before_structured: groundingIndex >= 0 && structuredIndex >= 0 && groundingIndex < structuredIndex,
    event_count: events.length, finish: null, structured_present: structured !== undefined && structured !== null,
  };
}

export function lifecycleCompletionBoundary({ events, sessionID, messageID, promptParts, structured }) {
  const lifecycle = qualifyLifecycle({ parts: promptParts, events, sessionID, messageID, structured });
  return {
    complete: lifecycle.final_message_identity && lifecycle.terminal_step && lifecycle.completed_repository_tool && lifecycle.structured_output_completed && lifecycle.grounding_before_structured,
    lifecycle,
  };
}

export function qualifyAttempt({ sessionID, info, events }) {
  if (!info || typeof info !== "object" || typeof info.id !== "string" || info.id.length === 0 || typeof info.sessionID !== "string" || info.sessionID.length === 0 || info.sessionID !== sessionID) {
    return { classification: "STRUCTURED_TRANSPORT_FAILED", reason: "successful prompt response lacks a matching assistant identity" };
  }
  const grounded = events.some((part) => part?.sessionID === sessionID && part.type === "tool" && TOOLS.has(part.tool) && part.state?.status === "completed");
  if (!grounded) return { classification: "GROUNDING_FAILED", reason: "no completed same-session repository tool was observed" };
  if (info.structured === undefined || info.structured === null) return { classification: "STRUCTURED_OUTPUT_MISSING", reason: "prompt response has no info.structured" };
  const schema = validateSchema(info.structured);
  if (!schema.valid) return { classification: "SCHEMA_INVALID", schema_validation: schema };
  const semantics = validateSemantics(info.structured);
  if (!semantics.valid) return { classification: "SEMANTIC_CONTRADICTION", schema_validation: schema, semantic_validation: semantics };
  return { classification: info.structured.verdict === "PASS" ? "VALID_PASS" : "VALID_BLOCK", schema_validation: schema, semantic_validation: semantics };
}

export function redact(value) {
  const text = String(value ?? "unknown error").replace(/Bearer\s+[^\s,;]+/gi, "Bearer [REDACTED]").replace(/\b(?:sk|pk|api)[_-][A-Za-z0-9_-]{8,}\b/gi, "[REDACTED]");
  return text.length <= LIMIT ? text : `${text.slice(0, LIMIT - 3)}...`;
}

function argument(name) { const i = process.argv.indexOf(name); return i < 0 ? undefined : process.argv[i + 1]; }
function required(name) { const value = argument(name); if (!value) throw new Error(`Missing required argument: ${name}`); return value; }

function waitForServer(child, timeout = 10000) {
  return new Promise((resolveAddress, reject) => {
    let buffer = ""; const timer = setTimeout(() => reject(new Error("OpenCode server startup timed out")), timeout);
    const onData = (data) => { buffer += data.toString(); const match = buffer.match(/https?:\/\/[^\s]+/); if (match) { clearTimeout(timer); resolveAddress(match[0].replace(/[).]+$/, "")); } };
    child.stdout.on("data", onData); child.stderr.on("data", onData);
    child.once("error", (error) => { clearTimeout(timer); reject(error); });
    child.once("exit", (code) => { if (code !== null) { clearTimeout(timer); reject(new Error(`OpenCode server exited with code ${code}`)); } });
  });
}
function waitForClose(stream, timeoutMs = 3000) {
  if (!stream || stream.destroyed || stream.readableEnded) return Promise.resolve(true);
  return new Promise((done) => {
    const timer = setTimeout(() => done(false), timeoutMs);
    stream.once("close", () => { clearTimeout(timer); done(true); });
    stream.once("end", () => { clearTimeout(timer); done(true); });
  });
}
export async function stopServer(server, { platform = process.platform, timeoutMs = 3000 } = {}) {
  let treeTerminationConfirmed = false;
  if (platform === "win32") {
      const killer = spawn("taskkill.exe", ["/PID", String(server.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      treeTerminationConfirmed = await new Promise((done) => {
        const timer = setTimeout(() => done(false), timeoutMs);
        killer.once("exit", (code) => { clearTimeout(timer); done(code === 0 || server.exitCode !== null); });
        killer.once("error", () => { clearTimeout(timer); done(false); });
      });
  } else if (server.exitCode === null) {
      try { server.kill(); } catch { return { tree_termination_confirmed: false, stdout_closed: false, stderr_closed: false, safe: false }; }
      treeTerminationConfirmed = await new Promise((done) => {
        const timer = setTimeout(() => done(false), timeoutMs);
        if (server.exitCode !== null) { clearTimeout(timer); done(true); }
        else server.once("exit", () => { clearTimeout(timer); done(true); });
      });
  } else { treeTerminationConfirmed = true; }
  const wrapperExited = server.exitCode !== null || await new Promise((done) => {
    const timer = setTimeout(() => done(false), timeoutMs);
    server.once("exit", () => { clearTimeout(timer); done(true); });
  });
  const [stdoutClosed, stderrClosed] = await Promise.all([waitForClose(server.stdout, timeoutMs), waitForClose(server.stderr, timeoutMs)]);
  return { tree_termination_confirmed: treeTerminationConfirmed, wrapper_exited: wrapperExited, stdout_closed: stdoutClosed, stderr_closed: stderrClosed, safe: treeTerminationConfirmed && wrapperExited && stdoutClosed && stderrClosed };
}
export function buildServerLaunch(platform = process.platform, shell = process.env.ComSpec ?? "cmd.exe") {
  const serverArgs = ["serve", "--hostname=127.0.0.1", "--port=0"];
  if (platform === "win32") {
    // Keep the command body fixed: no user-controlled value is interpolated
    // into cmd.exe, and NUL gives the server an explicit non-interactive EOF.
    return { executable: shell, args: ["/d", "/s", "/c", "opencode serve --hostname=127.0.0.1 --port=0 < NUL"] };
  }
  return { executable: "opencode", args: serverArgs };
}

export async function settleEventConsumer({ consumer, stream, abortController, timeoutMs = 3000 }) {
  abortController?.abort();
  try { await stream?.return?.(); } catch { /* cancellation is best effort; settlement is authoritative */ }
  const settled = Promise.resolve(consumer).then(() => true, () => false);
  return await Promise.race([settled, new Promise((resolveSettled) => setTimeout(() => resolveSettled(false), timeoutMs))]);
}

async function run() {
  const agent = required("--agent"); const model = required("--model"); const directory = resolve(required("--directory"));
  const prompt = await readFile(resolve(required("--prompt-file")), "utf8");
  const slash = model.indexOf("/"); if (slash <= 0 || slash === model.length - 1) throw new Error(`Invalid model: ${model}`);
  const sdk = await import("@opencode-ai/sdk/v2");
  const launch = buildServerLaunch();
  const server = spawn(launch.executable, launch.args, { cwd: directory, env: { ...process.env, OPENCODE_DB: ":memory:", OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_CONFIG_CONTENT: "{}" }, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
  let client; let cleanup = { safe: false, server_exit_confirmed: false, consumer_settled: false, subscription_cancelled: false };
  let consumer; let stream; let abortController;
  try {
    client = sdk.createOpencodeClient({ baseUrl: await waitForServer(server), throwOnError: true });
    const events = []; let subscription; let subscriptionEstablished = false;
    abortController = new AbortController();
    try { subscription = await client.event.subscribe({ signal: abortController.signal }); } catch (error) { throw new Error(`event.subscribe failed: ${redact(error.message)}`); }
    subscriptionEstablished = true;
    stream = subscription?.stream;
    consumer = (async () => { if (stream && Symbol.asyncIterator in stream) for await (const event of stream) { if (event?.properties?.part) events.push(event.properties.part); } })();
    const session = await client.session.create({ directory });
    const sessionID = session?.data?.id; if (!sessionID) throw new Error("session.create returned no session id");
    const result = await client.session.prompt({ sessionID, directory, agent, model: { providerID: model.slice(0, slash), modelID: model.slice(slash + 1) }, parts: [{ type: "text", text: prompt }], format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 } });
    const info = result?.data?.info; const parts = Array.isArray(result?.data?.parts) ? result.data.parts : [];
    const deadline = Date.now() + 5000; let boundary;
    do { boundary = lifecycleCompletionBoundary({ events, sessionID, messageID: info?.id, promptParts: parts, structured: info?.structured }); if (boundary.complete || Date.now() >= deadline) break; await new Promise((r) => setTimeout(r, 25)); } while (true);
    const lifecycle = boundary.lifecycle; lifecycle.finish = info?.finish ?? null; lifecycle.subscription_established_before_prompt = subscriptionEstablished; lifecycle.completion_boundary = boundary.complete ? "same-session-event-sequence" : "bounded-deadline";
    const structured = info?.structured; const attempt = qualifyAttempt({ sessionID, info, events }); const classification = attempt.classification;
    cleanup.consumer_settled = await settleEventConsumer({ consumer, stream, abortController }); cleanup.subscription_cancelled = Boolean(abortController?.signal.aborted);
    const serverCleanup = await stopServer(server); cleanup.server_exit_confirmed = serverCleanup.wrapper_exited; cleanup.process_tree_termination_confirmed = serverCleanup.tree_termination_confirmed; cleanup.stdout_closed = serverCleanup.stdout_closed; cleanup.stderr_closed = serverCleanup.stderr_closed; cleanup.safe = cleanup.consumer_settled && serverCleanup.safe;
    process.stdout.write(JSON.stringify({ schema_version: 1, agent, model, session_id: sessionID, message_id: info?.id ?? null, classification: cleanup.safe ? classification : "INFRASTRUCTURE_FAILED", lifecycle, structured: structured ?? null, schema_validation: attempt.schema_validation ?? null, semantic_validation: attempt.semantic_validation ?? null, cleanup }) + "\n");
  } finally { if (!cleanup.consumer_settled && consumer) { cleanup.consumer_settled = await settleEventConsumer({ consumer, stream, abortController }); cleanup.subscription_cancelled = Boolean(abortController?.signal.aborted); } if (!cleanup.server_exit_confirmed) { const serverCleanup = await stopServer(server); cleanup.server_exit_confirmed = serverCleanup.wrapper_exited; cleanup.process_tree_termination_confirmed = serverCleanup.tree_termination_confirmed; cleanup.stdout_closed = serverCleanup.stdout_closed; cleanup.stderr_closed = serverCleanup.stderr_closed; cleanup.safe = cleanup.consumer_settled && serverCleanup.safe; } }
}

if (pathToFileURL(resolve(process.argv[1] ?? "")).href === import.meta.url) run().catch((error) => { process.stderr.write(`STRUCTURED_REVIEW_ADAPTER_ERROR: ${redact(error.message)}\n`); process.exitCode = 1; });
