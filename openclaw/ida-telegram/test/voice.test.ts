import { describe, expect, test } from "bun:test";
import { prepareVoiceText, buildVoiceInEvent } from "../src/telegram/voice.js";

describe("Voice: Inbound transcription and Outbound synthesis", () => {
  test("builds voice-in failure event with transcript_error", () => {
    const event = buildVoiceInEvent({
      transcript: undefined,
      error: "Transcription timeout after 120s",
      duration: 60,
      audioPath: "/workspace/inbox/voice_102.ogg",
      messageId: 102,
    });

    expect(event.content).toContain("Voice note received; transcription failed: Transcription timeout after 120s");
    expect(event.meta.transcript_error).toBe("Transcription timeout after 120s");
    expect(event.meta.voice).toBe("true");
    expect(event.meta.duration).toBe("60");
    expect(event.meta.message_id).toBe("102");
  });

  test("voice out strips markdown, links, quotes, and code blocks from tier 1 text", () => {
    const tier1Markdown = "**Headline result**: All 10 tests passed.\n• Bullet 1 with `code`.\n• Bullet 2 with [link](https://example.com).\n> Ignore this quote\n```\nignore this code\n```";

    const spokenText = prepareVoiceText(tier1Markdown);

    expect(spokenText).not.toContain("**");
    expect(spokenText).not.toContain("`");
    expect(spokenText).not.toContain("https://example.com");
    expect(spokenText).not.toContain("ignore this quote");
    expect(spokenText).not.toContain("ignore this code");
    expect(spokenText).toContain("Headline result: All 10 tests passed.");
    expect(spokenText).toContain("Bullet 1 with code.");
    expect(spokenText).toContain("Bullet 2 with link.");
  });

  test("FR-7.1 & FR-7.3: reply with voice: true synthesizes Tier 1 text, calls sendVoice with OGG audio, caption, caption_entities, and inline keyboard, and moves Tier 2 quotes to Details", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-1-"));
    const speakScript = join(stateDir, "speak.sh");
    const capturedTextPath = join(stateDir, "spoken_input.txt");
    writeFileSync(
      speakScript,
      `#!/bin/sh\nset -e\ncp "$1" "${capturedTextPath}"\nprintf 'OggS-fake-opus-audio' > "$2"\n`,
      "utf-8"
    );
    chmodSync(speakScript, 0o755);

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: speakScript,
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any; isMultipart: boolean }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      const method = urlStr.split("/").pop() || "";
      const isMultipart = init?.body instanceof FormData;
      let body: any = {};
      if (isMultipart) {
        const fd = init?.body as FormData;
        for (const [k, v] of fd.entries()) {
          if (v instanceof Blob) {
            body[k] = { size: v.size, type: v.type, text: await v.text() };
          } else {
            body[k] = v;
          }
        }
      } else if (init?.body) {
        body = JSON.parse(String(init.body));
      }
      apiCalls.push({ method, body, isMultipart });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 1850 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**This is a voice reply.**\n• First bullet with `code`.\n>! Tier 2 evidence quote that goes behind Details.",
            detail: "## Tier 3 Detail\nExtra context.",
            voice: true,
          },
        },
      });

      const toolText = ((resp?.result as any)?.content?.[0]?.text as string) || "{}";
      const parsedResult = JSON.parse(toolText);

      expect(parsedResult.success).toBe(true);
      expect(parsedResult.voiceSent).toBe(true);
      expect(parsedResult.messageId).toBe(1850);
      expect(parsedResult.detailsId).toBeDefined();

      // Should have called sendVoice and NOT sendMessage
      expect(apiCalls.map((c) => c.method)).toEqual(["sendVoice"]);
      const voiceCall = apiCalls[0];
      expect(voiceCall.isMultipart).toBe(true);
      expect(voiceCall.body.chat_id).toBe("8860530746");
      expect(voiceCall.body.voice.text).toBe("OggS-fake-opus-audio");

      // speak.sh received the Tier 1 text as a file at $1
      const spokenInput = readFileSync(capturedTextPath, "utf-8");
      expect(spokenInput).toContain("This is a voice reply.");
      expect(spokenInput).not.toContain("Tier 2 evidence quote");

      // Caption has Tier 1 text only (no Tier 2 quote) with entities
      expect(voiceCall.body.caption).toContain("This is a voice reply.");
      expect(voiceCall.body.caption).not.toContain("Tier 2 evidence quote");
      const captionEntities = JSON.parse(voiceCall.body.caption_entities);
      expect(captionEntities.some((e: any) => e.type === "bold")).toBe(true);

      // Inline keyboard has the Details button
      const replyMarkup = JSON.parse(voiceCall.body.reply_markup);
      const flatButtons = replyMarkup.inline_keyboard.flat();
      expect(flatButtons.some((b: any) => b.text === "🔍 Details")).toBe(true);

      // Details page contains both the relocated Tier 2 quote and Tier 3 detail
      const storedDetail = store.getDetails(parsedResult.detailsId);
      expect(storedDetail?.markdown).toContain("Tier 2 evidence quote that goes behind Details.");
      expect(storedDetail?.markdown).toContain("## Tier 3 Detail");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-7.3: when Tier 1 text exceeds 1024-char caption limit, sends voice note first and then separate sendMessage with text and keyboard", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-2-"));
    const speakScript = join(stateDir, "speak.sh");
    writeFileSync(speakScript, `#!/bin/sh\nprintf 'OggS-long-voice' > "$2"\n`, "utf-8");
    chmodSync(speakScript, 0o755);

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1500,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: speakScript,
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any }> = [];
    let msgSeq = 1900;
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      let body: any = {};
      if (init?.body instanceof FormData) {
        for (const [k, v] of (init.body as FormData).entries()) {
          body[k] = v instanceof Blob ? await v.text() : v;
        }
      } else if (init?.body) {
        body = JSON.parse(String(init.body));
      }
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: ++msgSeq } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const longTier1 = "**Headline**: " + "A".repeat(1050);
      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 2,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: longTier1,
            voice: true,
            buttons: [{ label: "Go ahead (Recommended)" }, { label: "Hold" }],
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.voiceSent).toBe(true);
      expect(parsedResult.voiceMessageId).toBe(1901);
      expect(parsedResult.messageId).toBe(1902);

      expect(apiCalls.map((c) => c.method)).toEqual(["sendVoice", "sendMessage"]);
      expect(apiCalls[0].body.caption).toBeUndefined();
      expect(apiCalls[1].body.text).toContain("Headline: ");
      expect(apiCalls[1].body.reply_markup).toBeDefined();
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-7.4: when TTS fails, sends text via sendMessage and reports voiceSent: false and voiceError in tool result", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-3-"));
    const missingSpeakScript = join(stateDir, "nonexistent-speak.sh");

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: "",
      voiceSpeakCmd: missingSpeakScript,
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const method = String(url).split("/").pop() || "";
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, body });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 1850 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 3,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**This is a voice reply.**",
            voice: true,
          },
        },
      });

      const parsedResult = JSON.parse((resp?.result as any)?.content?.[0]?.text || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.voiceSent).toBe(false);
      expect(typeof parsedResult.voiceError).toBe("string");
      expect(parsedResult.voiceError.length).toBeGreaterThan(0);
      expect(parsedResult.messageId).toBe(1850);
      expect(apiCalls.map((c) => c.method)).toEqual(["sendMessage"]);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-7.1: voice_replies mirror setting automatically sends voice when last inbound message was voice, and text when last inbound message was text", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-4-"));
    const transcribeScript = join(stateDir, "transcribe.sh");
    writeFileSync(transcribeScript, `#!/bin/sh\necho "Hello from voice"\n`, "utf-8");
    chmodSync(transcribeScript, 0o755);

    const speakScript = join(stateDir, "speak.sh");
    writeFileSync(speakScript, `#!/bin/sh\nprintf 'OggS-mirror-voice' > "$2"\n`, "utf-8");
    chmodSync(speakScript, 0o755);

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "mirror" as const,
      voiceTranscribeCmd: transcribeScript,
      voiceSpeakCmd: speakScript,
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request) => {
      const urlStr = String(url);
      if (urlStr.includes("/file/bot")) {
        return new Response(new Uint8Array([1, 2, 3]), { status: 200 });
      }
      const method = urlStr.split("/").pop() || "";
      apiCalls.push({ method });
      if (method === "getFile") {
        return new Response(JSON.stringify({ ok: true, result: { file_path: "voice/in.ogg" } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2000 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      // 1. Simulate inbound voice note from Nic
      await (bot as any).handleUpdate({
        update_id: 10,
        message: {
          message_id: 300,
          date: 1700000000,
          chat: { id: 8860530746, type: "private" },
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          voice: { file_id: "vf_1", duration: 5 },
        },
      });

      apiCalls.length = 0;

      // 2. Reply with `voice` omitted -> should mirror voice note and call sendVoice
      const mirrorVoiceResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 10,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Mirrored voice answer.**",
          },
        },
      });
      const res1 = JSON.parse((mirrorVoiceResp?.result as any)?.content?.[0]?.text || "{}");
      expect(res1.voiceSent).toBe(true);
      expect(apiCalls.map((c) => c.method)).toEqual(["sendVoice"]);

      // 3. Simulate inbound plain text message from Nic
      await (bot as any).handleUpdate({
        update_id: 11,
        message: {
          message_id: 301,
          date: 1700000010,
          chat: { id: 8860530746, type: "private" },
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          text: "Now a text message",
        },
      });

      apiCalls.length = 0;

      // 4. Reply with `voice` omitted -> should mirror text and call sendMessage
      const mirrorTextResp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 11,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Mirrored text answer.**",
          },
        },
      });
      const res2 = JSON.parse((mirrorTextResp?.result as any)?.content?.[0]?.text || "{}");
      expect(res2.voiceSent).toBeUndefined();
      expect(apiCalls.map((c) => c.method)).toEqual(["sendMessage"]);
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("FR-6.1: first voice message on a fresh state directory creates inbox/ and transcribes", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync, existsSync, readdirSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-fresh-"));
    const scriptDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-scripts-"));
    const transcribeScript = join(scriptDir, "transcribe.sh");
    writeFileSync(transcribeScript, `#!/bin/sh\necho "Transcribed fresh voice note"\n`, "utf-8");
    chmodSync(transcribeScript, 0o755);

    const config = {
      botToken: "test-token",
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [8860530746],
      maxChatChars: 1200,
      voiceReplies: "off" as const,
      voiceTranscribeCmd: transcribeScript,
      voiceSpeakCmd: "",
      port: 8093,
      stateDir,
      socketPath: join(stateDir, "hook.sock"),
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request) => {
      const urlStr = String(url);
      if (urlStr.includes("/file/bot")) {
        return new Response(new Uint8Array([0x4f, 0x67, 0x67, 0x53]), { status: 200 });
      }
      const method = urlStr.split("/").pop() || "";
      if (method === "getFile") {
        return new Response(JSON.stringify({ ok: true, result: { file_path: "voice/fresh.ogg" } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
    }) as typeof fetch;

    try {
      expect(existsSync(join(stateDir, "inbox"))).toBe(false);

      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });

      await (bot as any).handleUpdate({
        update_id: 25,
        message: {
          message_id: 401,
          date: 1700000100,
          chat: { id: 8860530746, type: "private" },
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          voice: { file_id: "vf_fresh_1", duration: 8 },
        },
      });

      expect(existsSync(join(stateDir, "inbox"))).toBe(true);
      const inboxFiles = readdirSync(join(stateDir, "inbox")).filter((f) => f.endsWith(".ogg"));
      expect(inboxFiles.length).toBe(1);

      expect(emittedEvents.length).toBe(1);
      expect(emittedEvents[0].content).toBe("Transcribed fresh voice note");
      expect(emittedEvents[0].meta.voice).toBe("true");
      expect(emittedEvents[0].meta.transcript_error).toBeUndefined();
      expect(emittedEvents[0].meta.audio_path).toBe(join(stateDir, "inbox", inboxFiles[0]));
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
      rmSync(scriptDir, { recursive: true, force: true });
    }
  });

  test("voice-in passes stateDir as cwd and stateDir .env credentials to transcribe script", async () => {
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { loadConfig } = await import("../src/config.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-cred-"));
    const transcribeScript = join(stateDir, "transcribe.sh");

    // Write stateDir/.env with credentials
    writeFileSync(join(stateDir, ".env"), "ASSEMBLY_AI_API_KEY=test_secret_assembly_ai_key\n", "utf-8");

    // Script asserts ASSEMBLY_AI_API_KEY is present and PWD is stateDir
    writeFileSync(
      transcribeScript,
      `#!/bin/sh\n` +
      `if [ "\${ASSEMBLY_AI_API_KEY:-}" != "test_secret_assembly_ai_key" ]; then\n` +
      `  echo "Error: ASSEMBLY_AI_API_KEY environment variable is missing" >&2\n` +
      `  exit 1\n` +
      `fi\n` +
      `if [ "$PWD" != "${stateDir}" ]; then\n` +
      `  echo "Error: cwd is not stateDir, got $PWD" >&2\n` +
      `  exit 1\n` +
      `fi\n` +
      `echo "Transcribed successfully with stateDir credentials"\n`,
      "utf-8"
    );
    chmodSync(transcribeScript, 0o755);

    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      STATE_DIR: stateDir,
      VOICE_TRANSCRIBE_CMD: transcribeScript,
      ALLOWED_USER_IDS: "8860530746",
    });

    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const emittedEvents: Array<{ content: string; meta: Record<string, unknown> }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request) => {
      const urlStr = String(url);
      if (urlStr.includes("/file/bot")) {
        return new Response(new Uint8Array([0x4f, 0x67, 0x67, 0x53]), { status: 200 });
      }
      const method = urlStr.split("/").pop() || "";
      if (method === "getFile") {
        return new Response(JSON.stringify({ ok: true, result: { file_path: "voice/cred.ogg" } }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, (content, meta) => {
        emittedEvents.push({ content, meta });
      });

      await (bot as any).handleUpdate({
        update_id: 30,
        message: {
          message_id: 501,
          date: 1700000200,
          chat: { id: 8860530746, type: "private" },
          from: { id: 8860530746, is_bot: false, first_name: "Nic" },
          voice: { file_id: "vf_cred_1", duration: 5 },
        },
      });

      expect(emittedEvents.length).toBe(1);
      expect(emittedEvents[0].meta.transcript_error).toBeUndefined();
      expect(emittedEvents[0].content).toBe("Transcribed successfully with stateDir credentials");
      expect(emittedEvents[0].meta.voice).toBe("true");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("AC3: in an installed-plugin layout with VOICE_SPEAK_CMD=speak.sh, reply({voice: true}) returns voiceSent: true after resolving speak.sh, but reproduces Executable not found when unresolvable", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { formatMarkdownToEntities } = await import("../src/telegram/format.js");
    const { mkdtempSync, rmSync, writeFileSync, mkdirSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const installedPluginRoot = mkdtempSync(join(tmpdir(), "ida-tg-installed-"));
    const scriptsDir = join(installedPluginRoot, "scripts");
    mkdirSync(scriptsDir, { recursive: true });
    const bundledSpeak = join(scriptsDir, "speak.sh");
    writeFileSync(
      bundledSpeak,
      `#!/bin/sh\nset -e\nprintf 'OggS-fake-opus-audio' > "$2"\n`,
      "utf-8"
    );
    chmodSync(bundledSpeak, 0o755);

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-installed-state-"));

    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      const isVoice = urlStr.includes("sendVoice");
      if (isVoice) {
        return new Response(
          JSON.stringify({
            ok: true,
            result: { message_id: 3193, chat: { id: 8860530746 } },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      }
      return new Response(
        JSON.stringify({
          ok: true,
          result: { message_id: 3194, chat: { id: 8860530746 } },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }) as any;

    try {
      // Installed-plugin environment where VOICE_SPEAK_CMD is set to bare "speak.sh"
      const cfg = loadConfig({
        CLAUDE_PLUGIN_ROOT: installedPluginRoot,
        STATE_DIR: stateDir,
        VOICE_SPEAK_CMD: "speak.sh",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
      });

      // Assert that loadConfig resolves the candidate path to the bundled script
      expect(cfg.voiceSpeakCmd).toBe(bundledSpeak);

      const bot = new TelegramBotClient(
        cfg,
        new QuestionBroker(stateDir),
        new PermissionRelay(),
        () => {}
      );

      const formatted = formatMarkdownToEntities("Voice reply from installed plugin");
      const res = await bot.sendReply({
        chatId: 8860530746,
        formatted,
        voice: true,
      });

      expect(res).not.toBeNull();
      expect(res?.voiceSent).toBe(true);
      expect(res?.voiceError).toBeUndefined();

      // Verify that unresolvable bare command reproduces "Executable not found in $PATH"
      const unresolvableCfg = loadConfig({
        CLAUDE_PLUGIN_ROOT: installedPluginRoot,
        STATE_DIR: stateDir,
        VOICE_SPEAK_CMD: "nonexistent-speak.sh",
        TELEGRAM_BOT_TOKEN: "test-token",
        IDA_TELEGRAM_ROLE: "primary",
      });
      const unresolvableBot = new TelegramBotClient(
        unresolvableCfg,
        new QuestionBroker(stateDir),
        new PermissionRelay(),
        () => {}
      );
      const resUnresolvable = await unresolvableBot.sendReply({
        chatId: 8860530746,
        formatted,
        voice: true,
      });
      expect(resUnresolvable?.voiceSent).toBe(false);
      expect(resUnresolvable?.voiceError).toContain("nonexistent-speak.sh");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(installedPluginRoot, { recursive: true, force: true });
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("loadConfig defaults voiceSpeakCmd to bundled speak.sh when unset", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { mkdtempSync, rmSync, existsSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-cfg-"));
    try {
      const cfg = loadConfig({
        STATE_DIR: stateDir,
        VOICE_SPEAK_CMD: "",
      });
      expect(cfg.voiceSpeakCmd).toContain("scripts/speak.sh");
      expect(existsSync(cfg.voiceSpeakCmd)).toBe(true);
    } finally {
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("loadConfig probes candidate paths in order per spec_7a9caca5", async () => {
    const { loadConfig } = await import("../src/config.js");
    const { mkdtempSync, rmSync, writeFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-cfg-cand-"));
    try {
      // Create fake transcribe.sh and speak.sh in stateDir to test priority over bundled scripts
      writeFileSync(join(stateDir, "transcribe.sh"), "#!/bin/sh\n", { mode: 0o755 });
      writeFileSync(join(stateDir, "speak.sh"), "#!/bin/sh\n", { mode: 0o755 });

      const cfg = loadConfig({
        STATE_DIR: stateDir,
      });
      expect(cfg.voiceTranscribeCmd).toBe(join(stateDir, "transcribe.sh"));
      expect(cfg.voiceSpeakCmd).toBe(join(stateDir, "speak.sh"));
    } finally {
      rmSync(stateDir, { recursive: true, force: true });
    }
  });

  test("speak.sh validates arguments, missing file, missing key, and missing ffmpeg", async () => {
    const { mkdtempSync, rmSync, writeFileSync } = await import("node:fs");
    const { join, resolve } = await import("node:path");
    const { tmpdir } = await import("node:os");
    const { execFile } = await import("node:child_process");
    const { promisify } = await import("node:util");
    const execFileAsync = promisify(execFile);

    const speakScript = resolve(import.meta.dir, "../scripts/speak.sh");
    const testDir = mkdtempSync(join(tmpdir(), "ida-tg-speak-val-"));

    try {
      // 1. Missing arguments
      let err1: any;
      try {
        await execFileAsync(speakScript, [], { env: { PATH: process.env.PATH } });
      } catch (e) {
        err1 = e;
      }
      expect(err1).toBeDefined();
      expect(err1.stderr).toContain("text file argument and output ogg argument required");

      // 2. Missing text file
      let err2: any;
      try {
        await execFileAsync(speakScript, [join(testDir, "missing.txt"), join(testDir, "out.ogg")], {
          env: { PATH: process.env.PATH },
        });
      } catch (e) {
        err2 = e;
      }
      expect(err2).toBeDefined();
      expect(err2.stderr).toContain("text file not found");

      // 3. Missing GEMINI_API_KEY
      const sampleTextFile = join(testDir, "sample.txt");
      writeFileSync(sampleTextFile, "Hello world", "utf-8");

      let err3: any;
      try {
        await execFileAsync(speakScript, [sampleTextFile, join(testDir, "out.ogg")], {
          env: { PATH: process.env.PATH },
        });
      } catch (e) {
        err3 = e;
      }
      expect(err3).toBeDefined();
      expect(err3.stderr).toContain("GEMINI_API_KEY environment variable is missing");

      // 3b. Missing GEMINI_API_KEY even if GOOGLE_API_KEY is present (no-fallbacks)
      let err3b: any;
      try {
        await execFileAsync(speakScript, [sampleTextFile, join(testDir, "out.ogg")], {
          env: { PATH: process.env.PATH, GOOGLE_API_KEY: "fallback_key" },
        });
      } catch (e) {
        err3b = e;
      }
      expect(err3b).toBeDefined();
      expect(err3b.stderr).toContain("GEMINI_API_KEY environment variable is missing");

      // 4. Missing ffmpeg
      const emptyBinDir = join(testDir, "empty_bin");
      const { mkdirSync, symlinkSync } = await import("node:fs");
      const { execSync } = await import("node:child_process");
      mkdirSync(emptyBinDir, { recursive: true });
      symlinkSync(execSync("which bash").toString().trim(), join(emptyBinDir, "bash"));
      symlinkSync(execSync("which dirname").toString().trim(), join(emptyBinDir, "dirname"));
      symlinkSync(execSync("which python3").toString().trim(), join(emptyBinDir, "python3"));

      let err4: any;
      try {
        await execFileAsync(speakScript, [sampleTextFile, join(testDir, "out.ogg")], {
          env: {
            PATH: emptyBinDir, // ensure bash, dirname, and python3 are found but no ffmpeg
            GEMINI_API_KEY: "test_key",
          },
        });
      } catch (e) {
        err4 = e;
      }
      expect(err4).toBeDefined();
      expect(err4.stderr).toContain("ffmpeg is required to encode audio to OGG/Opus");
    } finally {
      rmSync(testDir, { recursive: true, force: true });
    }
  });

  test("speak.sh synthesises speech via Gemini 3.8 Flash TTS endpoint and encodes audio", async () => {
    const { mkdtempSync, rmSync, writeFileSync, chmodSync, existsSync, statSync } = await import("node:fs");
    const { join, resolve } = await import("node:path");
    const { tmpdir } = await import("node:os");
    const { execFile } = await import("node:child_process");
    const { promisify } = await import("node:util");
    const execFileAsync = promisify(execFile);

    const speakScript = resolve(import.meta.dir, "../scripts/speak.sh");
    const testDir = mkdtempSync(join(tmpdir(), "ida-tg-speak-syn-"));

    let receivedRequestBody: any = null;
    let receivedApiKey: string | null = null;

    // Spin up mock Gemini 3.8 Flash TTS server
    const server = Bun.serve({
      port: 0,
      async fetch(req) {
        const url = new URL(req.url);
        receivedApiKey = url.searchParams.get("key");
        receivedRequestBody = await req.json();

        // Return candidate with inline base64 audio
        const fakeAudioData = Buffer.from("OggS-mock-audio-opus-payload").toString("base64");
        return new Response(
          JSON.stringify({
            candidates: [
              {
                content: {
                  parts: [
                    {
                      inlineData: {
                        mimeType: "audio/ogg",
                        data: fakeAudioData,
                      },
                    },
                  ],
                },
              },
            ],
          }),
          { headers: { "Content-Type": "application/json" } }
        );
      },
    });

    // Create a mock ffmpeg in testDir/bin
    const binDir = join(testDir, "bin");
    const { mkdirSync } = await import("node:fs");
    mkdirSync(binDir, { recursive: true });

    const mockFfmpeg = join(binDir, "ffmpeg");
    writeFileSync(
      mockFfmpeg,
      `#!/bin/sh\n` +
      `# Mock ffmpeg that copies input to output target\n` +
      `# Last argument is output file\n` +
      `out=""\n` +
      `for arg in "$@"; do out="$arg"; done\n` +
      `printf 'OggS-mock-opus-converted' > "$out"\n`,
      "utf-8"
    );
    chmodSync(mockFfmpeg, 0o755);

    const inputFile = join(testDir, "input.txt");
    const outputFile = join(testDir, "output.ogg");
    writeFileSync(inputFile, "This is synthesized text via Gemini Flash TTS.", "utf-8");

    try {
      const { stdout, stderr } = await execFileAsync(speakScript, [inputFile, outputFile], {
        env: {
          PATH: `${binDir}:${process.env.PATH}`,
          GEMINI_API_KEY: "test_gemini_key_live",
          GEMINI_API_BASE_URL: `http://127.0.0.1:${server.port}`,
          GEMINI_TTS_VOICE: "Aoede",
        },
      });

      expect(receivedApiKey).toBe("test_gemini_key_live");
      expect(receivedRequestBody.generationConfig.responseModalities).toEqual(["AUDIO"]);
      expect(receivedRequestBody.generationConfig.speechConfig.voiceConfig.prebuiltVoiceConfig.voiceName).toBe("Aoede");
      expect(receivedRequestBody.contents[0].parts[0].text).toBe("This is synthesized text via Gemini Flash TTS.");

      expect(existsSync(outputFile)).toBe(true);
      expect(statSync(outputFile).size).toBeGreaterThan(0);
    } finally {
      server.stop();
      rmSync(testDir, { recursive: true, force: true });
    }
  });

  test("voice-out reply passes stateDir as cwd and stateDir .env credentials to speak script", async () => {
    const { StdioMcpServer } = await import("../src/mcp/server.js");
    const { TelegramBotClient } = await import("../src/telegram/bot.js");
    const { PluginStore } = await import("../src/store.js");
    const { QuestionBroker } = await import("../src/telegram/questions.js");
    const { PermissionRelay } = await import("../src/mcp/permissions.js");
    const { loadConfig } = await import("../src/config.js");
    const { mkdtempSync, rmSync, writeFileSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-out-cred-"));
    const speakScript = join(stateDir, "speak.sh");

    // Write stateDir/.env with GEMINI_API_KEY
    writeFileSync(join(stateDir, ".env"), "GEMINI_API_KEY=test_gemini_secret_key_789\n", "utf-8");

    // Script asserts GEMINI_API_KEY is present and PWD is stateDir
    writeFileSync(
      speakScript,
      `#!/bin/sh\n` +
      `if [ "\${GEMINI_API_KEY:-}" != "test_gemini_secret_key_789" ]; then\n` +
      `  echo "Error: GEMINI_API_KEY environment variable is missing" >&2\n` +
      `  exit 1\n` +
      `fi\n` +
      `if [ "$PWD" != "${stateDir}" ]; then\n` +
      `  echo "Error: cwd is not stateDir, got $PWD" >&2\n` +
      `  exit 1\n` +
      `fi\n` +
      `printf 'OggS-gemini-tts-audio' > "$2"\n`,
      "utf-8"
    );
    chmodSync(speakScript, 0o755);

    const config = loadConfig({
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_BOT_TOKEN: "test-token",
      STATE_DIR: stateDir,
      VOICE_SPEAK_CMD: speakScript,
      ALLOWED_USER_IDS: "8860530746",
    });

    const store = new PluginStore(stateDir);
    const broker = new QuestionBroker(stateDir);
    const permRelay = new PermissionRelay();

    const apiCalls: Array<{ method: string; body: any; isMultipart: boolean }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      const method = urlStr.split("/").pop() || "";
      const isMultipart = init?.body instanceof FormData;
      let body: any = {};
      if (isMultipart) {
        const fd = init?.body as FormData;
        for (const [k, v] of fd.entries()) {
          if (v instanceof Blob) {
            body[k] = { size: v.size, type: v.type, text: await v.text() };
          } else {
            body[k] = v;
          }
        }
      } else if (init?.body) {
        body = JSON.parse(String(init.body));
      }
      apiCalls.push({ method, body, isMultipart });
      return new Response(JSON.stringify({ ok: true, result: { message_id: 2999 } }), { status: 200 });
    }) as typeof fetch;

    try {
      const bot = new TelegramBotClient(config, broker, permRelay, () => {});
      const mcp = new StdioMcpServer(config, store, broker, bot, permRelay);

      const resp = await mcp.handleMessage({
        jsonrpc: "2.0",
        id: 99,
        method: "tools/call",
        params: {
          name: "reply",
          arguments: {
            chat_id: 8860530746,
            text: "**Voice out credential test.**\n• Bullet one.",
            voice: true,
          },
        },
      });

      const parsedResult = JSON.parse(((resp?.result as any)?.content?.[0]?.text as string) || "{}");
      expect(parsedResult.success).toBe(true);
      expect(parsedResult.voiceSent).toBe(true);
      expect(parsedResult.voiceError).toBeUndefined();
      expect(apiCalls.map((c) => c.method)).toEqual(["sendVoice"]);
      expect(apiCalls[0].body.voice.text).toBe("OggS-gemini-tts-audio");
    } finally {
      globalThis.fetch = origFetch;
      rmSync(stateDir, { recursive: true, force: true });
    }
  });
});



