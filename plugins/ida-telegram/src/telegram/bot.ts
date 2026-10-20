import { DEFAULT_MINI_APP_URL, PluginConfig } from "../config.js";
import { FormattedMessage, formatMarkdownToEntities } from "./format.js";
import { parseInboundUpdate, TelegramUpdate } from "./inbound.js";
import { resolveBotCommands } from "./commands.js";
import { QuestionBroker } from "./questions.js";
import { prepareVoiceText, buildVoiceInEvent } from "./voice.js";
import { PermissionRelay } from "../mcp/permissions.js";
import { PluginStore } from "../store.js";
import { acquireHostLock, releaseHostLock, calculate409Backoff } from "../role.js";
import { hostname } from "node:os";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const execFileAsync = promisify(execFile);

export interface ReplyButtonOption {
  label: string;
  callback_data?: string;
  url?: string;
  web_app?: string;
}

export interface SendReplyOptions {
  chatId: number;
  formatted: FormattedMessage;
  detailsId?: string;
  buttons?: ReplyButtonOption[];
  voice?: boolean;
  replyTo?: number;
  review?: { repo: string; pr?: number };
}

export interface SendReplyResult {
  messageId: number;
  voiceSent?: boolean;
  voiceMessageId?: number;
  voiceError?: string;
}

export class TelegramBotClient {
  private config: PluginConfig;
  private broker: QuestionBroker;
  private permRelay: PermissionRelay;
  private emitChannelEvent: (content: string, meta: Record<string, unknown>) => void;
  private isRunning = false;
  private lastUpdateId = 0;
  private conflictCount = 0;
  private lastAlertTime = 0;
  private lastInboundWasVoiceByChat = new Map<number, boolean>();
  public store?: PluginStore;
  private messageExcerpts = new Map<number, string>();

  constructor(
    config: PluginConfig,
    broker: QuestionBroker,
    permRelay: PermissionRelay,
    emitChannelEvent: (content: string, meta: Record<string, unknown>) => void,
    store?: PluginStore
  ) {
    this.config = config;
    this.broker = broker;
    this.permRelay = permRelay;
    this.emitChannelEvent = emitChannelEvent;
    this.store = store;

    this.permRelay.setEditCardCallback(async (chatId, messageId, text, replyMarkup) => {
      await this.editMessage(chatId, messageId, text, replyMarkup || { inline_keyboard: [] });
    });
  }

  public isLastInboundVoice(chatId: number): boolean {
    return this.lastInboundWasVoiceByChat.get(chatId) === true;
  }

  private recordMessageExcerpt(messageId: number | undefined, text: string | undefined) {
    if (messageId === undefined || !text) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    const excerpt = trimmed.length > 160 ? `${trimmed.slice(0, 157)}...` : trimmed;
    this.messageExcerpts.set(messageId, excerpt);
  }

  public getMessageExcerpt(messageId: number): string | undefined {
    return this.messageExcerpts.get(messageId);
  }

