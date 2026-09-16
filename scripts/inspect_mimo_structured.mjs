import launch from "cross-spawn";
import * as sdkV2 from "@opencode-ai/sdk/v2";

console.log("[MIMO TEST] Launching server...");
const child = launch("opencode", ["serve", "--hostname=127.0.0.1", "--port=0"], {
  env: { ...process.env, OPENCODE_DB: ":memory:", OPENCODE_DISABLE_AUTOUPDATE: "1", OPENCODE_CONFIG_CONTENT: "{}" },
  stdio: ["ignore", "pipe", "pipe"],
});

let output = "";
let serverReady = false;

child.stdout?.on("data", async (chunk) => {
  output += chunk.toString();
  if (serverReady) return;
  const line = output.split(/\r?\n/).find((e) => e.startsWith("opencode server listening"));
  const match = line?.match(/on\s+(https?:\/\/[^\s]+)/);
  if (match) {
    serverReady = true;
    const baseUrl = match[1];
    console.log(`[MIMO TEST] Server ready at: ${baseUrl}`);
    const client = sdkV2.createOpencodeClient({ baseUrl });
    try {
      const session = await client.session.create({ directory: process.cwd() }, { throwOnError: true });
      console.log(`[MIMO TEST] Session created: ${session.data.id}`);

      // Test minimal task with agent: regression-reviewer AND explicit instruction to output structured schema
      console.log(`[MIMO TEST] Sending minimal structured review prompt to regression-reviewer...`);
      const promptResult = await client.session.prompt({
        sessionID: session.data.id,
        directory: process.cwd(),
        agent: "regression-reviewer",
        model: { providerID: "opencode", modelID: "mimo-v2.5-free" },
        parts: [{ type: "text", text: "Minimal check: do not call tools. Review is PASS with 0 blocking findings. Emit the structured output." }],
        format: {
          type: "json_schema",
          schema: {
            type: "object",
            additionalProperties: false,
            properties: {
              verdict: { type: "string", enum: ["PASS", "BLOCK"] },
              blocking_findings: { type: "integer", minimum: 0 },
              report_markdown: { type: "string" },
            },
            required: ["verdict", "blocking_findings", "report_markdown"],
          },
          retryCount: 2,
        },
      }, { throwOnError: true });

      console.log(`[MIMO TEST] Status:`, promptResult.response?.status);
      console.log(`[MIMO TEST] Info.structured:`, JSON.stringify(promptResult.data?.info?.structured, null, 2));
      console.log(`[MIMO TEST] Finish:`, promptResult.data?.info?.finish);
      console.log(`[MIMO TEST] Raw parts count:`, promptResult.data?.parts?.length);
      for (const [i, p] of (promptResult.data?.parts ?? []).entries()) {
        console.log(`--- Part ${i} (${p.type}) ---`);
        if (p.text) console.log(`Text preview: ${p.text.slice(0, 200)}...`);
        if (p.tool) console.log(`Tool: ${p.tool}`);
      }
    } catch (err) {
      console.error(`[MIMO TEST] Error:`, err);
    } finally {
      child.stdout?.destroy();
      child.stderr?.destroy();
      child.kill();
      process.exit(0);
    }
  }
});

child.stderr?.on("data", () => {});
