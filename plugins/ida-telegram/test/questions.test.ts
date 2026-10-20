import { describe, expect, test, afterEach } from "bun:test";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PluginStore } from "../src/store.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Questions are never assumed: Asynchronous Broker and Hook", () => {
  const testStateDir = join(tmpdir(), "ida-telegram-q-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("ask_user creates a persistent question, formats buttons with recommendation first, and returns immediately", async () => {
    const broker = new QuestionBroker(testStateDir);

    const questionInput = {
      question: "Which component should we prioritize?",
      options: [
        { label: "Port Formatter (Recommended)", description: "High impact on readability" },
        { label: "Refactor Poller", description: "Better backoff" },
      ],
      allowOther: false,
      turnId: "turn_123",
      chatId: 12345678,
    };

    const immediateResult = await broker.askUser(questionInput);

    expect(immediateResult.questionId).toBeDefined();
    expect(immediateResult.status).toBe("posted");
    expect(immediateResult.message).toContain("Do not assume an answer; continue other work or end your turn.");

    // Check keyboard structure
    const card = broker.renderQuestionCard(immediateResult.questionId);
    expect(card).not.toBeNull();
    expect(card?.buttons.length).toBe(2);
    // Vertical order preserved, recommendation first
    expect(card?.buttons[0].text).toContain("1. Port Formatter (Recommended)");
    expect(card?.buttons[1].text).toContain("2. Refactor Poller");
    // Callback data adheres to Telegram 64-byte limit
    expect(card?.buttons[0].callbackData.length).toBeLessThanOrEqual(64);
  });

  test("questions persist across restarts and can be resolved late", async () => {
    // Session 1: Create question
    const broker1 = new QuestionBroker(testStateDir);
    const result = await broker1.askUser({
      question: "Choose deployment strategy",
      options: [{ label: "Blue-Green" }, { label: "Canary" }],
      turnId: "turn_456",
      chatId: 12345678,
    });
    const qid = result.questionId;

    // Simulate restart (Session 2 reinstantiates broker with same state dir)
    const broker2 = new QuestionBroker(testStateDir);
    const pending = broker2.getPendingQuestions();
    expect(pending.some((q) => q.id === qid)).toBe(true);

    // Nic taps option 2: Canary
    const resolution = await broker2.resolveAnswer(qid, 1); // index 1 is Canary
    expect(resolution).not.toBeNull();
    expect(resolution?.cardText).toContain("Selected: Canary ✅");
    expect(resolution?.channelEvent.choice).toBe("Canary");
    expect(resolution?.channelEvent.turn_id).toBe("turn_456");

    // Question is no longer pending
    expect(broker2.getPendingQuestions().some((q) => q.id === qid)).toBe(false);
  });

  test("handles multiSelect questions with toggles and Done button", async () => {
    const broker = new QuestionBroker(testStateDir);
    const result = await broker.askUser({
      question: "Select enabled features",
      options: [{ label: "Logging" }, { label: "Tracing" }, { label: "Metrics" }],
      multiSelect: true,
      turnId: "turn_789",
      chatId: 12345678,
    });

    const card = broker.renderQuestionCard(result.questionId);
    expect(card?.buttons.some((b) => b.text.includes("☐ Logging"))).toBe(true);
    expect(card?.buttons.some((b) => b.text.includes("Done"))).toBe(true);
  });

  test("batch of decisions and results renders as individual formatted cards in Telegram and resolves each in-app into channel events", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    let nextMessageId = 100;

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      channelEvents.push({ content, meta });
    });

    // Stub callApi to capture outbound Telegram payloads
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      if (method === "sendMessage") {
        return { ok: true, result: { message_id: ++nextMessageId } };
      }
      return { ok: true, result: true };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // 1. Send a batch of 3 decisions via ask_user (modeled on tg 1004 batch: value-model, polecat security, design proposal)
    const askResp = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              header: "Value model weight",
              question: "Raise `urgency` weight on cliff tasks?\n>! Facts: `aops_5ff43ec0` showed 3 cliff tasks ranked below routine cleanup.",
              options: [
                { label: "Raise to 2.5x (Recommended)", description: "Prioritizes due-within-48h tasks immediately" },
                { label: "Keep at 1.5x", description: "Preserve current focus balance" },
              ],
            },
            {
              header: "Polecat security scope",
              question: "Select network egress rules to enable for polecat containers:",
              options: [
                { label: "Allow GitHub API" },
                { label: "Allow PyPI / npm registries" },
                { label: "Block raw socket egress" },
              ],
              multiSelect: true,
            },
            {
              header: "Design proposal",
              question: "Adopt single-screen Question Canvas layout for `spec_7a9caca5`?",
              options: [
                { label: "Approve v3 layout (Recommended)", description: "Matches `kb_ee859e3f` native UI map" },
                { label: "Revise layout", description: "Keep multi-tab drawer" },
              ],
            },
          ],
        },
      },
    });

    const sentCards = apiCalls.filter((c) => c.method === "sendMessage");
    // Must render 3 separate Telegram cards (one per decision in batch)
    expect(sentCards.length).toBe(3);

    // Card 1 must have formatted UTF-16 entities (bold header, inline code, expandable_blockquote) and option descriptions
    const card1Payload = sentCards[0].payload;
    expect(card1Payload.text as string).toContain("Value model weight");
    expect(card1Payload.text as string).toContain("Prioritizes due-within-48h tasks immediately");
    expect(Array.isArray(card1Payload.entities)).toBe(true);
    expect((card1Payload.entities as any[]).some((e) => e.type === "bold")).toBe(true);
    expect((card1Payload.entities as any[]).some((e) => e.type === "expandable_blockquote")).toBe(true);

    // 2. Send a result card with custom action buttons and PR review via `reply`
    await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "reply",
        arguments: {
          text: "**PR #418 ready to merge** — `polecat/aops_a54ef4e6` passes all 40 tests.\n>! Changed `questions.ts`, `bot.ts`, `server.ts`.",
          detail: "## Full Diff Summary\n- Fixed batch truncation\n- Added entity formatting",
          review: { repo: "nicsuzor/academicOps", pr: 418 },
          buttons: [
            { label: "Merge PR #418 (Recommended)", callback_data: "decide:pr418:merge" },
            { label: "Hold for manual check", callback_data: "decide:pr418:hold" },
          ],
        },
      },
    });

    const resultCardCall = apiCalls[apiCalls.length - 1];
    expect(resultCardCall.method).toBe("sendMessage");
    const resultKb = (resultCardCall.payload.reply_markup as any).inline_keyboard as Array<Array<any>>;
    // Custom decision buttons appear on the result card alongside Details and Review diff buttons
    expect(resultKb.flat().some((b) => b.text === "Merge PR #418 (Recommended)" && b.callback_data === "decide:pr418:merge")).toBe(true);
    expect(resultKb.flat().some((b) => b.text === "🔍 Details")).toBe(true);
    expect(resultKb.flat().some((b) => b.text.includes("🔍 Review diff"))).toBe(true);

    // 3. Resolve Card 1 (single-select tap on option 0)
    const pendingBefore = broker.getPendingQuestions();
    expect(pendingBefore.length).toBe(3);
    const q1 = pendingBefore[0];
    const q2 = pendingBefore[1];
    const q3 = pendingBefore[2];

    await (bot as any).handleUpdate({
      update_id: 501,
      callback_query: {
        id: "cb_1",
        from: { id: 999, first_name: "Nic" },
        message: { message_id: 101, chat: { id: 999, type: "private" }, text: card1Payload.text as string },
        data: `q:${q1.id}:0:0`,
      },
    });

    expect(channelEvents.length).toBe(1);
    expect(channelEvents[0].meta.event).toBe("question_answered");
    expect(channelEvents[0].meta.question_id).toBe(q1.id);
    expect(channelEvents[0].meta.choice).toBe("Raise to 2.5x (Recommended)");

    const edit1 = apiCalls.find((c) => c.method === "editMessageText" && c.payload.message_id === 101);
    expect(edit1).toBeDefined();
    expect(edit1?.payload.text as string).toContain("Selected: Raise to 2.5x (Recommended) ✅");
    expect((edit1?.payload.reply_markup as any)?.inline_keyboard).toEqual([]);

    // 4. Resolve Card 2 (multi-select: toggle option 0 and option 2, then tap Done)
    await (bot as any).handleUpdate({
      update_id: 502,
      callback_query: {
        id: "cb_2a",
        from: { id: 999, first_name: "Nic" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:0`,
      },
    });
    // Must NOT have emitted channel event yet on multi-select toggle!
    expect(channelEvents.length).toBe(1);

    await (bot as any).handleUpdate({
      update_id: 503,
      callback_query: {
        id: "cb_2b",
        from: { id: 999, first_name: "Nic" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:2`,
      },
    });
    expect(channelEvents.length).toBe(1);

    // Now tap Done on Card 2
    await (bot as any).handleUpdate({
      update_id: 504,
      callback_query: {
        id: "cb_2c",
        from: { id: 999, first_name: "Nic" },
        message: { message_id: 102, chat: { id: 999, type: "private" }, text: sentCards[1].payload.text as string },
        data: `q:${q2.id}:0:done`,
      },
    });
    expect(channelEvents.length).toBe(2);
    expect(channelEvents[1].meta.question_id).toBe(q2.id);
    expect(channelEvents[1].meta.choice).toBe("Allow GitHub API, Block raw socket egress");

    // 5. Resolve Card 3 via "✏️ Other" force_reply prompt and custom text reply
    await (bot as any).handleUpdate({
      update_id: 505,
      callback_query: {
        id: "cb_3_other",
        from: { id: 999, first_name: "Nic" },
        message: { message_id: 103, chat: { id: 999, type: "private" }, text: sentCards[2].payload.text as string },
        data: `q:${q3.id}:0:other`,
      },
    });
    // Tapping Other should send a force_reply prompt and NOT resolve with empty string
    expect(channelEvents.length).toBe(2);
    const forceReplyCall = apiCalls.find(
      (c) => c.method === "sendMessage" && (c.payload.reply_markup as any)?.force_reply === true
    );
    expect(forceReplyCall).toBeDefined();
    const promptMsgId = nextMessageId;

    // Nic replies to the force_reply prompt with custom text
    await (bot as any).handleUpdate({
      update_id: 506,
      message: {
        message_id: 900,
        from: { id: 999, first_name: "Nic" },
        chat: { id: 999, type: "private" },
        date: 1700000000,
        text: "Approve v3 layout, but keep font size at 15px",
        reply_to_message: {
          message_id: promptMsgId,
          chat: { id: 999, type: "private" },
          text: forceReplyCall?.payload.text as string,
        },
      },
    });

    expect(channelEvents.length).toBe(3);
    expect(channelEvents[2].meta.event).toBe("question_answered");
    expect(channelEvents[2].meta.question_id).toBe(q3.id);
    expect(channelEvents[2].meta.choice).toBe("Approve v3 layout, but keep font size at 15px");

    // 6. Resolve Result Card (Card 4) by tapping custom inline button "Merge PR #418 (Recommended)"
    await (bot as any).handleUpdate({
      update_id: 507,
      callback_query: {
        id: "cb_4_merge",
        from: { id: 999, first_name: "Nic" },
        message: {
          message_id: 104,
          chat: { id: 999, type: "private" },
          text: resultCardCall.payload.text as string,
          reply_markup: resultCardCall.payload.reply_markup as any,
        },
        data: "decide:pr418:merge",
      },
    });

    expect(channelEvents.length).toBe(4);
    expect(channelEvents[3].meta.event).toBe("button_tap");
    expect(channelEvents[3].meta.payload).toBe("decide:pr418:merge");
    expect(channelEvents[3].meta.label).toBe("Merge PR #418 (Recommended)");
    const edit4 = apiCalls.find((c) => c.method === "editMessageText" && c.payload.message_id === 104);
    expect(edit4).toBeDefined();
    expect(edit4?.payload.text as string).toContain("Selected: Merge PR #418 (Recommended) ✅");
  });

  test("Mini App question answer settles pending question, edits the Telegram chat card, and emits channel event (FR-2.6)", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");
    const { PluginStore } = await import("../src/store.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);
    const posted = await broker.askUser({
      header: "Merge approval",
      question: "Ship `v0.10.16` to production?",
      options: [{ label: "Ship now (Recommended)" }, { label: "Wait for Monday" }],
      chatId: 999,
      turnId: "turn_999",
    });
    broker.setMessageId(posted.questionId, 777);

    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];
    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const sessionSecret = "test-secret-32-bytes-long-123456";
    const token = createSessionToken(999, sessionSecret, 3600);

    const req = new Request("http://127.0.0.1:8093/api/app/questions/answer", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        questionId: posted.questionId,
        optionIndex: 0,
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: (event, content, meta) => {
        emittedEvents.push({ event, content, meta });
      },
      editTelegramCard: async (chatId, messageId, text) => {
        editedCards.push({ chatId, messageId, text });
      },
    } as any);

    expect(resp.status).toBe(200);
    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].meta.choice).toBe("Ship now (Recommended)");
    expect(editedCards.length).toBe(1);
    expect(editedCards[0].chatId).toBe(999);
    expect(editedCards[0].messageId).toBe(777);
    expect(editedCards[0].text).toContain("Selected: Ship now (Recommended) ✅");
  });

  test("PreToolUse hook on AskUserQuestion posts question to socket and returns a decision Claude Code accepts (block / permissionDecision deny)", async () => {
    const { createServer } = await import("node:net");
    const { spawn } = await import("node:child_process");
    const { mkdirSync } = await import("node:fs");

    mkdirSync(testStateDir, { recursive: true });
    const socketPath = join(testStateDir, "bridge.sock");
    let receivedSocketReq: any = null;

    const server = createServer((client) => {
      let buf = "";
      client.on("data", (chunk) => {
        buf += chunk.toString();
        if (buf.includes("\n")) {
          receivedSocketReq = JSON.parse(buf.trim());
          client.write(JSON.stringify({ status: "ok", questionId: "q_hook123", questionIds: ["q_hook123"] }) + "\n");
        }
      });
    });

    await new Promise<void>((resolve) => server.listen(socketPath, () => resolve()));

    try {
      const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      const stdout = await new Promise<string>((resolve, reject) => {
        const proc = spawn("node", [hookScript], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: socketPath,
          },
        });
        let out = "";
        proc.stdout.on("data", (d) => (out += d.toString()));
        proc.on("error", reject);
        proc.on("close", () => resolve(out));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_hook_42",
            tool_input: {
              questions: [
                {
                  question: "Proceed with deployment?",
                  options: [{ label: "Yes (Recommended)" }, { label: "No" }],
                },
              ],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      expect(receivedSocketReq).not.toBeNull();
      expect(receivedSocketReq.type).toBe("ask_user");

      const parsed = JSON.parse(stdout.trim());
      // Claude Code PreToolUse rejects decision: "deny"; valid top-level decisions are "approve" | "block"
      expect(["approve", "block"]).toContain(parsed.decision);
      expect(parsed.decision).toBe("block");
      expect(parsed.reason).toContain("q_hook123");
      expect(parsed.reason).toContain("posted to the user over Telegram");
      expect(parsed.reason).not.toContain("Nic");
      expect(parsed.hookSpecificOutput?.permissionDecision).toBe("deny");
    } finally {
      server.close();
    }
  });

  test("emits answered questions as question_answered carrying turn_id", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      channelEvents.push({ content, meta });
    });
    (bot as any).callApi = async () => ({ ok: true, result: { message_id: 301 } });

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 77,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          turn_id: "turn_req_77",
          questions: [
            {
              question: "Deploy hotfix now?",
              options: [{ label: "Deploy now (Recommended)" }, { label: "Defer" }],
            },
          ],
        },
      },
    });

    const pending = broker.getPendingQuestions();
    expect(pending.length).toBe(1);
    const q = pending[0];

    await (bot as any).handleUpdate({
      update_id: 800,
      callback_query: {
        id: "cb_800",
        from: { id: 999, is_bot: false, first_name: "Nic" },
        message: { message_id: 301, date: 1700000000, chat: { id: 999, type: "private" }, text: "Deploy hotfix now?" },
        data: `q:${q.id}:0:0`,
      },
    });

    expect(channelEvents.length).toBe(1);
    expect(channelEvents[0].meta.event).toBe("question_answered");
    expect(channelEvents[0].meta.question_id).toBe(q.id);
    expect(channelEvents[0].meta.choice).toBe("Deploy now (Recommended)");
    expect(channelEvents[0].meta.turn_id).toBe("turn_req_77");
  });

  test("does not fabricate synthetic turn_id when turn_id is omitted", async () => {
    const broker = new QuestionBroker(testStateDir);
    const result = await broker.askUser({
      question: "Continue work?",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 12345678,
    });
    expect(result.message).toContain("posted to the user");
    expect(result.message).not.toContain("Nic");

    const resolved = await broker.resolveAnswer(result.questionId, 0);
    expect(resolved).not.toBeNull();
    expect(resolved!.channelEvent.turn_id).toBeUndefined();
  });

  test("MCP tools descriptions use 'the user' and omit personal names, and anchor schema has no context_tokens", async () => {
    const { MCP_TOOLS } = await import("../src/mcp/tools.js");
    for (const tool of MCP_TOOLS) {
      expect(tool.description).not.toContain("Nic");
    }
    const replyTool = MCP_TOOLS.find((t) => t.name === "reply");
    expect(replyTool?.description).toContain("the user");
    const askUserTool = MCP_TOOLS.find((t) => t.name === "ask_user");
    expect(askUserTool?.description).toContain("the user");

    const anchorTool = MCP_TOOLS.find((t) => t.name === "anchor");
    expect((anchorTool?.inputSchema.properties as any).context_tokens).toBeUndefined();
  });

  test("permission_request notification fails fast if request_id or tool_name is missing", async () => {
    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [12345678],
      maxChatChars: 1200,
      port: 8093,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "sock.sock"),
      voiceReplies: "off" as const,
      botCommands: [],
    };
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

    // Missing request_id
    expect(
      mcp.handleMessage({
        jsonrpc: "2.0",
        method: "notifications/claude/channel/permission_request",
        params: { tool_name: "Bash" },
      })
    ).rejects.toThrow();

    // Disproved method name fails fast (not handled as permission)
    const disprovedRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 99,
      method: "claude/channel/permission",
      params: { id: "old_perm_1" },
    });
    // Should not be recognized as permission handler
    expect((disprovedRes as any)?.error?.code ?? -32601).toBe(-32601);
  });

  test("lists pending questions with origin fields: id, text, session, turn, and when asked", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const askPayload = {
      question: "Which test strategy should we adopt?",
      options: [{ label: "Unit tests" }, { label: "Integration tests" }],
      turnId: "turn_session_001",
      sessionId: "session_abc_123",
      chatId: 999,
    };
    const posted = await broker.askUser(askPayload);

    // 1. Direct broker method test
    const pendingQuestions = broker.getPendingQuestions();
    expect(pendingQuestions.length).toBe(1);
    const qBroker = pendingQuestions[0];
    expect(qBroker.id).toBe(posted.questionId);
    expect(qBroker.text).toBe("Which test strategy should we adopt?");
    expect(qBroker.sessionId || qBroker.session_id).toBe("session_abc_123");
    expect(qBroker.turnId || qBroker.turn_id).toBe("turn_session_001");
    expect(qBroker.createdAt || qBroker.created_at).toBeDefined();

    // 2. HTTP route GET /api/app/questions
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: {
        Cookie: `ida_session=${token}`,
      },
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: () => {},
    } as any);

    expect(resp.status).toBe(200);
    const data = await resp.json();
    expect(data.questions).toBeDefined();
    expect(data.questions.length).toBe(1);
    const q = data.questions[0];
    expect(q.id).toBe(posted.questionId);
    expect(q.text).toBe("Which test strategy should we adopt?");
    expect(q.sessionId || q.session_id).toBe("session_abc_123");
    expect(q.turnId || q.turn_id).toBe("turn_session_001");
    expect(q.createdAt || q.created_at).toBeDefined();
  });

  test("closing a pending question with a reason removes it from Mini App, edits chat card, and emits channel event", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const posted = await broker.askUser({
      header: "Deployment",
      question: "Deploy release v1.0.0 to canary?",
      options: [{ label: "Deploy" }, { label: "Cancel" }],
      chatId: 999,
      turnId: "turn_close_test",
      sessionId: "session_close_test",
    });
    broker.setMessageId(posted.questionId, 888);

    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];
    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);

    // Call POST /api/app/questions/close with a reason
    const req = new Request("http://127.0.0.1:8093/api/app/questions/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        question_id: posted.questionId,
        reason: "answered elsewhere",
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
        socketPath: join(testStateDir, "hook.sock"),
        port: 8093,
        miniAppUrl: "https://ida.example.ts.net",
        isPrimary: true,
        maxChatChars: 1200,
        voiceTranscribeCmd: "",
        voiceSpeakCmd: "",
        voiceReplies: "off",
        botCommands: [],
      },
      sessionSecret,
      emitChannelEvent: (event, content, meta) => {
        emittedEvents.push({ event, content, meta });
      },
      editTelegramCard: async (chatId, messageId, text) => {
        editedCards.push({ chatId, messageId, text });
      },
    } as any);

    expect(resp.status).toBe(200);

    // 1. Removed from the Mini App (broker getPendingQuestions returns empty)
    expect(broker.getPendingQuestions().length).toBe(0);

    // 2. Chat card is edited to show the reason
    expect(editedCards.length).toBe(1);
    expect(editedCards[0].chatId).toBe(999);
    expect(editedCards[0].messageId).toBe(888);
    expect(editedCards[0].text).toContain("Closed: answered elsewhere");

    // 3. Emits channel event to the asking session
    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].event).toBe("question_closed");
    expect(emittedEvents[0].meta.question_id).toBe(posted.questionId);
    expect(emittedEvents[0].meta.reason).toBe("answered elsewhere");
    expect(emittedEvents[0].meta.turn_id).toBe("turn_close_test");
    expect(emittedEvents[0].meta.session_id).toBe("session_close_test");
  });
});



