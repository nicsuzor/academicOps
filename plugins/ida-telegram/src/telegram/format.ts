export interface TelegramEntity {
  type:
    | "bold"
    | "italic"
    | "underline"
    | "strikethrough"
    | "spoiler"
    | "code"
    | "pre"
    | "text_link"
    | "text_mention"
    | "custom_emoji"
    | "blockquote"
    | "expandable_blockquote";
  offset: number;
  length: number;
  url?: string;
  language?: string;
  custom_emoji_id?: string;
}

export interface FormattedMessage {
  plainText: string;
  entities: TelegramEntity[];
}

function preprocessTablesAndHeadings(markdown: string): string {
  const rawLines = markdown.split("\n");
  const processedLines: string[] = [];
  let inFence = false;
  let i = 0;

  const isTableRow = (line: string) => /^\s*\|.+\|\s*$/.test(line);
  const isTableSep = (line: string) => /^\s*\|[\s:|-]+\|\s*$/.test(line) && line.includes("-");

  while (i < rawLines.length) {
    const line = rawLines[i];
    if (line.trimStart().startsWith("```")) {
      inFence = !inFence;
      processedLines.push(line);
      i++;
      continue;
    }

    if (!inFence) {
      // Detect Markdown table block: header row + separator row + >= 1 data row
      if (
        i + 2 < rawLines.length &&
        isTableRow(rawLines[i]) &&
        isTableSep(rawLines[i + 1]) &&
        isTableRow(rawLines[i + 2])
      ) {
        const tableLines: string[] = [rawLines[i], rawLines[i + 1]];
        let j = i + 2;
        while (j < rawLines.length && isTableRow(rawLines[j])) {
          tableLines.push(rawLines[j]);
          j++;
        }
        const formatted = formatTable(tableLines.join("\n"));
        processedLines.push(...formatted.text.split("\n"));
        i = j;
        continue;
      }

      // Convert ATX headings (# to ######) outside code blocks into bold lines
      const headingMatch = line.match(/^(\s*>!?\s*)?(#{1,6})\s+(.+?)\s*$/);
      if (headingMatch) {
        const quotePrefix = headingMatch[1] || "";
        const headingText = headingMatch[3];
        processedLines.push(`${quotePrefix}**${headingText}**`);
        i++;
        continue;
      }
    }

    processedLines.push(line);
    i++;
  }

  return processedLines.join("\n");
}

export function formatMarkdownToEntities(markdown: string): FormattedMessage {
  const entities: TelegramEntity[] = [];
  let out = "";

  const preprocessed = preprocessTablesAndHeadings(markdown);

  // Process line by line to group consecutive blockquotes (> and >!)
  const lines = preprocessed.split("\n");
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
  const outToCleanOffset = new Array<number>(out.length + 1);

  function fillOffsets(fromOutIdx: number, toOutIdx: number, cleanPos: number) {
    for (let k = fromOutIdx; k <= toOutIdx && k <= out.length; k++) {
      outToCleanOffset[k] = cleanPos;
    }
  }

  function parseSegment(segment: string, baseOutIdx: number) {
    let idx = 0;
    while (idx < segment.length) {
      outToCleanOffset[baseOutIdx + idx] = cleanText.length;

      // 1. Triple backticks (pre)
      if (segment.startsWith("```", idx)) {
        const endPre = segment.indexOf("```", idx + 3);
        if (endPre !== -1) {
          const fullBlock = segment.substring(idx + 3, endPre);
          let lang = "";
          let code = fullBlock;
          const firstNewline = fullBlock.indexOf("\n");
          if (firstNewline !== -1) {
            lang = fullBlock.substring(0, firstNewline).trim();
            code = fullBlock.substring(firstNewline + 1);
          }
          if (code.endsWith("\n")) {
            code = code.slice(0, -1);
          }
          const startOffset = cleanText.length;
          cleanText += code;
          entities.push({
            type: "pre",
            offset: startOffset,
            length: code.length,
            language: lang || undefined,
          });
          fillOffsets(baseOutIdx + idx + 1, baseOutIdx + endPre + 3, cleanText.length);
          idx = endPre + 3;
          continue;
        }
      }

      // 2. Inline code: `code`
      if (segment[idx] === "`") {
        const endCode = segment.indexOf("`", idx + 1);
        if (endCode !== -1 && !segment.substring(idx + 1, endCode).includes("\n")) {
          const code = segment.substring(idx + 1, endCode);
          const startOffset = cleanText.length;
          cleanText += code;
          entities.push({
            type: "code",
            offset: startOffset,
            length: code.length,
          });
          fillOffsets(baseOutIdx + idx + 1, baseOutIdx + endCode + 1, cleanText.length);
          idx = endCode + 1;
          continue;
        }
      }

      // 3. Custom emoji: ![alt](tg://emoji?id=<id>)
      if (segment.startsWith("![", idx)) {
        const closeBracket = segment.indexOf("](", idx + 2);
        if (closeBracket !== -1) {
          const closeParen = segment.indexOf(")", closeBracket + 2);
          if (closeParen !== -1) {
            const altText = segment.substring(idx + 2, closeBracket);
            const url = segment.substring(closeBracket + 2, closeParen);
            const emojiMatch = url.match(/^tg:\/\/emoji\?id=([0-9]+)$/);
            if (emojiMatch && altText.length > 0) {
              const startOffset = cleanText.length;
              cleanText += altText;
              entities.push({
                type: "custom_emoji",
                offset: startOffset,
                length: altText.length,
                custom_emoji_id: emojiMatch[1],
              });
              fillOffsets(baseOutIdx + idx + 1, baseOutIdx + closeParen + 1, cleanText.length);
              idx = closeParen + 1;
              continue;
            }
          }
        }
      }

      // 4. Spoiler: ||text||
      if (segment.startsWith("||", idx)) {
        const endSpoiler = segment.indexOf("||", idx + 2);
        if (endSpoiler !== -1 && endSpoiler > idx + 2) {
          const inner = segment.substring(idx + 2, endSpoiler);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 2, startOffset);
          parseSegment(inner, baseOutIdx + idx + 2);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "spoiler",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endSpoiler, baseOutIdx + endSpoiler + 2, endOffset);
          idx = endSpoiler + 2;
          continue;
        }
      }

      // 5. Strikethrough: ~~text~~
      if (segment.startsWith("~~", idx)) {
        const endStrike = segment.indexOf("~~", idx + 2);
        if (endStrike !== -1 && endStrike > idx + 2) {
          const inner = segment.substring(idx + 2, endStrike);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 2, startOffset);
          parseSegment(inner, baseOutIdx + idx + 2);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "strikethrough",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endStrike, baseOutIdx + endStrike + 2, endOffset);
          idx = endStrike + 2;
          continue;
        }
      }

      // 6. Underline: __text__ or <u>text</u> or <ins>text</ins>
      if (segment.startsWith("__", idx)) {
        let endUnderline = segment.indexOf("__", idx + 2);
        if (endUnderline !== -1 && endUnderline > idx + 2) {
          while (segment[endUnderline + 2] === "_") {
            endUnderline++;
          }
          const inner = segment.substring(idx + 2, endUnderline);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 2, startOffset);
          parseSegment(inner, baseOutIdx + idx + 2);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "underline",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endUnderline, baseOutIdx + endUnderline + 2, endOffset);
          idx = endUnderline + 2;
          continue;
        }
      }
      if (segment.startsWith("<u>", idx) || segment.startsWith("<ins>", idx)) {
        const openTag = segment.startsWith("<u>", idx) ? "<u>" : "<ins>";
        const closeTag = openTag === "<u>" ? "</u>" : "</ins>";
        const endTag = segment.indexOf(closeTag, idx + openTag.length);
        if (endTag !== -1 && endTag > idx + openTag.length) {
          const inner = segment.substring(idx + openTag.length, endTag);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + openTag.length, startOffset);
          parseSegment(inner, baseOutIdx + idx + openTag.length);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "underline",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endTag, baseOutIdx + endTag + closeTag.length, endOffset);
          idx = endTag + closeTag.length;
          continue;
        }
      }

      // 7. Bold: **text**
      if (segment.startsWith("**", idx)) {
        let endBold = segment.indexOf("**", idx + 2);
        if (endBold !== -1 && endBold > idx + 2) {
          while (segment[endBold + 2] === "*") {
            endBold++;
          }
          const inner = segment.substring(idx + 2, endBold);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 2, startOffset);
          parseSegment(inner, baseOutIdx + idx + 2);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "bold",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endBold, baseOutIdx + endBold + 2, endOffset);
          idx = endBold + 2;
          continue;
        }
      }

      // 8. Markdown links: [text](url)
      if (segment[idx] === "[") {
        const closeBracket = segment.indexOf("]", idx + 1);
        if (closeBracket !== -1 && segment[closeBracket + 1] === "(") {
          const closeParen = segment.indexOf(")", closeBracket + 2);
          if (closeParen !== -1) {
            const linkText = segment.substring(idx + 1, closeBracket);
            const linkUrl = segment.substring(closeBracket + 2, closeParen);
            const startOffset = cleanText.length;
            fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 1, startOffset);
            parseSegment(linkText, baseOutIdx + idx + 1);
            const endOffset = cleanText.length;
            if (endOffset > startOffset) {
              entities.push({
                type: "text_link",
                offset: startOffset,
                length: endOffset - startOffset,
                url: linkUrl,
              });
            }
            fillOffsets(baseOutIdx + closeBracket, baseOutIdx + closeParen + 1, endOffset);
            idx = closeParen + 1;
            continue;
          }
        }
      }

      // 9. Italic: *text* (single asterisk)
      if (segment[idx] === "*" && !segment.startsWith("**", idx)) {
        let searchFrom = idx + 1;
        let endItalic = -1;
        while (searchFrom < segment.length) {
          const cand = segment.indexOf("*", searchFrom);
          if (cand === -1) break;
          if (segment.startsWith("**", cand)) {
            searchFrom = cand + 2;
            continue;
          }
          endItalic = cand;
          break;
        }
        if (endItalic !== -1 && endItalic > idx + 1) {
          const inner = segment.substring(idx + 1, endItalic);
          const startOffset = cleanText.length;
          fillOffsets(baseOutIdx + idx, baseOutIdx + idx + 1, startOffset);
          parseSegment(inner, baseOutIdx + idx + 1);
          const endOffset = cleanText.length;
          if (endOffset > startOffset) {
            entities.push({
              type: "italic",
              offset: startOffset,
              length: endOffset - startOffset,
            });
          }
          fillOffsets(baseOutIdx + endItalic, baseOutIdx + endItalic + 1, endOffset);
          idx = endItalic + 1;
          continue;
        }
      }

      cleanText += segment[idx];
      idx++;
    }
  }

  parseSegment(out, 0);
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
    // Format as stacked cards with bold column labels
    let out = "";
    for (const row of dataRows) {
      if (headers[0]) {
        out += `• **${headers[0]}**: ${row[0] || "Item"}\n`;
      } else {
        out += "• " + (row[0] || "Item") + "\n";
      }
      for (let i = 1; i < headers.length; i++) {
        out += `  **${headers[i]}**: ${row[i] || ""}\n`;
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
