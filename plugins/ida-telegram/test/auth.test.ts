import { describe, expect, test } from "bun:test";
import {
  verifyTelegramInitData,
  createSessionToken,
  verifySessionToken,
  verifyCfAccessJwt,
  ReplayCache,
} from "../src/web/auth.js";
import { createHmac, createSign, generateKeyPairSync } from "node:crypto";

describe("Mini App Security: initData validation and session tokens", () => {
  const botToken = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11";
  const allowFrom = [12345678];

  function generateValidInitData(userId: number, authDateSeconds: number): string {
    const userJson = JSON.stringify({ id: userId, first_name: "Nic", username: "nicsuzor" });
    const params = new URLSearchParams();
    params.set("auth_date", authDateSeconds.toString());
    params.set("query_id", "AAG_TEST_123");
    params.set("user", userJson);

    // Build data-check-string (sorted alphabetically by key)
    const pairs: string[] = [];
    const keys = Array.from(params.keys()).sort();
    for (const key of keys) {
      pairs.push(`${key}=${params.get(key)}`);
    }
    const dataCheckString = pairs.join("\n");

    // secret = HMAC_SHA256(key="WebAppData", msg=bot_token)
    const secret = createHmac("sha256", "WebAppData").update(botToken).digest();
    // hash = HMAC_SHA256(key=secret, msg=data_check_string)
    const hash = createHmac("sha256", secret).update(dataCheckString).digest("hex");

    params.set("hash", hash);
    return params.toString();
  }

  test("valid initData with fresh auth_date from allowFrom user passes verification", () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const initData = generateValidInitData(12345678, nowSeconds);

    const result = verifyTelegramInitData(initData, botToken, allowFrom);
    expect(result.valid).toBe(true);
    expect(result.user?.id).toBe(12345678);
  });

  test("rejects initData with forged or corrupted hash", () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const initData = generateValidInitData(12345678, nowSeconds);
    const corrupted = initData.replace(/hash=[a-f0-9]{10}/, "hash=0000000000");

    const result = verifyTelegramInitData(corrupted, botToken, allowFrom);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain("hash mismatch");
  });

  test("rejects initData older than 1 hour (3600 seconds)", () => {
    const twoHoursAgo = Math.floor(Date.now() / 1000) - 7200;
    const initData = generateValidInitData(12345678, twoHoursAgo);

    const result = verifyTelegramInitData(initData, botToken, allowFrom);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain("auth_date expired");
  });

  test("rejects initData from user not in allowFrom list", () => {
    const nowSeconds = Math.floor(Date.now() / 1000);
    const initData = generateValidInitData(99999999, nowSeconds); // Unauthorized user

    const result = verifyTelegramInitData(initData, botToken, allowFrom);
    expect(result.valid).toBe(false);
    expect(result.reason).toContain("user not allowed");
  });

  test("issues and verifies 1-hour session token", () => {
    const sessionSecret = "super-secret-session-key";
    const token = createSessionToken(12345678, sessionSecret, 3600);

    const verified = verifySessionToken(token, sessionSecret);
    expect(verified.valid).toBe(true);
    expect(verified.userId).toBe(12345678);

    // Tampered token fails
    const tampered = token + "xyz";
    expect(verifySessionToken(tampered, sessionSecret).valid).toBe(false);
  });
});

