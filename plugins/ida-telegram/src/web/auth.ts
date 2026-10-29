import {
  createHmac,
  createPublicKey,
  createVerify,
  KeyObject,
  timingSafeEqual,
} from "node:crypto";

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

export class ReplayCache {
  private seen = new Map<string, number>();

  has(key: string): boolean {
    const exp = this.seen.get(key);
    if (!exp) return false;
    const now = Math.floor(Date.now() / 1000);
    if (now > exp) {
      this.seen.delete(key);
      return false;
    }
    return true;
  }

  add(key: string, exp: number): void {
    if (this.seen.size > 1000) {
      const now = Math.floor(Date.now() / 1000);
      for (const [k, v] of this.seen.entries()) {
        if (now > v) this.seen.delete(k);
      }
    }
    this.seen.set(key, exp);
  }

  clear(): void {
    this.seen.clear();
  }
}

export interface CfAccessPayload {
  aud?: string | string[];
  email?: string;
  sub?: string;
  iss?: string;
  iat?: number;
  nbf?: number;
  exp: number;
  type?: string;
  identity_nonce?: string;
  jti?: string;
  [key: string]: unknown;
}

export interface VerifyCfAccessJwtOptions {
  keys?: Record<string, string | KeyObject> | Array<any> | string | KeyObject;
  aud?: string | string[];
  teamDomain?: string;
  certsUrl?: string;
  allowedEmails?: string[];
  replayCache?: ReplayCache | { has: (key: string) => boolean; add: (key: string, exp: number) => void };
  clockSkewSeconds?: number;
  nowSeconds?: number;
}

export interface VerifyCfAccessJwtResult {
  valid: boolean;
  reason?: string;
  payload?: CfAccessPayload;
}

const jwksCache = new Map<string, { keys: any[]; fetchedAt: number }>();

function toKeyObject(rawKey: any): KeyObject | null {
  if (!rawKey) return null;
  if (rawKey instanceof KeyObject) return rawKey;
  try {
    if (typeof rawKey === "string") {
      if (rawKey.includes("-----BEGIN")) {
        return createPublicKey(rawKey);
      }
      const parsed = JSON.parse(rawKey);
      return toKeyObject(parsed);
    }
    if (typeof rawKey === "object") {
      if (rawKey.kty) {
        return createPublicKey({ key: rawKey, format: "jwk" });
      }
      if (rawKey.key) {
        return toKeyObject(rawKey.key);
      }
      if (rawKey.cert) {
        return createPublicKey(rawKey.cert);
      }
    }
  } catch {
    return null;
  }
  return null;
}

function resolveKey(optionsKeys: any, kid?: string): KeyObject | null {
  if (!optionsKeys) return null;
  if (optionsKeys instanceof KeyObject) return optionsKeys;
  if (typeof optionsKeys === "string" && optionsKeys.includes("-----BEGIN")) {
    return toKeyObject(optionsKeys);
  }
  let keysObj = optionsKeys;
  if (typeof optionsKeys === "string") {
    try {
      keysObj = JSON.parse(optionsKeys);
    } catch {
      return null;
    }
  }
  const keyList = Array.isArray(keysObj) ? keysObj : Array.isArray(keysObj?.keys) ? keysObj.keys : null;
  if (keyList) {
    if (kid) {
      const match = keyList.find((k: any) => k.kid === kid);
      return match ? toKeyObject(match) : null;
    }
    if (keyList.length === 1) return toKeyObject(keyList[0]);
    return null;
  }
  if (typeof keysObj === "object" && keysObj !== null) {
    if (kid) {
      if (keysObj[kid]) return toKeyObject(keysObj[kid]);
      if (keysObj.kid === kid) return toKeyObject(keysObj);
      return null;
    }
    if (keysObj.kty) return toKeyObject(keysObj);
    const keys = Object.keys(keysObj);
    if (keys.length === 1) return toKeyObject(keysObj[keys[0]]);
  }
  return null;
}

export async function fetchCfAccessJwks(certsUrl: string): Promise<any[]> {
  const cached = jwksCache.get(certsUrl);
  const now = Date.now();
  if (cached && now - cached.fetchedAt < 3600000) {
    return cached.keys;
  }
  try {
    const res = await fetch(certsUrl);
    if (!res.ok) return [];
    const json: any = await res.json();
    const keys = Array.isArray(json?.keys) ? json.keys : [];
    jwksCache.set(certsUrl, { keys, fetchedAt: now });
    return keys;
  } catch {
    return [];
  }
}

