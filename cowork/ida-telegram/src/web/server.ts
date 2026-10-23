import { serve } from "bun";
import { handleApiRequest, WebContext } from "./routes.js";
import { join, resolve, sep } from "node:path";
import { readFileSync, realpathSync, statSync } from "node:fs";

export function startWebServer(ctx: WebContext, appDir: string) {
  const port = ctx.config.port ?? 8093;
  const root = realpathSync(appDir); // resolve once; symlinks inside must not escape it

  return serve({
    port,
    development: false, // never serve Bun's debug error page (leaks paths/source)
    error(err) {
      console.error("[ida-telegram] web server error:", err);
      return new Response("Internal Server Error", { status: 500 });
    },
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

        // Confine to appDir: reject traversal (e.g. "/app../x"), symlink escapes and non-files.
        try {
          const filePath = realpathSync(resolve(join(root, subPath)));
          if (filePath.startsWith(root + sep) && statSync(filePath).isFile()) {
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
        } catch {
          // ENOENT / ENOTDIR / ENAMETOOLONG / ELOOP etc: fall through to 404
        }
      }

      // 3. Any other path returns 404 (Hook bridge and local internals NOT exposed on HTTP)
      return new Response("Not Found", { status: 404 });
    },
  });
}
