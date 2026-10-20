import { existsSync, readFileSync, appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

export interface FeedbackTrace {
  turnId?: string;
  messageId: number;
  messageExcerpt: string;
  rating: "up" | "down";
  critique?: string;
  timestamp: string;
}

export interface UpvoteInput {
  turnId?: string;
  messageId: number;
  messageExcerpt: string;
}

export interface UpvoteResult {
  buttonText: string;
  emitsChannelEvent: false;
}

export interface CritiqueInput {
  turnId?: string;
  messageId: number;
  messageExcerpt: string;
  critique: string;
}

export interface DownvoteEvent {
  event: "feedback_down";
  turn_id?: string;
  critique: string;
  message_excerpt: string;
}

export interface CritiqueResult {
  emitsChannelEvent: true;
  channelEvent: DownvoteEvent;
}

export interface InlineButton {
  text: string;
  callback_data?: string;
  url?: string;
  web_app?: { url: string };
  [key: string]: unknown;
}

function isFeedbackButton(btn: InlineButton): boolean {
  const cb = btn.callback_data;
  if (!cb) return false;
  return cb.startsWith("fb:") || cb === "noop";
}

export class FeedbackManager {
  private stateDir: string;
  private traceFilePath: string;

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.traceFilePath = join(stateDir, "feedback.jsonl");
  }

  private ensureDir() {
    if (!existsSync(this.stateDir)) {
      mkdirSync(this.stateDir, { recursive: true });
    }
  }

  public getInitialFeedbackButtons(): InlineButton[] {
    return [
      { text: "👍", callback_data: "fb:up" },
      { text: "👎", callback_data: "fb:down" },
    ];
  }

  public replaceFeedbackButtonsInKeyboard(
    existingKeyboard: InlineButton[][] | undefined,
    replacementRows: InlineButton[][]
  ): InlineButton[][] {
    if (!existingKeyboard || existingKeyboard.length === 0) {
      return replacementRows;
    }

    const result: InlineButton[][] = [];
    let replaced = false;

    for (const row of existingKeyboard) {
      const hasFeedback = row.some(isFeedbackButton);
      if (!hasFeedback) {
        result.push(row);
        continue;
      }

      const preservedInRow = row.filter((b) => !isFeedbackButton(b));
      if (!replaced) {
        replaced = true;
        if (replacementRows.length > 0 && preservedInRow.length > 0) {
          const rowsCopy = replacementRows.map((r) => [...r]);
          rowsCopy[rowsCopy.length - 1].push(...preservedInRow);
          result.push(...rowsCopy);
        } else {
          result.push(...replacementRows);
          if (preservedInRow.length > 0) {
            result.push(preservedInRow);
          }
        }
      } else if (preservedInRow.length > 0) {
        if (result.length > 0) {
          result[result.length - 1] = [...result[result.length - 1], ...preservedInRow];
        } else {
          result.push(preservedInRow);
        }
      }
    }

    if (!replaced) {
      result.push(...replacementRows);
    }

    return result;
  }

  public async handleUpvote(input: UpvoteInput): Promise<UpvoteResult> {
    this.ensureDir();
    const trace: FeedbackTrace = {
      turnId: input.turnId,
      messageId: input.messageId,
      messageExcerpt: input.messageExcerpt,
      rating: "up",
      timestamp: new Date().toISOString(),
    };

    appendFileSync(this.traceFilePath, JSON.stringify(trace) + "\n", "utf-8");

    return {
      buttonText: "👍 saved",
      emitsChannelEvent: false,
    };
  }

  public getDownvoteCritiqueKeyboard(messageId: number): InlineButton[][] {
    return [
      [
        { text: "💨 Too verbose", callback_data: `fb:critique:${messageId}:Too verbose` },
        { text: "❌ Wrong premise", callback_data: `fb:critique:${messageId}:Wrong premise` },
      ],
      [
        { text: "📉 Poor logic", callback_data: `fb:critique:${messageId}:Poor logic` },
        { text: "🎙 Say why", callback_data: `fb:critique:${messageId}:Say why` },
      ],
      [{ text: "↩ Cancel", callback_data: `fb:cancel:${messageId}` }],
    ];
  }

  public async handleCritique(input: CritiqueInput): Promise<CritiqueResult> {
    this.ensureDir();
    const trace: FeedbackTrace = {
      turnId: input.turnId,
      messageId: input.messageId,
      messageExcerpt: input.messageExcerpt,
      rating: "down",
      critique: input.critique,
      timestamp: new Date().toISOString(),
    };

    appendFileSync(this.traceFilePath, JSON.stringify(trace) + "\n", "utf-8");

    return {
      emitsChannelEvent: true,
      channelEvent: {
        event: "feedback_down",
        turn_id: input.turnId,
        critique: input.critique,
        message_excerpt: input.messageExcerpt,
      },
    };
  }

  public getTraces(): FeedbackTrace[] {
    if (!existsSync(this.traceFilePath)) return [];
    try {
      const content = readFileSync(this.traceFilePath, "utf-8");
      return content
        .split("\n")
        .filter((l) => l.trim().length > 0)
        .map((l) => JSON.parse(l));
    } catch {
      return [];
    }
  }
}