export async function verifyCfAccessJwt(
  token: string,
  options: VerifyCfAccessJwtOptions = {}
): Promise<VerifyCfAccessJwtResult> {
  if (!token || typeof token !== "string" || !token.trim()) {
    return { valid: false, reason: "empty assertion token" };
  }

  const parts = token.trim().split(".");
  if (parts.length !== 3) {
    return { valid: false, reason: "malformed assertion: must contain 3 segments" };
  }

  let header: any;
  try {
    header = JSON.parse(Buffer.from(parts[0], "base64url").toString("utf-8"));
  } catch {
    return { valid: false, reason: "malformed assertion: invalid header JSON" };
  }

  let payload: CfAccessPayload;
  try {
    payload = JSON.parse(Buffer.from(parts[1], "base64url").toString("utf-8"));
  } catch {
    return { valid: false, reason: "malformed assertion: invalid payload JSON" };
  }

  if (header.alg !== "RS256") {
    return { valid: false, reason: `unsupported algorithm: ${header.alg}` };
  }

  // Resolve public key
  let resolvedKey = resolveKey(options.keys, header.kid);
  if (!resolvedKey) {
    const certsUrl = options.certsUrl || (options.teamDomain
      ? `https://${options.teamDomain.replace(/^https?:\/\//, "").replace(/\/+$/, "")}${options.teamDomain.includes(".") ? "" : ".cloudflareaccess.com"}/cdn-cgi/access/certs`
      : undefined);

    if (certsUrl) {
      const remoteKeys = await fetchCfAccessJwks(certsUrl);
      resolvedKey = resolveKey(remoteKeys, header.kid);
    }
  }

  if (!resolvedKey) {
    return { valid: false, reason: header.kid ? `unknown key id: ${header.kid}` : "no verification key available" };
  }

  // Cryptographic signature check
  try {
    const signingInput = `${parts[0]}.${parts[1]}`;
    const signatureBuffer = Buffer.from(parts[2], "base64url");
    const verify = createVerify("RSA-SHA256");
    verify.update(signingInput);
    const isValid = verify.verify(resolvedKey, signatureBuffer);
    if (!isValid) {
      return { valid: false, reason: "invalid signature (forged assertion)" };
    }
  } catch (e) {
    return { valid: false, reason: `signature verification failed: ${String(e)}` };
  }

  // Expiration and temporal validity
  const now = options.nowSeconds ?? Math.floor(Date.now() / 1000);
  const skew = options.clockSkewSeconds ?? 60;

  if (typeof payload.exp !== "number") {
    return { valid: false, reason: "missing exp claim" };
  }
  if (now > payload.exp + skew) {
    return { valid: false, reason: "assertion expired" };
  }
  if (typeof payload.nbf === "number" && now < payload.nbf - skew) {
    return { valid: false, reason: "assertion not yet valid (nbf in future)" };
  }
  if (typeof payload.iat === "number" && payload.iat > now + skew) {
    return { valid: false, reason: "assertion issued in future (iat)" };
  }

  // Replay prevention: check replay cache for jti, identity_nonce, or token signature
  const replayId = payload.jti || payload.identity_nonce || parts[2];
  if (options.replayCache) {
    if (options.replayCache.has(replayId)) {
      return { valid: false, reason: "assertion replayed" };
    }
    options.replayCache.add(replayId, payload.exp);
  }

  // Audience validation
  if (options.aud) {
    const expectedAuds = Array.isArray(options.aud) ? options.aud : [options.aud];
    const payloadAuds = Array.isArray(payload.aud)
      ? payload.aud
      : typeof payload.aud === "string"
      ? [payload.aud]
      : [];
    const hasAudMatch = expectedAuds.some((ea) => payloadAuds.includes(ea));
    if (!hasAudMatch) {
      return { valid: false, reason: "audience mismatch" };
    }
  }

  // Issuer validation
  if (options.teamDomain) {
    const rawDomain = options.teamDomain.replace(/^https?:\/\//, "").replace(/\/+$/, "");
    const expectedDomain = rawDomain.includes(".") ? rawDomain : `${rawDomain}.cloudflareaccess.com`;
    const expectedIss = `https://${expectedDomain}`;
    if (payload.iss && payload.iss.replace(/\/+$/, "") !== expectedIss) {
      return { valid: false, reason: `issuer mismatch: expected ${expectedIss} but got ${payload.iss}` };
    }
  }

  // Authorized email validation
  if (options.allowedEmails && options.allowedEmails.length > 0) {
    if (!payload.email || typeof payload.email !== "string") {
      return { valid: false, reason: "missing email claim" };
    }
    const allowed = options.allowedEmails.map((e) => e.trim().toLowerCase());
    if (!allowed.includes(payload.email.trim().toLowerCase())) {
      return { valid: false, reason: `email not authorized: ${payload.email}` };
    }
  }

  return {
    valid: true,
    payload,
  };
}
