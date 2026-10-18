import { serve } from "bun";
import { handleApiRequest, WebContext } from "./routes.js";
import { join, resolve, sep } from "node:path";
import { readFileSync, statSync } from "node:fs";

export function startWebServer(ctx: WebContext, appDir: string) {
  const port = ctx.config.port || 8093;

  return serve({
    port,
    hostname: "127.0.0.1", // Loopback only per FR-4.1
    async fetch(req) {
      const url = new URL(req.url);
      const path = url.pathname;

      // 1. API routes: /api/app/*
      if (path.startsWith("/api/app/")) {
        return handleApiRequest(req, ctx);
      }

      // 2. Static Mini App routes: /app/*
      if (path === "/app" || path.startsWith("/app/")) {
        let subPath = path.substring("/app".length);
        if (subPath === "" || subPath === "/") {
          subPath = "/index.html";
        }

        // Confine to appDir: reject traversal (e.g. "/app../x") and non-files.
        const root = resolve(appDir);
        const filePath = resolve(join(root, subPath));
        if (filePath.startsWith(root + sep) && statSync(filePath, { throwIfNoEntry: false })?.isFile()) {
          const content = readFileSync(filePath);
          let contentType = "text/plain";
          if (filePath.endsWith(".html")) contentType = "text/html; charset=utf-8";
          else if (filePath.endsWith(".css")) contentType = "text/css; charset=utf-8";
          else if (filePath.endsWith(".js")) contentType = "application/javascript; charset=utf-8";
          else if (filePath.endsWith(".json")) contentType = "application/json; charset=utf-8";

          return new Response(content, {
            status: 200,
            headers: {
              "Content-Type": contentType,
              "X-Content-Type-Options": "nosniff",
            },
          });
        }
      }

      // 3. Any other path returns 404 (Hook bridge and local internals NOT exposed on HTTP)
      return new Response("Not Found", { status: 404 });
    },
  });
}
