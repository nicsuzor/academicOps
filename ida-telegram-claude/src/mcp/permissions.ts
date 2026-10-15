import { parsePermissionRequest, ParsedPermissionView } from "../web/review.js";

export interface PendingPermission {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  parsed: ParsedPermissionView;
  resolve: (decision: "allow" | "deny") => void;
  createdAt: string;
  chatId?: number;
  messageId?: number;
  cardText?: string;
}

export class PermissionRelay {
  private pending: Map<string, PendingPermission> = new Map();

  public register(
    id: string,
    toolName: string,
    input: Record<string, unknown>,
    resolve: (decision: "allow" | "deny") => void
  ): PendingPermission {
    const parsed = parsePermissionRequest({ id, tool_name: toolName, tool_input: input });
    const item: PendingPermission = {
      id,
      toolName,
      input,
      parsed,
      resolve,
      createdAt: new Date().toISOString(),
    };
    this.pending.set(id, item);
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
    }
  }

  public resolve(id: string, decision: "allow" | "deny"): PendingPermission | null {
    const item = this.pending.get(id);
    if (!item) return null;
    item.resolve(decision);
    this.pending.delete(id);
    return item;
  }

  public get(id: string): PendingPermission | undefined {
    return this.pending.get(id);
  }

  public list(): PendingPermission[] {
    return Array.from(this.pending.values());
  }
}
