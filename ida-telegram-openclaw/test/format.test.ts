import { describe, expect, test } from "bun:test";
import {
  chunkMessage,
  formatMarkdownToEntities,
  formatTable,
  normalizeReaction,
} from "../src/telegram/format.js";

describe("Progressive disclosure: Format and Entities", () => {
  test("formats basic markdown to Telegram UTF-16 entities", () => {
    const text = "Hello **bold** and *italic* and `code` and [link](https://example.com)";
    const { plainText, entities } = formatMarkdownToEntities(text);

    expect(plainText).toBe("Hello bold and italic and code and link");
    expect(entities.length).toBe(4);

    const bold = entities.find((e) => e.type === "bold");
    expect(bold).toBeDefined();
    expect(bold?.offset).toBe("Hello ".length);
    expect(bold?.length).toBe("bold".length);

    const link = entities.find((e) => e.type === "text_link");
    expect(link).toBeDefined();
    expect(link?.url).toBe("https://example.com");
  });

  test("handles blockquotes and expandable blockquotes (>!)", () => {
    const text = "**Header**\n\n> Standard quote\n>! Expandable `code` evidence\n\nNormal text";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const stdQuote = entities.find((e) => e.type === "blockquote");
    expect(stdQuote).toBeDefined();
    expect(plainText.slice(stdQuote!.offset, stdQuote!.offset + stdQuote!.length)).toBe("Standard quote");

    const expQuote = entities.find((e) => e.type === "expandable_blockquote");
    expect(expQuote).toBeDefined();
    expect(plainText.slice(expQuote!.offset, expQuote!.offset + expQuote!.length)).toBe(
      "Expandable code evidence"
    );
  });

  test("groups consecutive >! lines into a single expandable_blockquote entity", () => {
    const text = "**Summary**\n\n>! Line one with `code`\n>! Line two with **bold**\n>! Line three\n\nFooter";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const expQuotes = entities.filter((e) => e.type === "expandable_blockquote");
    expect(expQuotes.length).toBe(1);
    expect(plainText.slice(expQuotes[0].offset, expQuotes[0].offset + expQuotes[0].length)).toBe(
      "Line one with code\nLine two with bold\nLine three"
    );

    const stdQuotes = entities.filter((e) => e.type === "blockquote");
    expect(stdQuotes.length).toBe(0);
  });

  test("groups consecutive standard > lines into a single blockquote entity per spec_7a9caca5 FR-1.2", () => {
    const text = "> Line 1\n> Line 2\n\nBody";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const quotes = entities.filter((e) => e.type === "blockquote");
    expect(quotes.length).toBe(1);
    expect(plainText.slice(quotes[0].offset, quotes[0].offset + quotes[0].length)).toBe("Line 1\nLine 2");
  });

  test("correctly calculates blockquote offsets when preceding text contains code blocks or inline markdown", () => {
    const text = "```javascript\nconsole.log('hello');\n```\n>! Multi-line quote 1\n>! Multi-line quote 2";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const expQuotes = entities.filter((e) => e.type === "expandable_blockquote");
    expect(expQuotes.length).toBe(1);
    expect(plainText.slice(expQuotes[0].offset, expQuotes[0].offset + expQuotes[0].length)).toBe(
      "Multi-line quote 1\nMulti-line quote 2"
    );
  });

  test("continues expandable_blockquote across contiguous > continuation lines", () => {
    const text = ">! **Receipts**\n> - item 1\n> - item 2";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const expQuotes = entities.filter((e) => e.type === "expandable_blockquote");
    expect(expQuotes.length).toBe(1);
    expect(plainText.slice(expQuotes[0].offset, expQuotes[0].offset + expQuotes[0].length)).toBe(
      "Receipts\n- item 1\n- item 2"
    );

    const stdQuotes = entities.filter((e) => e.type === "blockquote");
    expect(stdQuotes.length).toBe(0);
  });

  test("handles bare >! opening line followed by > continuation lines", () => {
    const text = ">!\n> Line 1\n> Line 2";
    const { plainText, entities } = formatMarkdownToEntities(text);

    const expQuotes = entities.filter((e) => e.type === "expandable_blockquote");
    expect(expQuotes.length).toBe(1);
    expect(plainText.slice(expQuotes[0].offset, expQuotes[0].offset + expQuotes[0].length)).toBe(
      "Line 1\nLine 2"
    );

    const stdQuotes = entities.filter((e) => e.type === "blockquote");
    expect(stdQuotes.length).toBe(0);
  });

  test("formats markdown tables: pre if <= 36 cols, stacked cards if > 36 cols", () => {
    const narrowTable = "| Col A | Col B |\n|---|---|\n| 1 | 2 |";
    const wideTable =
      "| Very Long Header Column A | Very Long Header Column B | Status |\n|---|---|---|\n| Extensive data value 1 | Extensive data value 2 | Active |";

    const narrowResult = formatTable(narrowTable);
    expect(narrowResult.isCodeBlock).toBe(true);
    expect(narrowResult.text).toContain("```");

    const wideResult = formatTable(wideTable);
    expect(wideResult.isCodeBlock).toBe(false);
    expect(wideResult.text).toContain("•");
  });

  test("chunks messages under 4096 UTF-16 code units without breaking code blocks", () => {
    const longCode = "```javascript\n" + "console.log('hello');\n".repeat(250) + "```";
    const chunks = chunkMessage(longCode, 4096);

    expect(chunks.length).toBeGreaterThan(1);
    for (const chunk of chunks) {
      expect(chunk.length).toBeLessThanOrEqual(4096);
    }
  });

  test("normalizes reactions to Telegram allow-list and strips VS16", () => {
    // ✍️ has VS16 (\uFE0F); Telegram requires bare ✍
    expect(normalizeReaction("✍️")).toBe("✍");
    expect(normalizeReaction("👍")).toBe("👍");
    expect(normalizeReaction("❤️")).toBe("❤");
    // Invalid reaction maps to null or fallback
    expect(normalizeReaction("🚀")).toBeNull();
  });
});
