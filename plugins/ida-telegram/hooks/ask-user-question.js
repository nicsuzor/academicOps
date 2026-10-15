import { createConnection } from "node:net";
import { join } from "node:path";
import { homedir } from "node:os";
import { existsSync } from "node:fs";

// PreToolUse Hook for AskUserQuestion
async function main() {
  const role = (process.env.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  if (role !== "primary") {
    // Non-primary instance: inert, exit 0
    process.exit(0);
  }

  const socketPath =
    process.env.SOCKET_PATH ||
    join(process.env.STATE_DIR || join(homedir(), ".claude", "channels", "telegram"), "bridge.sock");

  if (!existsSync(socketPath)) {
    // Socket missing: inert, exit 0
    process.exit(0);
  }

  let inputData = "";
  process.stdin.setEncoding("utf-8");

  for await (const chunk of process.stdin) {
    inputData += chunk;
  }

  if (!inputData.trim()) {
    process.exit(0);
  }

  let payload;
  try {
    payload = JSON.parse(inputData);
  } catch {
    process.exit(0);
  }

  const toolName = payload.tool_name || payload.toolName;
  if (toolName !== "AskUserQuestion" && toolName !== "ask_user_question") {
    process.exit(0);
  }

  const toolInput = payload.tool_input || payload.toolInput || {};
  const turnId = payload.turn_id || payload.turnId || payload.tool_use_id || payload.session_id;
  const transcriptPath = payload.transcript_path || payload.transcriptPath;
  const questions = toolInput.questions || [
    {
      question: toolInput.question || "Input requested",
      options: toolInput.options || [{ label: "Acknowledge" }],
    },
  ];

  // Send to question broker over Unix domain socket
  const client = createConnection(socketPath);

  client.on("connect", () => {
    client.write(
      JSON.stringify({
        type: "ask_user",
        turn_id: turnId,
        transcript_path: transcriptPath,
        questions,
      }) + "\n"
    );
  });

  let responseData = "";
  client.on("data", (data) => {
    responseData += data.toString();
    client.end();
  });

  client.on("end", () => {
    let qid = "q_telegram";
    try {
      const res = JSON.parse(responseData);
      if (res.questionId) qid = res.questionId;
    } catch {
      // Ignore parse failure
    }

    const reason = `Question ${qid} posted to Nic over Telegram. Do not assume an answer; continue other work or end your turn.`;
    const output = {
      decision: "block",
      reason,
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: reason,
      },
    };
    process.stdout.write(JSON.stringify(output) + "\n");
    process.exit(0);
  });

  client.on("error", () => {
    // Socket connection error: inert
    process.exit(0);
  });
}

main().catch(() => process.exit(0));
