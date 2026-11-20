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

  test("groups consecutive standard > lines into a single blockquote entity per format specification FR-1.2", () => {
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

  test("normalizes reactions by stripping VS16, canonical mapping, and validating single emoji grapheme", () => {
    // ✍️ has VS16 (\uFE0F); Telegram requires bare ✍
    expect(normalizeReaction("✍️")).toBe("✍");
    expect(normalizeReaction("👍")).toBe("👍");
    expect(normalizeReaction("❤️")).toBe("❤");
    // Arbitrary single valid emojis are accepted
    expect(normalizeReaction("🚀")).toBe("🚀");
    expect(normalizeReaction("🐱")).toBe("🐱");
    // Multi-emoji strings or non-emoji text are rejected
    expect(normalizeReaction("💩🦄")).toBeNull();
    expect(normalizeReaction("hello")).toBeNull();
  });

  test("formats Telegram advanced inline entities: spoiler, strikethrough, underline, and custom_emoji", () => {
    const text =
      "Check ||secret spoiler||, ~~struck text~~, __underlined__, <u>html underline</u>, and ![🔥](tg://emoji?id=5368324170671202286)!";
    const { plainText, entities } = formatMarkdownToEntities(text);

    expect(plainText).toBe(
      "Check secret spoiler, struck text, underlined, html underline, and 🔥!"
    );

    const spoiler = entities.find((e) => e.type === "spoiler");
    expect(spoiler).toBeDefined();
    expect(plainText.slice(spoiler!.offset, spoiler!.offset + spoiler!.length)).toBe(
      "secret spoiler"
    );

    const strike = entities.find((e) => e.type === "strikethrough");
    expect(strike).toBeDefined();
    expect(plainText.slice(strike!.offset, strike!.offset + strike!.length)).toBe(
      "struck text"
    );

    const underlines = entities.filter((e) => e.type === "underline");
    expect(underlines.length).toBe(2);
    expect(plainText.slice(underlines[0].offset, underlines[0].offset + underlines[0].length)).toBe(
      "underlined"
    );
    expect(plainText.slice(underlines[1].offset, underlines[1].offset + underlines[1].length)).toBe(
      "html underline"
    );

    const customEmoji = entities.find((e) => e.type === "custom_emoji");
    expect(customEmoji).toBeDefined();
    expect(customEmoji?.custom_emoji_id).toBe("5368324170671202286");
    expect(plainText.slice(customEmoji!.offset, customEmoji!.offset + customEmoji!.length)).toBe(
      "🔥"
    );
  });

  test("converts ATX markdown headings (# to ######) into bold entities outside code blocks", () => {
    const text = "# Main Title\n\n## Section Two\n\n```bash\n# shell comment stays literal\necho hi\n```";
    const { plainText, entities } = formatMarkdownToEntities(text);

    expect(plainText).toBe("Main Title\n\nSection Two\n\n# shell comment stays literal\necho hi");
    const bolds = entities.filter((e) => e.type === "bold");
    expect(bolds.length).toBe(2);
    expect(plainText.slice(bolds[0].offset, bolds[0].offset + bolds[0].length)).toBe("Main Title");
    expect(plainText.slice(bolds[1].offset, bolds[1].offset + bolds[1].length)).toBe("Section Two");

    const pre = entities.find((e) => e.type === "pre");
    expect(pre).toBeDefined();
    expect(plainText.slice(pre!.offset, pre!.offset + pre!.length)).toContain(
      "# shell comment stays literal"
    );
  });

  test("automatically converts markdown tables inside formatMarkdownToEntities", () => {
    const narrowMsg = "Summary:\n\n| Key | Val |\n|---|---|\n| A | 1 |\n\nDone.";
    const narrowRes = formatMarkdownToEntities(narrowMsg);
    const preEntity = narrowRes.entities.find((e) => e.type === "pre");
    expect(preEntity).toBeDefined();
    expect(narrowRes.plainText).toContain("Key | Val");

    const wideMsg =
      "Wide report:\n\n| Component Subsystem Name | Operational Status Summary | Owner |\n|---|---|---|\n| Telegram Formatting Engine | Active and verified in prod | Core |";
    const wideRes = formatMarkdownToEntities(wideMsg);
    expect(wideRes.plainText).toContain("• Component Subsystem Name: Telegram Formatting Engine");
    const boldHeaders = wideRes.entities.filter((e) => e.type === "bold");
    expect(boldHeaders.length).toBeGreaterThanOrEqual(3);
  });

  test("supports nested inline formatting entities with accurate UTF-16 offsets", () => {
    const text = "**Bold with *italic* and `code` and [link](https://example.com)** plus ||spoiler **bold**||";
    const { plainText, entities } = formatMarkdownToEntities(text);

    expect(plainText).toBe("Bold with italic and code and link plus spoiler bold");

    const outerBold = entities.find(
      (e) => e.type === "bold" && plainText.slice(e.offset, e.offset + e.length) === "Bold with italic and code and link"
    );
    expect(outerBold).toBeDefined();

    const innerItalic = entities.find((e) => e.type === "italic");
    expect(innerItalic).toBeDefined();
    expect(plainText.slice(innerItalic!.offset, innerItalic!.offset + innerItalic!.length)).toBe("italic");

    const innerCode = entities.find((e) => e.type === "code");
    expect(innerCode).toBeDefined();
    expect(plainText.slice(innerCode!.offset, innerCode!.offset + innerCode!.length)).toBe("code");

    const innerLink = entities.find((e) => e.type === "text_link");
    expect(innerLink).toBeDefined();
    expect(innerLink?.url).toBe("https://example.com");
    expect(plainText.slice(innerLink!.offset, innerLink!.offset + innerLink!.length)).toBe("link");

    const spoiler = entities.find((e) => e.type === "spoiler");
    expect(spoiler).toBeDefined();
    expect(plainText.slice(spoiler!.offset, spoiler!.offset + spoiler!.length)).toBe("spoiler bold");

    const spoilerBold = entities.find(
      (e) => e.type === "bold" && plainText.slice(e.offset, e.offset + e.length) === "bold"
    );
    expect(spoilerBold).toBeDefined();
  });
});
