/**
 * Tool call deadline: the rule for tools that should be basically instant.
 *
 * Every tool this server exposes answers within a deadline of
 * TOOL_TIMEOUT_MS (30 s) unless it is listed in LONG_RUNNING_TOOLS. When the
 * deadline passes the caller gets an error result and the call is abandoned
 * on our side (the underlying request is not cancelled; see the README).
 *
 * The default is "covered": a new tool gets the deadline automatically.
 * Adding a tool to LONG_RUNNING_TOOLS needs a stated reason next to its entry.
 * This is our own deadline, separate from the harness's MCP_TOOL_TIMEOUT,
 * which applies to every MCP server alike.
 */

export const TOOL_TIMEOUT_MS = 30_000;

/** Tools exempt from the deadline, each with the reason it can legitimately run past 30 s. */
export const LONG_RUNNING_TOOLS: ReadonlySet<string> = new Set([
  // Voice-out synthesis runs a child process with its own 60 s limit (bot.ts).
  "reply",
  // File uploads: time scales with file size and the connection.
  "send_photo",
  "send_document",
  "send_video",
  "send_animation",
  "send_media_group",
  "send_audio",
  "send_video_note",
]);

export class ToolTimeoutError extends Error {
  constructor(
    public readonly toolName: string,
    public readonly timeoutMs: number
  ) {
    super(`${toolName} timed out after ${Math.round(timeoutMs / 1000)}s without an answer`);
    this.name = "ToolTimeoutError";
  }
}

/** Run `run()`, rejecting with ToolTimeoutError if it has not settled within the tool's deadline. */
export async function withToolDeadline<T>(
  toolName: string,
  run: () => Promise<T>,
  timeoutMs: number = TOOL_TIMEOUT_MS
): Promise<T> {
  if (LONG_RUNNING_TOOLS.has(toolName)) {
    return run();
  }
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => reject(new ToolTimeoutError(toolName, timeoutMs)), timeoutMs);
  });
  try {
    return await Promise.race([run(), deadline]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
