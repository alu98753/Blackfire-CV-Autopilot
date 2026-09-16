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
  const ordered = [...parts, ...events].filter((part) => part?.sessionID === sessionID || !part?.sessionID);
  const repoTools = ordered.filter((part) => part?.type === "tool" && TOOLS.has(part.tool));
  const structuredIndex = ordered.findIndex((part) => part?.type === "tool" && part.tool === "StructuredOutput" && part.state?.status === "completed");
  const groundingIndex = repoTools.findIndex((part) => part.state?.status === "completed");
  const finalMessageIdentity = typeof messageID === "string" && parts.length > 0 && parts.every((part) => !part.messageID || part.messageID === messageID);
  return {
    source: "typed-event-and-prompt-response", session_id: sessionID, message_id: messageID ?? null,
    final_message_identity: finalMessageIdentity, terminal_step: parts.some((part) => part.type === "step-finish"),
    repository_tool_called: repoTools.length > 0, completed_repository_tool: groundingIndex >= 0,
    structured_output_completed: structuredIndex >= 0, grounding_before_structured: groundingIndex >= 0 && structuredIndex >= 0 && groundingIndex < structuredIndex,
    event_count: events.length, finish: null, structured_present: structured !== undefined && structured !== null,
  };
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
async function stopServer(server) {
  if (server.exitCode !== null) return true;
  try { server.kill(); } catch { return false; }
  return await new Promise((done) => {
    const timer = setTimeout(() => done(false), 3000);
    server.once("exit", () => { clearTimeout(timer); done(true); });
  });
}

async function run() {
  const agent = required("--agent"); const model = required("--model"); const directory = resolve(required("--directory"));
  const prompt = await readFile(resolve(required("--prompt-file")), "utf8");
  const slash = model.indexOf("/"); if (slash <= 0 || slash === model.length - 1) throw new Error(`Invalid model: ${model}`);
  const sdk = await import("@opencode-ai/sdk/v2");
  const server = spawn("opencode", ["serve", "--hostname=127.0.0.1", "--port=0"], { env: { ...process.env, OPENCODE_DB: ":memory:", OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_CONFIG_CONTENT: "{}" }, stdio: ["ignore", "pipe", "pipe"], windowsHide: true });
  let client; let cleanup = { safe: false, server_exit_confirmed: false };
  try {
    client = sdk.createOpencodeClient({ baseUrl: await waitForServer(server) });
    const events = []; let subscription; let subscriptionEstablished = false;
    try { subscription = await client.event.subscribe({ query: { directory } }); } catch (error) { throw new Error(`event.subscribe failed: ${redact(error.message)}`); }
    subscriptionEstablished = true;
    const consume = (async () => { if (subscription?.stream && Symbol.asyncIterator in subscription.stream) for await (const event of subscription.stream) { if (event?.properties?.part) events.push(event.properties.part); } })();
    const session = await client.session.create({ directory, throwOnError: true });
    const sessionID = session?.data?.id; if (!sessionID) throw new Error("session.create returned no session id");
    const result = await client.session.prompt({ sessionID, directory, agent, model: { providerID: model.slice(0, slash), modelID: model.slice(slash + 1) }, parts: [{ type: "text", text: prompt }], format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 }, throwOnError: true });
    const info = result?.data?.info; const parts = Array.isArray(result?.data?.parts) ? result.data.parts : [];
    const deadline = Date.now() + 5000; let lifecycleParts;
    do { lifecycleParts = [...parts, ...events]; if (lifecycleParts.some((part) => part.type === "tool" && part.tool === "StructuredOutput" && part.state?.status === "completed") || Date.now() >= deadline) break; await new Promise((r) => setTimeout(r, 25)); } while (true);
    const lifecycle = qualifyLifecycle({ parts, events: events.length ? events : lifecycleParts, sessionID, messageID: info?.id, structured: info?.structured }); lifecycle.finish = info?.finish ?? null; lifecycle.subscription_established_before_prompt = subscriptionEstablished; lifecycle.completion_boundary = lifecycle.structured_output_completed ? "completed-StructuredOutput" : "bounded-deadline";
    const structured = info?.structured;
    const schema = structured == null ? { valid: false, errors: ["structured result is missing"] } : validateSchema(structured);
    const semantics = schema.valid ? validateSemantics(structured) : { valid: false, errors: [] };
    let classification = "LIFECYCLE_UNTRUSTWORTHY";
    if (!lifecycle.subscription_established_before_prompt || !lifecycle.final_message_identity || !lifecycle.terminal_step) classification = "LIFECYCLE_UNTRUSTWORTHY";
    else if (!lifecycle.completed_repository_tool || !lifecycle.grounding_before_structured) classification = "GROUNDING_FAILED";
    else if (!lifecycle.structured_output_completed || structured == null) classification = structured == null ? "STRUCTURED_OUTPUT_MISSING" : "STRUCTURED_TRANSPORT_FAILED";
    else if (!schema.valid) classification = "SCHEMA_INVALID";
    else if (!semantics.valid) classification = "SEMANTIC_CONTRADICTION";
    else classification = structured.verdict === "PASS" ? "VALID_PASS" : "VALID_BLOCK";
    cleanup.server_exit_confirmed = await stopServer(server); cleanup.safe = cleanup.server_exit_confirmed;
    process.stdout.write(JSON.stringify({ schema_version: 1, agent, model, session_id: sessionID, message_id: info?.id ?? null, classification: cleanup.safe ? classification : "INFRASTRUCTURE_FAILED", lifecycle, structured: structured ?? null, schema_validation: schema, semantic_validation: semantics, cleanup }) + "\n");
  } finally { if (!cleanup.server_exit_confirmed) { cleanup.server_exit_confirmed = await stopServer(server); cleanup.safe = cleanup.server_exit_confirmed; } }
}

if (pathToFileURL(resolve(process.argv[1] ?? "")).href === import.meta.url) run().catch((error) => { process.stderr.write(`STRUCTURED_REVIEW_ADAPTER_ERROR: ${redact(error.message)}\n`); process.exitCode = 1; });
