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

export function loadConfig(env: NodeJS.ProcessEnv = process.env): PluginConfig {
  const stateDir = env.STATE_DIR || join(homedir(), ".claude", "channels", "telegram");
  const fileEnv = readDotEnvFile(join(stateDir, ".env"));
  const mergedEnv: NodeJS.ProcessEnv = { ...fileEnv, ...env };

  const role = (mergedEnv.IDA_TELEGRAM_ROLE || "").trim().toLowerCase();
  const isPrimary = role === "primary";

  // Parse allowFrom as comma-separated or space-separated user IDs
  const rawAllowFrom = mergedEnv.ALLOWED_USER_IDS || mergedEnv.TELEGRAM_ALLOW_FROM || "";
  const allowFrom = rawAllowFrom
    .split(/[\s,]+/)
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => !isNaN(n));

  const socketPath = mergedEnv.SOCKET_PATH || join(stateDir, "bridge.sock");
  const rawMiniAppUrl = (mergedEnv.MINI_APP_URL || mergedEnv.IDA_WEB_URL || DEFAULT_MINI_APP_URL).trim();
  const miniAppUrl = (rawMiniAppUrl || DEFAULT_MINI_APP_URL).replace(/\/+$/, "");

  // Voice transcribe candidate resolution per spec_7a9caca5 FR-7.5
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

  // Voice speak candidate resolution per spec_7a9caca5 FR-7.2 & FR-7.5
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
    botToken: mergedEnv.TELEGRAM_BOT_TOKEN || "",
    apiBaseUrl: (mergedEnv.TELEGRAM_API_BASE_URL || "https://api.telegram.org").replace(/\/+$/, ""),
    role,
    isPrimary,
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
    botCommands: resolveBotCommands(mergedEnv.TELEGRAM_BOT_COMMANDS),
    bridgeToken: mergedEnv.IDA_BRIDGE_TOKEN || mergedEnv.BRIDGE_TOKEN,
    cfAccessTeamDomain: (mergedEnv.CF_ACCESS_TEAM_DOMAIN || mergedEnv.CF_ACCESS_TEAM_NAME || "").trim() || undefined,
    cfAccessAud: (mergedEnv.CF_ACCESS_AUD || "").trim() || undefined,
    cfAccessAllowedEmails: (mergedEnv.CF_ACCESS_ALLOWED_EMAILS || "").trim()
      ? (mergedEnv.CF_ACCESS_ALLOWED_EMAILS || "").trim().split(/[\s,]+/).map((s) => s.trim().toLowerCase()).filter(Boolean)
      : undefined,
    cfAccessCertsUrl: (mergedEnv.CF_ACCESS_CERTS_URL || "").trim() || undefined,
    cfAccessKeys: (() => {
      const raw = mergedEnv.CF_ACCESS_KEYS || mergedEnv.CF_ACCESS_PUBKEY || "";
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

