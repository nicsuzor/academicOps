import { existsSync, readFileSync } from "node:fs";

export interface PermissionRequest {
  id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

export interface ParsedPermissionView {
  id: string;
  type: "diff" | "script" | "json";
  toolName: string;
  filePath?: string;
  diff?: string;
  script?: string;
  formattedJson?: string;
}

export function parsePermissionRequest(perm: PermissionRequest): ParsedPermissionView {
  const { id, tool_name, tool_input } = perm;

  if (tool_name === "Edit" || tool_name === "MultiEdit") {
    const filePath = (tool_input.file_path as string) || (tool_input.target_file as string);
    const edits = Array.isArray(tool_input.edits)
      ? (tool_input.edits as Array<{ old_string?: string; new_string?: string }>)
      : [
          {
            old_string: (tool_input.old_string as string) || (tool_input.target_content as string) || "",
            new_string: (tool_input.new_string as string) || (tool_input.replacement_content as string) || "",
          },
        ];

    const hunks: string[] = [];
    for (const edit of edits) {
      const oldStr = edit.old_string || "";
      const newStr = edit.new_string || "";
      const oldLines = oldStr.split("\n").map((l) => `-${l}`).join("\n");
      const newLines = newStr.split("\n").map((l) => `+${l}`).join("\n");
      hunks.push(`${oldLines}\n${newLines}`);
    }

    const diff = `--- ${filePath}\n+++ ${filePath}\n${hunks.join("\n@@ @@\n")}`;

    return {
      id,
      type: "diff",
      toolName: tool_name,
      filePath,
      diff,
    };
  }

  if (tool_name === "Write" || tool_name === "write_to_file") {
    const filePath = (tool_input.file_path as string) || (tool_input.target_file as string);
    const content = (tool_input.content as string) || (tool_input.code_content as string) || "";
    const newLines = content.split("\n").map((l) => `+${l}`).join("\n");
    let diff = `--- /dev/null\n+++ ${filePath}\n${newLines}`;
    if (filePath && existsSync(filePath)) {
      try {
        const existing = readFileSync(filePath, "utf-8");
        const oldLines = existing.split("\n").map((l) => `-${l}`).join("\n");
        diff = `--- ${filePath}\n+++ ${filePath}\n${oldLines}\n${newLines}`;
      } catch {
        // Fallback to new-file diff if unreadable
      }
    }

    return {
      id,
      type: "diff",
      toolName: tool_name,
      filePath,
      diff,
    };
  }

  if (tool_name === "Bash" || tool_name === "run_command") {
    const script = (tool_input.command as string) || (tool_input.command_line as string) || "";
    return {
      id,
      type: "script",
      toolName: tool_name,
      script,
    };
  }

  return {
    id,
    type: "json",
    toolName: tool_name,
    formattedJson: JSON.stringify(tool_input, null, 2),
  };
}

export interface PrFileDiff {
  path: string;
  patch: string;
}

export interface FormattedPrDiff {
  repo: string;
  prNumber: number;
  base?: string;
  head?: string;
  files: PrFileDiff[];
}

export function formatPrDiff(rawDiff: string, repo: string, prNumber: number): FormattedPrDiff {
  const files: PrFileDiff[] = [];
  const fileChunks = rawDiff.split(/^diff --git /m).filter(Boolean);

  for (const chunk of fileChunks) {
    const lines = chunk.split("\n");
    let path = "unknown";
    const headerMatch = lines[0].match(/a\/(.+?)\s+b\/(.+)/);
    if (headerMatch) {
      path = headerMatch[2];
    } else {
      const bPathLine = lines.find((l) => l.startsWith("+++ b/"));
      if (bPathLine) path = bPathLine.substring(6);
    }

    files.push({
      path,
      patch: chunk,
    });
  }

  return {
    repo,
    prNumber,
    files,
  };
}

export async function fetchPrDiff(
  review: { repo: string; pr?: number; base?: string; head?: string; rawDiff?: string },
  githubToken?: string
): Promise<FormattedPrDiff> {
  const prNum = review.pr || 0;
  if (review.rawDiff) {
    const formatted = formatPrDiff(review.rawDiff, review.repo, prNum);
    formatted.base = review.base;
    formatted.head = review.head;
    return formatted;
  }

  const headers: Record<string, string> = {
    Accept: "application/vnd.github.v3.diff",
    "User-Agent": "ida-telegram-miniapp",
  };
  if (githubToken) {
    headers.Authorization = `Bearer ${githubToken}`;
  }

  const endpoint = review.pr
    ? `https://api.github.com/repos/${review.repo}/pulls/${review.pr}`
    : `https://api.github.com/repos/${review.repo}/compare/${review.base || "main"}...${review.head || "HEAD"}`;

  try {
    const res = await fetch(endpoint, { headers });
    if (res.ok) {
      const rawDiff = await res.text();
      const formatted = formatPrDiff(rawDiff, review.repo, prNum);
      formatted.base = review.base;
      formatted.head = review.head;
      return formatted;
    }
  } catch {
    // Return empty diff structure if offline
  }

  return {
    repo: review.repo,
    prNumber: prNum,
    base: review.base,
    head: review.head,
    files: [],
  };
}
