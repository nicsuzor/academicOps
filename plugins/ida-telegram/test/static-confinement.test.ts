import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { startWebServer } from "../src/web/server.js";

describe("Mini App static server confinement", () => {
  let server: ReturnType<typeof startWebServer>;
  let base = "";
  let tmp = "";
  let appDir = "";

  beforeAll(() => {
    tmp = mkdtempSync(join(tmpdir(), "ida-tg-static-"));
    appDir = join(tmp, "app");
    mkdirSync(join(appDir, "sub"), { recursive: true });
    writeFileSync(join(appDir, "index.html"), "<html>ok</html>");
    writeFileSync(join(appDir, "app.js"), "// ok");
    writeFileSync(join(tmp, "secret.txt"), "SECRET");
    symlinkSync(join(tmp, "secret.txt"), join(appDir, "escape.txt"));
    symlinkSync(join(appDir, "loop-b"), join(appDir, "loop-a"));
    symlinkSync(join(appDir, "loop-a"), join(appDir, "loop-b"));
    // Static routes never touch the context; only config.port is read.
    server = startWebServer({ config: { port: 0 } } as any, appDir);
    base = `http://127.0.0.1:${server.port}`;
  });

  afterAll(() => {
    server.stop(true);
    rmSync(tmp, { recursive: true, force: true });
  });

  async function expect404(p: string) {
    const res = await fetch(base + p);
    const body = await res.text();
    expect(res.status).toBe(404);
    expect(body).not.toContain(appDir);
    expect(body).not.toContain("SECRET");
  }

  test("traversal via /app.. prefix is refused", async () => {
    await expect404("/app../secret.txt");
    await expect404("/app/../secret.txt");
    await expect404("/app/%2e%2e/secret.txt");
  });

  test("sibling-prefix paths are not served", async () => {
    await expect404("/appx/index.html");
  });

  test("existing directory is 404", async () => {
    await expect404("/app/sub");
    await expect404("/app/sub/");
  });

  test("stat errors are 404, not 500", async () => {
    await expect404("/app/index.html/x"); // ENOTDIR
    await expect404("/app/" + "a".repeat(5000)); // ENAMETOOLONG
    await expect404("/app/loop-a"); // ELOOP
  });

  test("symlink pointing outside app dir is refused", async () => {
    await expect404("/app/escape.txt");
  });

  test("legitimate assets are served", async () => {
    for (const p of ["/app", "/app/", "/app/index.html", "/app/app.js"]) {
      expect((await fetch(base + p)).status).toBe(200);
    }
  });
});
