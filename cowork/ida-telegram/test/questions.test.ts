import { describe, expect, test, afterEach } from "bun:test";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PluginStore } from "../src/store.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Questions are never assumed: Asynchronous Broker", () => {
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

    // The user taps option 2: Canary
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
      if (method === "sendWidget" || method === "sendRichMessage" || method === "sendMessage") {
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
              question: "Raise `urgency` weight on cliff tasks?\n>! Facts: `demo_00000002` showed 3 cliff tasks ranked below routine cleanup.",
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
              question: "Adopt single-screen Question Canvas layout for Telegram mini-app?",
              options: [
                { label: "Approve v3 layout (Recommended)", description: "Matches native UI map" },
                { label: "Revise layout", description: "Keep multi-tab drawer" },
              ],
            },
          ],
        },
      },
    });

    const sentRichCards = apiCalls.filter((c) => c.method === "sendRichMessage");
    // Must render 3 separate Telegram Rich Message cards (one per decision in batch), not widgets
    expect(sentRichCards.length).toBe(3);
    expect(apiCalls.filter((c) => c.method === "sendWidget").length).toBe(0);

    // Card 1 Rich Message must contain header, question, and option descriptions
    const card1Payload = sentRichCards[0].payload as { rich_message?: { markdown?: string } };
    expect(card1Payload.rich_message?.markdown).toContain("Value model weight");
    expect(card1Payload.rich_message?.markdown).toContain("Prioritizes due-within-48h tasks immediately");

    // 2. Send a result card with custom action buttons via `send_rich_message`
    await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "send_rich_message",
        arguments: {
          markdown: "**PR #418 ready to merge** — `polecat/demo_00000003` passes all 40 tests.\n<details><summary>Files</summary>Changed `questions.ts`, `bot.ts`, `server.ts`.</details>",
          buttons: [
            { label: "Merge PR #418 (Recommended)", callback_data: "decide:pr418:merge" },
            { label: "Hold for manual check", callback_data: "decide:pr418:hold" },
          ],
        },
      },
    });

    const resultCardCall = apiCalls[apiCalls.length - 1];
    expect(resultCardCall.method).toBe("sendRichMessage");
    const resultKb = (resultCardCall.payload.reply_markup as any).inline_keyboard as Array<Array<any>>;
    expect(resultKb.flat().some((b) => b.text === "Merge PR #418 (Recommended)" && b.callback_data === "decide:pr418:merge")).toBe(true);

    // 3. Resolve Card 1 (single-select tap on option 0)
    const pendingBefore = broker.getPendingQuestions();
    expect(pendingBefore.length).toBe(3);
    const q1 = pendingBefore[0];
    const q2 = pendingBefore[1];
    const q3 = pendingBefore[2];

    await (bot as any).handleUpdate({
      update_id: 501,
      widget_query: {
        id: "wq_1",
        from: { id: 999, is_bot: false, first_name: "Alex" },
        chat_instance: "batch_chat",
        message: { message_id: 101, date: 1700000000, chat: { id: 999, type: "private" } },
        data: `q:${q1.id}:opt:0`,
      },
    });

    expect(channelEvents.length).toBe(1);
    expect(channelEvents[0].meta.event).toBe("question_answered");
    expect(channelEvents[0].meta.question_id).toBe(q1.id);
    expect(channelEvents[0].meta.choice).toBe("Raise to 2.5x (Recommended)");

    const edit1 = apiCalls.find((c) => c.method === "editMessageWidgetData" && c.payload.message_id === 101);
    expect(edit1).toBeDefined();
    expect(JSON.parse(edit1?.payload.chat_data as string)).toMatchObject({
      s: "answered",
      lbl: "Raise to 2.5x (Recommended)",
    });

    // 4. Resolve Card 2 (multi-select: submit bitmask for options 0 and 2 -> 1 + 4 = 5)
    await (bot as any).handleUpdate({
      update_id: 502,
      widget_query: {
        id: "wq_2",
        from: { id: 999, is_bot: false, first_name: "Alex" },
        chat_instance: "batch_chat",
        message: { message_id: 102, date: 1700000000, chat: { id: 999, type: "private" } },
        data: `q:${q2.id}:m:5`,
      },
    });
    expect(channelEvents.length).toBe(2);
    expect(channelEvents[1].meta.question_id).toBe(q2.id);
    expect(channelEvents[1].meta.choice).toBe("Allow GitHub API, Block raw socket egress");

    // 5. Resolve Card 3 via Other force_reply prompt and custom text reply
    await (bot as any).handleUpdate({
      update_id: 505,
      widget_query: {
        id: "wq_3_other",
        from: { id: 999, is_bot: false, first_name: "Alex" },
        chat_instance: "batch_chat",
        message: { message_id: 103, date: 1700000000, chat: { id: 999, type: "private" } },
        data: `q:${q3.id}:other`,
      },
    });
    // Tapping Other should send a force_reply prompt and NOT resolve with empty string
    expect(channelEvents.length).toBe(2);
    const forceReplyCall = apiCalls.find(
      (c) => c.method === "sendMessage" && (c.payload.reply_markup as any)?.force_reply === true
    );
    expect(forceReplyCall).toBeDefined();
    const promptMsgId = nextMessageId;

    // The user replies to the force_reply prompt with custom text
    await (bot as any).handleUpdate({
      update_id: 506,
      message: {
        message_id: 900,
        from: { id: 999, first_name: "Alex" },
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
        from: { id: 999, first_name: "Alex" },
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
        from: { id: 999, is_bot: false, first_name: "Alex" },
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

  test("closing a pending question without a reason is rejected with 400 Bad Request and broker throws", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const broker = new QuestionBroker(testStateDir);
    const store = new PluginStore(testStateDir);

    const posted = await broker.askUser({
      question: "Reject without reason test",
      options: [{ label: "A" }],
      chatId: 999,
    });

    // 1. Broker throws on empty or whitespace reason
    await expect(broker.closeQuestion(posted.questionId, "")).rejects.toThrow("Missing reason");
    await expect(broker.closeQuestion(posted.questionId, "   ")).rejects.toThrow("Missing reason");

    // 2. HTTP route returns 400 Bad Request
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions/close", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Cookie: `ida_session=${token}`,
      },
      body: JSON.stringify({
        question_id: posted.questionId,
        reason: "   ",
      }),
    });

    const resp = await handleApiRequest(req, {
      store,
      broker,
      config: {
        botToken: "test-token",
        allowFrom: [999],
        stateDir: testStateDir,
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

    expect(resp.status).toBe(400);
    const data = await resp.json();
    expect(data.error).toContain("Missing reason");

    // Question remains pending
    expect(broker.getPendingQuestions().length).toBe(1);
  });

  test("ask_user with mini_app_only: true or chat: false appears in Mini App and posts nothing to chat (AC1)", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
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
    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: Record<string, unknown>) => {
      apiCalls.push({ method, payload });
      return { ok: true, result: { message_id: 12345 } };
    };

    const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

    // Call ask_user with mini_app_only: true
    const res = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 1,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          mini_app_only: true,
          questions: [
            {
              header: "Background Task Priority",
              question: "Which background worker should handle data indexing?",
              options: [
                { label: "Worker A (Recommended)", description: "High-memory container" },
                { label: "Worker B", description: "Standard worker" },
              ],
            },
          ],
        },
      },
    });

    // Verify transparent return message indicating queued in Mini App without chat cards (Fix #3528, #3529)
    const returnText = (res?.result as any)?.content?.[0]?.text || "";
    expect(returnText).toContain("queued in Mini App");
    expect(returnText).toContain("no chat cards sent");

    // 1. Posts NOTHING to chat (no sendMessage calls)
    const chatCards = apiCalls.filter((c) => c.method === "sendMessage");
    expect(chatCards.length).toBe(0);

    // 2. Appears in the pending questions list for Mini App
    const pending = broker.getPendingQuestions();
    expect(pending.length).toBe(1);
    expect(pending[0].question).toBe("Which background worker should handle data indexing?");
    expect(pending[0].status).toBe("pending");
    expect((pending[0] as any).mini_app_only || (pending[0] as any).miniAppOnly || (pending[0] as any).chat === false).toBe(true);

    // 3. Question can also be specified with per-question chat: false
    const res2 = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              chat: false,
              question: "Silent question for Mini App only?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    // Still no chat cards sent
    expect(apiCalls.filter((c) => c.method === "sendMessage").length).toBe(0);
    expect(broker.getPendingQuestions().length).toBe(2);
  });

  test("AC2: a question answered in the asking session leaves the outstanding list", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const mcp = new StdioMcpServer(config, store, broker, null, permRelay);

    // 1. Post a question
    const postRes = await broker.askUser({
      question: "Which database should we use?",
      options: [{ label: "PostgreSQL" }, { label: "SQLite" }],
      turnId: "turn_sess_1",
      chatId: 999,
    });
    const qid = postRes.questionId;

    // Verify it is initially pending in broker and Mini App endpoint
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const reqBefore = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const respBefore = await handleApiRequest(reqBefore, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const dataBefore = await respBefore.json();
    expect(dataBefore.questions.some((q: any) => q.id === qid)).toBe(true);

    // 2. The asking agent learns the question was answered in its session and resolves it via answer_question tool
    const answerCall = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: {
        name: "answer_question",
        arguments: {
          question_id: qid,
          choice: "PostgreSQL",
        },
      },
    });

    expect(answerCall?.isError).toBeFalsy();

    // 3. Question must have left the outstanding list in broker and Mini App
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(false);

    const reqAfter = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const respAfter = await handleApiRequest(reqAfter, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const dataAfter = await respAfter.json();
    expect(dataAfter.questions.some((q: any) => q.id === qid)).toBe(false);
  });

  test("AC3: a question answered outside the Mini App and outside the asking session (e.g. a plain Telegram reply) leaves the outstanding list", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const editedCards: Array<{ chatId?: number; messageId?: number; chatData?: string }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ content, meta });
    }, store);

    (bot as any).callApi = async () => ({ ok: true, result: true });
    (bot as any).editMessageWidgetData = async (opts: { chatId?: number; messageId?: number; chatData?: string }) => {
      editedCards.push(opts);
      return { ok: true, updated: true };
    };

    // 1. Post a question that sends a card to Telegram with messageId 601
    const postRes = await broker.askUser({
      question: "Which items should go to Sara and Pauli?",
      options: [{ label: "Both items" }, { label: "Sara only" }],
      chatId: 999,
      presentation: "widget",
    });
    const qid = postRes.questionId;
    broker.setMessageId(qid, 601);

    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);

    // 2a. A non-matching conversational reply does not answer or dismiss the question
    await (bot as any).handleUpdate({
      update_id: 1233,
      message: {
        message_id: 6015,
        date: Math.floor(Date.now() / 1000),
        chat: { id: 999, type: "private" },
        from: { id: 999, is_bot: false, first_name: "User" },
        text: "What does this mean?",
        reply_to_message: {
          message_id: 601,
          date: Math.floor(Date.now() / 1000) - 10,
          chat: { id: 999, type: "private" },
          text: "Which items should go to Sara and Pauli?",
        },
      },
    });
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(true);
    expect(editedCards.length).toBe(0);

    // 2b. User in Telegram replies directly to message 601 with "Both items" (outside Mini App and outside asking session)
    await (bot as any).handleUpdate({
      update_id: 1234,
      message: {
        message_id: 602,
        date: Math.floor(Date.now() / 1000),
        chat: { id: 999, type: "private" },
        from: { id: 999, is_bot: false, first_name: "User" },
        text: "Both items",
        reply_to_message: {
          message_id: 601,
          date: Math.floor(Date.now() / 1000) - 10,
          chat: { id: 999, type: "private" },
          text: "Which items should go to Sara and Pauli?",
        },
      },
    });

    // 3. The question card in Telegram was settled to show resolved answer
    expect(editedCards.some((c) => c.messageId === 601 && (c.chatData || "").includes("Both items"))).toBe(true);

    // 4. Question must leave the outstanding list in broker and Mini App
    expect(broker.getPendingQuestions().some((q) => q.id === qid)).toBe(false);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const resp = await handleApiRequest(req, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const data = await resp.json();
    expect(data.questions.some((q: any) => q.id === qid)).toBe(false);
  });

  test("AC4: an unanswered question stays listed", async () => {
    const { handleApiRequest } = await import("../src/web/routes.js");
    const { createSessionToken } = await import("../src/web/auth.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 8093,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
    };

    // Post two questions: q1 (to be answered) and q2 (unanswered)
    const q1 = await broker.askUser({
      question: "Answered question",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 999,
    });
    const q2 = await broker.askUser({
      question: "Unanswered question waiting for operator",
      options: [{ label: "Option A" }, { label: "Option B" }],
      chatId: 999,
    });

    // Resolve q1
    await broker.resolveAnswer(q1.questionId, 0);

    // q2 remains unanswered
    const pending = broker.getPendingQuestions();
    expect(pending.some((q) => q.id === q1.questionId)).toBe(false);
    expect(pending.some((q) => q.id === q2.questionId)).toBe(true);

    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(999, sessionSecret, 3600);
    const req = new Request("http://127.0.0.1:8093/api/app/questions", {
      method: "GET",
      headers: { Cookie: `ida_session=${token}` },
    });
    const resp = await handleApiRequest(req, { store, broker, config, sessionSecret, emitChannelEvent: () => {} } as any);
    const data = await resp.json();

    expect(data.questions.some((q: any) => q.id === q1.questionId)).toBe(false);
    expect(data.questions.some((q: any) => q.id === q2.questionId)).toBe(true);
    const found = data.questions.find((q: any) => q.id === q2.questionId);
    expect(found.status).toBe("pending");
  });

  test("AC1 & AC2: channel core created before the bot delivers the card with buttons and messageId once the bot is attached", async () => {
    const { SharedTelegramChannelCore } = await import("../src/core/channel-core.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [999],
      maxChatChars: 1200,
      port: 8095,
      stateDir: testStateDir,
      voiceReplies: "off" as const,
      botCommands: [],
      miniAppUrl: "https://ida.example.ts.net",
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const sentCards: any[] = [];

    // server.ts creates the channel core with no bot, then attaches the bot once it exists
    const channelCore = new SharedTelegramChannelCore({ config: config as any, store, broker, bot: null, permRelay });

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    (bot as any).sendQuestionCard = async (chatId: number, qid: string, card: any) => {
      sentCards.push({ chatId, qid, card });
      broker.setMessageId(qid, 42001);
      return { ok: true, result: { message_id: 42001 } };
    };

    channelCore.bot = bot;

    const res: any = await channelCore.handleIpcMessage({
      type: "ask_user",
      questions: [
        {
          question: "Confirm deployment of fix for vanished buttons?",
          header: "Deployment Question",
          options: [{ label: "Approve (Recommended)" }, { label: "Reject" }],
        },
      ],
    });
    expect(res.status).toBe("posted");

    // Verify chat card WAS sent and buttons are present
    expect(sentCards.length).toBe(1);
    expect(sentCards[0].chatId).toBe(999);
    expect(sentCards[0].card.buttons.length).toBeGreaterThanOrEqual(2);
    expect(sentCards[0].card.buttons[0].text).toContain("Approve (Recommended)");

    // Verify messageId was recorded on the stored question
    const storedQ = broker.getQuestion(res.questionId);
    expect(storedQ).toBeDefined();
    expect(storedQ!.messageId).toBe(42001);
  });

  test("AC2: ask_user returns error and does not report question posted when Telegram API fails", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    // Simulate Telegram sendWidget/sendRichMessage/sendMessage failing
    (bot as any).callApi = async (method: string) => {
      if (method === "sendWidget" || method === "sendRichMessage" || method === "sendMessage") {
        return { ok: false, description: "Bad Request: chat not found" };
      }
      return { ok: true };
    };

    const mcp = new StdioMcpServer(config as any, store, broker, bot, permRelay);

    const askResp = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 88,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this fail?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    const parsed = typeof (askResp as any)?.result?.content?.[0]?.text === "string"
      ? JSON.parse((askResp as any).result.content[0].text)
      : (askResp as any)?.result;

    // Must NOT report "Question ... posted to the user" when send failed
    expect(parsed.success).toBe(false);
    expect(parsed.error).toContain("chat not found");
    expect("isError" in (askResp || {})).toBe(false);
    expect((askResp as any)?.result?.isError).toBe(true);
  });

  test("ask_user MCP tool surfaces failure when delivery fails and succeeds without failure signal when delivered", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);
    const channelEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 8093,
      miniAppUrl: "https://ida.example.test",
      isPrimary: true,
      maxChatChars: 1200,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      voiceReplies: "off" as const,
      botCommands: [],
      instance: "prime",
    };

    // When bot fails delivery
    const failingBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.markDeliveryFailed(qid, "Telegram network error");
        return { ok: false, error: "Telegram network error" };
      },
    } as any;

    const failingServer = new StdioMcpServer(config as any, store, broker, failingBot, permRelay);
    failingServer.emitChannelNotification = (content, meta) => {
      channelEvents.push({ content, meta });
    };

    const failCall = await failingServer.handleMessage({
      jsonrpc: "2.0",
      id: "req_fail_1",
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this fail?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    expect("isError" in (failCall || {})).toBe(false);
    expect((failCall?.result as any)?.isError).toBe(true);
    expect(failCall?.result?.content?.[0]?.text).toContain("Telegram network error");
    expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(true);

    // When bot succeeds delivery
    channelEvents.length = 0;
    const succeedingBot = {
      getLastThreadId: () => undefined,
      sendQuestionCard: async (chatId: number, qid: string) => {
        broker.setMessageId(qid, 991122);
        return { ok: true, messageId: 991122, result: { message_id: 991122 } };
      },
    } as any;

    const succeedingServer = new StdioMcpServer(config as any, store, broker, succeedingBot, permRelay);
    succeedingServer.emitChannelNotification = (content, meta) => {
      channelEvents.push({ content, meta });
    };

    const okCall = await succeedingServer.handleMessage({
      jsonrpc: "2.0",
      id: "req_ok_1",
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [
            {
              question: "Will this succeed?",
              options: [{ label: "Yes" }, { label: "No" }],
            },
          ],
        },
      },
    });

    expect(okCall?.isError).toBeUndefined();
    expect(okCall?.result?.content?.[0]?.text).toContain("posted to the user");
    expect(okCall?.result?.content?.[0]?.text).not.toContain("Failed to deliver");
    expect(channelEvents.some((e) => e.meta.event === "question_delivery_failed")).toBe(false);
  });

  test("sweepUndeliveredQuestions detects legacy questions left pending with no messageId and marks them failed", async () => {
    const broker = new QuestionBroker(testStateDir);

    // Create a question stuck in pending with no messageId (legacy failure shape per issue 3415)
    const qStuck = await broker.askUser({
      question: "Legacy stuck question with no messageId?",
      options: [{ label: "Yes" }, { label: "No" }],
      turnId: "turn_legacy_stuck",
      chatId: 999,
      chat: true,
      mini_app_only: false,
    });

    // Create a delivered question with messageId
    const qDelivered = await broker.askUser({
      question: "Delivered question with messageId?",
      options: [{ label: "Yes" }, { label: "No" }],
      chatId: 999,
    });
    broker.setMessageId(qDelivered.questionId, 882244);

    // Create a mini_app_only question with no messageId (valid, should stay pending)
    const qMiniApp = await broker.askUser({
      question: "Mini app only question?",
      options: [{ label: "Yes" }, { label: "No" }],
      mini_app_only: true,
    });

    const swept = broker.sweepUndeliveredQuestions();
    expect(swept.some((q) => q.id === qStuck.questionId)).toBe(true);
    expect(swept.some((q) => q.id === qDelivered.questionId)).toBe(false);
    expect(swept.some((q) => q.id === qMiniApp.questionId)).toBe(false);

    const pending = broker.getPendingQuestions();
    expect(pending.some((q) => q.id === qStuck.questionId)).toBe(false);
    expect(pending.some((q) => q.id === qDelivered.questionId)).toBe(true);
    expect(pending.some((q) => q.id === qMiniApp.questionId)).toBe(true);

    const stuckDoc = broker.getQuestion(qStuck.questionId);
    expect(stuckDoc?.status).toBe("failed");
    expect(stuckDoc?.deliveryError).toContain("no Telegram messageId");
  });

  test("AC1.3: sendQuestionCard never downgrades failed sendWidget silently", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const calls: Array<{ method: string; payload: any }> = [];

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {});
    (bot as any).callApi = async (method: string, payload: any) => {
      calls.push({ method, payload });
      if (method === "sendWidget") {
        return { ok: false, error_code: 400, description: "Bad Request: INPUT_MEDIA_WIDGET_NOT_ALLOWED" };
      }
      return { ok: true, result: { message_id: 777 } };
    };

    const q = await broker.askUser({
      question: "No silent fallback question?",
      options: [{ label: "OK" }],
      presentation: "widget",
      chatId: 999,
    });
    const card = broker.renderQuestionCard(q.questionId)!;
    const widgetFailRes = await bot.sendQuestionCard(999, q.questionId, card);
    expect(widgetFailRes.ok).toBe(false);
    expect(widgetFailRes.error).toContain("INPUT_MEDIA_WIDGET_NOT_ALLOWED");
    expect(calls.some((c) => c.method === "sendRichMessage" || c.method === "sendMessage")).toBe(false);
  });

  test("ask_user with no presentation defaults to Rich Message, mirrored AskUserQuestion defaults to Rich Message, and explicit widget rejection has no fallback", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { SharedTelegramChannelCore } = await import("../src/core/channel-core.js");
    const { spawn } = await import("node:child_process");
    const { createServer } = await import("node:net");

    const config = {
      botToken: "test-token",
      allowFrom: [999],
      stateDir: testStateDir,
      socketPath: join(testStateDir, "rich_default_hook.sock"),
      port: 0,
      miniAppUrl: "https://ida.example.ts.net",
      isPrimary: true,
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      botCommands: [],
    };

    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);
    const apiCalls: Array<{ method: string; payload: any }> = [];
    let msgId = 1000;

    const bot = new TelegramBotClient(config as any, broker, permRelay, () => {}, store);
    (bot as any).callApi = async (method: string, payload: any) => {
      apiCalls.push({ method, payload });
      if (method === "sendWidget") {
        return { ok: false, error_code: 400, description: "Bad Request: INPUT_MEDIA_WIDGET_NOT_ALLOWED" };
      }
      if (method === "sendRichMessage" || method === "sendMessage") {
        return { ok: true, result: { message_id: ++msgId } };
      }
      return { ok: true, result: true };
    };

    const mcp = new StdioMcpServer(config as any, store, broker, bot, permRelay);

    // 1. Direct ask_user with no presentation sends Rich Message, not widget
    const directRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 201,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          questions: [{ question: "Default card surface?", options: [{ label: "Rich" }, { label: "Widget" }] }],
        },
      },
    });
    const directParsed = JSON.parse((directRes?.result as any).content[0].text);
    expect(directParsed.status).toBe("posted");
    expect(directParsed.presentation).toBe("rich");
    expect(apiCalls.filter((c) => c.method === "sendRichMessage").length).toBe(1);
    expect(apiCalls.filter((c) => c.method === "sendWidget").length).toBe(0);

    // 2. Console AskUserQuestion mirrored via hook -> IPC socket -> ChannelCore also sends Rich Message
    apiCalls.length = 0;
    const core = new SharedTelegramChannelCore({ config: config as any, store, broker, bot, permRelay });
    const ipcServer = createServer((socket) => {
      let buf = "";
      socket.on("data", (d) => {
        buf += d.toString();
        const nl = buf.indexOf("\n");
        if (nl !== -1) {
          const msg = JSON.parse(buf.slice(0, nl));
          core.handleIpcMessage(msg).then((res) => {
            socket.write(JSON.stringify(res) + "\n");
            socket.end();
          });
        }
      });
    });
    await new Promise<void>((resolve) => ipcServer.listen(config.socketPath, resolve));

    try {
      const hookPath = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
      await new Promise<void>((resolve, reject) => {
        const proc = spawn("node", [hookPath], {
          env: {
            ...process.env,
            IDA_TELEGRAM_ROLE: "primary",
            STATE_DIR: testStateDir,
            SOCKET_PATH: config.socketPath,
          },
        });
        let stderr = "";
        proc.stderr.on("data", (d) => (stderr += d.toString()));
        proc.on("error", reject);
        proc.on("close", (code) => (code === 0 ? resolve() : reject(new Error(`Hook exited ${code}: ${stderr}`))));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            turn_id: "turn_mirror_1",
            tool_input: {
              questions: [{ question: "Mirrored question?", options: [{ label: "Yes" }, { label: "No" }] }],
            },
          }) + "\n"
        );
        proc.stdin.end();
      });

      expect(apiCalls.filter((c) => c.method === "sendRichMessage").length).toBe(1);
      expect(apiCalls.filter((c) => c.method === "sendWidget").length).toBe(0);
    } finally {
      ipcServer.close();
    }

    // 3. Explicit widget request rejected by Telegram fails with Telegram's error and zero fallback
    apiCalls.length = 0;
    const widgetRes = await mcp.handleMessage({
      jsonrpc: "2.0",
      id: 202,
      method: "tools/call",
      params: {
        name: "ask_user",
        arguments: {
          presentation: "widget",
          questions: [{ question: "Force widget?", options: [{ label: "Try" }] }],
        },
      },
    });
    const widgetParsed = JSON.parse((widgetRes?.result as any).content[0].text);
    expect((widgetRes?.result as any)?.isError).toBe(true);
    expect(widgetParsed.success).toBe(false);
    expect(widgetParsed.error).toContain("INPUT_MEDIA_WIDGET_NOT_ALLOWED");
    expect(apiCalls.filter((c) => c.method === "sendWidget").length).toBe(1);
    expect(apiCalls.filter((c) => c.method === "sendRichMessage" || c.method === "sendMessage").length).toBe(0);
  });
});
