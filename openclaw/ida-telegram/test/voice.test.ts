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
    const { mkdtempSync, rmSync, writeFileSync, chmodSync } = await import("node:fs");
    const { join } = await import("node:path");
    const { tmpdir } = await import("node:os");

    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-voice-1-"));
    const speakScript = join(stateDir, "speak.sh");
    const capturedTextPath = join(stateDir, "spoken_input.txt");
    writeFileSync(
      speakScript,
      `#!/bin/sh\ncp "$1" "${capturedTextPath}"\nprintf 'OggS-fake-opus-audio' > "$2"\n`,
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
});


