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
  callback_data: string;
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
