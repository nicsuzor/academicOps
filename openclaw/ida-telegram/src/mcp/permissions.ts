import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { parsePermissionRequest, ParsedPermissionView } from "../web/review.js";

export type PermissionStatus = "pending" | "allowed" | "denied" | "expired";

export interface PendingPermission {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  parsed: ParsedPermissionView;
  resolve: (decision: "allow" | "deny") => void;
  status: PermissionStatus;
  createdAt: string;
  resolvedAt?: string;
  chatId?: number;
  messageId?: number;
  cardText?: string;
  timer?: any;
}

interface StoredPermissionRecord {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  status: PermissionStatus;
  createdAt: string;
  resolvedAt?: string;
  chatId?: number;
  messageId?: number;
  cardText?: string;
}

export class PermissionRelay {
  private stateDir?: string;
  private permissionsFile?: string;
  private pending: Map<string, PendingPermission> = new Map();
  private expireListeners: Array<(item: PendingPermission) => void> = [];
  private editCardFn?: (chatId: number, messageId: number, text: string, replyMarkup?: any) => Promise<void>;

  constructor(stateDir?: string) {
    if (stateDir) {
      this.stateDir = stateDir;
      this.permissionsFile = join(stateDir, "permissions.json");
      this.loadState();
    }
  }

  private loadState() {
    if (this.permissionsFile && existsSync(this.permissionsFile)) {
      try {
        const raw = readFileSync(this.permissionsFile, "utf-8");
        const list: StoredPermissionRecord[] = JSON.parse(raw);
        for (const item of list) {
          const parsed = parsePermissionRequest({ id: item.id, tool_name: item.toolName, tool_input: item.input });
          this.pending.set(item.id, {
            ...item,
            parsed,
            resolve: () => {},
          });
        }
      } catch {
        // Corrupted file, fallback to empty
      }
    }
  }

  private saveState() {
    if (!this.stateDir || !this.permissionsFile) return;
    try {
      if (!existsSync(this.stateDir)) {
        mkdirSync(this.stateDir, { recursive: true });
      }
      const list: StoredPermissionRecord[] = Array.from(this.pending.values()).map((p) => ({
        id: p.id,
        toolName: p.toolName,
        input: p.input,
        status: p.status,
        createdAt: p.createdAt,
        resolvedAt: p.resolvedAt,
        chatId: p.chatId,
        messageId: p.messageId,
        cardText: p.cardText,
      }));
      writeFileSync(this.permissionsFile, JSON.stringify(list, null, 2), "utf-8");
    } catch {
      // Ignore write errors
    }
  }

  public setEditCardCallback(fn: (chatId: number, messageId: number, text: string, replyMarkup?: any) => Promise<void>) {
    this.editCardFn = fn;
  }

  public onExpire(listener: (item: PendingPermission) => void) {
    this.expireListeners.push(listener);
    return () => {
      const idx = this.expireListeners.indexOf(listener);
      if (idx !== -1) this.expireListeners.splice(idx, 1);
    };
  }

  public register(
    id: string,
    toolName: string,
    input: Record<string, unknown>,
    resolve: (decision: "allow" | "deny") => void,
    timeoutMs: number = 300000
  ): PendingPermission {
    const parsed = parsePermissionRequest({ id, tool_name: toolName, tool_input: input });
    let timer: any = null;
    if (timeoutMs > 0 && timeoutMs < 2147483647) {
      timer = setTimeout(() => {
        this.expire(id, "timeout");
      }, timeoutMs);
    }

    const item: PendingPermission = {
      id,
      toolName,
      input,
      parsed,
      resolve,
      status: "pending",
      createdAt: new Date().toISOString(),
      timer,
    };
    this.pending.set(id, item);
    this.saveState();
    return item;
  }

  public setMessageInfo(id: string, chatId: number, messageId: number, cardText?: string) {
    const item = this.pending.get(id);
    if (item) {
      item.chatId = chatId;
      item.messageId = messageId;
      if (cardText !== undefined) {
        item.cardText = cardText;
      }
      this.saveState();
    }
  }

  public expire(id: string, reason: "timeout" | "restart" = "timeout"): PendingPermission | null {
    const item = this.pending.get(id);
    if (!item || item.status !== "pending") return null;

    if (item.timer) {
      clearTimeout(item.timer);
      item.timer = undefined;
    }

    item.status = "expired";
    item.resolvedAt = new Date().toISOString();
    try {
      item.resolve("deny");
    } catch {
      // Ignore
    }

    this.saveState();

    for (const fn of this.expireListeners) {
      try {
        fn(item);
      } catch {
        // Ignore
      }
    }

    if (this.editCardFn && item.chatId && item.messageId) {
      const baseText = item.cardText || `Permission request: *${item.toolName}*`;
      const expiredText = `${baseText}\n\n*Expired ⏱️*`;
      this.editCardFn(item.chatId, item.messageId, expiredText, { inline_keyboard: [] }).catch(() => {});
    }

    return item;
  }

  public async sweepRestartCutPermissions(
    editCardFn?: (chatId: number, messageId: number, text: string, replyMarkup?: any) => Promise<void>
  ): Promise<PendingPermission[]> {
    const expired: PendingPermission[] = [];
    const fnToUse = editCardFn || this.editCardFn;

    for (const item of this.pending.values()) {
      if (item.status === "pending") {
        item.status = "expired";
        item.resolvedAt = new Date().toISOString();
        if (item.timer) {
          clearTimeout(item.timer);
          item.timer = undefined;
        }
        expired.push(item);

        for (const fn of this.expireListeners) {
          try {
            fn(item);
          } catch {
            // Ignore
          }
        }

        if (fnToUse && item.chatId && item.messageId) {
          const baseText = item.cardText || `Permission request: *${item.toolName}*`;
          const expiredText = `${baseText}\n\n*Expired ⏱️*`;
          await fnToUse(item.chatId, item.messageId, expiredText, { inline_keyboard: [] });
        }
      }
    }

    if (expired.length > 0) {
      this.saveState();
    }
    return expired;
  }

  public resolve(id: string, decision: "allow" | "deny"): PendingPermission | null {
    const item = this.pending.get(id);
    if (!item || item.status !== "pending") return null;

    if (item.timer) {
      clearTimeout(item.timer);
      item.timer = undefined;
    }

    item.status = decision === "allow" ? "allowed" : "denied";
    item.resolvedAt = new Date().toISOString();
    item.resolve(decision);
    this.saveState();
    return item;
  }

  public get(id: string): PendingPermission | undefined {
    return this.pending.get(id);
  }

  public list(): PendingPermission[] {
    return Array.from(this.pending.values());
  }
}
