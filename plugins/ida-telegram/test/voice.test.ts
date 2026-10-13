import { describe, expect, test } from "bun:test";
import { prepareVoiceText, buildVoiceInEvent } from "../src/telegram/voice.js";

describe("Voice: Inbound transcription and Outbound synthesis", () => {
  test("builds voice-in event with voice: true and duration", () => {
    const event = buildVoiceInEvent({
      transcript: "Please verify the latest PR on GitHub.",
      duration: 45,
      audioPath: "/workspace/inbox/voice_101.ogg",
      messageId: 101,
      replyToMessageId: 99,
    });

    expect(event.content).toBe("Please verify the latest PR on GitHub.");
    expect(event.meta.voice).toBe(true);
    expect(event.meta.duration).toBe(45);
    expect(event.meta.audio_path).toBe("/workspace/inbox/voice_101.ogg");
    expect(event.meta.message_id).toBe(101);
  });

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
});
