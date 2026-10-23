import { createHmac, timingSafeEqual } from "node:crypto";

export interface TelegramWebUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

export interface VerifyInitDataResult {
  valid: boolean;
  reason?: string;
  user?: TelegramWebUser;
  authDate?: number;
}

export function verifyTelegramInitData(
  initData: string,
  botToken: string,
  allowFrom: number[]
): VerifyInitDataResult {
  if (!initData || !botToken) {
    return { valid: false, reason: "missing initData or botToken" };
  }

  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if (!hash) {
    return { valid: false, reason: "missing hash in initData" };
  }

  // Check auth_date freshness (< 1 hour = 3600 seconds)
  const authDateStr = params.get("auth_date");
  if (!authDateStr) {
    return { valid: false, reason: "missing auth_date" };
  }
  const authDate = parseInt(authDateStr, 10);
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (nowSeconds - authDate > 3600) {
    return { valid: false, reason: "auth_date expired (> 1 hour old)" };
  }

  // Parse user and check allowFrom
  const userJson = params.get("user");
  let user: TelegramWebUser | undefined;
  if (userJson) {
    try {
      user = JSON.parse(userJson);
    } catch {
      return { valid: false, reason: "malformed user JSON" };
    }
  }

  if (!user || !allowFrom.includes(user.id)) {
    return { valid: false, reason: "user not allowed in allowFrom" };
  }

  // Build data-check-string: all parameters except 'hash', sorted alphabetically by key
  const keys = Array.from(params.keys())
    .filter((k) => k !== "hash")
    .sort();
  const dataCheckString = keys.map((k) => `${k}=${params.get(k)}`).join("\n");

  // secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
  const secretKey = createHmac("sha256", "WebAppData").update(botToken).digest();

  // computed_hash = HMAC_SHA256(key=secret, msg=data_check_string)
  const computedHashHex = createHmac("sha256", secretKey).update(dataCheckString).digest("hex");

  // Constant-time comparison
  const hashBuffer = Buffer.from(hash, "utf-8");
  const computedBuffer = Buffer.from(computedHashHex, "utf-8");

  if (hashBuffer.length !== computedBuffer.length || !timingSafeEqual(hashBuffer, computedBuffer)) {
    return { valid: false, reason: "hash mismatch" };
  }

  return {
    valid: true,
    user,
    authDate,
  };
}

export interface SessionTokenResult {
  valid: boolean;
  userId?: number;
  reason?: string;
}

export function createSessionToken(userId: number, secretKey: string, maxAgeSeconds = 3600): string {
  const expiresAt = Math.floor(Date.now() / 1000) + maxAgeSeconds;
  const payload = `${userId}:${expiresAt}`;
  const sig = createHmac("sha256", secretKey).update(payload).digest("hex");
  return `${payload}:${sig}`;
}

export function verifySessionToken(token: string, secretKey: string): SessionTokenResult {
  if (!token) return { valid: false, reason: "empty token" };

  const parts = token.split(":");
  if (parts.length !== 3) return { valid: false, reason: "malformed token" };

  const [userIdStr, expiresAtStr, sig] = parts;
  const payload = `${userIdStr}:${expiresAtStr}`;
  const expectedSig = createHmac("sha256", secretKey).update(payload).digest("hex");

  const sigBuf = Buffer.from(sig, "utf-8");
  const expBuf = Buffer.from(expectedSig, "utf-8");

  if (sigBuf.length !== expBuf.length || !timingSafeEqual(sigBuf, expBuf)) {
    return { valid: false, reason: "invalid signature" };
  }

  const expiresAt = parseInt(expiresAtStr, 10);
  const now = Math.floor(Date.now() / 1000);
  if (now > expiresAt) {
    return { valid: false, reason: "token expired" };
  }

  return {
    valid: true,
    userId: parseInt(userIdStr, 10),
  };
}
