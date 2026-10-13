import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

export interface StoredDetailsPage {
  id: string;
  markdown: string;
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

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.detailsDir = join(stateDir, "details");
    this.anchorFile = join(stateDir, "anchor.json");
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
  }

  public getAnchor(): AnchorState | null {
    if (!existsSync(this.anchorFile)) return null;
    try {
      return JSON.parse(readFileSync(this.anchorFile, "utf-8"));
    } catch {
      return null;
    }
  }
}
