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
    const oldStr = (tool_input.old_string as string) || (tool_input.target_content as string) || "";
    const newStr = (tool_input.new_string as string) || (tool_input.replacement_content as string) || "";

    const oldLines = oldStr.split("\n").map((l) => `-${l}`).join("\n");
    const newLines = newStr.split("\n").map((l) => `+${l}`).join("\n");
    const diff = `--- ${filePath}\n+++ ${filePath}\n${oldLines}\n${newLines}`;

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
    const diff = `--- /dev/null\n+++ ${filePath}\n${newLines}`;

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
