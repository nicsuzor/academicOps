import { afterAll, beforeAll, describe, expect, test } from "bun:test";
import { join } from "node:path";
import { startWebServer } from "../src/web/server.js";

describe("Mini App static server confinement", () => {
  let server: ReturnType<typeof startWebServer>;
  let base = "";

  beforeAll(() => {
    // Static routes never touch the context; only config.port is read.
    server = startWebServer({ config: { port: 0 } } as any, join(import.meta.dir, "..", "app"));
    base = `http://127.0.0.1:${server.port}`;
  });

  afterAll(() => server.stop(true));

  const status = async (p: string) => (await fetch(base + p)).status;

  test("traversal via /app.. prefix is refused", async () => {
    expect(await status("/app../server.ts")).toBe(404);
    expect(await status("/app../src/config.ts")).toBe(404);
    expect(await status("/app/../server.ts")).toBe(404);
    expect(await status("/app/%2e%2e/server.ts")).toBe(404);
  });

  test("sibling-prefix paths are not served", async () => {
    expect(await status("/appx/index.html")).toBe(404);
  });

  test("directories are 404, not errors", async () => {
    expect(await status("/app/sub/")).toBe(404);
  });

  test("legitimate assets are served", async () => {
    expect(await status("/app")).toBe(200);
    expect(await status("/app/")).toBe(200);
    expect(await status("/app/index.html")).toBe(200);
    expect(await status("/app/app.js")).toBe(200);
  });
});
