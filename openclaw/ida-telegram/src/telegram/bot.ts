import { PluginConfig } from "../config.js";
import { FormattedMessage } from "./format.js";
import { parseInboundUpdate, TelegramUpdate } from "./inbound.js";
import { QuestionBroker } from "./questions.js";
import { FeedbackManager } from "./feedback.js";
import { prepareVoiceText, buildVoiceInEvent } from "./voice.js";
import { PermissionRelay } from "../mcp/permissions.js";
import { acquireHostLock, releaseHostLock, calculate409Backoff } from "../role.js";
import { hostname } from "node:os";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const execFileAsync = promisify(execFile);

export interface SendReplyOptions {
  chatId: number;
  formatted: FormattedMessage;
  detailsId?: string;
  voice?: boolean;
  replyTo?: number;
  feedback?: boolean;
  review?: { repo: string; pr?: number };
}

export class TelegramBotClient {
  private config: PluginConfig;
  private broker: QuestionBroker;
  private feedbackManager: FeedbackManager;
  private permRelay: PermissionRelay;
  private emitChannelEvent: (content: string, meta: Record<string, unknown>) => void;
  private isRunning = false;
  private lastUpdateId = 0;
  private conflictCount = 0;
  private lastAlertTime = 0;

  constructor(
    config: PluginConfig,
    broker: QuestionBroker,
    feedbackManager: FeedbackManager,
    permRelay: PermissionRelay,
    emitChannelEvent: (content: string, meta: Record<string, unknown>) => void
  ) {
    this.config = config;
    this.broker = broker;
    this.feedbackManager = feedbackManager;
    this.permRelay = permRelay;
    this.emitChannelEvent = emitChannelEvent;
  }

