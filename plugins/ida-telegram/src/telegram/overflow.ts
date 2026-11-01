export interface ProcessReplyInput {
  text: string;
  detail?: string;
  maxChatChars?: number;
}

export interface ProcessReplyResult {
  chatText: string;
  hasOverflow: boolean;
  hasRealOverflow?: boolean;
  isReferencesOnly?: boolean;
  detailsLabel?: string;
  combinedDetail?: string;
  hasDetailsButton: boolean;
}

/**
 * Determines whether markdown content holds only references, sources, citations,
 * or bibliography entries rather than substantive message text.
 */
export function isReferencesOnly(content?: string): boolean {
  if (!content) return false;
  const trimmed = content.trim();
  if (!trimmed) return false;

  const lines = trimmed
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && !/^[-*_]{3,}$/.test(l));

  if (lines.length === 0) return false;

  const refHeaderRegex = /^(?:#{1,6}\s+|\*{0,2}|_{0,2})(?:references|sources|citations|bibliography)(?:\s*&.*)?(?::|\*{0,2}|_{0,2})\s*$/i;
  const nonRefHeaderRegex = /^#{1,6}\s+/i;
  const citationItemRegex = /^(?:(?:[-*+]|\d+\.|\(\d+\)|\[\d+\])\s+|\[.+\]\(.+\)|https?:\/\/|\[(?:[0-9]+|[A-Za-z]+(?:\s+et\s+al\.?)?,?\s*\d{4})\]|doi:|\[\[.+\]\])/i;

  if (refHeaderRegex.test(lines[0])) {
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      if (nonRefHeaderRegex.test(line) && !refHeaderRegex.test(line)) {
        return false;
      }
    }
    return true;
  }

  // If there is no explicit header, every non-empty line must be a citation or source item
  return lines.every((line) => citationItemRegex.test(line));
}

export function processReplyOverflow(input: ProcessReplyInput): ProcessReplyResult {
  const { text, detail } = input;
  const maxChars = input.maxChatChars || 1200;

  const continuationSuffix = "\n\n… continued in Details";
  const referencesSuffix = "\n\n… references in Details";
  const maxSuffixLen = Math.max(continuationSuffix.length, referencesSuffix.length);

  // If text fits comfortably under maxChars and no detail was provided:
  if (text.length <= maxChars && !detail) {
    return {
      chatText: text,
      hasOverflow: false,
      hasRealOverflow: false,
      isReferencesOnly: false,
      combinedDetail: undefined,
      hasDetailsButton: false,
    };
  }

  const detailIsRefOnly = detail ? isReferencesOnly(detail) : false;

  // If text fits and detail was explicitly provided:
  if (text.length <= maxChars && detail) {
    if (detailIsRefOnly) {
      const trimmed = text.trimEnd();
      const alreadyHasRefSuffix =
        trimmed.endsWith("… references in Details") || trimmed.endsWith("... references in Details");
      let chatText = text;
      if (!alreadyHasRefSuffix) {
        if (text.length + referencesSuffix.length <= maxChars) {
          chatText = trimmed + referencesSuffix;
        } else {
          // If appending referencesSuffix pushes text over maxChars, fall through to paragraph budgeting
        }
      }
      if (alreadyHasRefSuffix || text.length + referencesSuffix.length <= maxChars) {
        return {
          chatText,
          hasOverflow: false,
          hasRealOverflow: false,
          isReferencesOnly: true,
          detailsLabel: "… references in Details",
          combinedDetail: detail,
          hasDetailsButton: true,
        };
      }
    } else {
      return {
        chatText: text,
        hasOverflow: false,
        hasRealOverflow: false,
        isReferencesOnly: false,
        combinedDetail: detail,
        hasDetailsButton: true,
      };
    }
  }

  // Text exceeds budget or needs budget adjustment for suffix: find the last whole paragraph that fits
  const paragraphs = text.split("\n\n");
  let fittedParagraphs: string[] = [];
  let remainingParagraphs: string[] = [];
  let currentLen = 0;

  const effectiveBudget = Math.max(100, maxChars - maxSuffixLen);

  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i];
    const addedLen = p.length + (fittedParagraphs.length > 0 ? 2 : 0);

    if (currentLen + addedLen <= effectiveBudget) {
      fittedParagraphs.push(p);
      currentLen += addedLen;
    } else {
      // If even the first paragraph doesn't fit within budget, we take up to effectiveBudget at last sentence/word
      if (fittedParagraphs.length === 0) {
        let splitIdx = p.lastIndexOf(". ", effectiveBudget);
        if (splitIdx === -1) {
          splitIdx = p.lastIndexOf(" ", effectiveBudget);
        }
        if (splitIdx === -1) {
          splitIdx = effectiveBudget;
        }
        fittedParagraphs.push(p.substring(0, splitIdx).trim());
        remainingParagraphs.push(p.substring(splitIdx).trimStart());
      } else {
        remainingParagraphs.push(p);
      }
      // Add all subsequent paragraphs to remaining
      for (let j = i + 1; j < paragraphs.length; j++) {
        remainingParagraphs.push(paragraphs[j]);
      }
      break;
    }
  }

  // Prevent orphan headings at the end of fitted paragraphs when content overflows
  if (
    fittedParagraphs.length > 0 &&
    remainingParagraphs.length > 0 &&
    /^#{1,6}\s+/.test(fittedParagraphs[fittedParagraphs.length - 1].trim())
  ) {
    const orphanHeading = fittedParagraphs.pop()!;
    remainingParagraphs.unshift(orphanHeading);
  }

  const overflowText = remainingParagraphs.join("\n\n");

  // Prepend overflow to existing detail character-for-character
  let combinedDetail = overflowText;
  if (detail) {
    combinedDetail = overflowText ? `${overflowText}\n\n---\n\n${detail}` : detail;
  }

  const hasRealOverflow = overflowText.length > 0 && !isReferencesOnly(overflowText);
  const totalRefOnly = isReferencesOnly(combinedDetail);

  let suffix = continuationSuffix;
  let detailsLabel = "… continued in Details";
  let hasOverflow = true;

  if (!hasRealOverflow && totalRefOnly) {
    suffix = referencesSuffix;
    detailsLabel = "… references in Details";
    hasOverflow = false;
  }

  const baseChatText = fittedParagraphs.join("\n\n").trimEnd();
  const alreadyHasSuffix =
    baseChatText.endsWith("… continued in Details") ||
    baseChatText.endsWith("... continued in Details") ||
    baseChatText.endsWith("… references in Details") ||
    baseChatText.endsWith("... references in Details");

  const chatText = alreadyHasSuffix ? baseChatText : baseChatText + suffix;

  return {
    chatText,
    hasOverflow,
    hasRealOverflow,
    isReferencesOnly: totalRefOnly,
    detailsLabel,
    combinedDetail,
    hasDetailsButton: true,
  };
}
