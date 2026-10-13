import { parsePermissionRequest, ParsedPermissionView } from "../web/review.js";

export interface PendingPermission {
  id: string;
  toolName: string;
  input: Record<string, unknown>;
  parsed: ParsedPermissionView;
  resolve: (decision: "allow" | "deny") => void;
  createdAt: string;
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

  public resolve(id: string, decision: "allow" | "deny"): boolean {
    const item = this.pending.get(id);
    if (!item) return false;
    item.resolve(decision);
    this.pending.delete(id);
    return true;
  }

  public get(id: string): PendingPermission | undefined {
    return this.pending.get(id);
  }

  public list(): PendingPermission[] {
    return Array.from(this.pending.values());
  }
}
