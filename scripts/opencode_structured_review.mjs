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
    const session = await client.session.create({
      query: { directory },
      body: { agent, model: { providerID: model.slice(0, separator), modelID: model.slice(separator + 1) } }
    });
    const sessionId = session.data?.id;
    if (!sessionId) throw new Error("OpenCode SDK did not return a session id.");
    const result = await client.session.prompt({
      path: { id: sessionId }, query: { directory },
      body: {
        agent, model: { providerID: model.slice(0, separator), modelID: model.slice(separator + 1) },
        parts: [{ type: "text", text: prompt }],
        format: { type: "json_schema", schema: OUTCOME_SCHEMA, retryCount: 2 }
      }
    });
    const structured = result.data?.info?.structured_output;
    if (structured === undefined || structured === null) throw new Error("OpenCode SDK response did not contain structured_output.");
    process.stdout.write(JSON.stringify({ structured_output: structured }) + "\n");
  } finally { server.close(); }
}

main().catch((error) => {
  process.stderr.write(`STRUCTURED_REVIEW_ADAPTER_ERROR: ${error?.message ?? String(error)}\n`);
  process.exitCode = 1;
});
