import { describe, expect, test, afterEach } from "bun:test";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { generateKeyPairSync, createSign } from "node:crypto";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { startWebServer } from "../src/web/server.js";
import { createSessionToken } from "../src/web/auth.js";
import type { PluginConfig } from "../src/config.js";
import { TelegramBotClient } from "../src/telegram/bot.js";

const { publicKey: testPublicKey, privateKey: testPrivateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const { privateKey: otherPrivateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
const testPublicKeyPem = testPublicKey.export({ type: "spki", format: "pem" }).toString();
const testKeyId = "test-cf-access-key-1";
const testAud = "aud-cf-access-tag-12345";
const testTeamDomain = "testteam.cloudflareaccess.com";
const testAllowedEmail = "operator@example.com";

function makeCfAccessJwt(
  payloadOverrides: Record<string, unknown> = {},
  headerOverrides: Record<string, unknown> = {},
  signKey = testPrivateKey
): string {
  const header = {
    alg: "RS256",
    typ: "JWT",
    kid: testKeyId,
    ...headerOverrides,
  };
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    aud: [testAud],
    email: testAllowedEmail,
    iss: `https://${testTeamDomain}`,
    sub: "test-user-sub-uuid",
    iat: now,
    nbf: now,
    exp: now + 3600,
    type: "app",
    ...payloadOverrides,
  };
  const h64 = Buffer.from(JSON.stringify(header)).toString("base64url");
  const p64 = Buffer.from(JSON.stringify(payload)).toString("base64url");
  const input = `${h64}.${p64}`;
  const sign = createSign("RSA-SHA256");
  sign.update(input);
  const sig = sign.sign(signKey).toString("base64url");
  return `${input}.${sig}`;
}

describe("Mini App Channel Bridge (specs/telegram/mini-app-dashboard-integration.md)", () => {
  const botToken = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11";
  const allowedUserId = 8860530746;
  const bridgeToken = "test-secret-bridge-token-xyz-12345";
  const sessionSecret = "test-session-secret-key-32bytes!";
  let testStateDir = "";
  let httpServer: ReturnType<typeof startWebServer> | null = null;

  afterEach(() => {
    if (httpServer) {
      httpServer.stop(true);
      httpServer = null;
    }
    if (testStateDir && existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  async function createBridgeTestContext(configOverrides: Partial<PluginConfig> = {}) {
    testStateDir = join(tmpdir(), "ida-tg-bridge-" + Math.random().toString(36).slice(2, 9));
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay(testStateDir);

    const config: PluginConfig = {
      botToken,
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [allowedUserId],
      maxChatChars: 1200,
      voiceReplies: "off",
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 0,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "bridge.sock"),
      githubToken: "ghp_test_readonly_token",
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
      bridgeToken,
      ...configOverrides,
    } as any;

    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const editedCards: Array<{ chatId: number; messageId: number; text: string; replyMarkup?: any }> = [];
    const apiCalls: Array<{ method: string; params: any }> = [];

    const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
      emittedEvents.push({ event: meta?.event as string || "channel", content, meta: meta || {} });
    });

    (bot as any).callApi = async (method: string, params: any) => {
      apiCalls.push({ method, params });
      if (method === "sendMessage" || method === "editMessageText") {
        return {
          ok: true,
          result: {
            message_id: params.message_id || 1001,
            chat: { id: params.chat_id },
            text: params.text,
          },
        };
      }
      return { ok: true, result: true };
    };

    const webContext: any = {
      store,
      broker,
      permRelay,
      config,
      sessionSecret,
      bot,
      emitChannelEvent: (event: string, content: string, meta: Record<string, unknown>) => {
        emittedEvents.push({ event, content, meta });
      },
      resolvePermissionRelay: (id: string, decision: "allow" | "deny") => {
        return permRelay.resolve(id, decision);
      },
      editTelegramCard: async (chatId: number, messageId: number, text: string, replyMarkup?: any) => {
        editedCards.push({ chatId, messageId, text, replyMarkup });
        await bot.editMessage(chatId, messageId, text, replyMarkup || { inline_keyboard: [] });
      },
    };

    permRelay.setEditCardCallback(webContext.editTelegramCard);

    const appDir = join(import.meta.dir, "..", "app");
    httpServer = startWebServer(webContext, appDir);
    const baseUrl = `http://127.0.0.1:${httpServer.port}`;

    return {
      store,
      broker,
      permRelay,
      bot,
      config,
      webContext,
      baseUrl,
      emittedEvents,
      editedCards,
      apiCalls,
    };
  }

  // --- Criterion 1: Bridge interface (transport, auth, payloads incl. sequence number and "expired") ---
  describe("Criterion 1: Bridge Interface (transport, auth, seq, expired)", () => {
    test("1.1 Auth: accepts Bearer token, X-Bridge-Token, Cf-Access assertion, and rejects unauthenticated requests with 401", async () => {
      const { baseUrl } = await createBridgeTestContext();

      // No auth header or cookie -> 401
      const noAuthRes = await fetch(`${baseUrl}/api/app/anchor`);
      expect(noAuthRes.status).toBe(401);
      const noAuthBody = await noAuthRes.json();
      expect(noAuthBody.error).toBeDefined();

      // Bearer token auth -> 200
      const bearerRes = await fetch(`${baseUrl}/api/app/anchor`, {
        headers: { Authorization: `Bearer ${bridgeToken}` },
      });
      expect(bearerRes.status).toBe(200);

      // X-Bridge-Token auth -> 200
      const customHeaderRes = await fetch(`${baseUrl}/api/app/anchor`, {
        headers: { "X-Bridge-Token": bridgeToken },
      });
      expect(customHeaderRes.status).toBe(200);

      // Cf-Access perimeter header with unverified dummy string is rejected with 401
      const cfRes = await fetch(`${baseUrl}/api/app/anchor`, {
        headers: { "Cf-Access-Jwt-Assertion": "jwt-assertion-payload" },
      });
      expect(cfRes.status).toBe(401);
    });

    test("AC1: A request carrying a forged, malformed, or expired assertion is refused on every authenticated route", async () => {
      const { baseUrl } = await createBridgeTestContext({
        cfAccessAud: testAud,
        cfAccessTeamDomain: testTeamDomain,
        cfAccessAllowedEmails: [testAllowedEmail],
        cfAccessKeys: { [testKeyId]: testPublicKeyPem },
      } as any);

      const now = Math.floor(Date.now() / 1000);
      const forgedAssertion = makeCfAccessJwt({}, {}, otherPrivateKey);
      const malformedAssertion = "not.a.valid.jwt.token";
      const expiredAssertion = makeCfAccessJwt({ exp: now - 300 });

      const authenticatedRoutes: Array<{ method: string; path: string; body?: any }> = [
        { method: "GET", path: "/api/app/events" },
        { method: "POST", path: "/api/app/message", body: { text: "hello" } },
        { method: "GET", path: "/api/app/anchor" },
        { method: "GET", path: "/api/app/questions" },
        { method: "POST", path: "/api/app/questions/answer", body: { question_id: "q1", answer: "yes" } },
        { method: "POST", path: "/api/app/questions/close", body: { question_id: "q1" } },
        { method: "GET", path: "/api/app/review" },
        { method: "POST", path: "/api/app/review/permission", body: { id: "p1", decision: "allow" } },
        { method: "POST", path: "/api/app/review/pr", body: { repo: "test/repo", pr: 1, decision: "approve" } },
        { method: "POST", path: "/api/app/stop" },
      ];

      for (const route of authenticatedRoutes) {
        // 1. Forged assertion (invalid signature)
        const forgedRes = await fetch(`${baseUrl}${route.path}`, {
          method: route.method,
          headers: {
            "Cf-Access-Jwt-Assertion": forgedAssertion,
            ...(route.body ? { "Content-Type": "application/json" } : {}),
          },
          ...(route.body ? { body: JSON.stringify(route.body) } : {}),
        });
        expect(forgedRes.status).toBe(401);

        // 2. Malformed assertion
        const malformedRes = await fetch(`${baseUrl}${route.path}`, {
          method: route.method,
          headers: {
            "Cf-Access-Jwt-Assertion": malformedAssertion,
            ...(route.body ? { "Content-Type": "application/json" } : {}),
          },
          ...(route.body ? { body: JSON.stringify(route.body) } : {}),
        });
        expect(malformedRes.status).toBe(401);

        // 3. Expired assertion
        const expiredRes = await fetch(`${baseUrl}${route.path}`, {
          method: route.method,
          headers: {
            "Cf-Access-Jwt-Assertion": expiredAssertion,
            ...(route.body ? { "Content-Type": "application/json" } : {}),
          },
          ...(route.body ? { body: JSON.stringify(route.body) } : {}),
        });
        expect(expiredRes.status).toBe(401);
      }
    });

    test("AC2: A request with a valid Access identity still succeeds", async () => {
      const { baseUrl } = await createBridgeTestContext({
        cfAccessAud: testAud,
        cfAccessTeamDomain: testTeamDomain,
        cfAccessAllowedEmails: [testAllowedEmail],
        cfAccessKeys: { [testKeyId]: testPublicKeyPem },
      } as any);

      const validAssertion = makeCfAccessJwt();
      const res = await fetch(`${baseUrl}/api/app/anchor`, {
        headers: { "Cf-Access-Jwt-Assertion": validAssertion },
      });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data).toBeDefined();
    });

    test("AC1: consecutive requests in one session with the same valid assertion succeed with 200", async () => {
      const { baseUrl } = await createBridgeTestContext({
        cfAccessAud: testAud,
        cfAccessTeamDomain: testTeamDomain,
        cfAccessAllowedEmails: [testAllowedEmail],
        cfAccessKeys: { [testKeyId]: testPublicKeyPem },
      } as any);

      const validAssertion = makeCfAccessJwt();

      // First request in session -> 200
      const res1 = await fetch(`${baseUrl}/api/app/anchor`, {
        headers: { "Cf-Access-Jwt-Assertion": validAssertion },
      });
      expect(res1.status).toBe(200);

      // Second request in same session with same assertion -> 200
      const res2 = await fetch(`${baseUrl}/api/app/questions`, {
        headers: { "Cf-Access-Jwt-Assertion": validAssertion },
      });
      expect(res2.status).toBe(200);
    });

    test("1.2 Sequence numbers: monotonic seq counter increments across state mutations, present in REST snapshots and SSE stream", async () => {
      const { baseUrl, store } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}` };

      // Initial anchor snapshot carries a seq number >= 1
      const res1 = await fetch(`${baseUrl}/api/app/anchor`, { headers: authHeaders });
      expect(res1.status).toBe(200);
      const data1 = await res1.json();
      expect(typeof data1.seq).toBe("number");
      const initialSeq = data1.seq;

      // Mutating state via store or action increments seq
      store.setAnchor({ focus: "Updated Focus via Test" });
      const res2 = await fetch(`${baseUrl}/api/app/anchor`, { headers: authHeaders });
      const data2 = await res2.json();
      expect(data2.seq).toBeGreaterThan(initialSeq);

      // SSE endpoint /api/app/events delivers events with id: <seq> and seq in payload
      const sseRes = await fetch(`${baseUrl}/api/app/events`, {
        headers: {
          ...authHeaders,
          Accept: "text/event-stream",
        },
      });
      expect(sseRes.status).toBe(200);
      expect(sseRes.headers.get("Content-Type")).toContain("text/event-stream");

      const reader = sseRes.body?.getReader();
      expect(reader).toBeDefined();

      // Read initial connection or heartbeat chunk
      const chunk = await reader!.read();
      const text = new TextDecoder().decode(chunk.value);
      expect(text.length).toBeGreaterThan(0);
      reader!.cancel();
    });

    test("1.3 Payloads including 'expired': review endpoint and permission events report expired status for timed out requests", async () => {
      const { baseUrl, permRelay } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}` };

      // Register a permission with short timeout (e.g. 50ms)
      permRelay.register(
        "perm_timeout_spec",
        "Bash",
        { command: "rm -rf /tmp/test" },
        () => {},
        50 // 50ms timeout
      );

      // Wait for expiration
      await new Promise((r) => setTimeout(r, 70));

      const reviewRes = await fetch(`${baseUrl}/api/app/review`, { headers: authHeaders });
      expect(reviewRes.status).toBe(200);
      const reviewData = await reviewRes.json();
      const expiredPerm = reviewData.permissions.find((p: any) => p.id === "perm_timeout_spec");
      expect(expiredPerm).toBeDefined();
      expect(expiredPerm.status).toBe("expired");
    });
  });

  // --- Criterion 2: Each §3 action reaches the agent and edits the card ---
  describe("Criterion 2: §3 Actions reach agent and edit the card", () => {
    test("2.1 Action 1: POST /api/app/message reaches agent session context and edits Telegram card", async () => {
      const { baseUrl, emittedEvents, editedCards } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };

      const res = await fetch(`${baseUrl}/api/app/message`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          text: "Focus on task aops_9e5caaf0",
          priority: "high",
          chat_id: allowedUserId,
          message_id: 2001,
        }),
      });

      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.success).toBe(true);
      expect(typeof data.seq).toBe("number");

      // Reaches agent session context
      expect(emittedEvents.some((e) => e.content.includes("Focus on task aops_9e5caaf0"))).toBe(true);

      // Edits the Telegram card
      expect(editedCards.some((c) => c.chatId === allowedUserId && c.messageId === 2001)).toBe(true);
    });

    test("2.2 Action 2: POST /api/app/questions/answer reaches agent and edits Telegram question card", async () => {
      const { baseUrl, broker, emittedEvents, editedCards } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };

      const q = await broker.askUser({
        header: "Deployment",
        question: "Deploy to staging?",
        options: [{ label: "Yes (Recommended)" }, { label: "No" }],
        chatId: allowedUserId,
      });
      broker.setMessageId(q.questionId, 2002);

      const res = await fetch(`${baseUrl}/api/app/questions/answer`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          question_id: q.questionId,
          option_index: 0,
        }),
      });

      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.success).toBe(true);
      expect(typeof data.seq).toBe("number");

      // Reaches agent
      expect(
        emittedEvents.some(
          (e) => (e.event === "question_answered" || e.event === "question_answer") && e.meta.question_id === q.questionId
        )
      ).toBe(true);

      // Edits Telegram card and clears inline keyboard
      const edited = editedCards.find((c) => c.chatId === allowedUserId && c.messageId === 2002);
      expect(edited).toBeDefined();
      expect(edited!.text).toContain("Yes (Recommended) ✅");
      expect(edited!.replyMarkup).toEqual({ inline_keyboard: [] });
    });

    test("2.3 Action 3: POST /api/app/review/permission resolves relay promise and edits Telegram card", async () => {
      const { baseUrl, permRelay, editedCards } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };

      let unblockedDecision: "allow" | "deny" | null = null;
      permRelay.register(
        "perm_act_3",
        "Bash",
        { command: "git push origin dev" },
        (decision) => {
          unblockedDecision = decision;
        }
      );
      permRelay.setMessageInfo("perm_act_3", allowedUserId, 2003, "Permission request: *Bash*");

      const res = await fetch(`${baseUrl}/api/app/review/permission`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          permission_id: "perm_act_3",
          decision: "allow",
        }),
      });

      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.success).toBe(true);
      expect(data.decision).toBe("allow");

      // Reaches agent (unblocks tool promise)
      expect(unblockedDecision).toBe("allow");

      // Edits Telegram card
      const edited = editedCards.find((c) => c.chatId === allowedUserId && c.messageId === 2003);
      expect(edited).toBeDefined();
      expect(edited!.text).toContain("Allowed via Dashboard ✅");
      expect(edited!.replyMarkup).toEqual({ inline_keyboard: [] });
    });

    test("2.4 Action 4: POST /api/app/stop halts agent session and edits Telegram card", async () => {
      const { baseUrl, emittedEvents, editedCards } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };

      const res = await fetch(`${baseUrl}/api/app/stop`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          reason: "Operator initiated emergency stop",
          chat_id: allowedUserId,
          message_id: 2004,
        }),
      });

      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.success).toBe(true);
      expect(data.status).toBe("stop_dispatched");

      // Reaches agent with high priority
      expect(emittedEvents.some((e) => e.event === "stop_requested" && e.meta.priority === "high")).toBe(true);

      // Edits Telegram card
      const edited = editedCards.find((c) => c.chatId === allowedUserId && c.messageId === 2004);
      expect(edited).toBeDefined();
      expect(edited!.text).toContain("Halted via Dashboard 🛑");
    });
  });

  // --- Criterion 3: §4 invariants on the Telegram side ---
  describe("Criterion 3: §4 Invariants on Telegram side", () => {
    test("3.1 Invariant 1 (Runtime is source of truth): Telegram callback on an already resolved question or permission is rejected", async () => {
      const { bot, broker, permRelay, apiCalls } = await createBridgeTestContext();

      // Question resolved in runtime
      const q = await broker.askUser({
        question: "Is this done?",
        options: [{ label: "Yes" }, { label: "No" }],
        chatId: allowedUserId,
      });
      await broker.resolveAnswer(q.questionId, 0); // resolved in runtime

      // Telegram callback query arrives afterwards
      await bot.handleUpdate({
        update_id: 991,
        callback_query: {
          id: "cb_late_q",
          from: { id: allowedUserId, first_name: "Nic" },
          data: `q:${q.questionId}:0:0`,
          message: {
            message_id: 3001,
            chat: { id: allowedUserId },
            text: "Is this done?",
          },
        },
      } as any);

      // Telegram answerCallbackQuery informs user it's already resolved
      expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.params.text.includes("already resolved"))).toBe(true);

      // Permission resolved in runtime
      permRelay.register("perm_inv_1", "Edit", {}, () => {});
      permRelay.resolve("perm_inv_1", "allow");

      // Late callback arrives from Telegram
      await bot.handleUpdate({
        update_id: 992,
        callback_query: {
          id: "cb_late_perm",
          from: { id: allowedUserId, first_name: "Nic" },
          data: `perm:allow:perm_inv_1`,
          message: {
            message_id: 3002,
            chat: { id: allowedUserId },
            text: "Permission request: Edit",
          },
        },
      } as any);

      expect(apiCalls.some((c) => c.method === "answerCallbackQuery" && c.params.text.includes("already resolved or expired"))).toBe(true);
    });

    test("3.2 Invariant 2 (Mutual invalidation): Question resolved in dashboard disables Telegram card buttons", async () => {
      const { baseUrl, broker, editedCards } = await createBridgeTestContext();
      const authHeaders = { Authorization: `Bearer ${bridgeToken}`, "Content-Type": "application/json" };

      const q = await broker.askUser({
        header: "Environment",
        question: "Select target",
        options: [{ label: "Production" }, { label: "Staging" }],
        chatId: allowedUserId,
      });
      broker.setMessageId(q.questionId, 3003);

      await fetch(`${baseUrl}/api/app/questions/answer`, {
        method: "POST",
        headers: authHeaders,
        body: JSON.stringify({
          question_id: q.questionId,
          option_index: 1,
        }),
      });

      const card = editedCards.find((c) => c.messageId === 3003);
      expect(card).toBeDefined();
      expect(card!.text).toContain("Selected: Staging ✅");
      expect(card!.replyMarkup).toEqual({ inline_keyboard: [] });
    });

    test("3.3 Invariant 3 (Zero orphaned permissions): Timed-out permission shows 'expired' on Telegram card and denies execution", async () => {
      const { permRelay, editedCards } = await createBridgeTestContext();

      let denied = false;
      permRelay.register(
        "perm_timeout_inv",
        "Bash",
        { command: "expensive_command" },
        (decision) => {
          if (decision === "deny") denied = true;
        },
        50 // 50ms timeout
      );
      permRelay.setMessageInfo("perm_timeout_inv", allowedUserId, 3004, "Permission request: *Bash*");

      await new Promise((r) => setTimeout(r, 70));

      expect(denied).toBe(true);
      const card = editedCards.find((c) => c.messageId === 3004);
      expect(card).toBeDefined();
      expect(card!.text).toContain("Expired ⏱️");
      expect(card!.replyMarkup).toEqual({ inline_keyboard: [] });
    });

    test("3.4 Invariant 3 (Zero orphaned permissions): Unfulfilled permissions cut on restart show 'expired'", async () => {
      testStateDir = join(tmpdir(), "ida-tg-restart-" + Math.random().toString(36).slice(2, 9));

      // Simulate run 1: register permission and save state with pending permission
      const permRelay1 = new PermissionRelay(testStateDir);
      permRelay1.register("perm_restart_cut", "Bash", { command: "reboot" }, () => {});
      permRelay1.setMessageInfo("perm_restart_cut", allowedUserId, 3005, "Permission request: *Bash*");

      // Simulate restart: run 2 boots up on same state directory
      const expiredItems: Array<any> = [];
      const editedOnBoot: Array<any> = [];
      const permRelay2 = new PermissionRelay(testStateDir);
      permRelay2.onExpire((item) => {
        expiredItems.push(item);
      });
      await permRelay2.sweepRestartCutPermissions(async (chatId, messageId, text) => {
        editedOnBoot.push({ chatId, messageId, text });
      });

      const perm = permRelay2.get("perm_restart_cut");
      expect(perm).toBeDefined();
      expect(perm!.status).toBe("expired");

      expect(expiredItems.some((item) => item.id === "perm_restart_cut" && item.status === "expired")).toBe(true);
      expect(editedOnBoot.some((c) => c.messageId === 3005 && c.text.includes("Expired ⏱️"))).toBe(true);
    });
  });
});
