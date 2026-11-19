import { PluginStore } from "../store.js";
import { randomBytes } from "node:crypto";

export interface TurnExecutionRequest {
  turnId: string;
  chatId: number;
  prompt: string;
  sessionId?: string;
  meta?: Record<string, unknown>;
  isBackgroundContinuation?: boolean;
}

export interface TurnExecutionResult {
  turnId: string;
  chatId: number;
  sessionId?: string;
  output?: string;
  exitCode?: number;
  error?: string;
  status: "completed" | "interrupted" | "failed";
}

export type TurnRunner = (
  request: TurnExecutionRequest,
  signal: AbortSignal
) => Promise<{
  output?: string;
  exitCode?: number;
  error?: string;
  sessionId?: string;
}>;

export interface ActiveTurn {
  turnId: string;
  chatId: number;
  prompt: string;
  sessionId?: string;
  abortController: AbortController;
  startedAt: number;
  promise: Promise<TurnExecutionResult>;
}

export class TurnManager {
  private store: PluginStore;
  private autoInterrupt: boolean;
  private runner: TurnRunner;
  private activeTurns: Map<number, ActiveTurn> = new Map();
  private chatQueues: Map<number, TurnExecutionRequest[]> = new Map();
  private errorListeners: Array<(error: Error | string, context: Record<string, unknown>) => void> = [];

  constructor(options: {
    store: PluginStore;
    autoInterrupt?: boolean;
    runner: TurnRunner;
  }) {
    this.store = options.store;
    this.autoInterrupt = options.autoInterrupt !== false;
    this.runner = options.runner;
  }

  public onError(listener: (error: Error | string, context: Record<string, unknown>) => void) {
    this.errorListeners.push(listener);
    return () => {
      const idx = this.errorListeners.indexOf(listener);
      if (idx !== -1) this.errorListeners.splice(idx, 1);
    };
  }

  private notifyError(error: Error | string, context: Record<string, unknown>) {
    for (const listener of this.errorListeners) {
      try {
        listener(error, context);
      } catch {
        // Ignore listener exceptions
      }
    }
  }

  public getActiveTurn(chatId: number): ActiveTurn | undefined {
    return this.activeTurns.get(chatId);
  }

  public isTurnRunning(chatId: number): boolean {
    return this.activeTurns.has(chatId);
  }

  /**
   * Dispatches an inbound message to the turn runner.
   * - If a turn is running and auto-interrupt is enabled, cancels in-flight turn and
   *   starts a combined replacement turn (AC-1.4).
   * - Supplies the persisted session identifier so context is preserved (AC-1.3).
   * - Surfacing errors verbatim without swallowing or retries (AC-4.3).
   */
  public async dispatchTurn(options: {
    chatId: number;
    prompt: string;
    turnId?: string;
    meta?: Record<string, unknown>;
  }): Promise<TurnExecutionResult> {
    const { chatId, prompt, meta } = options;
    const active = this.activeTurns.get(chatId);

    if (active) {
      if (this.autoInterrupt) {
        // AC-1.4: Cancel the in-flight turn
        active.abortController.abort();
        const combinedPrompt = `${active.prompt}\n\n${prompt}`;
        const existingSessionId = active.sessionId || this.store.getSession(chatId);

        // Start replacement turn with combined prompt
        return this.executeTurnInternal({
          turnId: options.turnId || `turn_${randomBytes(4).toString("hex")}`,
          chatId,
          prompt: combinedPrompt,
          sessionId: existingSessionId,
          meta,
        });
      } else {
        // Enqueue if auto-interrupt is disabled
        const queuedRequest: TurnExecutionRequest = {
          turnId: options.turnId || `turn_${randomBytes(4).toString("hex")}`,
          chatId,
          prompt,
          sessionId: this.store.getSession(chatId),
          meta,
        };
        const queue = this.chatQueues.get(chatId) || [];
        queue.push(queuedRequest);
        this.chatQueues.set(chatId, queue);
        return {
          turnId: queuedRequest.turnId,
          chatId,
          status: "completed",
          output: "queued",
        };
      }
    }

    // AC-1.3: Resume existing session mapping for chat across turns and container restarts
    const sessionId = this.store.getSession(chatId);

    return this.executeTurnInternal({
      turnId: options.turnId || `turn_${randomBytes(4).toString("hex")}`,
      chatId,
      prompt,
      sessionId,
      meta,
    });
  }

