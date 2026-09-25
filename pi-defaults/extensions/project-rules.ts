import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// Worktrees live outside their umbrella folder. Reattach its explicit local rules.
export default function projectRules(pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event, ctx) => {
    const agentDir = process.env.PI_CODING_AGENT_DIR || join(homedir(), ".pi", "agent");
    const result = await pi.exec("python3", [join(agentDir, "defaults", "workflow.py"), "context", "--cwd", ctx.cwd], { timeout: 10000 });
    if (result.code !== 0) {
      // Non-project conversations still work. Project edits must resolve context.
      return { systemPrompt: event.systemPrompt + "\nProject context is unresolved. Before project edits, run pi-workflow context and resolve its diagnostic. Read-only/non-project work can continue." };
    }
    const context = JSON.parse(result.stdout);
    const rules = context.rules.map((file: string) => `\nLocal rules from ${file}:\n${readFileSync(file, "utf8")}`).join("\n");
    return { systemPrompt: event.systemPrompt + `\nCanonical project context: ${JSON.stringify(context)}\n${rules}\nThe global pi-workflow owns Plane transitions and branch delivery; engineering skills use that same Plane item. Main promotion requires approval; Done requires verified main delivery.` };
  });
}
