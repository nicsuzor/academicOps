import { describe, expect, test } from "bun:test";
import { processReplyOverflow } from "../src/telegram/overflow.js";

describe("Progressive disclosure: Overflow handling", () => {
  test("short reply under max_chat_chars stays in chat with no overflow", () => {
    const text = "A concise update under budget.\nWith two paragraphs.";
    const result = processReplyOverflow({
      text,
      detail: undefined,
      maxChatChars: 1200,
    });

    expect(result.chatText).toBe(text);
    expect(result.hasOverflow).toBe(false);
    expect(result.combinedDetail).toBeUndefined();
    expect(result.hasDetailsButton).toBe(false);
  });

  test("reply with explicit detail adds Details button and keeps detail", () => {
    const text = "A concise headline and bullet.";
    const detail = "# Extensive Investigation Details\nFull log output...";
    const result = processReplyOverflow({
      text,
      detail,
      maxChatChars: 1200,
    });

    expect(result.chatText).toBe(text);
    expect(result.hasOverflow).toBe(false);
    expect(result.combinedDetail).toBe(detail);
    expect(result.hasDetailsButton).toBe(true);
  });

  test("overflow > max_chat_chars moves remaining text to Details without dropping a single character", () => {
    const p1 = "Paragraph 1: Summary of key events. " + "A".repeat(400);
    const p2 = "Paragraph 2: Additional context. " + "B".repeat(500);
    const p3 = "Paragraph 3: Deep methodology. " + "C".repeat(600);
    const fullText = `${p1}\n\n${p2}\n\n${p3}`;

    const result = processReplyOverflow({
      text: fullText,
      detail: undefined,
      maxChatChars: 600,
    });

    expect(result.hasOverflow).toBe(true);
    expect(result.hasDetailsButton).toBe(true);
    expect(result.chatText).toContain("… continued in Details");
    expect(result.chatText.startsWith(p1)).toBe(true);

    // Verify character-for-character fidelity of the overflow in combinedDetail
    expect(result.combinedDetail).toBeDefined();
    expect(result.combinedDetail?.startsWith(p2)).toBe(true);
    expect(result.combinedDetail).toContain(p3);
  });

  test("overflow prepends character-for-character to existing detail", () => {
    const p1 = "Short lead paragraph.";
    const p2 = "Heavy paragraph that exceeds the budget: " + "X".repeat(1100);
    const existingDetail = "## Existing Deep Detail\nOriginal content";

    const result = processReplyOverflow({
      text: `${p1}\n\n${p2}`,
      detail: existingDetail,
      maxChatChars: 500,
    });

    expect(result.hasOverflow).toBe(true);
    expect(result.hasDetailsButton).toBe(true);
    expect(result.combinedDetail).toContain(p2);
    expect(result.combinedDetail).toContain(existingDetail);
  });
});
