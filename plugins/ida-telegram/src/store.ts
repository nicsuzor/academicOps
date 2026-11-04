import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";
import { ReplayCache } from "./web/auth.js";

export interface StoredDetailsPage {
  id: string;
  markdown: string;
  createdAt: string;
}

export interface TurnRecord {
  direction: "in" | "out";
  text: string;
  timestamp: string;
}

export interface StoredReview {
  id: string;
  repo: string;
  pr?: number;
  base?: string;
  head?: string;
  rawDiff?: string;
  createdAt: string;
}

export interface ContextTokensUsage {
  usedTokens: number;
  totalTokens: number;
  percentage: number;
}

export interface AnchorState {
  focus: string;
  taskId?: string;
  waitingOn?: string[];
  delegations?: string[];
  contextTokens?: ContextTokensUsage;
  updatedAt: string;
}

export class PluginStore {
  private stateDir: string;
  private detailsDir: string;
  private anchorFile: string;
  private turnsFile: string;
  private reviewsFile: string;
  private contextFile: string;
  private startedAt: number;
  private seq: number = 1;
  private lastCard: { chatId: number; messageId: number; text: string } | null = null;
  private changeListeners: Array<(seq: number, type: string, data: any) => void> = [];
  private replayCache: ReplayCache = new ReplayCache();

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.detailsDir = join(stateDir, "details");
    this.anchorFile = join(stateDir, "anchor.json");
    this.turnsFile = join(stateDir, "turns.json");
    this.reviewsFile = join(stateDir, "reviews.json");
    this.contextFile = join(stateDir, "context.json");
    this.startedAt = Date.now();
    this.initDirs();
  }

  public getSeq(): number {
    return this.seq;
  }

  public getReplayCache(): ReplayCache {
    return this.replayCache;
  }

  public nextSeq(type?: string, data?: any): number {
    this.seq += 1;
    if (type) {
      for (const fn of this.changeListeners) {
        try {
          fn(this.seq, type, data);
        } catch {
          // Ignore listener error
        }
      }
    }
    return this.seq;
  }

  public onMutation(listener: (seq: number, type: string, data: any) => void) {
    this.changeListeners.push(listener);
    return () => {
      const idx = this.changeListeners.indexOf(listener);
      if (idx !== -1) this.changeListeners.splice(idx, 1);
    };
  }

  public setLastCard(chatId: number, messageId: number, text: string) {
    this.lastCard = { chatId, messageId, text };
  }

  public getLastCard(): { chatId: number; messageId: number; text: string } | null {
    return this.lastCard;
  }

  private initDirs() {
    if (!existsSync(this.detailsDir)) {
      mkdirSync(this.detailsDir, { recursive: true });
    }
  }

  public getUptimeSeconds(): number {
    return Math.max(1, Math.floor((Date.now() - this.startedAt) / 1000));
  }

  public storeDetails(markdown: string): string {
    this.initDirs();
    const id = "d_" + randomBytes(4).toString("hex");
    const page: StoredDetailsPage = {
      id,
      markdown,
      createdAt: new Date().toISOString(),
    };
    writeFileSync(join(this.detailsDir, `${id}.json`), JSON.stringify(page, null, 2), "utf-8");
    return id;
  }

  public getDetails(id: string): StoredDetailsPage | null {
    const filePath = join(this.detailsDir, `${id}.json`);
    if (!existsSync(filePath)) return null;
    try {
      return JSON.parse(readFileSync(filePath, "utf-8"));
    } catch (err) {
      console.warn(`[ida-telegram] Failed to read details page ${id}:`, err);
      return null;
    }
  }

  public setAnchor(state: Partial<AnchorState>) {
    this.initDirs();
    const current = this.getStoredAnchor() || {
      focus: "Initializing",
      updatedAt: new Date().toISOString(),
    };
    const updated: AnchorState = {
      ...current,
      ...state,
      updatedAt: new Date().toISOString(),
    };
    writeFileSync(this.anchorFile, JSON.stringify(updated, null, 2), "utf-8");
    this.nextSeq("anchor", updated);
  }

  private getStoredAnchor(): AnchorState | null {
    if (!existsSync(this.anchorFile)) return null;
    try {
      return JSON.parse(readFileSync(this.anchorFile, "utf-8"));
    } catch (err) {
      console.warn(`[ida-telegram] Failed to read anchor file:`, err);
      return null;
    }
  }

  public getAnchor(): AnchorState | null {
    const stored = this.getStoredAnchor();
    const liveContext = this.resolveContextTokens();
    if (!stored && !liveContext && !existsSync(this.contextFile)) return null;
    const base: AnchorState = stored || {
      focus: "Standing by",
      updatedAt: new Date().toISOString(),
    };
    if (liveContext) {
      return {
        ...base,
        contextTokens: liveContext,
      };
    }
    if (!base.contextTokens && existsSync(this.contextFile)) {
      try {
        const ctxData = JSON.parse(readFileSync(this.contextFile, "utf-8"));
        if (ctxData && typeof ctxData.percentage === "number") {
          base.contextTokens = {
            usedTokens: Number(ctxData.usedTokens || 0),
            totalTokens: Number(ctxData.totalTokens || 0),
            percentage: Number(ctxData.percentage),
          };
        }
      } catch (err) {
        console.warn(`[ida-telegram] Failed to read context file:`, err);
      }
    }
    return base;
  }

  public recordTurn(direction: "in" | "out", text: string, maxTurns = 10) {
    this.initDirs();
    const turns = this.getRecentTurns(maxTurns);
    turns.push({
      direction,
      text: text.length > 240 ? text.slice(0, 237) + "..." : text,
      timestamp: new Date().toISOString(),
    });
    const trimmed = turns.slice(-maxTurns);
    writeFileSync(this.turnsFile, JSON.stringify(trimmed, null, 2), "utf-8");
    this.nextSeq("turn_recorded", { direction, text });
  }

  public getRecentTurns(limit = 10): TurnRecord[] {
    if (!existsSync(this.turnsFile)) return [];
    try {
      const list = JSON.parse(readFileSync(this.turnsFile, "utf-8"));
      if (Array.isArray(list)) {
        return list.slice(-limit);
      }
      return [];
    } catch {
      return [];
    }
  }

  public addReview(review: {
    repo: string;
    pr?: number;
    base?: string;
    head?: string;
    rawDiff?: string;
  }): StoredReview {
    this.initDirs();
    const existing = this.getReviews();
    const id = `rev_${review.repo.replace(/[^a-zA-Z0-9_-]/g, "_")}_${review.pr ?? `${review.base || "base"}_${review.head || "head"}`}`;
    const entry: StoredReview = {
      id,
      repo: review.repo,
      pr: review.pr,
      base: review.base,
      head: review.head,
      rawDiff: review.rawDiff,
      createdAt: new Date().toISOString(),
    };
    const filtered = existing.filter((r) => r.id !== id);
    filtered.push(entry);
    writeFileSync(this.reviewsFile, JSON.stringify(filtered, null, 2), "utf-8");
    this.nextSeq("review", entry);
    return entry;
  }

  public getReviews(): StoredReview[] {
    if (!existsSync(this.reviewsFile)) return [];
    try {
      const list = JSON.parse(readFileSync(this.reviewsFile, "utf-8"));
      return Array.isArray(list) ? list : [];
    } catch {
      return [];
    }
  }

  public readContextFromTranscript(filePath: string): ContextTokensUsage | null {
    if (!filePath || !existsSync(filePath)) return null;
    let content: string;
    try {
      content = readFileSync(filePath, "utf-8");
    } catch (err) {
      console.warn(`[ida-telegram] Failed to read transcript file at ${filePath}:`, err);
      return null;
    }

    const lines = content.split("\n");
    for (let i = lines.length - 1; i >= 0; i--) {
      const line = lines[i].trim();
      if (!line) continue;
      let entry: any;
      try {
        entry = JSON.parse(line);
      } catch (err) {
        console.warn(`[ida-telegram] Malformed JSONL line in transcript ${filePath}:`, err);
        continue;
      }

      const cw = entry?.context_window;
      if (cw && typeof cw === "object") {
        const totalTokens =
          typeof cw.context_window_size === "number" && cw.context_window_size > 0
            ? cw.context_window_size
            : undefined;

        let usedTokens = 0;
        if (cw.current_usage && typeof cw.current_usage === "object") {
          const cu = cw.current_usage;
          usedTokens =
            (Number(cu.input_tokens) || 0) +
            (Number(cu.output_tokens) || 0) +
            (Number(cu.cache_creation_input_tokens) || 0) +
            (Number(cu.cache_read_input_tokens) || 0);
        } else if (typeof cw.total_input_tokens === "number") {
          usedTokens = (Number(cw.total_input_tokens) || 0) + (Number(cw.total_output_tokens) || 0);
        }

        if (totalTokens !== undefined && totalTokens > 0) {
          const percentage =
            typeof cw.used_percentage === "number"
              ? Math.round(cw.used_percentage)
              : Math.min(100, Math.round((usedTokens / totalTokens) * 100));
          return { usedTokens, totalTokens, percentage };
        }
      }

      const usage = entry?.message?.usage || entry?.usage;
      if (usage && typeof usage === "object") {
        const usedTokens =
          (Number(usage.input_tokens) || 0) +
          (Number(usage.output_tokens) || 0) +
          (Number(usage.cache_creation_input_tokens) || 0) +
          (Number(usage.cache_read_input_tokens) || 0);

        const totalTokens =
          typeof entry?.context_window_size === "number" && entry.context_window_size > 0
            ? entry.context_window_size
            : typeof entry?.message?.context_window_size === "number" && entry.message.context_window_size > 0
              ? entry.message.context_window_size
              : undefined;

        if (usedTokens > 0 && totalTokens !== undefined && totalTokens > 0) {
          const percentage = Math.min(100, Math.round((usedTokens / totalTokens) * 100));
          return { usedTokens, totalTokens, percentage };
        }
      }
    }
    return null;
  }

  public resolveContextTokens(explicitTranscriptPath?: string): ContextTokensUsage | null {
    const transcriptPath = explicitTranscriptPath || process.env.CLAUDE_TRANSCRIPT_PATH;
    if (!transcriptPath) return null;
    return this.readContextFromTranscript(transcriptPath);
  }
}
