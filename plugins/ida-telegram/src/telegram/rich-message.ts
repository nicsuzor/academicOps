export const RICH_MESSAGE_MAX_CHARS = 32_768;
export const RICH_MESSAGE_MAX_BLOCKS = 500;
export const RICH_MESSAGE_MAX_MEDIA = 50;
export const RICH_MEDIA_ID_RE = /^[A-Za-z0-9_-]{1,64}$/;

export type RichMediaKind = "photo" | "video" | "audio" | "document" | "animation" | "voice" | "voice_note";

export interface RichMediaInputItem {
  id: string;
  type: RichMediaKind;
  file: string;
  mime_type?: string;
  filename?: string;
  caption?: string;
  duration?: number;
  performer?: string;
  title?: string;
  width?: number;
  height?: number;
  has_spoiler?: boolean;
  supports_streaming?: boolean;
  disable_content_type_detection?: boolean;
}

export interface InputRichMessageSpec {
  markdown?: string;
  html?: string;
  blocks?: Array<Record<string, unknown>>;
  is_rtl?: boolean;
  skip_entity_detection?: boolean;
  media?: RichMediaInputItem[];
}

export type ValidationResult = { ok: true } | { ok: false; error: string };

export function validateRichMessageContent(spec: {
  markdown?: unknown;
  html?: unknown;
  blocks?: unknown;
  media?: unknown;
  allowMedia?: boolean;
}): ValidationResult {
  const hasMd = typeof spec.markdown === "string" && spec.markdown.trim().length > 0;
  const hasHtml = typeof spec.html === "string" && spec.html.trim().length > 0;
  const hasBlocks = Array.isArray(spec.blocks);

  const count = (hasMd ? 1 : 0) + (hasHtml ? 1 : 0) + (hasBlocks ? 1 : 0);
  if (count !== 1) {
    return { ok: false, error: "Provide exactly one of markdown, html, or blocks" };
  }

  if (hasMd) {
    const md = spec.markdown as string;
    const len = Math.max(md.length, Buffer.byteLength(md, "utf8"));
    if (len > RICH_MESSAGE_MAX_CHARS) {
      return { ok: false, error: `Rich message markdown size ${len} exceeds ${RICH_MESSAGE_MAX_CHARS} limit` };
    }
  }
  if (hasHtml) {
    const html = spec.html as string;
    const len = Math.max(html.length, Buffer.byteLength(html, "utf8"));
    if (len > RICH_MESSAGE_MAX_CHARS) {
      return { ok: false, error: `Rich message html size ${len} exceeds ${RICH_MESSAGE_MAX_CHARS} limit` };
    }
  }
  if (hasBlocks) {
    const blocks = spec.blocks as unknown[];
    if (blocks.length === 0) {
      return { ok: false, error: "Rich message blocks array must not be empty" };
    }
    if (blocks.length > RICH_MESSAGE_MAX_BLOCKS) {
      return { ok: false, error: `Rich message blocks length ${blocks.length} exceeds ${RICH_MESSAGE_MAX_BLOCKS} limit` };
    }
  }

  if (spec.media !== undefined) {
    if (spec.allowMedia === false) {
      return { ok: false, error: "Draft messages do not support media attachments" };
    }
    if (!Array.isArray(spec.media)) {
      return { ok: false, error: "media must be an array" };
    }
    if (spec.media.length > RICH_MESSAGE_MAX_MEDIA) {
      return { ok: false, error: `Rich message media count ${spec.media.length} exceeds ${RICH_MESSAGE_MAX_MEDIA} limit` };
    }
    const seenIds = new Set<string>();
    const validTypes = new Set<string>(["photo", "video", "audio", "document", "animation", "voice", "voice_note"]);
    for (const item of spec.media) {
      if (!item || typeof item !== "object") {
        return { ok: false, error: "Each rich media entry must be an object" };
      }
      const m = item as Record<string, unknown>;
      if (typeof m.id !== "string" || !RICH_MEDIA_ID_RE.test(m.id)) {
        return { ok: false, error: `Invalid media id "${String(m.id ?? "")}": must match ^[A-Za-z0-9_-]{1,64}$` };
      }
      if (seenIds.has(m.id)) {
        return { ok: false, error: `Duplicate media id "${m.id}" in rich message` };
      }
      seenIds.add(m.id);
      if (typeof m.type !== "string" || !validTypes.has(m.type)) {
        return { ok: false, error: `Unsupported rich media type "${String(m.type ?? "")}"` };
      }
      if (typeof m.file !== "string" || m.file.trim().length === 0) {
        return { ok: false, error: `Media item "${m.id}" requires non-empty file path, file_id, or HTTPS URL` };
      }
    }
  }

  return { ok: true };
}

