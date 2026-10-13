import { describe, expect, test } from "bun:test";
import { parsePermissionRequest, formatPrDiff, type PermissionRequest } from "../src/web/review.js";

describe("Review: Permission diffs and PR reviews", () => {
  test("parses Edit tool permission request into unified diff", () => {
    const perm: PermissionRequest = {
      id: "perm_1",
      tool_name: "Edit",
      tool_input: {
        file_path: "/workspace/src/example.ts",
        old_string: "const x = 1;\nconsole.log(x);",
        new_string: "const x = 2;\nconsole.log(x * 2);",
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.type).toBe("diff");
    expect(parsed.filePath).toBe("/workspace/src/example.ts");
    expect(parsed.diff).toContain("-const x = 1;");
    expect(parsed.diff).toContain("+const x = 2;");
  });

  test("parses Write tool permission request", () => {
    const perm: PermissionRequest = {
      id: "perm_2",
      tool_name: "Write",
      tool_input: {
        file_path: "/workspace/config.json",
        content: '{\n  "mode": "production"\n}',
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.filePath).toBe("/workspace/config.json");
    expect(parsed.diff).toContain("+{\n+  \"mode\": \"production\"\n+}");
  });

  test("parses Bash tool permission request into monospace script", () => {
    const perm: PermissionRequest = {
      id: "perm_3",
      tool_name: "Bash",
      tool_input: {
        command: "bun run build && bun test",
      },
    };

    const parsed = parsePermissionRequest(perm);
    expect(parsed.type).toBe("script");
    expect(parsed.script).toBe("bun run build && bun test");
  });

  test("formats PR diff without writing to GitHub directly", () => {
    const rawDiff = `diff --git a/file.ts b/file.ts
--- a/file.ts
+++ b/file.ts
@@ -1,3 +1,3 @@
-oldLine
+newLine`;

    const formatted = formatPrDiff(rawDiff, "owner/repo", 42);
    expect(formatted.repo).toBe("owner/repo");
    expect(formatted.prNumber).toBe(42);
    expect(formatted.files.length).toBe(1);
    expect(formatted.files[0].path).toBe("file.ts");
  });
});
