import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

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

export interface AnchorState {
  focus: string;
  taskId?: string;
  waitingOn?: string[];
  delegations?: string[];
  contextTokens?: {
    usedTokens: number;
    totalTokens: number;
    percentage: number;
  };
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
    } catch {
      return null;
    }
  }

  public setAnchor(state: Partial<AnchorState>) {
    this.initDirs();
    const current = this.getAnchor() || {
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

  public getAnchor(): AnchorState | null {
    let anchor: AnchorState | null = null;
    if (existsSync(this.anchorFile)) {
      try {
        anchor = JSON.parse(readFileSync(this.anchorFile, "utf-8"));
      } catch {
        anchor = null;
      }
    }
    if (!anchor && existsSync(this.contextFile)) {
      anchor = {
        focus: "Standing by",
        updatedAt: new Date().toISOString(),
      };
    }
    if (anchor && !anchor.contextTokens && existsSync(this.contextFile)) {
      try {
        const ctxData = JSON.parse(readFileSync(this.contextFile, "utf-8"));
        if (ctxData && typeof ctxData.percentage === "number") {
          anchor.contextTokens = {
            usedTokens: Number(ctxData.usedTokens || 0),
            totalTokens: Number(ctxData.totalTokens || 0),
            percentage: Number(ctxData.percentage),
          };
        }
      } catch {
        // Ignore malformed context file
      }
    }
    return anchor;
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
}
