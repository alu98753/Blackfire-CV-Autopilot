import { readFile } from "node:fs/promises";
import { createOpencode } from "@opencode-ai/sdk";

const OUTCOME_SCHEMA = {
  type: "object", additionalProperties: false,
  properties: {
    verdict: { type: "string", enum: ["PASS", "BLOCK"] },
    blocking_findings: { type: "integer", minimum: 0 },
    report_markdown: { type: "string" }
  },
  required: ["verdict", "blocking_findings", "report_markdown"]
};

function argument(name) {
  const index = process.argv.indexOf(name);
  return index < 0 ? undefined : process.argv[index + 1];
}
function required(name) {
  const value = argument(name);
  if (!value) throw new Error(`Missing required argument: ${name}`);
  return value;
}

function sdkError(operation, error) {
  const status = error?.cause?.status;
  const detail = typeof error?.message === "string" && error.message.length > 0
    ? error.message.slice(0, 240)
    : "unknown SDK error";
  return new Error(`OpenCode ${operation} API error${Number.isInteger(status) ? ` (HTTP ${status})` : ""}: ${detail}`);
}

async function main() {
  if (process.argv.includes("--check-sdk")) { console.log("SDK_OK"); return; }
  const agent = required("--agent");
  const model = required("--model");
  const directory = required("--directory");
  const prompt = await readFile(required("--prompt-file"), "utf8");
  const separator = model.indexOf("/");
  if (separator <= 0 || separator === model.length - 1) throw new Error(`Invalid candidate model: ${model}`);
  const previousDatabase = process.env.OPENCODE_DB;
  process.env.OPENCODE_DB = ":memory:";
  let opencode;
  try {
    opencode = await createOpencode({ hostname: "127.0.0.1", port: 0 });
  } finally {
    if (previousDatabase === undefined) delete process.env.OPENCODE_DB;
    else process.env.OPENCODE_DB = previousDatabase;
  }
  const { client, server } = opencode;
  try {
    let session;
    try {
      session = await client.session.create({
        query: { directory },
        body: { agent, model: { providerID: model.slice(0, separator), modelID: model.slice(separator + 1) } },
        throwOnError: true
      });
    } catch (error) {
      throw sdkError("session.create", error);
    }
    if (!session || typeof session !== "object" || !("data" in session) || session.data === undefined || session.data === null) {
      throw new Error("OpenCode SDK session.create response did not contain response data.");
    }
    const sessionId = session.data.id;
    if (typeof sessionId !== "string" || sessionId.trim().length === 0) {
      throw new Error("OpenCode SDK session.create response contained a malformed session object without a session id.");
    }
    let result;
    try {
      result = await client.session.prompt({
        path: { id: sessionId }, query: { directory },
        body: {
          agent, model: { providerID: model.slice(0, separator), modelID: model.slice(separator + 1) },
          parts: [{ type: "text", text: prompt }],
          format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 }
        },
        throwOnError: true
      });
    } catch (error) {
      throw sdkError("session.prompt", error);
    }
    if (!result || typeof result !== "object" || !("data" in result) || result.data === undefined || result.data === null) {
      throw new Error("OpenCode SDK session.prompt response did not contain response data.");
    }
    const structured = result.data?.info?.structured_output;
    if (structured === undefined || structured === null) throw new Error("OpenCode SDK response did not contain structured_output.");
    process.stdout.write(JSON.stringify({ structured_output: structured }) + "\n");
  } finally { server.close(); }
}

main().catch((error) => {
  process.stderr.write(`STRUCTURED_REVIEW_ADAPTER_ERROR: ${error?.message ?? String(error)}\n`);
  process.exitCode = 1;
});
