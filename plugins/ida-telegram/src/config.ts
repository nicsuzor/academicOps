import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
import { resolveBotCommands, type TelegramBotCommand } from "./telegram/commands.js";

export interface PluginConfig {
  botToken: string;
  apiBaseUrl: string;
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
  miniAppUrl: string;
  instance?: string;
  botCommands: TelegramBotCommand[];
  bridgeToken?: string;
  autoInterrupt: boolean;
  cfAccessTeamDomain?: string;
  cfAccessAud?: string;
  cfAccessAllowedEmails?: string[];
  cfAccessCertsUrl?: string;
  cfAccessKeys?: any;
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

function mergeWithStateDirDotEnv(env: NodeJS.ProcessEnv): {
  stateDir: string;
  mergedEnv: NodeJS.ProcessEnv;
  role: string;
  isPrimary: boolean;
} {
  const stateDir = (env.STATE_DIR || "").trim();
  const fileEnv = stateDir ? readDotEnvFile(join(stateDir, ".env")) : {};
  const mergedEnv: NodeJS.ProcessEnv = { ...fileEnv };
  for (const [k, v] of Object.entries(env)) {
    if (v !== undefined) {
      mergedEnv[k] = v;
    }
  }
  const role = (mergedEnv.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  return {
    stateDir,
    mergedEnv,
    role,
    isPrimary: role === "primary",
  };
}

export function isPrimaryRole(env: NodeJS.ProcessEnv = process.env): boolean {
  return mergeWithStateDirDotEnv(env).isPrimary;
}

export function createNonPrimaryConfig(env: NodeJS.ProcessEnv = process.env): PluginConfig {
  const { stateDir, mergedEnv, role } = mergeWithStateDirDotEnv(env);
  return {
    botToken: "",
    apiBaseUrl: (mergedEnv.TELEGRAM_API_BASE_URL || "https://api.telegram.org").replace(/\/+$/, ""),
    role,
    isPrimary: false,
    allowFrom: [],
    maxChatChars: parseInt(mergedEnv.MAX_CHAT_CHARS || "4000", 10),
    voiceReplies: (mergedEnv.VOICE_REPLIES as "off" | "mirror" | "always") || "mirror",
    voiceTranscribeCmd: "",
    voiceSpeakCmd: "",
    port: parseInt(mergedEnv.PORT || "8093", 10),
    stateDir,
    socketPath: (mergedEnv.SOCKET_PATH || "").trim() || (stateDir ? join(stateDir, "bridge.sock") : ""),
    miniAppUrl: (mergedEnv.MINI_APP_URL || "").trim().replace(/\/+$/, ""),
    instance: (mergedEnv.IDA_NAME || "").trim() || undefined,
    botCommands: [],
    autoInterrupt: mergedEnv.TELEGRAM_AUTO_INTERRUPT !== "false",
    env: mergedEnv as Record<string, string>,
  };
}

export function loadConfig(env: NodeJS.ProcessEnv = process.env): PluginConfig {
  const { stateDir, mergedEnv, role, isPrimary } = mergeWithStateDirDotEnv(env);

  // Parse allowFrom as comma-separated or space-separated user IDs
  const rawAllowFrom = mergedEnv.ALLOWED_USER_IDS || "";
  const allowFrom = rawAllowFrom
    .split(/[\s,]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));

  const botToken = (mergedEnv.TELEGRAM_BOT_TOKEN || "").trim();
  const miniAppUrl = (mergedEnv.MINI_APP_URL || "").trim().replace(/\/+$/, "");

  if (isPrimary) {
    const missing: string[] = [];
    if (!stateDir) missing.push("STATE_DIR");
    if (!miniAppUrl) missing.push("MINI_APP_URL");
    if (!botToken) missing.push("TELEGRAM_BOT_TOKEN");
    if (allowFrom.length === 0) missing.push("ALLOWED_USER_IDS");
    if (missing.length > 0) {
      throw new Error(
        `[ida-telegram] Missing required environment variable(s) for primary instance: ${missing.join(", ")}. Configure them in the environment or $STATE_DIR/.env`
      );
    }
  } else {
    if (!stateDir) {
      throw new Error(
        "[ida-telegram] STATE_DIR is not set: configure the state directory path in STATE_DIR"
      );
    }
    if (!miniAppUrl) {
      throw new Error(
        "[ida-telegram] MINI_APP_URL is not set: configure the public URL of this plugin's Mini App in the environment or $STATE_DIR/.env"
      );
    }
  }

  const socketPath = (mergedEnv.SOCKET_PATH || "").trim() || join(stateDir, "bridge.sock");

  // Voice transcribe candidate resolution per Telegram voice specification FR-7.5
  const transcribeCandidates = [
    join(stateDir, "transcribe.sh"),
    join(homedir(), ".claude", "channels", "telegram", "transcribe.sh"),
    "/usr/local/bin/transcribe.sh",
    join(homedir(), ".local", "bin", "transcribe.sh"),
  ];
  let defaultTranscribeCmd = join(homedir(), ".claude", "channels", "telegram", "transcribe.sh");
  for (const cand of transcribeCandidates) {
    if (existsSync(cand)) {
      defaultTranscribeCmd = cand;
      break;
    }
  }

  const rawTranscribeCmd = (mergedEnv.VOICE_TRANSCRIBE_CMD || "").trim();
  let voiceTranscribeCmd = defaultTranscribeCmd;
  if (rawTranscribeCmd) {
    if (rawTranscribeCmd.includes("/") || rawTranscribeCmd.includes("\\")) {
      voiceTranscribeCmd = rawTranscribeCmd;
    } else {
      const bareCandidates = [
        join(stateDir, rawTranscribeCmd),
        join(homedir(), ".claude", "channels", "telegram", rawTranscribeCmd),
        join("/usr/local/bin", rawTranscribeCmd),
        join(homedir(), ".local", "bin", rawTranscribeCmd),
      ];
      let found = false;
      for (const cand of bareCandidates) {
        if (existsSync(cand)) {
          voiceTranscribeCmd = cand;
          found = true;
          break;
        }
      }
      if (!found) {
        voiceTranscribeCmd = rawTranscribeCmd;
      }
    }
  }

  // Voice speak candidate resolution per Telegram voice specification FR-7.2 & FR-7.5
  const bundledSpeak = mergedEnv.CLAUDE_PLUGIN_ROOT
    ? join(mergedEnv.CLAUDE_PLUGIN_ROOT, "scripts", "speak.sh")
    : join(import.meta.dir, "..", "scripts", "speak.sh");
  const speakCandidates = [
    join(stateDir, "speak.sh"),
    join(homedir(), ".claude", "channels", "telegram", "speak.sh"),
    "/usr/local/bin/speak.sh",
    bundledSpeak,
    join(import.meta.dir, "..", "scripts", "speak.sh"),
  ];
  let defaultSpeakCmd = bundledSpeak;
  for (const cand of speakCandidates) {
    if (existsSync(cand)) {
      defaultSpeakCmd = cand;
      break;
    }
  }

  const rawSpeakCmd = (mergedEnv.VOICE_SPEAK_CMD || "").trim();
  let voiceSpeakCmd = defaultSpeakCmd;
  if (rawSpeakCmd) {
    if (rawSpeakCmd.includes("/") || rawSpeakCmd.includes("\\")) {
      voiceSpeakCmd = rawSpeakCmd;
    } else {
      const bareCandidates = [
        join(stateDir, rawSpeakCmd),
        join(homedir(), ".claude", "channels", "telegram", rawSpeakCmd),
        join("/usr/local/bin", rawSpeakCmd),
        mergedEnv.CLAUDE_PLUGIN_ROOT ? join(mergedEnv.CLAUDE_PLUGIN_ROOT, "scripts", rawSpeakCmd) : "",
        join(import.meta.dir, "..", "scripts", rawSpeakCmd),
      ].filter(Boolean);
      let found = false;
      for (const cand of bareCandidates) {
        if (existsSync(cand)) {
          voiceSpeakCmd = cand;
          found = true;
          break;
        }
      }
      if (!found) {
        voiceSpeakCmd = rawSpeakCmd;
      }
    }
  }

  return {
    botToken,
    apiBaseUrl: (mergedEnv.TELEGRAM_API_BASE_URL || "https://api.telegram.org").replace(/\/+$/, ""),
    role,
    isPrimary,
    allowFrom,
    maxChatChars: parseInt(mergedEnv.MAX_CHAT_CHARS || "4000", 10),
    voiceReplies: (mergedEnv.VOICE_REPLIES as "off" | "mirror" | "always") || "mirror",
    voiceTranscribeCmd,
    voiceSpeakCmd,
    port: parseInt(mergedEnv.PORT || "8093", 10),
    stateDir,
    socketPath,
    githubToken: mergedEnv.GITHUB_TOKEN,
    miniAppUrl,
    instance: (mergedEnv.IDA_NAME || "").trim() || undefined,
    botCommands: resolveBotCommands(mergedEnv.TELEGRAM_BOT_COMMANDS),
    bridgeToken: mergedEnv.IDA_BRIDGE_TOKEN,
    autoInterrupt: mergedEnv.TELEGRAM_AUTO_INTERRUPT !== "false",
    cfAccessTeamDomain: (mergedEnv.CF_ACCESS_TEAM_DOMAIN || "").trim() || undefined,
    cfAccessAud: (mergedEnv.CF_ACCESS_AUD || "").trim() || undefined,
    cfAccessAllowedEmails: (mergedEnv.CF_ACCESS_ALLOWED_EMAILS || "").trim()
      ? (mergedEnv.CF_ACCESS_ALLOWED_EMAILS || "").trim().split(/[\s,]+/).map((s) => s.trim().toLowerCase()).filter(Boolean)
      : undefined,
    cfAccessCertsUrl: (mergedEnv.CF_ACCESS_CERTS_URL || "").trim() || undefined,
    cfAccessKeys: (() => {
      const raw = mergedEnv.CF_ACCESS_KEYS || "";
      if (!raw) return undefined;
      try {
        return JSON.parse(raw);
      } catch {
        return raw;
      }
    })(),
    env: mergedEnv as Record<string, string>,
  };
}

