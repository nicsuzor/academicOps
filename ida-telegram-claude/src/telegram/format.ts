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
  const entities: TelegramEntity[] = [];
  let out = "";

  // Process line by line to handle blockquotes first
  const lines = markdown.split("\n");
  let inStdQuote = false;
  let inExpQuote = false;
  let quoteStartOffset = 0;

  function closeQuote() {
    if (inStdQuote) {
      entities.push({
        type: "blockquote",
        offset: quoteStartOffset,
        length: out.length - quoteStartOffset,
      });
      inStdQuote = false;
    }
    if (inExpQuote) {
      entities.push({
        type: "expandable_blockquote",
        offset: quoteStartOffset,
        length: out.length - quoteStartOffset,
      });
      inExpQuote = false;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const sep = i > 0 ? "\n" : "";

    if (rawLine.startsWith(">!")) {
      if (!inExpQuote) {
        closeQuote();
        inExpQuote = true;
        quoteStartOffset = out.length + sep.length;
      }
      const lineContent = rawLine.substring(2).trimStart();
      out += sep + lineContent;
      continue;
    } else if (rawLine.startsWith(">")) {
      if (!inStdQuote) {
        closeQuote();
        inStdQuote = true;
        quoteStartOffset = out.length + sep.length;
      }
      const lineContent = rawLine.substring(1).trimStart();
      out += sep + lineContent;
      continue;
    } else {
      if (inStdQuote || inExpQuote) {
        closeQuote();
      }
      out += sep + rawLine;
    }
  }
  closeQuote();

  // Now scan inline markup in `out`
  // We handle ```pre```, `code`, **bold**, *italic*, [link](url)
  let cleanText = "";
  let idx = 0;

  while (idx < out.length) {
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
        idx = endPre + 3;
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
        idx = endCode + 1;
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
        idx = endBold + 2;
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
          idx = closeParen + 1;
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
        idx = endItalic + 1;
        continue;
      }
    }

    cleanText += out[idx];
    idx++;
  }

  // Shift blockquote entity lengths based on stripped markdown characters in quotes
  // Simple re-scan for quotes in cleanText
  const finalEntities: TelegramEntity[] = [];
  const linesClean = cleanText.split("\n");
  let runningOffset = 0;

  for (let i = 0; i < lines.length && i < linesClean.length; i++) {
    const rawLine = lines[i];
    const cleanLine = linesClean[i];
    const lineLen = cleanLine.length + (i < linesClean.length - 1 ? 1 : 0);

    if (rawLine.startsWith(">!")) {
      finalEntities.push({
        type: "expandable_blockquote",
        offset: runningOffset,
        length: cleanLine.length,
      });
    } else if (rawLine.startsWith(">")) {
      finalEntities.push({
        type: "blockquote",
        offset: runningOffset,
        length: cleanLine.length,
      });
    }
    runningOffset += lineLen;
  }

  // Merge non-quote entities with quote entities
  for (const ent of entities) {
    if (ent.type !== "blockquote" && ent.type !== "expandable_blockquote") {
      finalEntities.push(ent);
    }
  }

  finalEntities.sort((a, b) => a.offset - b.offset);

  return {
    plainText: cleanText,
    entities: finalEntities,
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
