export interface ProcessReplyInput {
  text: string;
  detail?: string;
  maxChatChars?: number;
}

export interface ProcessReplyResult {
  chatText: string;
  hasOverflow: boolean;
  combinedDetail?: string;
  hasDetailsButton: boolean;
}

export function processReplyOverflow(input: ProcessReplyInput): ProcessReplyResult {
  const { text, detail } = input;
  const maxChars = input.maxChatChars || 1200;

  // If text fits comfortably under maxChars and no detail was provided:
  if (text.length <= maxChars && !detail) {
    return {
      chatText: text,
      hasOverflow: false,
      combinedDetail: undefined,
      hasDetailsButton: false,
    };
  }

  // If text fits and detail was explicitly provided:
  if (text.length <= maxChars && detail) {
    return {
      chatText: text,
      hasOverflow: false,
      combinedDetail: detail,
      hasDetailsButton: true,
    };
  }

  // Text exceeds maxChatChars: find the last whole paragraph that fits
  const paragraphs = text.split("\n\n");
  let fittedParagraphs: string[] = [];
  let remainingParagraphs: string[] = [];
  let currentLen = 0;

  const continuationSuffix = "\n\n… continued in Details";
  const effectiveBudget = Math.max(100, maxChars - continuationSuffix.length);

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

  const chatText = fittedParagraphs.join("\n\n") + continuationSuffix;
  const overflowText = remainingParagraphs.join("\n\n");

  // Prepend overflow to existing detail character-for-character
  let combinedDetail = overflowText;
  if (detail) {
    combinedDetail = overflowText ? `${overflowText}\n\n---\n\n${detail}` : detail;
  }

  return {
    chatText,
    hasOverflow: true,
    combinedDetail,
    hasDetailsButton: true,
  };
}
