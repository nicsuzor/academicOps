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
  editTelegramCard?: (chatId: number, messageId: number, text: string, replyMarkup?: Record<string, unknown>) => Promise<void>;
  bot?: any;
}

interface SseClient {
  controller: ReadableStreamDefaultController;
}

const sseClients = new Set<SseClient>();
const sseBuffer: Array<{ seq: number; event: string; data: any }> = [];

export function broadcastSseEvent(event: string, data: any, seq: number) {
  const payload = { ...data, seq };
  sseBuffer.push({ seq, event, data: payload });
  if (sseBuffer.length > 200) {
    sseBuffer.shift();
  }
  const text = `id: ${seq}\nevent: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
  const encoded = new TextEncoder().encode(text);
  for (const client of sseClients) {
    try {
      client.controller.enqueue(encoded);
    } catch {
      sseClients.delete(client);
    }
  }
}

function authenticateRequest(req: Request, ctx: WebContext): boolean {
  // Mode A: Cookie ida_session
  const cookieHeader = req.headers.get("Cookie") || "";
  const match = cookieHeader.match(/ida_session=([^;]+)/);
  if (match) {
    const session = verifySessionToken(match[1], ctx.sessionSecret);
    if (session.valid) return true;
  }

  // Mode B: Bearer token or X-Bridge-Token
  const authHeader = req.headers.get("Authorization") || "";
  const bridgeTokenHeader = req.headers.get("X-Bridge-Token") || "";
  const token = authHeader.startsWith("Bearer ")
    ? authHeader.slice(7).trim()
    : bridgeTokenHeader.trim();

  if (token) {
    if (ctx.config.bridgeToken && token === ctx.config.bridgeToken) return true;
    if (token === ctx.sessionSecret) return true;
    const session = verifySessionToken(token, ctx.sessionSecret);
    if (session.valid) return true;
  }

  // Mode B: Perimeter identity assertion header
  const cfHeader = req.headers.get("Cf-Access-Jwt-Assertion");
  if (cfHeader && cfHeader.trim().length > 0) {
    return true;
  }

  return false;
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

  // All other /api/app/* routes require valid session cookie or perimeter/bridge credentials
  if (!authenticateRequest(req, ctx)) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // 2. Reactive Event Stream: GET /api/app/events
  if (path === "/api/app/events" && req.method === "GET") {
    const sinceHeader = req.headers.get("Last-Event-ID");
    const sinceParam = url.searchParams.get("since");
    const sinceSeq = sinceHeader ? parseInt(sinceHeader, 10) : sinceParam ? parseInt(sinceParam, 10) : 0;

    let heartbeatTimer: any = null;
    let clientObj: SseClient;

    const stream = new ReadableStream({
      start(controller) {
        clientObj = { controller };
        sseClients.add(clientObj);

        // Immediate connection frame
        const currentSeq = ctx.store.getSeq();
        controller.enqueue(
          new TextEncoder().encode(
            `id: ${currentSeq}\nevent: connect\ndata: ${JSON.stringify({ seq: currentSeq, status: "connected" })}\n\n`
          )
        );

        // Replay missed buffered events if client provided Last-Event-ID / since
        if (sinceSeq > 0) {
          for (const item of sseBuffer) {
            if (item.seq > sinceSeq) {
              const text = `id: ${item.seq}\nevent: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`;
              controller.enqueue(new TextEncoder().encode(text));
            }
          }
        }

        // Heartbeat comment every 15 seconds per spec
        heartbeatTimer = setInterval(() => {
          try {
            controller.enqueue(new TextEncoder().encode(": keepalive\n\n"));
          } catch {
            clearInterval(heartbeatTimer);
            sseClients.delete(clientObj);
          }
        }, 15000);
      },
      cancel() {
        if (heartbeatTimer) clearInterval(heartbeatTimer);
        if (clientObj) sseClients.delete(clientObj);
      },
    });

    return new Response(stream, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  }

  // 3. Freeform Direct Messaging: POST /api/app/message
  if (path === "/api/app/message" && req.method === "POST") {
    return (async () => {
      try {
        const body = await req.json();
        const { text, priority, chat_id, message_id } = body;
        if (!text) {
          return new Response(JSON.stringify({ error: "Missing text parameter" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        const msgId = `msg_${Date.now()}`;
        ctx.emitChannelEvent("message", text, {
          priority: priority || "normal",
          message_id: msgId,
          source: "dashboard",
        });
        ctx.store.recordTurn("in", text);

        if (ctx.editTelegramCard) {
          if (chat_id && message_id) {
            await ctx.editTelegramCard(chat_id, message_id, text, { inline_keyboard: [] });
          } else {
            const lastCard = ctx.store.getLastCard();
            if (lastCard) {
              await ctx.editTelegramCard(
                lastCard.chatId,
                lastCard.messageId,
                `${lastCard.text}\n\n*Dashboard directive: ${text}*`,
                { inline_keyboard: [] }
              );
            }
          }
        }

        const seq = ctx.store.getSeq();
        broadcastSseEvent("turn_recorded", { direction: "in", text }, seq);

        return new Response(
          JSON.stringify({ success: true, message_id: msgId, seq }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e) }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
    })();
  }

  // 4. Details: GET /api/app/details/:id
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

  // 5. Questions: GET /api/app/questions, POST /api/app/questions/answer
  if (path === "/api/app/questions" && req.method === "GET") {
    const pending = ctx.broker.getPendingQuestions();
    const seq = ctx.store.getSeq();
    return new Response(JSON.stringify({ questions: pending, seq }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (path === "/api/app/questions/answer" && req.method === "POST") {
    return (async () => {
      try {
        const body = await req.json();
        const questionId = body.question_id || body.questionId;
        const optionIndex = body.option_index !== undefined ? body.option_index : body.optionIndex;
        const optionIndices = body.option_indices || body.optionIndices;
        const customText = body.custom_text !== undefined ? body.custom_text : body.customText;

        const result = await ctx.broker.resolveAnswer(questionId, optionIndex, customText, optionIndices);
        if (!result) {
          return new Response(JSON.stringify({ error: "Question not found or already answered" }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (ctx.editTelegramCard && result.question.chatId && result.question.messageId) {
          await ctx.editTelegramCard(result.question.chatId, result.question.messageId, result.cardText, { inline_keyboard: [] });
        }
        ctx.emitChannelEvent(
          result.channelEvent.event,
          `Answered: ${result.channelEvent.choice}`,
          result.channelEvent as unknown as Record<string, unknown>
        );

        const seq = ctx.store.nextSeq("question_resolved", {
          question_id: questionId,
          choice: result.channelEvent.choice,
          turn_id: result.channelEvent.turn_id,
        });
        broadcastSseEvent("question_resolved", {
          question_id: questionId,
          choice: result.channelEvent.choice,
          turn_id: result.channelEvent.turn_id,
        }, seq);

        return new Response(JSON.stringify({ success: true, resolved_at: new Date().toISOString(), resolution: result, seq }), {
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

  // 6. Anchor: GET /api/app/anchor
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
    const seq = ctx.store.getSeq();
    return new Response(
      JSON.stringify({
        ...anchor,
        pendingQuestions: pending.length,
        pendingQuestionItems,
        recentTurns,
        uptimeSeconds,
        seq,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  }

  // 7. Stop session control: POST /api/app/stop
  if (path === "/api/app/stop" && req.method === "POST") {
    return (async () => {
      try {
        let reason = "Nic asks you to stop and report";
        let chatId: number | undefined;
        let messageId: number | undefined;

        try {
          const body = await req.json();
          if (body?.reason) reason = body.reason;
          if (body?.chat_id) chatId = body.chat_id;
          if (body?.message_id) messageId = body.message_id;
        } catch {
          // Empty or non-json body allowed
        }

        ctx.emitChannelEvent("stop_requested", reason, {
          priority: "high",
          reason,
          source: "dashboard",
        });

        if (ctx.editTelegramCard) {
          if (chatId && messageId) {
            await ctx.editTelegramCard(
              chatId,
              messageId,
              `*Halted via Dashboard 🛑*${reason ? `\nReason: ${reason}` : ""}`,
              { inline_keyboard: [] }
            );
          } else {
            const lastCard = ctx.store.getLastCard();
            if (lastCard) {
              await ctx.editTelegramCard(
                lastCard.chatId,
                lastCard.messageId,
                `${lastCard.text}\n\n*Halted via Dashboard 🛑*`,
                { inline_keyboard: [] }
              );
            }
          }
        }

        const seq = ctx.store.nextSeq("stop_requested", { reason });
        return new Response(
          JSON.stringify({ success: true, status: "stop_dispatched", message: "Stop event dispatched to Ida", seq }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      } catch (e) {
        return new Response(JSON.stringify({ error: String(e) }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        });
      }
    })();
  }

  // 8. Review state: GET /api/app/review (pending permissions + PR/branch diffs)
  if (path === "/api/app/review" && req.method === "GET") {
    return (async () => {
      const permissions = (ctx.permRelay ? ctx.permRelay.list() : []).map((p) => ({
        id: p.id,
        toolName: p.toolName,
        createdAt: p.createdAt,
        parsed: p.parsed,
        status: p.status || "pending",
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

      const seq = ctx.store.getSeq();
      return new Response(JSON.stringify({ permissions, reviews, seq }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    })();
  }

  // 9. Review permission resolution: POST /api/app/review/permission
  if (path === "/api/app/review/permission" && req.method === "POST") {
    return (async () => {
      try {
        const body = await req.json();
        const permId = body.permission_id || body.permId;
        const decision = body.decision as "allow" | "deny";
        const perm = ctx.permRelay?.get(permId);

        if (ctx.resolvePermissionRelay) {
          ctx.resolvePermissionRelay(permId, decision);
        } else if (ctx.permRelay) {
          ctx.permRelay.resolve(permId, decision);
        }

        if (ctx.editTelegramCard && perm?.chatId && perm?.messageId) {
          const isMiniApp =
            (req.headers.get("Cookie") || "").includes("ida_session") &&
            !req.headers.get("Authorization") &&
            !req.headers.get("X-Bridge-Token");
          const via = isMiniApp ? "Mini App" : "Dashboard";
          const outcomeText = decision === "allow" ? `Allowed via ${via} ✅` : `Denied via ${via} ❌`;
          const baseText = perm.cardText || `Permission request: *${perm.toolName}*`;
          await ctx.editTelegramCard(perm.chatId, perm.messageId, `${baseText}\n\n*${outcomeText}*`, { inline_keyboard: [] });
        }

        const seq = ctx.store.nextSeq("permission_resolved", {
          permission_id: permId,
          outcome: decision,
          decision,
        });
        broadcastSseEvent("permission_resolved", {
          permission_id: permId,
          outcome: decision,
          decision,
        }, seq);

        return new Response(JSON.stringify({ success: true, decision, seq }), {
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

  // 10. Review PR action: POST /api/app/review/pr
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
      const seq = ctx.store.nextSeq("pr_review", { action, repo, pr });
      return new Response(JSON.stringify({ success: true, event: eventName, seq }), {
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
