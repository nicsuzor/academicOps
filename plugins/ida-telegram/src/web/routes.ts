import { PluginStore } from "../store.js";
import { QuestionBroker } from "../telegram/questions.js";
import { PermissionRelay } from "../mcp/permissions.js";
import { verifySessionToken, verifyTelegramInitData, createSessionToken } from "./auth.js";
import { fetchPrDiff, FormattedPrDiff } from "./review.js";
import { PluginConfig } from "../config.js";

export interface WebContext {
  store: PluginStore;
  broker: QuestionBroker;
  permRelay?: PermissionRelay;
  config: PluginConfig;
  sessionSecret: string;
  emitChannelEvent: (event: string, content: string, meta: Record<string, unknown>) => void;
  resolvePermissionRelay?: (id: string, decision: "allow" | "deny") => void;
  editTelegramCard?: (chatId: number, messageId: number, text: string) => Promise<void>;
}

export function handleApiRequest(req: Request, ctx: WebContext): Response | Promise<Response> {
  const url = new URL(req.url);
  const path = url.pathname;

  // 1. Auth endpoint: POST /api/app/auth
  if (path === "/api/app/auth" && req.method === "POST") {
    return (async () => {
      try {
        const body = await req.json();
        const initData = body.initData;
        const authRes = verifyTelegramInitData(initData, ctx.config.botToken, ctx.config.allowFrom);

        if (!authRes.valid || !authRes.user) {
          return new Response(JSON.stringify({ error: authRes.reason || "Unauthorized" }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
          });
        }

        const token = createSessionToken(authRes.user.id, ctx.sessionSecret, 3600);
        return new Response(JSON.stringify({ success: true, user: authRes.user }), {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "Set-Cookie": `ida_session=${token}; Path=/; Max-Age=3600; HttpOnly; SameSite=Strict; Secure`,
          },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e) }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
    })();
  }

  // All other /api/app/* routes require valid session cookie
  const cookieHeader = req.headers.get("Cookie") || "";
  const match = cookieHeader.match(/ida_session=([^;]+)/);
  const token = match ? match[1] : null;

  if (!token) {
    return new Response(JSON.stringify({ error: "Missing session token" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const session = verifySessionToken(token, ctx.sessionSecret);
  if (!session.valid) {
    return new Response(JSON.stringify({ error: session.reason || "Invalid session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 2. Details: GET /api/app/details/:id
  if (path.startsWith("/api/app/details/")) {
    const id = path.substring("/api/app/details/".length);
    const details = ctx.store.getDetails(id);
    if (!details) {
      return new Response(JSON.stringify({ error: "Details page not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify(details), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 3. Questions: GET /api/app/questions, POST /api/app/questions/answer
  if (path === "/api/app/questions" && req.method === "GET") {
    const pending = ctx.broker.getPendingQuestions();
    return new Response(JSON.stringify({ questions: pending }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (path === "/api/app/questions/answer" && req.method === "POST") {
    return (async () => {
      try {
        const body = await req.json();
        const { questionId, optionIndex, customText, optionIndices } = body;
        const result = await ctx.broker.resolveAnswer(questionId, optionIndex, customText, optionIndices);
        if (!result) {
          return new Response(JSON.stringify({ error: "Question not found or already answered" }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (ctx.editTelegramCard && result.question.chatId && result.question.messageId) {
          await ctx.editTelegramCard(result.question.chatId, result.question.messageId, result.cardText);
        }
        ctx.emitChannelEvent(
          result.channelEvent.event,
          `Answered: ${result.channelEvent.choice}`,
          result.channelEvent as unknown as Record<string, unknown>
        );
        return new Response(JSON.stringify({ success: true, resolution: result }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e) }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
    })();
  }

  // 4. Anchor: GET /api/app/anchor
  if (path === "/api/app/anchor" && req.method === "GET") {
    const anchor = ctx.store.getAnchor() || {
      focus: "Standing by",
      updatedAt: new Date().toISOString(),
    };
    const pending = ctx.broker.getPendingQuestions();
    const pendingQuestionItems = pending.map((q) => ({
      id: q.id,
      header: q.header,
      question: q.question,
    }));
    const recentTurns = ctx.store.getRecentTurns();
    const uptimeSeconds = ctx.store.getUptimeSeconds();
    return new Response(
      JSON.stringify({
        ...anchor,
        pendingQuestions: pending.length,
        pendingQuestionItems,
        recentTurns,
        uptimeSeconds,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 5. Stop session control: POST /api/app/stop
  if (path === "/api/app/stop" && req.method === "POST") {
    ctx.emitChannelEvent("stop_requested", "Nic asks you to stop and report", {
      priority: "high",
      source: "miniapp",
    });
    return new Response(JSON.stringify({ success: true, message: "Stop event dispatched to Ida" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 6. Review state: GET /api/app/review (pending permissions + PR/branch diffs)
  if (path === "/api/app/review" && req.method === "GET") {
    return (async () => {
      const permissions = (ctx.permRelay ? ctx.permRelay.list() : []).map((p) => ({
        id: p.id,
        toolName: p.toolName,
        createdAt: p.createdAt,
        parsed: p.parsed,
      }));

      const storedReviews = [...ctx.store.getReviews()];
      const qRepo = url.searchParams.get("repo");
      const qPr = url.searchParams.get("pr");
      const qBase = url.searchParams.get("base");
      const qHead = url.searchParams.get("head");
      if (qRepo && (qPr || (qBase && qHead))) {
        const prNum = qPr ? parseInt(qPr, 10) : undefined;
        const alreadyStored = storedReviews.some(
          (r) => r.repo === qRepo && r.pr === prNum && r.base === (qBase || undefined) && r.head === (qHead || undefined)
        );
        if (!alreadyStored) {
          storedReviews.push(
            ctx.store.addReview({
              repo: qRepo,
              pr: prNum,
              base: qBase || undefined,
              head: qHead || undefined,
            })
          );
        }
      }

      const reviews: FormattedPrDiff[] = [];
      for (const rev of storedReviews) {
        const formatted = await fetchPrDiff(rev, ctx.config.githubToken);
        reviews.push(formatted);
      }

      return new Response(JSON.stringify({ permissions, reviews }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    })();
  }

  // 7. Review permission resolution: POST /api/app/review/permission
  if (path === "/api/app/review/permission" && req.method === "POST") {
    return (async () => {
      const body = await req.json();
      const { permId, decision } = body as { permId: string; decision: "allow" | "deny" };
      const perm = ctx.permRelay?.get(permId);

      if (ctx.resolvePermissionRelay) {
        ctx.resolvePermissionRelay(permId, decision);
      } else if (ctx.permRelay) {
        ctx.permRelay.resolve(permId, decision);
      }

      if (ctx.editTelegramCard && perm?.chatId && perm?.messageId) {
        const outcomeText = decision === "allow" ? "Allowed via Mini App ✅" : "Denied via Mini App ❌";
        const baseText = perm.cardText || `Permission request: *${perm.toolName}*`;
        await ctx.editTelegramCard(perm.chatId, perm.messageId, `${baseText}\n\n*${outcomeText}*`);
      }

      return new Response(JSON.stringify({ success: true, decision }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    })();
  }

  // 8. Review PR action: POST /api/app/review/pr
  if (path === "/api/app/review/pr" && req.method === "POST") {
    return (async () => {
      const body = await req.json();
      const { action, repo, pr, critique } = body;
      // Emits review_approve or review_changes to Ida; never touches GitHub directly!
      const eventName = action === "approve" ? "review_approve" : "review_changes";
      ctx.emitChannelEvent(eventName, critique || `PR #${pr} ${action}`, {
        repo,
        pr,
        critique,
        source: "miniapp",
      });
      return new Response(JSON.stringify({ success: true, event: eventName }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    })();
  }

  return new Response(JSON.stringify({ error: "Not found" }), {
    status: 404,
    headers: { "Content-Type": "application/json" },
  });
}