describe("Mini App Security: Cloudflare Access JWT validation (AC1, AC2)", () => {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const { privateKey: otherPrivateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const pem = publicKey.export({ type: "spki", format: "pem" }).toString();
  const jwk = publicKey.export({ format: "jwk" });
  jwk.kid = "test-kid-1";

  const aud = "aud-test-tag";
  const teamDomain = "myteam.cloudflareaccess.com";
  const allowedEmail = "operator@example.com";

  function makeJwt(
    payloadOverrides: Record<string, unknown> = {},
    headerOverrides: Record<string, unknown> = {},
    signKey = privateKey
  ): string {
    const header = {
      alg: "RS256",
      typ: "JWT",
      kid: "test-kid-1",
      ...headerOverrides,
    };
    const now = Math.floor(Date.now() / 1000);
    const payload = {
      aud: [aud],
      email: allowedEmail,
      iss: `https://${teamDomain}`,
      sub: "user-uuid-1",
      iat: now,
      nbf: now,
      exp: now + 3600,
      type: "app",
      ...payloadOverrides,
    };
    const h64 = Buffer.from(JSON.stringify(header)).toString("base64url");
    const p64 = Buffer.from(JSON.stringify(payload)).toString("base64url");
    const input = `${h64}.${p64}`;
    const sign = createSign("RSA-SHA256");
    sign.update(input);
    const sig = sign.sign(signKey).toString("base64url");
    return `${input}.${sig}`;
  }

  test("AC2: valid JWT with valid claims and signature passes verification", async () => {
    const token = makeJwt();
    const res = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      aud,
      teamDomain,
      allowedEmails: [allowedEmail],
    });
    expect(res.valid).toBe(true);
    expect(res.payload?.email).toBe(allowedEmail);
    expect(res.payload?.sub).toBe("user-uuid-1");
  });

  test("AC2: supports JWKS array format for keys", async () => {
    const token = makeJwt();
    const res = await verifyCfAccessJwt(token, {
      keys: { keys: [jwk] },
      aud,
      teamDomain,
      allowedEmails: [allowedEmail],
    });
    expect(res.valid).toBe(true);
  });

  test("AC1 (forged): rejects JWT signed with wrong private key", async () => {
    const forged = makeJwt({}, {}, otherPrivateKey);
    const res = await verifyCfAccessJwt(forged, {
      keys: { "test-kid-1": pem },
      aud,
      teamDomain,
      allowedEmails: [allowedEmail],
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("invalid signature");
  });

  test("AC1 (forged): rejects JWT with unsupported or none algorithm", async () => {
    const noneHeaderToken = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url") +
      "." +
      Buffer.from(JSON.stringify({ sub: "u", exp: Math.floor(Date.now() / 1000) + 3600 })).toString("base64url") +
      ".";
    const res = await verifyCfAccessJwt(noneHeaderToken, {
      keys: { "test-kid-1": pem },
    });
    expect(res.valid).toBe(false);
  });

  test("AC1 (malformed): rejects non-JWT, corrupted base64, or bad JSON", async () => {
    const badTokens = [
      "",
      "not-a-jwt",
      "a.b",
      "a.b.c.d",
      "!!!.!!!.!!!",
      Buffer.from("not json").toString("base64url") + "." + Buffer.from("{}").toString("base64url") + ".sig",
    ];
    for (const bad of badTokens) {
      const res = await verifyCfAccessJwt(bad, {
        keys: { "test-kid-1": pem },
      });
      expect(res.valid).toBe(false);
      expect(res.reason).toBeDefined();
    }
  });

  test("AC1 (expired): rejects expired assertion", async () => {
    const now = Math.floor(Date.now() / 1000);
    const expired = makeJwt({ exp: now - 120 });
    const res = await verifyCfAccessJwt(expired, {
      keys: { "test-kid-1": pem },
      aud,
      teamDomain,
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("expired");
  });

  test("AC1 (replayed): rejects assertion when jti or identity_nonce is in replay cache", async () => {
    const replayCache = new ReplayCache();
    const now = Math.floor(Date.now() / 1000);
    const token = makeJwt({ jti: "nonce-xyz-456", exp: now + 3600 });

    // First use: succeeds and records into replay cache
    const firstRes = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      replayCache,
    });
    expect(firstRes.valid).toBe(true);

    // Second use: replayed assertion refused
    const replayRes = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      replayCache,
    });
    expect(replayRes.valid).toBe(false);
    expect(replayRes.reason).toContain("replayed");
  });

  test("rejects assertion with mismatched audience", async () => {
    const token = makeJwt({ aud: "wrong-aud" });
    const res = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      aud,
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("audience mismatch");
  });

  test("rejects assertion with mismatched issuer", async () => {
    const token = makeJwt({ iss: "https://evilteam.cloudflareaccess.com" });
    const res = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      teamDomain,
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("issuer mismatch");
  });

  test("rejects assertion with missing issuer when teamDomain configured", async () => {
    const token = makeJwt({ iss: undefined });
    const res = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      teamDomain,
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("issuer mismatch");
  });

  test("rejects assertion with unauthorized email", async () => {
    const token = makeJwt({ email: "unauthorized@example.com" });
    const res = await verifyCfAccessJwt(token, {
      keys: { "test-kid-1": pem },
      allowedEmails: [allowedEmail],
    });
    expect(res.valid).toBe(false);
    expect(res.reason).toContain("email not authorized");
  });

  test("rejects assertion when no keys configured", async () => {
    const token = makeJwt();
    const res = await verifyCfAccessJwt(token, {});
    expect(res.valid).toBe(false);
    expect(res.reason).toBeDefined();
  });
});
