import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
const corePath = join(dir, "..", "CORE.md");

if (existsSync(corePath)) {
  const content = readFileSync(corePath, "utf-8").trim();
  if (content) {
    const output = {
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: content,
      },
    };
    process.stdout.write(JSON.stringify(output) + "\n");
  }
}
process.exit(0);