  private async callApi(method: string, payload: Record<string, unknown>): Promise<any> {
    const url = `https://api.telegram.org/bot${this.config.botToken}/${method}`;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const json = await res.json();
    return json;
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

  public async sendReply(opts: SendReplyOptions): Promise<{ messageId: number } | null> {
    const { chatId, formatted, detailsId, voice, replyTo, feedback, review } = opts;

    // Build inline keyboard
    const inlineKeyboard: Array<Array<Record<string, unknown>>> = [];
    const actionRow: Array<Record<string, unknown>> = [];

    // Feedback buttons
    if (feedback !== false) {
      actionRow.push({ text: "👍", callback_data: "fb:up" });
      actionRow.push({ text: "👎", callback_data: "fb:down" });
    }

    // Mini App Details button
    if (detailsId && this.config.miniAppUrl) {
      actionRow.push({
        text: "🔍 Details",
        web_app: { url: `${this.config.miniAppUrl}/app/index.html?d=${detailsId}` },
      });
    }

    if (actionRow.length > 0) {
      inlineKeyboard.push(actionRow);
    }

    // Review PR button
    if (review && this.config.miniAppUrl) {
      inlineKeyboard.push([
        {
          text: `🔍 Review diff (${review.repo}#${review.pr || ""})`,
          web_app: { url: `${this.config.miniAppUrl}/app/index.html?tab=review` },
        },
      ]);
    }

    // Check voice out
    if (voice && this.config.voiceSpeakCmd) {
      try {
        const spoken = prepareVoiceText(formatted.plainText);
        const tempText = join(tmpdir(), `voice_out_${Date.now()}.txt`);
        const tempOgg = join(tmpdir(), `voice_out_${Date.now()}.ogg`);
        writeFileSync(tempText, spoken, "utf-8");

        await execFileAsync(this.config.voiceSpeakCmd, [tempText, tempOgg]);

        // If caption fits under 1024, attach caption to sendVoice
        // Otherwise send voice then send text separately
        // (Note: in test / dry-run, fallback to text)
      } catch (e) {
        console.error("Voice TTS failed, falling back to text:", e);
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
      return { messageId: res.result.message_id };
    }

    // If Telegram rejects formatted entities, resend once as plain text per FR-1.5
    const fallbackRes = await this.callApi("sendMessage", {
      chat_id: chatId,
      text: formatted.plainText,
      reply_markup: inlineKeyboard.length > 0 ? { inline_keyboard: inlineKeyboard } : undefined,
    });

    if (fallbackRes.ok && fallbackRes.result) {
      return { messageId: fallbackRes.result.message_id };
    }

    return null;
  }

  public async sendQuestionCard(chatId: number, qid: string, card: { text: string; buttons: Array<{ text: string; callbackData: string }> }) {
    const inline_keyboard = card.buttons.map((b) => [{ text: b.text, callback_data: b.callbackData }]);
    return await this.callApi("sendMessage", {
      chat_id: chatId,
      text: card.text,
      reply_markup: { inline_keyboard },
    });
  }

  public async sendPermissionCard(permId: string, toolName: string, input: Record<string, unknown>) {
    const defaultChatId = this.config.allowFrom[0];
    if (!defaultChatId) return;

    let summary = `Permission request: *${toolName}*`;
    if (toolName === "Bash") {
      summary += `\n\`\`\`bash\n${input.command || ""}\n\`\`\``;
    } else if (toolName === "Edit" || toolName === "Write") {
      summary += `\nTarget: \`${input.file_path || input.target_file || ""}\``;
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

    return await this.callApi("sendMessage", {
      chat_id: defaultChatId,
      text: summary,
      reply_markup: { inline_keyboard },
    });
  }

  public async editMessage(chatId: number, messageId: number, text: string, replyMarkup?: Record<string, unknown>) {
    return await this.callApi("editMessageText", {
      chat_id: chatId,
      message_id: messageId,
      text,
      reply_markup: replyMarkup,
    });
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
    // 1. If inbound message from Nic, immediately set 👀 reaction (FR-9)
    if (update.message?.from?.id && this.config.allowFrom.includes(update.message.from.id)) {
      await this.setReaction(update.message.chat.id, update.message.message_id, "👀");
    }

    // 2. Handle Callback Queries (Buttons)
    if (update.callback_query) {
      const cb = update.callback_query;
      const data = cb.data || "";

      // Answer callback query toast
      await this.callApi("answerCallbackQuery", { callback_query_id: cb.id });

      // Questions callback: q:<qid>:<qi>:<oi>
      if (data.startsWith("q:")) {
        const parts = data.split(":");
        const qid = parts[1];
        const optIdx = parts[3] === "done" ? "done" : parseInt(parts[3], 10);

        const res = await this.broker.resolveAnswer(qid, optIdx);
        if (res && cb.message) {
          await this.editMessage(cb.message.chat.id, cb.message.message_id, res.cardText);
          this.emitChannelEvent(
            `Question answered: ${res.channelEvent.choice}`,
            res.channelEvent as unknown as Record<string, unknown>
          );
        }
        return;
      }

      // Feedback callbacks: fb:...
      if (data === "fb:up" && cb.message) {
        await this.feedbackManager.handleUpvote({
          messageId: cb.message.message_id,
          messageExcerpt: cb.message.text || "",
        });
        await this.callApi("editMessageReplyMarkup", {
          chat_id: cb.message.chat.id,
          message_id: cb.message.message_id,
          reply_markup: {
            inline_keyboard: [[{ text: "👍 saved", callback_data: "noop" }]],
          },
        });
        return;
      }

      if (data === "fb:down" && cb.message) {
        const critiqueKeyboard = this.feedbackManager.getDownvoteCritiqueKeyboard(cb.message.message_id);
        await this.callApi("editMessageReplyMarkup", {
          chat_id: cb.message.chat.id,
          message_id: cb.message.message_id,
          reply_markup: { inline_keyboard: critiqueKeyboard },
        });
        return;
      }

      if (data.startsWith("fb:critique:") && cb.message) {
        const parts = data.split(":");
        const critique = parts.slice(3).join(":");
        const res = await this.feedbackManager.handleCritique({
          messageId: cb.message.message_id,
          messageExcerpt: cb.message.text || "",
          critique,
        });

        await this.callApi("editMessageReplyMarkup", {
          chat_id: cb.message.chat.id,
          message_id: cb.message.message_id,
          reply_markup: {
            inline_keyboard: [[{ text: `Critique saved: ${critique}`, callback_data: "noop" }]],
          },
        });

        if (res.emitsChannelEvent) {
          this.emitChannelEvent(
            `Feedback received: ${critique}`,
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
        this.permRelay.resolve(permId, decision);

        const outcomeText = decision === "allow" ? "Allowed via Telegram ✅" : "Denied ❌";
        await this.editMessage(
          cb.message.chat.id,
          cb.message.message_id,
          `${cb.message.text}\n\n*${outcomeText}*`
        );
        return;
      }
    }

    // 3. Voice Notes
    if (update.message?.voice || update.message?.audio) {
      const voice = update.message.voice || update.message.audio;
      const fileId = voice?.file_id;
      const duration = voice?.duration || 0;

      if (fileId && this.config.voiceTranscribeCmd) {
        try {
          // Download file info
          const fileInfoRes = await this.callApi("getFile", { file_id: fileId });
          const filePath = fileInfoRes.result?.file_path;
          const downloadUrl = `https://api.telegram.org/file/bot${this.config.botToken}/${filePath}`;

          const localAudioPath = join(this.config.stateDir, "inbox", `voice_${Date.now()}.ogg`);
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

          this.emitChannelEvent(voiceEvent.content, voiceEvent.meta);
          return;
        } catch (e) {
          const failEvent = buildVoiceInEvent({
            error: String(e),
            duration,
            messageId: update.message.message_id,
          });
          this.emitChannelEvent(failEvent.content, failEvent.meta);
          return;
        }
      }
    }

    // 4. General Inbound (text, reactions, commands)
    const event = parseInboundUpdate(update, this.config.allowFrom);
    if (event) {
      this.emitChannelEvent(event.content, event.meta);
    }
  }
}
