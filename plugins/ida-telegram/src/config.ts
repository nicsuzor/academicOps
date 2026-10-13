import { join } from "node:path";
import { homedir } from "node:os";
import { resolveBotCommands, type TelegramBotCommand } from "./telegram/commands.js";

export interface PluginConfig {
  botToken: string;
  role: string;
  isPrimary: boolean;
  allowFrom: number[];
  maxChatChars: number;
  voiceReplies: "off" | "mirror" | "always";
  voiceTranscribeCmd: string;
  voiceSpeakCmd: string;
  port: number;
  stateDir: string;
  socketPath: string;
  githubToken?: string;
  miniAppUrl?: string;
  botCommands: TelegramBotCommand[];
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): PluginConfig {
  const role = (env.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  const isPrimary = role === "primary";

  // Parse allowFrom as comma-separated or space-separated user IDs
  const rawAllowFrom = env.ALLOWED_USER_IDS || env.TELEGRAM_ALLOW_FROM || "";
  const allowFrom = rawAllowFrom
    .split(/[\s,]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));

  const stateDir = env.STATE_DIR || join(homedir(), ".claude", "channels", "telegram");
  const socketPath = env.SOCKET_PATH || join(stateDir, "bridge.sock");

  return {
    botToken: env.TELEGRAM_BOT_TOKEN || "",
    role,
    isPrimary,
    allowFrom,
    maxChatChars: parseInt(env.MAX_CHAT_CHARS || "1200", 10),
    voiceReplies: (env.VOICE_REPLIES as "off" | "mirror" | "always") || "mirror",
    voiceTranscribeCmd: env.VOICE_TRANSCRIBE_CMD || join(homedir(), ".claude", "channels", "telegram", "transcribe.sh"),
    voiceSpeakCmd: env.VOICE_SPEAK_CMD || join(homedir(), ".claude", "channels", "telegram", "speak.sh"),
    port: parseInt(env.PORT || "8093", 10),
    stateDir,
    socketPath,
    githubToken: env.GITHUB_TOKEN,
    miniAppUrl: env.MINI_APP_URL,
    botCommands: resolveBotCommands(env.TELEGRAM_BOT_COMMANDS),
  };
}
