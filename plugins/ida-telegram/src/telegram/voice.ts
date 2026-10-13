export interface VoiceInEventInput {
  transcript?: string;
  error?: string;
  duration?: number;
  audioPath?: string;
  messageId: number;
  replyToMessageId?: number;
}

export interface VoiceChannelEvent {
  event: "voice";
  content: string;
  meta: {
    voice: boolean;
    duration?: number;
    audio_path?: string;
    message_id: number;
    reply_to_message_id?: number;
    transcript_error?: string;
  };
}

export function buildVoiceInEvent(input: VoiceInEventInput): VoiceChannelEvent {
  if (input.error || !input.transcript) {
    const errorMsg = input.error || "unknown transcription failure";
    return {
      event: "voice",
      content: `Voice note received; transcription failed: ${errorMsg}`,
      meta: {
        voice: true,
        duration: input.duration,
        audio_path: input.audioPath,
        message_id: input.messageId,
        reply_to_message_id: input.replyToMessageId,
        transcript_error: errorMsg,
      },
    };
  }

  return {
    event: "voice",
    content: input.transcript,
    meta: {
      voice: true,
      duration: input.duration,
      audio_path: input.audioPath,
      message_id: input.messageId,
      reply_to_message_id: input.replyToMessageId,
    },
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
