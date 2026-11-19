import { serve } from "bun";
import { handleApiRequest, WebContext } from "./routes.js";

export function startWebServer(ctx: WebContext, _appDir?: string) {
  const port = ctx.config.port ?? 8093;

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

      // 1. Internal API routes: /api/app/* (state synchronization & event bridge per AC-5.2)
      if (path.startsWith("/api/app/")) {
        return handleApiRequest(req, ctx);
      }

      // 2. Static Mini App routes: /app/* are decommissioned and retired per §5 of
      // specs/telegram/mini-app-dashboard-integration.md (AC-5.1, AC-5.2).
      // The Overwhelm Dashboard at dash.suzor.com serves all static assets.
      // The agent process binds only internal API routes; all other paths return 404.
      return new Response("Not Found", { status: 404 });
    },
  });
}
