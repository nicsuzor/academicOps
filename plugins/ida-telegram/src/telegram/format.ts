export interface TelegramEntity {
  type:
    | "bold"
    | "italic"
    | "underline"
    | "strikethrough"
    | "code"
    | "pre"
    | "text_link"
    | "text_mention"
    | "blockquote"
    | "expandable_blockquote";
  offset: number;
  length: number;
  url?: string;
  language?: string;
}

export interface FormattedMessage {
  plainText: string;
  entities: TelegramEntity[];
}

export function formatMarkdownToEntities(markdown: string): FormattedMessage {
  interface QuoteBlock {
    type: "blockquote" | "expandable_blockquote";
    startInOut: number;
    endInOut: number;
  }

  const quoteBlocks: QuoteBlock[] = [];
  const lines = markdown.split("\n");
  let currentQuoteType: "blockquote" | "expandable_blockquote" | null = null;
  let quoteStartOffset = 0;
  let out = "";

  function closeQuote() {
    if (currentQuoteType !== null) {
      quoteBlocks.push({
        type: currentQuoteType,
        startInOut: quoteStartOffset,
        endInOut: out.length,
      });
      currentQuoteType = null;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const sep = i > 0 ? "\n" : "";

    if (rawLine.startsWith(">!")) {
      if (currentQuoteType !== "expandable_blockquote") {
        closeQuote();
        currentQuoteType = "expandable_blockquote";
        quoteStartOffset = out.length + sep.length;
      }
      const lineContent = rawLine.replace(/^>!\s?/, "");
      out += sep + lineContent;
    } else if (rawLine.startsWith(">")) {
      if (currentQuoteType !== "blockquote") {
        closeQuote();
        currentQuoteType = "blockquote";
        quoteStartOffset = out.length + sep.length;
      }
      const lineContent = rawLine.replace(/^>\s?/, "");
      out += sep + lineContent;
    } else {
      closeQuote();
      out += sep + rawLine;
    }
  }
  closeQuote();

  const outToClean = new Array(out.length + 1);
  let cleanText = "";
  let idx = 0;
  const entities: TelegramEntity[] = [];

  while (idx < out.length) {
    outToClean[idx] = cleanText.length;

    // 1. Triple backticks (pre)
    if (out.startsWith("```", idx)) {
      const endPre = out.indexOf("```", idx + 3);
      if (endPre !== -1) {
        const fullBlock = out.substring(idx + 3, endPre);
        let lang = "";
        let code = fullBlock;
        const firstNewline = fullBlock.indexOf("\n");
        if (firstNewline !== -1) {
          lang = fullBlock.substring(0, firstNewline).trim();
          code = fullBlock.substring(firstNewline + 1);
        }
        const startOffset = cleanText.length;
        cleanText += code;
        entities.push({
          type: "pre",
          offset: startOffset,
          length: code.length,
          language: lang || undefined,
        });
        const nextIdx = endPre + 3;
        for (let k = idx; k < nextIdx; k++) {
          outToClean[k] = startOffset;
        }
        outToClean[nextIdx] = cleanText.length;
        idx = nextIdx;
        continue;
      }
    }

    // 2. Inline code
    if (out[idx] === "`") {
      const endCode = out.indexOf("`", idx + 1);
      if (endCode !== -1 && !out.substring(idx + 1, endCode).includes("\n")) {
        const code = out.substring(idx + 1, endCode);
        const startOffset = cleanText.length;
        cleanText += code;
        entities.push({
          type: "code",
          offset: startOffset,
          length: code.length,
        });
        const nextIdx = endCode + 1;
        for (let k = idx; k < nextIdx; k++) {
          outToClean[k] = startOffset;
        }
        outToClean[nextIdx] = cleanText.length;
        idx = nextIdx;
        continue;
      }
    }

    // 3. Bold: **text**
    if (out.startsWith("**", idx)) {
      const endBold = out.indexOf("**", idx + 2);
      if (endBold !== -1) {
        const boldText = out.substring(idx + 2, endBold);
        const startOffset = cleanText.length;
        cleanText += boldText;
        entities.push({
          type: "bold",
          offset: startOffset,
          length: boldText.length,
        });
        const nextIdx = endBold + 2;
        for (let k = idx; k < nextIdx; k++) {
          outToClean[k] = startOffset;
        }
        outToClean[nextIdx] = cleanText.length;
        idx = nextIdx;
        continue;
      }
    }

    // 4. Markdown links: [text](url)
    if (out[idx] === "[") {
      const closeBracket = out.indexOf("]", idx + 1);
      if (closeBracket !== -1 && out[closeBracket + 1] === "(") {
        const closeParen = out.indexOf(")", closeBracket + 2);
        if (closeParen !== -1) {
          const linkText = out.substring(idx + 1, closeBracket);
          const linkUrl = out.substring(closeBracket + 2, closeParen);
          const startOffset = cleanText.length;
          cleanText += linkText;
          entities.push({
            type: "text_link",
            offset: startOffset,
            length: linkText.length,
            url: linkUrl,
          });
          const nextIdx = closeParen + 1;
          for (let k = idx; k < nextIdx; k++) {
            outToClean[k] = startOffset;
          }
          outToClean[nextIdx] = cleanText.length;
          idx = nextIdx;
          continue;
        }
      }
    }

    // 5. Italic: *text* (single asterisk)
    if (out[idx] === "*" && !out.startsWith("**", idx)) {
      const endItalic = out.indexOf("*", idx + 1);
      if (endItalic !== -1 && !out.startsWith("**", endItalic)) {
        const italicText = out.substring(idx + 1, endItalic);
        const startOffset = cleanText.length;
        cleanText += italicText;
        entities.push({
          type: "italic",
          offset: startOffset,
          length: italicText.length,
        });
        const nextIdx = endItalic + 1;
        for (let k = idx; k < nextIdx; k++) {
          outToClean[k] = startOffset;
        }
        outToClean[nextIdx] = cleanText.length;
        idx = nextIdx;
        continue;
      }
    }

    outToClean[idx] = cleanText.length;
    cleanText += out[idx];
    idx++;
    outToClean[idx] = cleanText.length;
  }
  outToClean[out.length] = cleanText.length;

  for (const block of quoteBlocks) {
    const startOffset = outToClean[block.startInOut];
    const endOffset = outToClean[block.endInOut];
    if (endOffset > startOffset) {
      entities.push({
        type: block.type,
        offset: startOffset,
        length: endOffset - startOffset,
      });
    }
  }

  entities.sort((a, b) => a.offset - b.offset || b.length - a.length);

  return {
    plainText: cleanText,
    entities,
  };
}

export function formatTable(markdownTable: string): { isCodeBlock: boolean; text: string } {
  const lines = markdownTable.trim().split("\n");
  if (lines.length < 2) return { isCodeBlock: false, text: markdownTable };

  const parseRow = (line: string) =>
    line
      .trim()
      .replace(/^\||\|$/g, "")
      .split("|")
      .map((c) => c.trim());

  const headers = parseRow(lines[0]);
  const dataRows = lines
    .slice(1)
    .filter((l) => !l.includes("---"))
    .map(parseRow);

  // Compute column widths
  const colWidths = headers.map((h, i) => {
    let max = h.length;
    for (const row of dataRows) {
      if (row[i] && row[i].length > max) max = row[i].length;
    }
    return max;
  });

  const totalWidth = colWidths.reduce((sum, w) => sum + w + 3, 1);

  if (totalWidth <= 36) {
    // Format as monospace pre
    let out = "```\n";
    out += headers.map((h, i) => h.padEnd(colWidths[i])).join(" | ") + "\n";
    out += colWidths.map((w) => "-".repeat(w)).join("-|-") + "\n";
    for (const row of dataRows) {
      out += row.map((cell, i) => (cell || "").padEnd(colWidths[i])).join(" | ") + "\n";
    }
    out += "```";
    return { isCodeBlock: true, text: out };
  } else {
    // Format as stacked cards
    let out = "";
    for (const row of dataRows) {
      out += "• " + (row[0] || "Item") + "\n";
      for (let i = 1; i < headers.length; i++) {
        out += `  ${headers[i]}: ${row[i] || ""}\n`;
      }
      out += "\n";
    }
    return { isCodeBlock: false, text: out.trim() };
  }
}

export function chunkMessage(text: string, maxChunkSize = 4096): string[] {
  if (text.length <= maxChunkSize) {
    return [text];
  }

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxChunkSize) {
      chunks.push(remaining);
      break;
    }

    let splitAt = remaining.lastIndexOf("\n\n", maxChunkSize);
    if (splitAt === -1 || splitAt < maxChunkSize / 2) {
      splitAt = remaining.lastIndexOf("\n", maxChunkSize);
    }
    if (splitAt === -1 || splitAt < maxChunkSize / 2) {
      splitAt = remaining.lastIndexOf(" ", maxChunkSize);
    }
    if (splitAt === -1) {
      splitAt = maxChunkSize;
    }

    const chunk = remaining.substring(0, splitAt).trim();
    chunks.push(chunk);
    remaining = remaining.substring(splitAt).trimStart();
  }

  return chunks;
}

const ALLOWED_REACTIONS = new Set([
  "❤", "👍", "👎", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🎉", "🤩",
  "🤮", "💩", "🙏", "👌", "🕊", "🤡", "🥱", "🥴", "😍", "🐳", "❤‍🔥", "🌚", "🌭", "💯",
  "🤣", "⚡", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭",
  "🤓", "👻", "👨‍💻", "👀", "🎃", "🙈", "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄",
  "☃", "💅", "🤪", "🗿", "🆒", "💘", "🙉", "🦄", "😘", "💊", "🙊", "😎", "👾", "🤷‍♂",
  "🤷", "🤷‍♀", "😡",
]);

export function normalizeReaction(reaction: string): string | null {
  if (!reaction) return null;
  // Strip VS16 variation selector
  let norm = reaction.replace(/\uFE0F/g, "").trim();

  // Near-miss maps
  if (norm === "❤️") norm = "❤";
  if (norm === "✍️") norm = "✍";

  if (ALLOWED_REACTIONS.has(norm)) {
    return norm;
  }
  return null;
}
