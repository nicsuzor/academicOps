import { describe, expect, test } from "bun:test";
import { verifyTelegramInitData, createSessionToken, verifySessionToken } from "../src/web/auth.js";
import { createHmac } from "node:crypto";

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