export function normalizeRichMediaType(type: RichMediaKind): string {
  return type === "voice" ? "voice_note" : type;
}

export function buildInputRichMessagePayload(
  spec: InputRichMessageSpec,
  mediaFiles: Array<{ fieldName: string; filePath: string }>,
  isLocalFilePath: (ref: string) => boolean
): Record<string, unknown> {
  const richMessage: Record<string, unknown> = {};
  if (typeof spec.markdown === "string") richMessage.markdown = spec.markdown;
  if (typeof spec.html === "string") richMessage.html = spec.html;
  if (Array.isArray(spec.blocks)) richMessage.blocks = spec.blocks;
  if (spec.is_rtl !== undefined) richMessage.is_rtl = spec.is_rtl;
  if (spec.skip_entity_detection !== undefined) richMessage.skip_entity_detection = spec.skip_entity_detection;

  if (Array.isArray(spec.media) && spec.media.length > 0) {
    richMessage.media = spec.media.map((item, idx) => {
      const wireType = normalizeRichMediaType(item.type);
      let mediaRef = item.file;
      if (isLocalFilePath(item.file)) {
        const fieldName = `rich_media_${mediaFiles.length}`;
        mediaFiles.push({ fieldName, filePath: item.file });
        mediaRef = `attach://${fieldName}`;
      }
      const mediaObj: Record<string, unknown> = {
        type: wireType,
        media: mediaRef,
      };
      if (item.mime_type !== undefined) mediaObj.mime_type = item.mime_type;
      if (item.duration !== undefined) mediaObj.duration = item.duration;
      if (item.performer !== undefined) mediaObj.performer = item.performer;
      if (item.title !== undefined) mediaObj.title = item.title;
      if (item.width !== undefined) mediaObj.width = item.width;
      if (item.height !== undefined) mediaObj.height = item.height;
      if (item.has_spoiler !== undefined) mediaObj.has_spoiler = item.has_spoiler;
      if (item.supports_streaming !== undefined) mediaObj.supports_streaming = item.supports_streaming;
      if (item.disable_content_type_detection !== undefined) {
        mediaObj.disable_content_type_detection = item.disable_content_type_detection;
      }
      return {
        id: item.id,
        media: mediaObj,
      };
    });
  }

  return richMessage;
}

function collectRichTextParts(node: unknown, out: string[]): void {
  if (!node) return;
  if (typeof node === "string") {
    if (node.trim()) out.push(node.trim());
    return;
  }
  if (Array.isArray(node)) {
    for (const item of node) collectRichTextParts(item, out);
    return;
  }
  if (typeof node === "object") {
    const obj = node as Record<string, unknown>;
    if (obj.type === "thinking" || obj.type === "details") return;
    if (typeof obj.text === "string" && obj.text.trim()) {
      out.push(obj.text.trim());
    } else if (Array.isArray(obj.text)) {
      collectRichTextParts(obj.text, out);
    }
    if (Array.isArray(obj.blocks)) {
      collectRichTextParts(obj.blocks, out);
    }
    if (Array.isArray(obj.items)) {
      collectRichTextParts(obj.items, out);
    }
  }
}

/** Extract clean readable text from an inbound or outbound RichMessage (skipping collapsed/thinking tags). */
export function extractRichMessageText(input: {
  markdown?: string;
  html?: string;
  blocks?: unknown[];
} | undefined): string {
  if (!input) return "";
  if (Array.isArray(input.blocks)) {
    const parts: string[] = [];
    collectRichTextParts(input.blocks, parts);
    return parts.join(" ").replace(/\s+/g, " ").trim();
  }
  const raw = input.markdown || input.html || "";
  return raw
    .replace(/<details[\s\S]*?<\/details>/gi, " ")
    .replace(/<tg-thinking[\s\S]*?<\/tg-thinking>/gi, " ")
    .replace(/<tg-button-row[\s\S]*?<\/tg-button-row>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/==([^=]+)==/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}
