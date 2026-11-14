#!/usr/bin/env bun
import { loadConfig, PluginConfig } from "./config.js";
import { PluginStore } from "./store.js";
import { QuestionBroker } from "./telegram/questions.js";
import { PermissionRelay } from "./mcp/permissions.js";
import { TelegramBotClient } from "./telegram/bot.js";
import { SharedTelegramChannelCore } from "./core/channel-core.js";
import { TurnManager, TurnRunner } from "./core/turn-manager.js";
import { createServer, Server as NetServer } from "node:net";
import { existsSync, unlinkSync, chmodSync } from "node:fs";
import { spawn } from "node:child_process";

export interface GatewayOptions {
  config?: PluginConfig;
  runner?: TurnRunner;
}

export class ContainerGateway {
  public config: PluginConfig;
  public store: PluginStore;
  public broker: QuestionBroker;
  public permRelay: PermissionRelay;
  public bot: TelegramBotClient | null = null;
  public channelCore: SharedTelegramChannelCore;
  public turnManager: TurnManager;
  private socketServer: NetServer | null = null;

  constructor(options: GatewayOptions = {}) {
    this.config = options.config || loadConfig(process.env);
    this.store = new PluginStore(this.config.stateDir);
    this.broker = new QuestionBroker(this.config.stateDir);
    this.permRelay = new PermissionRelay(this.config.stateDir);

    const defaultRunner: TurnRunner = async (req, signal) => {
      // Default container turn runner: spawn agent CLI process
      return new Promise((resolve) => {
        const cmd = process.env.IDA_AGENT_CMD || "agy";
        const args: string[] = ["--agent", "ida", "--print", req.prompt];

        if (req.sessionId) {
          args.push("--conversation", req.sessionId);
        }

        const proc = spawn(cmd, args, {
          env: {
            ...process.env,
            AOPS_AGENT_NAME: process.env.AOPS_AGENT_NAME || "ida",
            TELEGRAM_CHAT_ID: String(req.chatId),
            TELEGRAM_TURN_ID: req.turnId,
            SOCKET_PATH: this.config.socketPath,
          },
        });

        let stdout = "";
        let stderr = "";

        proc.stdout?.on("data", (d) => {
          stdout += d.toString();
        });
        proc.stderr?.on("data", (d) => {
          stderr += d.toString();
        });

        signal.addEventListener("abort", () => {
          proc.kill("SIGTERM");
        });

        proc.on("close", (code) => {
          resolve({
            output: stdout,
            exitCode: code ?? 0,
            error: code !== 0 ? stderr || `Process failed with exit code ${code}` : undefined,
          });
        });

        proc.on("error", (err) => {
          resolve({
            error: err.message,
            exitCode: 1,
          });
        });
      });
    };

    this.turnManager = new TurnManager({
      store: this.store,
      autoInterrupt: this.config.autoInterrupt,
      runner: options.runner || defaultRunner,
    });

    this.channelCore = new SharedTelegramChannelCore({
      config: this.config,
      store: this.store,
      broker: this.broker,
      bot: null,
      permRelay: this.permRelay,
      turnManager: this.turnManager,
    });

    if (this.config.botToken) {
      this.bot = new TelegramBotClient(
        this.config,
        this.broker,
        this.permRelay,
        (content, meta) => {
          const chatId = meta?.chat_id ? parseInt(String(meta.chat_id), 10) : this.channelCore.getDefaultChatId();
          this.turnManager.dispatchTurn({
            chatId,
            prompt: content,
            meta,
          });
        },
        this.store
      );
      this.channelCore.bot = this.bot;
    }
  }

  public async start(): Promise<void> {
    if (!this.config.isPrimary) {
      console.log("[ida-telegram-gateway] Non-primary instance: poller and gateway disabled.");
      return;
    }

    // Start local IPC socket server
    if (existsSync(this.config.socketPath)) {
      try {
        unlinkSync(this.config.socketPath);
      } catch {
        // Ignore
      }
    }

    this.socketServer = createServer((client) => {
      let raw = "";
      client.on("data", async (chunk) => {
        raw += chunk.toString();
        let newlineIdx = raw.indexOf("\n");
        while (newlineIdx !== -1) {
          const line = raw.substring(0, newlineIdx).trim();
          raw = raw.substring(newlineIdx + 1);

          if (line) {
            try {
              const req = JSON.parse(line);
              const resp = await this.channelCore.handleIpcMessage(req);
              client.write(JSON.stringify(resp) + "\n");
            } catch (err: any) {
              client.write(JSON.stringify({ error: err.message || String(err) }) + "\n");
            }
          }
          newlineIdx = raw.indexOf("\n");
        }
      });
    });

    await new Promise<void>((resolve, reject) => {
      this.socketServer!.listen(this.config.socketPath, () => {
        try {
          chmodSync(this.config.socketPath, 0o600);
        } catch {
          // Ignore
        }
        resolve();
      });
      this.socketServer!.on("error", reject);
    });

    console.log(`[ida-telegram-gateway] IPC bridge listening on ${this.config.socketPath}`);

    // Start Telegram Poller
    if (this.bot) {
      this.bot.startPolling().catch((err) => {
        console.error("[ida-telegram-gateway] Polling error:", err);
      });
    }
  }

  public stop(): void {
    if (this.bot) {
      this.bot.stopPolling();
    }
    if (this.socketServer) {
      this.socketServer.close();
      if (existsSync(this.config.socketPath)) {
        try {
          unlinkSync(this.config.socketPath);
        } catch {
          // Ignore
        }
      }
    }
  }
}

if (import.meta.main) {
  const gateway = new ContainerGateway();
  gateway.start().catch((err) => {
    console.error("[ida-telegram-gateway] Fatal error:", err);
    process.exit(1);
  });

  const cleanup = () => {
    gateway.stop();
    process.exit(0);
  };

  process.on("SIGINT", cleanup);
  process.on("SIGTERM", cleanup);
}
