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

export interface ChatState {
  activeThreadId?: number;
  lastInboundMessageId?: number;
  lastInboundThreadId?: number;
  topicsEnabled?: boolean;
}

export type ThreadState = "open" | "closed" | "deleted";

/** The plugin's own record of one forum topic (the Bot API cannot list topics). */
export interface ThreadRecord {
  threadId: number;
  name?: string;
  state: ThreadState;
  /** How the record last changed: our own tool call, a Telegram service message, or a message seen in the thread. */
  source: "tool" | "service_message" | "seen";
  updatedAt: string;
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
  private chatStateFile: string;
  private chatStates: Map<number, ChatState> = new Map();
  private threadsFile: string;
  private threads: Map<number, Map<number, ThreadRecord>> = new Map();
  private sessionsFile: string;
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
    this.chatStateFile = join(stateDir, "chat_state.json");
    this.sessionsFile = join(stateDir, "sessions.json");
    this.threadsFile = join(stateDir, "threads.json");
    this.startedAt = Date.now();
    this.initDirs();
    this.loadChatStates();
    this.loadThreads();
  }

  private loadThreads() {
    if (!existsSync(this.threadsFile)) return;
    try {
      const raw = JSON.parse(readFileSync(this.threadsFile, "utf-8"));
      if (!raw || typeof raw !== "object") return;
      for (const [chatKey, records] of Object.entries(raw)) {
        const chatId = Number(chatKey);
        if (isNaN(chatId) || !records || typeof records !== "object") continue;
        const byThread = new Map<number, ThreadRecord>();
        for (const rec of Object.values(records as Record<string, ThreadRecord>)) {
          if (rec && typeof rec.threadId === "number") byThread.set(rec.threadId, rec);
        }
        this.threads.set(chatId, byThread);
      }
    } catch (err) {
      console.warn("[ida-telegram] Failed to read threads file:", err);
    }
  }

  private saveThreads() {
    try {
      this.initDirs();
      const obj: Record<string, Record<string, ThreadRecord>> = {};
      for (const [chatId, byThread] of this.threads.entries()) {
        obj[String(chatId)] = {};
        for (const [tid, rec] of byThread.entries()) obj[String(chatId)][String(tid)] = rec;
      }
      writeFileSync(this.threadsFile, JSON.stringify(obj, null, 2), "utf-8");
    } catch (err) {
      console.warn("[ida-telegram] Failed to save threads file:", err);
    }
  }

  /**
   * Record what the plugin learned about a forum topic. A `seen` observation only
   * creates a record (open) and never overrides a known one; other sources override.
   * General topic #1 is never recorded.
   */
  public recordThread(
    chatId: number,
    threadId: number,
    patch: { name?: string; state?: ThreadState; source: ThreadRecord["source"] }
  ): void {
    if (threadId === 1) return;
    let byThread = this.threads.get(chatId);
    if (!byThread) {
      byThread = new Map();
      this.threads.set(chatId, byThread);
    }
    const existing = byThread.get(threadId);
    if (existing && patch.source === "seen") return;
    byThread.set(threadId, {
      threadId,
      name: patch.name ?? existing?.name,
      state: patch.state ?? existing?.state ?? "open",
      source: patch.source,
      updatedAt: new Date().toISOString(),
    });
    this.saveThreads();
  }

  /** Threads the plugin knows about in a chat, newest-updated first. Deleted topics are omitted. */
  public listThreads(chatId: number): ThreadRecord[] {
    const state = this.chatStates.get(chatId);
    for (const tid of [state?.activeThreadId, state?.lastInboundThreadId]) {
      if (tid !== undefined && !this.threads.get(chatId)?.has(tid)) {
        this.recordThread(chatId, tid, { source: "seen" });
      }
    }
    return [...(this.threads.get(chatId)?.values() ?? [])]
      .filter((r) => r.state !== "deleted")
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  private loadChatStates() {
    if (!existsSync(this.chatStateFile)) return;
    try {
      const raw = JSON.parse(readFileSync(this.chatStateFile, "utf-8"));
      if (raw && typeof raw === "object") {
        for (const [k, v] of Object.entries(raw)) {
          const chatId = Number(k);
          if (!isNaN(chatId) && v && typeof v === "object") {
            this.chatStates.set(chatId, v as ChatState);
          }
        }
      }
    } catch (err) {
      console.warn("[ida-telegram] Failed to read chat state file:", err);
    }
  }

  private saveChatStates() {
    try {
      this.initDirs();
      const obj: Record<string, ChatState> = {};
      for (const [k, v] of this.chatStates.entries()) {
        obj[String(k)] = v;
      }
      writeFileSync(this.chatStateFile, JSON.stringify(obj, null, 2), "utf-8");
    } catch (err) {
      console.warn("[ida-telegram] Failed to save chat state file:", err);
    }
  }

  public getChatState(chatId: number): ChatState | undefined {
    return this.chatStates.get(chatId);
  }

  public getAllChatStates(): Map<number, ChatState> {
    return new Map(this.chatStates);
  }

  public updateChatState(chatId: number, update: Partial<ChatState>) {
    const current = this.chatStates.get(chatId) || {};
    const next: ChatState = { ...current, ...update };
    if (update.activeThreadId === undefined && "activeThreadId" in update) {
      delete next.activeThreadId;
    }
    if (update.lastInboundThreadId === undefined && "lastInboundThreadId" in update) {
      delete next.lastInboundThreadId;
    }
    this.chatStates.set(chatId, next);
    this.saveChatStates();
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

  public getSession(chatId: number): string | undefined {
    const sessions = this.getSessions();
    return sessions[String(chatId)];
  }

  public setSession(chatId: number, sessionId: string): void {
    this.initDirs();
    const sessions = this.getSessions();
    sessions[String(chatId)] = sessionId;
    writeFileSync(this.sessionsFile, JSON.stringify(sessions, null, 2), "utf-8");
    this.nextSeq("session_mapped", { chatId, sessionId });
  }

  public removeSession(chatId: number): void {
    this.initDirs();
    const sessions = this.getSessions();
    delete sessions[String(chatId)];
    writeFileSync(this.sessionsFile, JSON.stringify(sessions, null, 2), "utf-8");
    this.nextSeq("session_removed", { chatId });
  }

  public getSessions(): Record<string, string> {
    if (!existsSync(this.sessionsFile)) return {};
    try {
      const data = JSON.parse(readFileSync(this.sessionsFile, "utf-8"));
      return typeof data === "object" && data !== null ? data : {};
    } catch {
      return {};
    }
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
