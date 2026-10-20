import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { resolveBotCommands, type TelegramBotCommand } from "./telegram/commands.js";

export const DEFAULT_MINI_APP_URL = "https://ida.suzor.com";

export interface PluginConfig {
  botToken: string;
  apiBaseUrl: string;
  role: string;
  isPrimary: boolean;
  persona: string;
  allowFrom: number[];
  maxChatChars: number;
  voiceReplies: "off" | "mirror" | "always";
  voiceTranscribeCmd: string;
  voiceSpeakCmd: string;
  port: number;
  stateDir: string;
  socketPath: string;
  githubToken?: string;
  miniAppUrl: string;
  botCommands: TelegramBotCommand[];
  bridgeToken?: string;
  env?: Record<string, string>;
}

function readDotEnvFile(envPath: string): Record<string, string> {
  if (!existsSync(envPath)) return {};
  try {
    const content = readFileSync(envPath, "utf-8");
    const parsed: Record<string, string> = {};
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim();
      if (!line || line.startsWith("#")) continue;
      const cleaned = line.startsWith("export ") ? line.slice(7).trim() : line;
      const eqIdx = cleaned.indexOf("=");
      if (eqIdx <= 0) continue;
      const key = cleaned.slice(0, eqIdx).trim();
      let val = cleaned.slice(eqIdx + 1).trim();
      if (
        (val.startsWith('"') && val.endsWith('"')) ||
        (val.startsWith("'") && val.endsWith("'"))
      ) {
        val = val.slice(1, -1);
      }
      parsed[key] = val;
    }
    return parsed;
  } catch {
    return {};
  }
}

export function resolvePersona(rawPersona?: string, stateDir?: string): string {
  const explicit = (rawPersona || "").trim().toLowerCase();
  if (explicit) {
    if (explicit === "pauli" || explicit === "prime") return "prime";
    if (explicit === "ida" || explicit === "strategic") return "strategic";
    return explicit;
  }
  if (stateDir) {
    const dir = stateDir.toLowerCase();
    if (dir.includes("telegram-pauli") || dir.includes("telegram-prime") || dir.endsWith("/prime")) {
      return "prime";
    }
    if (dir.includes("telegram-ida") || dir.includes("telegram-strategic") || dir.endsWith("/strategic")) {
      return "strategic";
    }
  }
  return "prime";
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): PluginConfig {
  const stateDir = env.STATE_DIR || join(homedir(), ".claude", "channels", "telegram");
  const fileEnv = readDotEnvFile(join(stateDir, ".env"));
  const mergedEnv: NodeJS.ProcessEnv = { ...fileEnv, ...env };

  const role = (mergedEnv.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  const isPrimary = role === "primary";

  const rawPersona = mergedEnv.IDA_TELEGRAM_PERSONA || mergedEnv.TELEGRAM_PERSONA || "";
  const persona = resolvePersona(rawPersona, stateDir);

  // Parse allowFrom as comma-separated or space-separated user IDs
  const rawAllowFrom = mergedEnv.ALLOWED_USER_IDS || mergedEnv.TELEGRAM_ALLOW_FROM || "";
  const allowFrom = rawAllowFrom
    .split(/[\s,]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));

  const socketPath = mergedEnv.SOCKET_PATH || join(stateDir, "bridge.sock");
  const rawMiniAppUrl = (mergedEnv.MINI_APP_URL || mergedEnv.IDA_WEB_URL || DEFAULT_MINI_APP_URL).trim();
  const miniAppUrl = (rawMiniAppUrl || DEFAULT_MINI_APP_URL).replace(/\/+$/, "");

  const defaultTranscribeCmd = join(homedir(), ".claude", "channels", "telegram", "transcribe.sh");
  const voiceTranscribeCmd = mergedEnv.VOICE_TRANSCRIBE_CMD || defaultTranscribeCmd;

  const defaultSpeakCmd = join(import.meta.dir, "..", "scripts", "speak.sh");
  const voiceSpeakCmd = mergedEnv.VOICE_SPEAK_CMD || defaultSpeakCmd;

  return {
    botToken: mergedEnv.TELEGRAM_BOT_TOKEN || "",
    apiBaseUrl: (mergedEnv.TELEGRAM_API_BASE_URL || "https://api.telegram.org").replace(/\/+$/, ""),
    role,
    isPrimary,
    persona,
    allowFrom,
    maxChatChars: parseInt(mergedEnv.MAX_CHAT_CHARS || "1200", 10),
    voiceReplies: (mergedEnv.VOICE_REPLIES as "off" | "mirror" | "always") || "mirror",
    voiceTranscribeCmd,
    voiceSpeakCmd,
    port: parseInt(mergedEnv.PORT || "8093", 10),
    stateDir,
    socketPath,
    githubToken: mergedEnv.GITHUB_TOKEN,
    miniAppUrl,
    botCommands: resolveBotCommands(persona, mergedEnv.TELEGRAM_BOT_COMMANDS),
    bridgeToken: mergedEnv.IDA_BRIDGE_TOKEN || mergedEnv.BRIDGE_TOKEN,
    env: mergedEnv as Record<string, string>,
  };
}

