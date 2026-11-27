import { describe, test, expect } from "bun:test";
import { loadConfig } from "../src/config.js";
import { StdioMcpServer } from "../src/mcp/server.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Message Actions: Logic Check and Explain Buttons (AC1, AC2)", () => {
  const allowFrom = [1111111111];

  test("AC1: pressing logic-check button delivers request naming message and Ida replies with premise-check verdict", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac1-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2003 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message with conclusions
      const messageText = "**Conclusion:** Migrating the schema now will eliminate duplicate records.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 10,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: messageText,
          },
        },
      });

      // 2. User presses the logic-check button on that message (message_id: 2003)
      await (bot as any).handleUpdate({
        update_id: 501,
        callback_query: {
          id: "cb_lc_1",
          from: { id: 1111111111, is_bot: false, first_name: "Alex" },
          message: {
            message_id: 2003,
            date: Date.now(),
            chat: { id: 1111111111, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[{ text: "🧐 Check logic", callback_data: "logic_check" }, { text: "💡 Explain", callback_data: "explain" }]],
            },
          },
          data: "logic_check",
        },
      });

      // 3. Verify channel event delivered to session naming that message
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("logic_check");
      expect(event.meta.target_message_id).toBe("2003");
      expect(event.meta.target_excerpt).toContain("Migrating the schema now");
      expect(event.content).toContain("2003");
      expect(event.content).toContain("logic check");
      expect(event.content).toContain("receiving it from a peer");

      // Verify button tap answered and message edited
      const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
      expect(answerCall).toBeDefined();

      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: 🧐 Check logic ✅");

      // 4. Ida's reply is a premise-check verdict with appealable natural-language reasons
      const verdictText = [
        "**Verdict: PASS**",
        "",
        ">! **Premise Check:**",
        "> Evaluated on the face of the record against the deduplication ask. The conclusion follows validly from the dry-run migration output quoted inline, evidence is proportionate to the migration stakes with no plausible unruled rival explanation, and no standing rules are breached. Verified for upstream reporting.",
      ].join("\n");

      const verdictResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 11,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: verdictText,
            reply_to: 2003,
          },
        },
      });

      const parsedVerdict = JSON.parse((verdictResp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedVerdict.success).toBe(true);

      const lastSendMessage = apiCalls.filter((c) => c.method === "sendRichMessage").pop();
      expect(lastSendMessage?.body.rich_message?.markdown).toContain("Verdict: PASS");
      expect(lastSendMessage?.body.rich_message?.markdown).toContain("face of the record");
      expect(lastSendMessage?.body.rich_message?.markdown).toContain("dry-run migration output");
      expect(lastSendMessage?.body.reply_parameters?.message_id).toBe(2003);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC2: pressing explain button delivers request naming message and Ida replies expanding that message", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac2-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2004 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message
      const messageText = "**Policy:** We defer non-critical dependencies to stage 2.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 20,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: messageText,
          },
        },
      });

      // 2. User presses the explain button on message 2004
      await (bot as any).handleUpdate({
        update_id: 502,
        callback_query: {
          id: "cb_exp_1",
          from: { id: 1111111111, is_bot: false, first_name: "Alex" },
          message: {
            message_id: 2004,
            date: Date.now(),
            chat: { id: 1111111111, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[{ text: "🧐 Check logic", callback_data: "logic_check" }, { text: "💡 Explain", callback_data: "explain" }]],
            },
          },
          data: "explain",
        },
      });

      // 3. Verify channel event delivered to session naming that message
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("explain");
      expect(event.meta.target_message_id).toBe("2004");
      expect(event.meta.target_excerpt).toContain("We defer non-critical dependencies");
      expect(event.content).toContain("2004");
      expect(event.content).toContain("explain");
      expect(event.content).toContain("in more detail");

      // 4. Ida's reply expands that message
      const explanationText = [
        "**Detailed Explanation:**",
        "",
        "Deferring non-critical dependencies protects the current delivery deadline by:",
        "1. Keeping the immediate execution graph acyclic and small.",
        "2. Preventing speculative work from compounding review load.",
        "3. Allowing empirical feedback from stage 1 to reshape stage 2 requirements.",
      ].join("\n");

      const explainResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 21,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: explanationText,
            reply_to: 2004,
          },
        },
      });

      const parsedExplain = JSON.parse((explainResp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedExplain.success).toBe(true);

      const lastSendMessage = apiCalls.filter((c) => c.method === "sendRichMessage").pop();
      expect(lastSendMessage?.body.rich_message?.markdown).toContain("Detailed Explanation");
      expect(lastSendMessage?.body.rich_message?.markdown).toContain("Deferring non-critical dependencies");
      expect(lastSendMessage?.body.reply_parameters?.message_id).toBe(2004);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC2: pressing reasons button marks card and delivers request naming message to Ida", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac2-reasons-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2005 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message with action buttons
      const messageText = "**Finding:** The pipeline verified 14 invariant properties.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 30,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: messageText,
          },
        },
      });

      // 2. User presses the reasons button on message 2005
      await (bot as any).handleUpdate({
        update_id: 503,
        callback_query: {
          id: "cb_rsn_1",
          from: { id: 1111111111, is_bot: false, first_name: "Alex" },
          message: {
            message_id: 2005,
            date: Date.now(),
            chat: { id: 1111111111, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[
                { text: "🧐 Check logic", callback_data: "logic_check" },
                { text: "💡 Explain", callback_data: "explain" },
                { text: "🧾 Reasons", callback_data: "reasons" },
              ]],
            },
          },
          data: "reasons",
        },
      });

      // 3. Verify channel event delivered to session naming target message and excerpt
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("reasons");
      expect(event.meta.action).toBe("reasons");
      expect(event.meta.target_message_id).toBe("2005");
      expect(event.meta.target_excerpt).toContain("pipeline verified 14 invariant properties");
      expect(event.content).toContain("2005");
      expect(event.content).toContain("reasons");
      expect(event.content).toContain("How do you know that?");

      // 4. Verify card was marked with Selected: 🧾 Reasons ✅ and action buttons removed
      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: 🧾 Reasons ✅");
      const remainingKb = editCall?.body.reply_markup?.inline_keyboard || [];
      expect(remainingKb.flat().find((b: any) => b.callback_data === "reasons")).toBeUndefined();
      expect(remainingKb.flat().find((b: any) => b.callback_data === "logic_check")).toBeUndefined();
      expect(remainingKb.flat().find((b: any) => b.callback_data === "explain")).toBeUndefined();

      // 5. Verify callback answered
      const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
      expect(answerCall).toBeDefined();
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("pressing the thanks button marks card and tells Ida the user is done with the thread", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-thanks-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2005 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Ida sends a message with action buttons
      const messageText = "**Finding:** The pipeline verified 14 invariant properties.";
      await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 30,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: messageText,
          },
        },
      });

      // 2. User presses the thanks button on message 2005
      await (bot as any).handleUpdate({
        update_id: 504,
        callback_query: {
          id: "cb_thx_1",
          from: { id: 1111111111, is_bot: false, first_name: "Alex" },
          message: {
            message_id: 2005,
            date: Date.now(),
            chat: { id: 1111111111, type: "private" },
            text: messageText,
            reply_markup: {
              inline_keyboard: [[
                { text: "🧐 Check logic", callback_data: "logic_check" },
                { text: "💡 Explain", callback_data: "explain" },
                { text: "🧾", callback_data: "reasons" },
                { text: "🙏", callback_data: "thanks" },
              ]],
            },
          },
          data: "thanks",
        },
      });

      // 3. Verify channel event delivered to session naming the message, meaning read and done
      expect(emittedEvents.length).toBe(1);
      const event = emittedEvents[0];
      expect(event.meta.event).toBe("thanks");
      expect(event.meta.action).toBe("thanks");
      expect(event.meta.payload).toBe("thanks");
      expect(event.meta.target_message_id).toBe("2005");
      expect(event.meta.target_excerpt).toContain("pipeline verified 14 invariant properties");
      expect(event.content).toContain("2005");
      expect(event.content).toContain("done with its thread");
      expect(event.content).toContain("close the thread unless more on its topic is due soon");

      // 4. Verify card was marked with Selected: 🙏 Thanks ✅ and action buttons removed
      const editCall = apiCalls.find((c) => c.method === "editMessageText");
      expect(editCall).toBeDefined();
      expect(editCall?.body.text).toContain("Selected: 🙏 Thanks ✅");
      const remainingKb = editCall?.body.reply_markup?.inline_keyboard || [];
      expect(remainingKb.flat().find((b: any) => b.callback_data === "thanks")).toBeUndefined();
      expect(remainingKb.flat().find((b: any) => b.callback_data === "logic_check")).toBeUndefined();
      expect(remainingKb.flat().find((b: any) => b.callback_data === "explain")).toBeUndefined();

      // 5. Verify callback answered
      const answerCall = apiCalls.find((c) => c.method === "answerCallbackQuery");
      expect(answerCall).toBeDefined();
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC3: Ida handles reasons event by returning multi-level verbatim argument chain in details", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-ac3-reasons-"));
    const config = loadConfig({
      MINI_APP_URL: "https://ida.example.test",
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      ALLOWED_USER_IDS: "1111111111",
      STATE_DIR: stateDir,
      VOICE_REPLIES: "off",
    });

    const store = new PluginStore(config.stateDir);
    const broker = new QuestionBroker(config.stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2006 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // Verbatim Argdown for Level 1 (Ida Prime -> Test User)
      const primeArgdown = [
        "```argdown",
        "===",
        "asks:",
        "  tg-638: Are all 14 pipeline invariants verified?",
        "answers:",
        "  tg-638: 3",
        "notes:",
        "  a: plugins/ida/skills/premise-check/SKILL.md",
        "===",
        "",
        "(1) Sara verified the child worker reports without defects. -- test trace ^a",
        "(2) Verified reports prove invariant compliance. -- semantic check",
        "-- Sound aggregation warrant. Unless: sub-reports contradictory. --",
        "(3) Therefore, all 14 pipeline invariants are verified.",
        "```",
      ].join("\n");

      // Verbatim Argdown for Level 2 (Sara -> Ida Prime)
      const saraArgdown = [
        "```argdown",
        "===",
        "asks:",
        "  sara-sub-1: Did RBG compliance review pass?",
        "answers:",
        "  sara-sub-1: 3",
        "notes:",
        "  b: plugins/crew/skills/axioms/reasons.md",
        "===",
        "",
        "(1) RBG review judged the compliance axioms satisfied. -- rule audit ^b",
        "(2) Axiom satisfaction is verified. -- tool output",
        "-- Axiomatic deduction. Unless: rule conflict detected. --",
        "(3) Therefore, compliance review passes without exception.",
        "```",
      ].join("\n");

      // Verbatim Argdown for Level 3 (Worker rbg -> Sara)
      const rbgArgdown = [
        "```argdown",
        "===",
        "asks:",
        "  rbg-task-1: Are reasons axioms observed in execution trace?",
        "answers:",
        "  rbg-task-1: 2",
        "===",
        "",
        "(1) All 14 trace spans contain Toulmin argdowns. -- phoenix span inspection",
        "-- Complete induction over closed trace set. --",
        "(2) Therefore, reasons axioms are satisfied across all spans.",
        "```",
      ].join("\n");

      // Level 4 (Worker analyst -> Worker rbg): missing argument link
      const missingLinkText = "[Missing argument: no premise-check record found for delegation to Worker (analyst)]";

      // Multi-level delegation chain formatted into detail (Details page)
      const reasonsDetail = [
        "# Reasons & Argument Chain for Message 2005",
        "",
        "## Delegation Chain Overview",
        "- Level 1: Ida Prime → Test User (User)",
        "  - Level 2: Sara → Ida Prime",
        "    - Level 3: Worker (rbg) → Sara",
        "      - Level 4: Worker (analyst) → Worker (rbg) [MISSING]",
        "",
        "---",
        "",
        "### Level 1: Ida Prime → Test User (User)",
        primeArgdown,
        "",
        "### Level 2: Sara → Ida Prime",
        saraArgdown,
        "",
        "### Level 3: Worker (rbg) → Sara",
        rbgArgdown,
        "",
        "### Level 4: Worker (analyst) → Worker (rbg)",
        missingLinkText,
      ].join("\n");

      const chatSummaryText = [
        "**Reasons for message 2005:**",
        "• Root conclusion verified through a 3-tier delegation chain (Prime → Sara → Worker rbg).",
        "• Link to analyst unrecorded and noted as missing.",
        "• Full verbatim Toulmin argdown arguments are attached in Details.",
      ].join("\n");

      // Ida replies with reply_to: 2005, summary and collapsed <details> argument chain in Rich Message
      const fullMarkdown = `${chatSummaryText}\n\n<details>\n<summary>Argument Chain</summary>\n\n${reasonsDetail}\n\n</details>`;
      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 31,
        method: "tools/call",
        params: {
          name: "send_rich_message",
          arguments: {
            chat_id: 1111111111,
            markdown: fullMarkdown,
            reply_to: 2005,
          },
        },
      });

      const parsedResp = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResp.success).toBe(true);

      const lastSendMessage = apiCalls.filter((c) => c.method === "sendRichMessage").pop();
      expect(lastSendMessage?.body.reply_parameters?.message_id).toBe(2005);
      const sentMarkdown = lastSendMessage?.body.rich_message?.markdown as string;
      expect(sentMarkdown).toContain("Reasons for message 2005");

      // Verbatim Argdowns present
      expect(sentMarkdown).toContain(primeArgdown);
      expect(sentMarkdown).toContain(saraArgdown);
      expect(sentMarkdown).toContain(rbgArgdown);

      // Senders and recipients labeled per link
      expect(sentMarkdown).toContain("Level 1: Ida Prime → Test User");
      expect(sentMarkdown).toContain("Level 2: Sara → Ida Prime");
      expect(sentMarkdown).toContain("Level 3: Worker (rbg) → Sara");

      // Delegation depth nesting
      expect(sentMarkdown).toContain("Level 1:");
      expect(sentMarkdown).toContain("Level 2:");
      expect(sentMarkdown).toContain("Level 3:");
      expect(sentMarkdown).toContain("Level 4:");

      // Missing argument explicitly named and never paraphrased
      expect(sentMarkdown).toContain(missingLinkText);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("parseInboundUpdate parses logic_check and explain callback queries", () => {
    const updateLogicCheck: TelegramUpdate = {
      update_id: 503,
      callback_query: {
        id: "cb_lc_2",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        message: {
          message_id: 3001,
          date: Date.now(),
          chat: { id: 1111111111, type: "private" },
          text: "Here is statement A.",
        },
        data: "logic_check",
      },
    };

    const resultLc = parseInboundUpdate(updateLogicCheck, allowFrom);
    expect(resultLc).not.toBeNull();
    expect(resultLc?.event).toBe("logic_check");
    expect(resultLc?.meta.target_message_id).toBe("3001");
    expect(resultLc?.meta.target_excerpt).toBe("Here is statement A.");
    expect(resultLc?.content).toContain("3001");
    expect(resultLc?.content).toContain("logic check");

    const updateExplain: TelegramUpdate = {
      update_id: 504,
      callback_query: {
        id: "cb_exp_2",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        message: {
          message_id: 3002,
          date: Date.now(),
          chat: { id: 1111111111, type: "private" },
          text: "Here is statement B.",
        },
        data: "explain",
      },
    };

    const resultExp = parseInboundUpdate(updateExplain, allowFrom);
    expect(resultExp).not.toBeNull();
    expect(resultExp?.event).toBe("explain");
    expect(resultExp?.meta.target_message_id).toBe("3002");
    expect(resultExp?.meta.target_excerpt).toBe("Here is statement B.");
    expect(resultExp?.content).toContain("3002");
    expect(resultExp?.content).toContain("explain");

    const updateReasons: TelegramUpdate = {
      update_id: 505,
      callback_query: {
        id: "cb_rsn_2",
        from: { id: 1111111111, is_bot: false, first_name: "Alex" },
        message: {
          message_id: 3003,
          date: Date.now(),
          chat: { id: 1111111111, type: "private" },
          text: "Here is statement C.",
        },
        data: "reasons",
      },
    };

    const resultRsn = parseInboundUpdate(updateReasons, allowFrom);
    expect(resultRsn).not.toBeNull();
    expect(resultRsn?.event).toBe("reasons");
    expect(resultRsn?.meta.target_message_id).toBe("3003");
    expect(resultRsn?.meta.target_excerpt).toBe("Here is statement C.");
    expect(resultRsn?.content).toContain("3003");
    expect(resultRsn?.content).toContain("reasons");
    expect(resultRsn?.content).toContain("How do you know that?");
  });
});