  /**
   * AC-4.1: When background work completes with an undelivered result,
   * starts a continuation turn on the same conversation.
   */
  public async onBackgroundWorkCompleted(options: {
    chatId: number;
    result: string;
    taskId?: string;
  }): Promise<TurnExecutionResult> {
    const { chatId, result, taskId } = options;
    const sessionId = this.store.getSession(chatId);

    const continuationPrompt = taskId
      ? `Background task ${taskId} completed:\n\n${result}`
      : `Background task completed:\n\n${result}`;

    return this.dispatchTurn({
      chatId,
      prompt: continuationPrompt,
      meta: {
        background_continuation: "true",
        ...(taskId ? { task_id: taskId } : {}),
      },
    });
  }

  private async executeTurnInternal(
    request: TurnExecutionRequest
  ): Promise<TurnExecutionResult> {
    const { chatId, turnId, prompt, sessionId, meta } = request;
    const abortController = new AbortController();

    const turnPromise = (async (): Promise<TurnExecutionResult> => {
      try {
        const runRes = await this.runner(request, abortController.signal);

        // AC-4.3: Strict failure propagation on non-zero exit or runner error
        if (runRes.exitCode !== undefined && runRes.exitCode !== 0) {
          const errMsg = runRes.error || runRes.output || `Process exited with code ${runRes.exitCode}`;
          this.notifyError(errMsg, {
            turnId,
            chatId,
            exitCode: runRes.exitCode,
            sessionId,
          });
          return {
            turnId,
            chatId,
            sessionId,
            exitCode: runRes.exitCode,
            error: errMsg,
            status: "failed",
          };
        }

        if (runRes.error) {
          this.notifyError(runRes.error, { turnId, chatId, sessionId });
          return {
            turnId,
            chatId,
            sessionId,
            error: runRes.error,
            status: "failed",
          };
        }

        // Persist session if updated
        const effectiveSessionId = runRes.sessionId || sessionId;
        if (effectiveSessionId) {
          this.store.setSession(chatId, effectiveSessionId);
        }

        return {
          turnId,
          chatId,
          sessionId: effectiveSessionId,
          output: runRes.output,
          exitCode: 0,
          status: "completed",
        };
      } catch (err: any) {
        if (abortController.signal.aborted) {
          return {
            turnId,
            chatId,
            sessionId,
            status: "interrupted",
            output: "Turn interrupted by user follow-up",
          };
        }

        // AC-4.3: Halt immediately and surface verbatim error
        const errMsg = err instanceof Error ? err.message : String(err);
        this.notifyError(errMsg, { turnId, chatId, sessionId });
        return {
          turnId,
          chatId,
          sessionId,
          error: errMsg,
          status: "failed",
        };
      } finally {
        if (this.activeTurns.get(chatId)?.turnId === turnId) {
          this.activeTurns.delete(chatId);
          this.processNextQueuedTurn(chatId);
        }
      }
    })();

    const activeTurn: ActiveTurn = {
      turnId,
      chatId,
      prompt,
      sessionId,
      abortController,
      startedAt: Date.now(),
      promise: turnPromise,
    };

    this.activeTurns.set(chatId, activeTurn);
    return turnPromise;
  }

  private processNextQueuedTurn(chatId: number) {
    const queue = this.chatQueues.get(chatId);
    if (!queue || queue.length === 0) return;

    const nextReq = queue.shift();
    if (nextReq) {
      this.executeTurnInternal(nextReq).catch((err) => {
        console.error(`[TurnManager] Error running queued turn for chat ${chatId}:`, err);
      });
    }
  }
}