  private async callApi(method: string, payload: Record<string, unknown>): Promise<any> {
    const baseUrl = this.config.apiBaseUrl || "https://api.telegram.org";
    const url = `${baseUrl}/bot${this.config.botToken}/${method}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await res.json();
  }

  private async callVoiceApi(
    chatId: number,
    oggBuffer: Buffer,
    options: {
      caption?: string;
      captionEntities?: unknown[];
      replyTo?: number;
      inlineKeyboard?: Array<Array<Record<string, unknown>>>;
    }
  ): Promise<any> {
    const baseUrl = this.config.apiBaseUrl || "https://api.telegram.org";
    const url = `${baseUrl}/bot${this.config.botToken}/sendVoice`;
    const formData = new FormData();
    formData.append("chat_id", String(chatId));
    formData.append("voice", new Blob([oggBuffer], { type: "audio/ogg" }), "reply.ogg");

    if (options.caption !== undefined) {
      formData.append("caption", options.caption);
    }
    if (options.captionEntities && options.captionEntities.length > 0) {
      formData.append("caption_entities", JSON.stringify(options.captionEntities));
    }
    if (options.replyTo) {
      formData.append("reply_parameters", JSON.stringify({ message_id: options.replyTo }));
    }
    if (options.inlineKeyboard && options.inlineKeyboard.length > 0) {
      formData.append("reply_markup", JSON.stringify({ inline_keyboard: options.inlineKeyboard }));
    }

    const res = await fetch(url, {
      method: "POST",
      body: formData,
    });
    return await res.json();
  }

  public async setReaction(chatId: number, messageId: number, emoji: string): Promise<boolean> {
    try {
      const res = await this.callApi("setMessageReaction", {
        chat_id: chatId,
        message_id: messageId,
        reaction: [{ type: "emoji", emoji }],
      });
      return !!res.ok;
    } catch {
      return false;
    }
  }

  public async sendReply(opts: SendReplyOptions): Promise<SendReplyResult | null> {
    const { chatId, formatted, detailsId, buttons, voice, replyTo, review } = opts;

    // Build inline keyboard
    const inlineKeyboard: Array<Array<Record<string, unknown>>> = [];

    // Custom decision / action buttons (vertical rows, recommendation first per FR-1.1 / FR-2.2)
    if (buttons && buttons.length > 0) {
      for (const b of buttons) {
        const btnObj: Record<string, unknown> = { text: b.label };
        if (b.callback_data) {
          btnObj.callback_data = b.callback_data;
        } else if (b.url) {
          btnObj.url = b.url;
        } else if (b.web_app) {
          btnObj.web_app = { url: b.web_app };
        } else {
          btnObj.callback_data = `action:${b.label}`;
        }
        inlineKeyboard.push([btnObj]);
      }
    }

    const actionRow: Array<Record<string, unknown>> = [];

    const miniAppBaseUrl = (this.config.miniAppUrl || DEFAULT_MINI_APP_URL).replace(/\/+$/, "");

    // Mini App Details button
    if (detailsId) {
      actionRow.push({
        text: "🔍 Details",
        web_app: { url: `${miniAppBaseUrl}/app/index.html?d=${detailsId}` },
      });
    }

    if (actionRow.length > 0) {
      inlineKeyboard.push(actionRow);
    }

    // Review PR button
    if (review) {
      inlineKeyboard.push([
        {
          text: `🔍 Review diff (${review.repo}#${review.pr || ""})`,
          web_app: { url: `${miniAppBaseUrl}/app/index.html?tab=review` },
        },
      ]);
    }

    let voiceError: string | undefined;

    // Check voice out (FR-7)
    if (voice) {
      if (!this.config.voiceSpeakCmd) {
        voiceError = "VOICE_SPEAK_CMD is not configured";
      } else {
        const stamp = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const tempText = join(tmpdir(), `voice_out_${stamp}.txt`);
        const tempOgg = join(tmpdir(), `voice_out_${stamp}.ogg`);
        try {
          const spoken = prepareVoiceText(formatted.plainText);
          writeFileSync(tempText, spoken, "utf-8");

          await execFileAsync(this.config.voiceSpeakCmd, [tempText, tempOgg]);

          if (!existsSync(tempOgg)) {
            throw new Error(`TTS script did not produce output file: ${tempOgg}`);
          }
          const oggBuffer = readFileSync(tempOgg);
          if (oggBuffer.byteLength === 0) {
            throw new Error(`TTS script produced an empty audio file: ${tempOgg}`);
          }

          // FR-7.3: If caption fits under 1024 UTF-16 code units, attach caption and entities to sendVoice.
          // Otherwise send voice first, then send text message separately.
          if (formatted.plainText.length <= 1024) {
            const voiceRes = await this.callVoiceApi(chatId, oggBuffer, {
              caption: formatted.plainText,
              captionEntities: formatted.entities,
              replyTo,
              inlineKeyboard,
            });
            if (voiceRes?.ok && voiceRes?.result) {
              this.recordMessageExcerpt(voiceRes.result.message_id, formatted.plainText);
              return {
                messageId: voiceRes.result.message_id,
                voiceSent: true,
              };
            }
            throw new Error(voiceRes?.description || "Telegram sendVoice API call failed");
          } else {
            const voiceRes = await this.callVoiceApi(chatId, oggBuffer, {
              replyTo,
            });
            if (!voiceRes?.ok || !voiceRes?.result) {
              throw new Error(voiceRes?.description || "Telegram sendVoice API call failed");
            }
            const voiceMessageId: number = voiceRes.result.message_id;

            const textPayload: Record<string, unknown> = {
              chat_id: chatId,
              text: formatted.plainText,
              entities: formatted.entities,
            };
            if (inlineKeyboard.length > 0) {
              textPayload.reply_markup = { inline_keyboard: inlineKeyboard };
            }

            let textRes = await this.callApi("sendMessage", textPayload);
            if (!textRes?.ok || !textRes?.result) {
              textRes = await this.callApi("sendMessage", {
                chat_id: chatId,
                text: formatted.plainText,
                reply_markup: inlineKeyboard.length > 0 ? { inline_keyboard: inlineKeyboard } : undefined,
              });
            }

            const finalMessageId = textRes?.result?.message_id ?? voiceMessageId;
            this.recordMessageExcerpt(finalMessageId, formatted.plainText);
            return {
              messageId: finalMessageId,
              voiceMessageId,
              voiceSent: true,
            };
          }
        } catch (e) {
          voiceError = e instanceof Error ? e.message : String(e);
          console.error("Voice TTS failed, falling back to text:", e);
        } finally {
          try {
            if (existsSync(tempText)) unlinkSync(tempText);
            if (existsSync(tempOgg)) unlinkSync(tempOgg);
          } catch {
            // Ignore temp cleanup errors
          }
        }
      }
    }

    const payload: Record<string, unknown> = {
      chat_id: chatId,
      text: formatted.plainText,
      entities: formatted.entities,
    };

    if (replyTo) {
      payload.reply_parameters = { message_id: replyTo };
    }

    if (inlineKeyboard.length > 0) {
      payload.reply_markup = { inline_keyboard: inlineKeyboard };
    }

    const res = await this.callApi("sendMessage", payload);
    if (res.ok && res.result) {
      if (this.store && inlineKeyboard.length > 0) {
        this.store.setLastCard(chatId, res.result.message_id, formatted.plainText);
      }
      this.recordMessageExcerpt(res.result.message_id, formatted.plainText);
      if (voice) {
        return { messageId: res.result.message_id, voiceSent: false, voiceError };
      }
      return { messageId: res.result.message_id };
    }

    // If Telegram rejects formatted entities, resend once as plain text per FR-1.5
    const fallbackRes = await this.callApi("sendMessage", {
      chat_id: chatId,
      text: formatted.plainText,
      reply_markup: inlineKeyboard.length > 0 ? { inline_keyboard: inlineKeyboard } : undefined,
    });

    if (fallbackRes.ok && fallbackRes.result) {
      if (this.store && inlineKeyboard.length > 0) {
        this.store.setLastCard(chatId, fallbackRes.result.message_id, formatted.plainText);
      }
      this.recordMessageExcerpt(fallbackRes.result.message_id, formatted.plainText);
      if (voice) {
        return { messageId: fallbackRes.result.message_id, voiceSent: false, voiceError };
      }
      return { messageId: fallbackRes.result.message_id };
    }

    return null;
  }

  public async sendQuestionCard(chatId: number, qid: string, card: { text: string; buttons: Array<{ text: string; callbackData: string }> }) {
    const formatted = formatMarkdownToEntities(card.text);
    const inline_keyboard = card.buttons.map((b) => [{ text: b.text, callback_data: b.callbackData }]);
    const res = await this.callApi("sendMessage", {
      chat_id: chatId,
      text: formatted.plainText,
      entities: formatted.entities,
      reply_markup: { inline_keyboard },
    });
    if (res?.ok && res?.result?.message_id) {
      this.broker.setMessageId(qid, res.result.message_id);
      if (this.store) {
        this.store.setLastCard(chatId, res.result.message_id, card.text);
      }
      this.recordMessageExcerpt(res.result.message_id, formatted.plainText);
    }
    return res;
  }

  public async sendPermissionCard(
    permId: string,
    toolName: string,
    input: Record<string, unknown>,
    description?: string,
    inputPreview?: string
  ) {
    const defaultChatId = this.config.allowFrom[0];
    if (!defaultChatId) return;

    let summary = `Permission request: *${toolName}*`;
    if (description) {
      summary += `\n${description}`;
    }
    if (toolName === "Bash" && input.command) {
      summary += `\n\`\`\`bash\n${input.command}\n\`\`\``;
    } else if ((toolName === "Edit" || toolName === "Write") && (input.file_path || input.target_file)) {
      summary += `\nTarget: \`${input.file_path || input.target_file}\``;
    } else if (inputPreview) {
      summary += `\n\`\`\`\n${inputPreview}\n\`\`\``;
    }

    const inline_keyboard: Array<Array<Record<string, unknown>>> = [
      [
        { text: "Allow ✅", callback_data: `perm:allow:${permId}` },
        { text: "Deny ❌", callback_data: `perm:deny:${permId}` },
      ],
    ];

    if (this.config.miniAppUrl) {
      inline_keyboard.push([
        {
          text: "🔍 Review in Mini App",
          web_app: { url: `${this.config.miniAppUrl}/app/index.html?tab=review` },
        },
      ]);
    }

    const res = await this.callApi("sendMessage", {
      chat_id: defaultChatId,
      text: summary,
      reply_markup: { inline_keyboard },
    });
    if (res?.ok && res?.result?.message_id) {
      this.permRelay.setMessageInfo(permId, defaultChatId, res.result.message_id, summary);
      if (this.store) {
        this.store.setLastCard(defaultChatId, res.result.message_id, summary);
      }
      this.recordMessageExcerpt(res.result.message_id, summary);
    }
    return res;
  }

  public async editMessage(chatId: number, messageId: number, text: string, replyMarkup?: Record<string, unknown>) {
    const formatted = formatMarkdownToEntities(text);
    const res = await this.callApi("editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text: formatted.plainText,
      entities: formatted.entities,
      reply_markup: replyMarkup,
    });
    if (res?.ok) {
      this.recordMessageExcerpt(messageId, formatted.plainText);
    }
    return res;
  }

  public async registerCommands(persona?: string): Promise<boolean> {
    if (!this.config.isPrimary) {
      return false;
    }

    const commands = persona
      ? resolveBotCommands(persona)
      : (this.config.botCommands && this.config.botCommands.length > 0
          ? this.config.botCommands
          : resolveBotCommands(this.config.persona));

    if (commands.length === 0) {
      return false;
    }

    let allOk = true;
    for (const chatId of this.config.allowFrom) {
      const res = await this.callApi("setMyCommands", {
        commands,
        scope: { type: "chat", chat_id: chatId },
      });
      if (!res?.ok) {
        allOk = false;
      }
    }
    return allOk;
  }

  public async getRegisteredCommands(chatId: number): Promise<Array<{ command: string; description: string }>> {
    const res = await this.callApi("getMyCommands", {
      scope: { type: "chat", chat_id: chatId },
    });
    if (res?.ok && Array.isArray(res.result)) {
      return res.result;
    }
    return [];
  }

  public async startPolling() {
    if (!this.config.isPrimary) {
      console.log("[ida-telegram] Non-primary instance: poller disabled.");
      return;
    }

    const lock = acquireHostLock(this.config.stateDir, hostname(), "primary", process.pid);
    if (!lock.acquired) {
      console.error(`[ida-telegram] Cannot acquire host lock: ${lock.reason}. Exiting.`);
      return;
    }

    await this.registerCommands();

    this.isRunning = true;

    while (this.isRunning) {
      try {
        const res = await this.callApi("getUpdates", {
          offset: this.lastUpdateId + 1,
          timeout: 20,
          allowed_updates: ["message", "edited_message", "callback_query", "message_reaction"],
        });

        if (res.ok && Array.isArray(res.result)) {
          this.conflictCount = 0;
          for (const update of res.result as TelegramUpdate[]) {
            this.lastUpdateId = Math.max(this.lastUpdateId, update.update_id);
            await this.handleUpdate(update);
          }
        } else if (res.error_code === 409) {
          this.conflictCount++;
          const delay = calculate409Backoff(this.conflictCount);
          console.warn(`[ida-telegram] 409 Conflict: another poller active. Backing off for ${delay}ms`);

          const now = Date.now();
          if (now - this.lastAlertTime > 3600000) {
            this.lastAlertTime = now;
            this.emitChannelEvent("system_warning", "Warning: another poller is using this Telegram bot token.", {
              type: "warning",
            });
          }

          await new Promise((r) => setTimeout(r, delay));
        }
      } catch (err) {
        console.error("[ida-telegram] Polling error:", err);
        await new Promise((r) => setTimeout(r, 5000));
      }
    }

    releaseHostLock(this.config.stateDir);
  }

  public stopPolling() {
    this.isRunning = false;
    releaseHostLock(this.config.stateDir);
  }

  private async handleUpdate(update: TelegramUpdate) {
    if (update.message?.message_id && (update.message.text || update.message.caption)) {
      this.recordMessageExcerpt(update.message.message_id, update.message.text || update.message.caption);
    }

    // 1. If inbound message from user, immediately set 👀 reaction (FR-9) and record voice-vs-text for FR-7.1 mirror
    if (update.message?.from?.id && this.config.allowFrom.includes(update.message.from.id)) {
      const isInboundVoice = Boolean(update.message.voice || update.message.audio);
      this.lastInboundWasVoiceByChat.set(update.message.chat.id, isInboundVoice);
      await this.setReaction(update.message.chat.id, update.message.message_id, "👀");
    }

    // 2. Check if message is a reply to a force_reply "✏️ Other" question prompt
    if (
      update.message?.from?.id &&
      this.config.allowFrom.includes(update.message.from.id) &&
      update.message.reply_to_message &&
      update.message.text
    ) {
      const pendingQ = this.broker.findQuestionByPromptMessageId(update.message.reply_to_message.message_id);
      if (pendingQ) {
        const res = await this.broker.resolveAnswer(pendingQ.id, "other", update.message.text);
        if (res) {
          const targetMsgId = pendingQ.messageId || update.message.reply_to_message.message_id;
          await this.editMessage(update.message.chat.id, targetMsgId, res.cardText, { inline_keyboard: [] });
          this.emitChannelEvent(
            `Question answered: ${res.channelEvent.choice}`,
            res.channelEvent as unknown as Record<string, unknown>
          );
        }
        return;
      }
    }

    // 3. Handle Callback Queries (Buttons)
    if (update.callback_query) {
      const cb = update.callback_query;
      const data = cb.data || "";

      if (!data.startsWith("q:") && !data.startsWith("perm:")) {
        await this.callApi("answerCallbackQuery", { callback_query_id: cb.id });
      }

      if (data === "noop") {
        return;
      }

      // Questions callback: q:<qid>:<qi>:<oi>
      if (data.startsWith("q:")) {
        const parts = data.split(":");
        const qid = parts[1];
        const action = parts[3];
        const q = this.broker.getQuestion(qid);

        if (!q || q.status !== "pending") {
          await this.callApi("answerCallbackQuery", {
            callback_query_id: cb.id,
            text: "Question already resolved.",
          });
          if (cb.message) {
            await this.callApi("editMessageReplyMarkup", {
              chat_id: cb.message.chat.id,
              message_id: cb.message.message_id,
              reply_markup: { inline_keyboard: [] },
            });
          }
          return;
        }

        await this.callApi("answerCallbackQuery", { callback_query_id: cb.id });

        if (action === "other") {
          if (cb.message) {
            const promptTitle = q?.header || q?.question || qid;
            const promptRes = await this.callApi("sendMessage", {
              chat_id: cb.message.chat.id,
              text: `✏️ Reply to this message with your answer for: ${promptTitle}`,
              reply_parameters: { message_id: cb.message.message_id },
              reply_markup: { force_reply: true, selective: true },
            });
            if (promptRes?.ok && promptRes?.result?.message_id) {
              this.broker.setPromptMessageId(qid, promptRes.result.message_id);
            }
          }
          return;
        }

        if (q?.multiSelect && action !== "done") {
          const optIdx = parseInt(action, 10);
          const updatedCard = this.broker.toggleOption(qid, optIdx);
          if (updatedCard && cb.message) {
            const inline_keyboard = updatedCard.buttons.map((b) => [{ text: b.text, callback_data: b.callbackData }]);
            await this.callApi("editMessageReplyMarkup", {
              chat_id: cb.message.chat.id,
              message_id: cb.message.message_id,
              reply_markup: { inline_keyboard },
            });
          }
          return;
        }

        const optIdx = action === "done" ? "done" : parseInt(action, 10);
        const res = await this.broker.resolveAnswer(qid, optIdx);
        if (res && cb.message) {
          await this.editMessage(cb.message.chat.id, cb.message.message_id, res.cardText, { inline_keyboard: [] });
          this.emitChannelEvent(
            `Question answered: ${res.channelEvent.choice}`,
            res.channelEvent as unknown as Record<string, unknown>
          );
        }
        return;
      }

      // Permission callbacks: perm:allow:<id> / perm:deny:<id>
      if (data.startsWith("perm:") && cb.message) {
        const parts = data.split(":");
        const decision = parts[1] as "allow" | "deny";
        const permId = parts[2];
        const perm = this.permRelay.get(permId);

        if (!perm || perm.status !== "pending") {
          await this.callApi("answerCallbackQuery", {
            callback_query_id: cb.id,
            text: "Permission already resolved or expired.",
          });
          await this.editMessage(
            cb.message.chat.id,
            cb.message.message_id,
            `${cb.message.text}\n\n*Already resolved or expired.*`,
            { inline_keyboard: [] }
          );
          return;
        }

        await this.callApi("answerCallbackQuery", { callback_query_id: cb.id });
        this.permRelay.resolve(permId, decision);

        const outcomeText = decision === "allow" ? "Allowed via Telegram ✅" : "Denied ❌";
        await this.editMessage(
          cb.message.chat.id,
          cb.message.message_id,
          `${cb.message.text}\n\n*${outcomeText}*`,
          { inline_keyboard: [] }
        );
        return;
      }

      // Custom action / decision buttons on reply cards (FR-1.1 / FR-8)
      if (cb.message && this.config.allowFrom.includes(cb.from.id)) {
        const kbRows = cb.message.reply_markup?.inline_keyboard || [];
        const matchedBtn = kbRows.flat().find((b) => b.callback_data === data);
        const label = matchedBtn?.text || data;
        const splitIdx = data.indexOf(":");
        const callbackPrefix = splitIdx !== -1 ? data.substring(0, splitIdx) : data;
        const originalText = cb.message.text || "";

        await this.editMessage(
          cb.message.chat.id,
          cb.message.message_id,
          `${originalText}\n\nSelected: ${label} ✅`,
          { inline_keyboard: [] }
        );

        this.emitChannelEvent(`tapped ${label}`, {
          event: "button_tap",
          callback_id: cb.id,
          callback_prefix: callbackPrefix,
          payload: data,
          label,
          target_message_id: String(cb.message.message_id),
          chat_id: String(cb.message.chat.id),
          user_id: String(cb.from.id),
        });
        return;
      }
    }

    // 4. Voice Notes
    if (update.message?.voice || update.message?.audio) {
      const voice = update.message.voice || update.message.audio;
      const fileId = voice?.file_id;
      const duration = voice?.duration || 0;

      if (fileId && this.config.voiceTranscribeCmd) {
        try {
          // Download file info
          const fileInfoRes = await this.callApi("getFile", { file_id: fileId });
          const filePath = fileInfoRes.result?.file_path;
          const baseUrl = this.config.apiBaseUrl || "https://api.telegram.org";
          const downloadUrl = `${baseUrl}/file/bot${this.config.botToken}/${filePath}`;

          const inboxDir = join(this.config.stateDir, "inbox");
          mkdirSync(inboxDir, { recursive: true });
          const localAudioPath = join(inboxDir, `voice_${Date.now()}.ogg`);
          const res = await fetch(downloadUrl);
          const buf = await res.arrayBuffer();
          writeFileSync(localAudioPath, Buffer.from(buf));

          // Run transcription script
          const { stdout } = await execFileAsync(this.config.voiceTranscribeCmd, [localAudioPath], {
            timeout: 120000,
          });

          const voiceEvent = buildVoiceInEvent({
            transcript: stdout.trim(),
            duration,
            audioPath: localAudioPath,
            messageId: update.message.message_id,
            replyToMessageId: update.message.reply_to_message?.message_id,
          });

          this.emitChannelEvent(voiceEvent.content, {
            ...voiceEvent.meta,
            chat_id: String(update.message.chat.id),
            user_id: update.message.from?.id !== undefined ? String(update.message.from.id) : undefined,
          });
          return;
        } catch (e) {
          const failEvent = buildVoiceInEvent({
            error: String(e),
            duration,
            messageId: update.message.message_id,
          });
          this.emitChannelEvent(failEvent.content, {
            ...failEvent.meta,
            chat_id: String(update.message.chat.id),
            user_id: update.message.from?.id !== undefined ? String(update.message.from.id) : undefined,
          });
          return;
        }
      }
    }

    // 5. General Inbound (text, attachments, reactions, commands)
    const event = parseInboundUpdate(update, this.config.allowFrom, (msgId) => this.getMessageExcerpt(msgId), this.config.persona);
    if (event) {
      if (event.event === "attachment" && event.meta.file_id && this.config.botToken) {
        try {
          const fileInfoRes = await this.callApi("getFile", { file_id: event.meta.file_id });
          const filePath = fileInfoRes?.result?.file_path;
          if (filePath) {
            const baseUrl = this.config.apiBaseUrl || "https://api.telegram.org";
            const downloadUrl = `${baseUrl}/file/bot${this.config.botToken}/${filePath}`;
            const inboxDir = join(this.config.stateDir, "inbox");
            mkdirSync(inboxDir, { recursive: true });
            const baseName = event.meta.file_name || filePath.split("/").pop() || `file_${Date.now()}`;
            const localPath = join(inboxDir, `${Date.now()}_${baseName}`);
            const res = await fetch(downloadUrl);
            const buf = await res.arrayBuffer();
            writeFileSync(localPath, Buffer.from(buf));
            event.meta.attachment_path = localPath;
          }
        } catch {
          // Proceed with emitting attachment event even if download fails
        }
      }
      this.emitChannelEvent(event.content, event.meta);
    }
  }
}

