import { existsSync, readFileSync, writeFileSync, mkdirSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { randomBytes } from "node:crypto";

export interface StoredDetailsPage {
  id: string;
  markdown: string;
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
  transcriptPath?: string;
  updatedAt: string;
}

const DEFAULT_CONTEXT_WINDOW_SIZE = 200000;

export class PluginStore {
  private stateDir: string;
  private detailsDir: string;
  private anchorFile: string;
  private statusLineFile: string;

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.detailsDir = join(stateDir, "details");
    this.anchorFile = join(stateDir, "anchor.json");
    this.statusLineFile = join(stateDir, "statusline.json");
    this.initDirs();
  }

  private initDirs() {
    if (!existsSync(this.detailsDir)) {
      mkdirSync(this.detailsDir, { recursive: true });
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
    } catch {
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
  }

  private getStoredAnchor(): AnchorState | null {
    if (!existsSync(this.anchorFile)) return null;
    try {
      return JSON.parse(readFileSync(this.anchorFile, "utf-8"));
    } catch {
      return null;
    }
  }

  public getAnchor(): AnchorState | null {
    const stored = this.getStoredAnchor();
    const liveContext = this.resolveContextTokens(stored?.transcriptPath);
    if (!stored && !liveContext) return null;
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
    return base;
  }

  /**
   * Ingest a Claude Code statusLine JSON payload (`context_window` object) and persist to statusline.json.
   */
  public ingestStatusLine(payload: Record<string, any>): ContextTokensUsage | null {
    this.initDirs();
    writeFileSync(this.statusLineFile, JSON.stringify(payload, null, 2), "utf-8");
    return this.parseStatusLineContext(payload);
  }

  private parseStatusLineContext(payload: Record<string, any>): ContextTokensUsage | null {
    const cw = payload?.context_window;
    if (!cw || typeof cw !== "object") return null;

    const totalTokens =
      typeof cw.context_window_size === "number" && cw.context_window_size > 0
        ? cw.context_window_size
        : DEFAULT_CONTEXT_WINDOW_SIZE;

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

    const percentage =
      typeof cw.used_percentage === "number"
        ? Math.round(cw.used_percentage)
        : totalTokens > 0
          ? Math.min(100, Math.round((usedTokens / totalTokens) * 100))
          : 0;

    if (usedTokens === 0 && typeof cw.used_percentage === "number" && cw.used_percentage > 0) {
      usedTokens = Math.round((cw.used_percentage / 100) * totalTokens);
    }

    return { usedTokens, totalTokens, percentage };
  }

  private readContextFromTranscript(filePath: string): ContextTokensUsage | null {
    if (!filePath || !existsSync(filePath)) return null;
    try {
      const content = readFileSync(filePath, "utf-8");
      const lines = content.split("\n");
      for (let i = lines.length - 1; i >= 0; i--) {
        const line = lines[i].trim();
        if (!line) continue;
        try {
          const entry = JSON.parse(line);
          if (entry?.context_window) {
            const parsed = this.parseStatusLineContext(entry);
            if (parsed) return parsed;
          }
          const usage = entry?.message?.usage || entry?.usage;
          if (usage && typeof usage === "object") {
            const usedTokens =
              (Number(usage.input_tokens) || 0) +
              (Number(usage.output_tokens) || 0) +
              (Number(usage.cache_creation_input_tokens) || 0) +
              (Number(usage.cache_read_input_tokens) || 0);
            if (usedTokens > 0) {
              const totalTokens =
                typeof entry?.context_window_size === "number" && entry.context_window_size > 0
                  ? entry.context_window_size
                  : DEFAULT_CONTEXT_WINDOW_SIZE;
              const percentage = Math.min(100, Math.round((usedTokens / totalTokens) * 100));
              return { usedTokens, totalTokens, percentage };
            }
          }
        } catch {
          // Ignore malformed JSONL lines
        }
      }
    } catch {
      // Ignore read errors
    }
    return null;
  }

  private findLatestClaudeTranscript(): string | null {
    const candidates: string[] = [];
    const envPath = process.env.CLAUDE_TRANSCRIPT_PATH;
    if (envPath && existsSync(envPath)) return envPath;

    const localTranscript = join(this.stateDir, "transcript.jsonl");
    if (existsSync(localTranscript)) return localTranscript;

    const claudeProjectsDir = process.env.CLAUDE_PROJECTS_DIR || join(homedir(), ".claude", "projects");
    if (!existsSync(claudeProjectsDir)) return null;

    try {
      const walk = (dir: string, depth: number) => {
        if (depth > 3) return;
        for (const entry of readdirSync(dir, { withFileTypes: true })) {
          const full = join(dir, entry.name);
          if (entry.isDirectory()) {
            walk(full, depth + 1);
          } else if (entry.isFile() && entry.name.endsWith(".jsonl")) {
            candidates.push(full);
          }
        }
      };
      walk(claudeProjectsDir, 0);
      if (candidates.length === 0) return null;
      candidates.sort((a, b) => {
        try {
          return statSync(b).mtimeMs - statSync(a).mtimeMs;
        } catch {
          return 0;
        }
      });
      return candidates[0];
    } catch {
      return null;
    }
  }

  public resolveContextTokens(explicitTranscriptPath?: string): ContextTokensUsage | null {
    if (existsSync(this.statusLineFile)) {
      try {
        const parsed = this.parseStatusLineContext(JSON.parse(readFileSync(this.statusLineFile, "utf-8")));
        if (parsed) return parsed;
      } catch {
        // Ignore
      }
    }

    const stored = this.getStoredAnchor();
    if (stored?.contextTokens && stored.contextTokens.usedTokens > 0) {
      return stored.contextTokens;
    }

    const transcriptPath = explicitTranscriptPath || stored?.transcriptPath || this.findLatestClaudeTranscript();
    if (transcriptPath) {
      const fromTranscript = this.readContextFromTranscript(transcriptPath);
      if (fromTranscript) return fromTranscript;
    }

    return stored?.contextTokens || null;
  }
}
