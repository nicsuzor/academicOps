import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { checkRole, acquireHostLock, releaseHostLock, calculate409Backoff } from "../src/role.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Concurrency: Role gating and Host lock", () => {
  const testLockDir = join(tmpdir(), "ida-telegram-role-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testLockDir)) {
      rmSync(testLockDir, { recursive: true, force: true });
    }
  });

  test("when IDA_TELEGRAM_ROLE is unset or not primary, isPrimary is false", () => {
    expect(checkRole({}).isPrimary).toBe(false);
    expect(checkRole({ IDA_TELEGRAM_ROLE: "worker" }).isPrimary).toBe(false);
    expect(checkRole({ IDA_TELEGRAM_ROLE: "secondary" }).isPrimary).toBe(false);
  });

  test("when IDA_TELEGRAM_ROLE is primary, isPrimary is true", () => {
    expect(checkRole({ IDA_TELEGRAM_ROLE: "primary" }).isPrimary).toBe(true);
  });

  test("same-host lock detects live PID on same host and refuses acquisition", () => {
    const lock1 = acquireHostLock(testLockDir, "hostA", "container1", process.pid);
    expect(lock1.acquired).toBe(true);

    // Another process/instance on same host attempting to acquire while current process is alive
    const lock2 = acquireHostLock(testLockDir, "hostA", "container1", process.pid);
    expect(lock2.acquired).toBe(false);
    expect(lock2.reason).toContain("live holder on the same host");

    releaseHostLock(testLockDir);
  });

  test("reclaims lock from dead PID or different host with warning", () => {
    // Acquire with a dead PID (e.g. 99999999)
    acquireHostLock(testLockDir, "hostB", "container2", 99999999);

    const lock2 = acquireHostLock(testLockDir, "hostA", "container1", process.pid);
    expect(lock2.acquired).toBe(true);
    expect(lock2.reclaimed).toBe(true);

    releaseHostLock(testLockDir);
  });

  test("409 backoff calculates exponential delay capped at 5 minutes", () => {
    expect(calculate409Backoff(0)).toBe(5000);
    expect(calculate409Backoff(1)).toBe(10000);
    expect(calculate409Backoff(2)).toBe(20000);
    expect(calculate409Backoff(3)).toBe(40000);
    expect(calculate409Backoff(10)).toBe(300000); // Capped at 5 min (300,000 ms)
  });
});
