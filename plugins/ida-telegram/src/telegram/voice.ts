export interface VoiceInEventInput {
  transcript?: string;
  error?: string;
  duration?: number;
  audioPath?: string;
  messageId: number;
  replyToMessageId?: number;
  messageThreadId?: number;
}

export interface VoiceChannelEvent {
  event: "voice";
  content: string;
  meta: Record<string, string>;
}

export function buildVoiceInEvent(input: VoiceInEventInput): VoiceChannelEvent {
  const baseMeta: Record<string, string> = {
    event: "voice",
    voice: "true",
    message_id: String(input.messageId),
  };

  if (input.messageThreadId !== undefined) {
    baseMeta.message_thread_id = String(input.messageThreadId);
    baseMeta.thread_id = String(input.messageThreadId);
  }

  if (input.duration !== undefined) {
    baseMeta.duration = String(input.duration);
  }
  if (input.audioPath !== undefined) {
    baseMeta.audio_path = input.audioPath;
  }
  if (input.replyToMessageId !== undefined) {
    baseMeta.reply_to_message_id = String(input.replyToMessageId);
  }

  if (input.error || !input.transcript) {
    const errorMsg = input.error || "unknown transcription failure";
    return {
      event: "voice",
      content: `Voice note received; transcription failed: ${errorMsg}`,
      meta: {
        ...baseMeta,
        transcript_error: errorMsg,
      },
    };
  }

  return {
    event: "voice",
    content: input.transcript,
    meta: baseMeta,
  };
}

export function prepareVoiceText(markdown: string): string {
  // Speaks tier 1 only: headline and bullets
  // Strips code blocks, blockquotes, raw links, and markdown syntax
  let text = markdown;

  // 1. Remove code blocks ```...```
  text = text.replace(/```[\s\S]*?```/g, "");

  // 2. Remove blockquotes (> and >!)
  text = text
    .split("\n")
    .filter((line) => !line.trim().startsWith(">"))
    .join("\n");

  // 3. Remove inline code `...`
  text = text.replace(/`([^`]+)`/g, "$1");

  // 4. Remove bold **...** and *...*
  text = text.replace(/\*\*([^*]+)\*\*/g, "$1");
  text = text.replace(/\*([^*]+)\*/g, "$1");
  text = text.replace(/__([^_]+)__/g, "$1");
  text = text.replace(/_([^_]+)_/g, "$1");

  // 5. Replace [label](url) with label
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

  // 6. Clean up bullets and extra whitespace
  text = text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .join("\n");

  return text;
}

export function splitVoiceTier2Quotes(markdown: string): { tier1Text: string; tier2Quotes: string } {
  const lines = markdown.split("\n");
  const tier1Lines: string[] = [];
  const tier2Lines: string[] = [];

  for (const line of lines) {
    if (line.trim().startsWith(">")) {
      tier2Lines.push(line);
    } else {
      tier1Lines.push(line);
    }
  }

  return {
    tier1Text: tier1Lines.join("\n").trim(),
    tier2Quotes: tier2Lines.join("\n").trim(),
  };
}

