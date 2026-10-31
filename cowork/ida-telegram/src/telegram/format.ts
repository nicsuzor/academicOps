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

  // Process line by line to group consecutive blockquotes (> and >!)
  const lines = markdown.split("\n");
  let inStdQuote = false;
  let inExpQuote = false;
  let quoteStartOffset = 0;
  const quoteSpans: Array<{
    type: "blockquote" | "expandable_blockquote";
    outStart: number;
    outEnd: number;
  }> = [];

  function closeQuote() {
    if (inStdQuote) {
      if (quoteStartOffset !== -1 && out.length > quoteStartOffset) {
        quoteSpans.push({
          type: "blockquote",
          outStart: quoteStartOffset,
          outEnd: out.length,
        });
      }
      inStdQuote = false;
      quoteStartOffset = -1;
    }
    if (inExpQuote) {
      if (quoteStartOffset !== -1 && out.length > quoteStartOffset) {
        quoteSpans.push({
          type: "expandable_blockquote",
          outStart: quoteStartOffset,
          outEnd: out.length,
        });
      }
      inExpQuote = false;
      quoteStartOffset = -1;
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];

    if (rawLine.startsWith(">!")) {
      if (!inExpQuote) {
        closeQuote();
        inExpQuote = true;
        quoteStartOffset = -1;
      }
      const lineContent = rawLine.substring(2).trimStart();
      if (quoteStartOffset === -1) {
        if (lineContent.length > 0) {
          quoteStartOffset = out.length + (out.length > 0 ? 1 : 0);
          out += (out.length > 0 ? "\n" : "") + lineContent;
        }
      } else {
        out += "\n" + lineContent;
      }
      continue;
    } else if (rawLine.startsWith(">")) {
      const lineContent = rawLine.substring(1).trimStart();
      if (inExpQuote) {
        if (quoteStartOffset === -1) {
          if (lineContent.length > 0) {
            quoteStartOffset = out.length + (out.length > 0 ? 1 : 0);
            out += (out.length > 0 ? "\n" : "") + lineContent;
          }
        } else {
          out += "\n" + lineContent;
        }
      } else {
        if (!inStdQuote) {
          closeQuote();
          inStdQuote = true;
          quoteStartOffset = -1;
        }
        if (quoteStartOffset === -1) {
          if (lineContent.length > 0) {
            quoteStartOffset = out.length + (out.length > 0 ? 1 : 0);
            out += (out.length > 0 ? "\n" : "") + lineContent;
          }
        } else {
          out += "\n" + lineContent;
        }
      }
      continue;
    } else {
      if (inStdQuote || inExpQuote) {
        closeQuote();
      }
      const sep = i > 0 ? "\n" : "";
      out += sep + rawLine;
    }
  }
  closeQuote();

  // Scan inline markup in `out` while tracking `out` -> `cleanText` UTF-16 offsets
  let cleanText = "";
  let idx = 0;
  const outToCleanOffset = new Array<number>(out.length + 1);

  while (idx < out.length) {
    outToCleanOffset[idx] = cleanText.length;

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
        for (let k = idx + 1; k <= endPre + 3; k++) {
          outToCleanOffset[k] = cleanText.length;
        }
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
        for (let k = idx + 1; k <= endCode + 1; k++) {
          outToCleanOffset[k] = cleanText.length;
        }
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
        for (let k = idx + 1; k <= endBold + 2; k++) {
          outToCleanOffset[k] = cleanText.length;
        }
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
          for (let k = idx + 1; k <= closeParen + 1; k++) {
            outToCleanOffset[k] = cleanText.length;
          }
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
        for (let k = idx + 1; k <= endItalic + 1; k++) {
          outToCleanOffset[k] = cleanText.length;
        }
        idx = endItalic + 1;
        continue;
      }
    }

    cleanText += out[idx];
    idx++;
  }
  outToCleanOffset[out.length] = cleanText.length;

  for (const span of quoteSpans) {
    const start = outToCleanOffset[span.outStart] ?? 0;
    const end = outToCleanOffset[span.outEnd] ?? cleanText.length;
    if (end > start) {
      entities.push({
        type: span.type,
        offset: start,
        length: end - start,
      });
    }
  }

  entities.sort((a, b) => a.offset - b.offset);

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

export function normalizeReaction(reaction: string): string | null {
  if (!reaction || typeof reaction !== "string") return null;

  // Strip Unicode variation selector VS16 (\uFE0F) and trim whitespace
  let norm = reaction.replace(/\uFE0F/g, "").trim();
  if (!norm) return null;

  // Canonical near-miss mappings
  if (norm === "❤️") norm = "❤";
  if (norm === "✍️") norm = "✍";

  // Validate single grapheme cluster
  const segmenter = new Intl.Segmenter();
  const segments = Array.from(segmenter.segment(norm));
  if (segments.length !== 1) {
    return null;
  }

  // Verify that the single grapheme cluster contains an emoji/pictographic character
  if (!/\p{Extended_Pictographic}/u.test(norm)) {
    return null;
  }

  return norm;
}
