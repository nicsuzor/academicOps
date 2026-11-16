import { afterEach, describe, expect, test } from "bun:test";
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createNonPrimaryConfig, isPrimaryRole, loadConfig } from "../src/config.js";
import { ContainerGateway } from "../src/gateway.js";

describe("Canonical environment configuration and non-primary startup", () => {
  const tempDirs: string[] = [];

  function makeTempDir(prefix: string): string {
    const dir = mkdtempSync(join(tmpdir(), prefix));
    tempDirs.push(dir);
    return dir;
  }

  afterEach(() => {
    while (tempDirs.length > 0) {
      const dir = tempDirs.pop()!;
      if (existsSync(dir)) {
        rmSync(dir, { recursive: true, force: true });
      }
    }
  });

  test("loadConfig reads canonical variables and ignores retired legacy aliases", () => {
    const stateDir = makeTempDir("ida-tg-canonical-");

    // Retired IDA_WEB_URL does not satisfy MINI_APP_URL
    let webUrlErr: Error | undefined;
    try {
      loadConfig({
        STATE_DIR: stateDir,
        IDA_WEB_URL: "https://legacy-web.example.test",
      });
    } catch (err: any) {
      webUrlErr = err;
    }
    expect(webUrlErr).toBeDefined();
    expect(webUrlErr!.message).toContain("MINI_APP_URL");
    expect(webUrlErr!.message).not.toContain("IDA_WEB_URL");

    // Retired aliases for allowFrom, bridgeToken, cfAccessTeamDomain, cfAccessKeys, and instance are ignored
    const cfgWithLegacyOnly = loadConfig({
      STATE_DIR: stateDir,
      MINI_APP_URL: "https://dash.example.test/",
      TELEGRAM_ALLOW_FROM: "1111111111,2222222222",
      BRIDGE_TOKEN: "legacy-bridge-token",
      CF_ACCESS_TEAM_NAME: "legacy.cloudflareaccess.com",
      CF_ACCESS_PUBKEY: '{"kid":"legacy-pem"}',
      INSTANCE_NAME: "legacy-instance-name",
      INSTANCE_ID: "legacy-instance-id",
    });

    expect(cfgWithLegacyOnly.miniAppUrl).toBe("https://dash.example.test");
    expect(cfgWithLegacyOnly.allowFrom).toEqual([]);
    expect(cfgWithLegacyOnly.bridgeToken).toBeUndefined();
    expect(cfgWithLegacyOnly.cfAccessTeamDomain).toBeUndefined();
    expect(cfgWithLegacyOnly.cfAccessKeys).toBeUndefined();
    expect(cfgWithLegacyOnly.instance).toBeUndefined();

    // Canonical variables populate the corresponding fields
    const cfgCanonical = loadConfig({
      STATE_DIR: stateDir,
      IDA_TELEGRAM_ROLE: "primary",
      MINI_APP_URL: "https://dash.example.test/",
      TELEGRAM_BOT_TOKEN: "canonical-bot-token",
      ALLOWED_USER_IDS: "1111111111, 2222222222",
      IDA_BRIDGE_TOKEN: "canonical-bridge-token",
      CF_ACCESS_TEAM_DOMAIN: "team.example.test",
      CF_ACCESS_KEYS: '{"kid1":"pem-data"}',
      IDA_NAME: "prime",
    });

    expect(cfgCanonical.isPrimary).toBe(true);
    expect(cfgCanonical.miniAppUrl).toBe("https://dash.example.test");
    expect(cfgCanonical.botToken).toBe("canonical-bot-token");
    expect(cfgCanonical.allowFrom).toEqual([1111111111, 2222222222]);
    expect(cfgCanonical.bridgeToken).toBe("canonical-bridge-token");
    expect(cfgCanonical.cfAccessTeamDomain).toBe("team.example.test");
    expect(cfgCanonical.cfAccessKeys).toEqual({ kid1: "pem-data" });
    expect(cfgCanonical.instance).toBe("prime");
  });

  test("loadConfig requires STATE_DIR instead of falling back to ~/.claude/channels/telegram", () => {
    expect(() =>
      loadConfig({
        MINI_APP_URL: "https://dash.example.test",
      })
    ).toThrow(/STATE_DIR/);
  });

  test("primary loadConfig throws naming every missing canonical variable and honors $STATE_DIR/.env", () => {
    const stateDir = makeTempDir("ida-tg-primary-req-");

    // Missing STATE_DIR
    expect(() =>
      loadConfig({
        IDA_TELEGRAM_ROLE: "primary",
        MINI_APP_URL: "https://dash.example.test",
        TELEGRAM_BOT_TOKEN: "token-1",
        ALLOWED_USER_IDS: "12345",
      })
    ).toThrow(/STATE_DIR/);

    // Missing MINI_APP_URL
    expect(() =>
      loadConfig({
        IDA_TELEGRAM_ROLE: "primary",
        STATE_DIR: stateDir,
        TELEGRAM_BOT_TOKEN: "token-1",
        ALLOWED_USER_IDS: "12345",
      })
    ).toThrow(/MINI_APP_URL/);

    // Missing TELEGRAM_BOT_TOKEN
    expect(() =>
      loadConfig({
        IDA_TELEGRAM_ROLE: "primary",
        STATE_DIR: stateDir,
        MINI_APP_URL: "https://dash.example.test",
        ALLOWED_USER_IDS: "12345",
      })
    ).toThrow(/TELEGRAM_BOT_TOKEN/);

    // Missing ALLOWED_USER_IDS (even when retired TELEGRAM_ALLOW_FROM is provided)
    let allowErr: Error | undefined;
    try {
      loadConfig({
        IDA_TELEGRAM_ROLE: "primary",
        STATE_DIR: stateDir,
        MINI_APP_URL: "https://dash.example.test",
        TELEGRAM_BOT_TOKEN: "token-1",
        TELEGRAM_ALLOW_FROM: "12345",
      });
    } catch (err: any) {
      allowErr = err;
    }
    expect(allowErr).toBeDefined();
    expect(allowErr!.message).toContain("ALLOWED_USER_IDS");
    expect(allowErr!.message).not.toContain("TELEGRAM_ALLOW_FROM");

    // Missing all four canonical primary variables names every one of them
    let allMissingErr: Error | undefined;
    try {
      loadConfig({
        IDA_TELEGRAM_ROLE: "primary",
      });
    } catch (err: any) {
      allMissingErr = err;
    }
    expect(allMissingErr).toBeDefined();
    expect(allMissingErr!.message).toContain("STATE_DIR");
    expect(allMissingErr!.message).toContain("MINI_APP_URL");
    expect(allMissingErr!.message).toContain("TELEGRAM_BOT_TOKEN");
    expect(allMissingErr!.message).toContain("ALLOWED_USER_IDS");
    expect(allMissingErr!.message).not.toContain("IDA_WEB_URL");
    expect(allMissingErr!.message).not.toContain("TELEGRAM_ALLOW_FROM");

    // Role and primary variables in $STATE_DIR/.env are honored
    writeFileSync(
      join(stateDir, ".env"),
      [
        "IDA_TELEGRAM_ROLE=primary",
        "MINI_APP_URL=https://dash.example.test",
        "TELEGRAM_BOT_TOKEN=dotenv-token",
      ].join("\n") + "\n",
      "utf-8"
    );
    expect(isPrimaryRole({ STATE_DIR: stateDir })).toBe(true);
    expect(() => loadConfig({ STATE_DIR: stateDir })).toThrow(/ALLOWED_USER_IDS/);

    const resolvedFromDotEnv = loadConfig({
      STATE_DIR: stateDir,
      ALLOWED_USER_IDS: "987654321",
    });
    expect(resolvedFromDotEnv.isPrimary).toBe(true);
    expect(resolvedFromDotEnv.miniAppUrl).toBe("https://dash.example.test");
    expect(resolvedFromDotEnv.botToken).toBe("dotenv-token");
    expect(resolvedFromDotEnv.allowFrom).toEqual([987654321]);
  });

  test("spawning bun server.ts as non-primary starts cleanly, returns [] for tools/list, and creates zero directories or store files", async () => {
    const serverScript = join(import.meta.dir, "..", "server.ts");

    async function runNonPrimaryServer(customEnv: Record<string, string>) {
      const fakeHome = makeTempDir("ida-tg-fake-home-");
      const emptyWorkDir = makeTempDir("ida-tg-empty-cwd-");
      const proc = spawn(process.execPath, [serverScript], {
        cwd: emptyWorkDir,
        env: {
          PATH: process.env.PATH || "",
          HOME: fakeHome,
          ...customEnv,
        },
        stdio: ["pipe", "pipe", "pipe"],
      });

      const responses: Array<Record<string, any>> = [];
      let stdoutBuf = "";
      let stderrBuf = "";

      const twoResponsesPromise = new Promise<void>((resolve, reject) => {
        const timer = setTimeout(() => {
          proc.kill("SIGKILL");
          reject(new Error(`Timed out waiting for MCP responses. stderr=${stderrBuf}`));
        }, 5000);

        proc.stdout.on("data", (chunk) => {
          stdoutBuf += chunk.toString();
          let idx = stdoutBuf.indexOf("\n");
          while (idx !== -1) {
            const line = stdoutBuf.slice(0, idx).trim();
            stdoutBuf = stdoutBuf.slice(idx + 1);
            if (line) {
              responses.push(JSON.parse(line));
              if (responses.length >= 2) {
                clearTimeout(timer);
                resolve();
              }
            }
            idx = stdoutBuf.indexOf("\n");
          }
        });

        proc.stderr.on("data", (chunk) => {
          stderrBuf += chunk.toString();
        });

        proc.on("exit", (code) => {
          if (responses.length < 2) {
            clearTimeout(timer);
            reject(new Error(`server.ts exited prematurely with code ${code}: ${stderrBuf}`));
          }
        });
      });

      proc.stdin.write(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "initialize",
          params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "test", version: "1.0" } },
        }) + "\n"
      );
      proc.stdin.write(
        JSON.stringify({
          jsonrpc: "2.0",
          id: 2,
          method: "tools/list",
          params: {},
        }) + "\n"
      );

      await twoResponsesPromise;
      proc.kill("SIGTERM");
      await new Promise<void>((resolve) => proc.on("close", () => resolve()));

      return { responses, fakeHome, emptyWorkDir, stderrBuf };
    }

    // Scenario A: IDA_TELEGRAM_ROLE unset, STATE_DIR unset, MINI_APP_URL unset
    const unsetRun = await runNonPrimaryServer({});
    expect(unsetRun.responses[0].result.capabilities).toEqual({});
    expect(unsetRun.responses[1].result.tools).toEqual([]);
    expect(readdirSync(unsetRun.emptyWorkDir)).toEqual([]);
    expect(existsSync(join(unsetRun.fakeHome, ".claude"))).toBe(false);
    expect(readdirSync(unsetRun.fakeHome).filter((name) => name !== ".bun")).toEqual([]);

    // Scenario B: IDA_TELEGRAM_ROLE="standby", MINI_APP_URL unset, STATE_DIR pointing to non-existent directory
    const parentTemp = makeTempDir("ida-tg-nonexistent-parent-");
    const nonExistentStateDir = join(parentTemp, "should-not-be-created");
    const standbyRun = await runNonPrimaryServer({
      IDA_TELEGRAM_ROLE: "standby",
      STATE_DIR: nonExistentStateDir,
    });
    expect(standbyRun.responses[0].result.capabilities).toEqual({});
    expect(standbyRun.responses[1].result.tools).toEqual([]);
    expect(existsSync(nonExistentStateDir)).toBe(false);
    expect(readdirSync(parentTemp)).toEqual([]);
    expect(readdirSync(standbyRun.emptyWorkDir)).toEqual([]);
    expect(existsSync(join(standbyRun.fakeHome, ".claude"))).toBe(false);
    expect(readdirSync(standbyRun.fakeHome).filter((name) => name !== ".bun")).toEqual([]);
  });

  test("non-primary ContainerGateway startup creates zero directories or store files on disk", async () => {
    const parentTemp = makeTempDir("ida-tg-gw-parent-");
    const nonExistentStateDir = join(parentTemp, "gw-state-unused");

    // 1. Explicit non-primary config with non-existent stateDir
    const inertCfg = createNonPrimaryConfig({
      IDA_TELEGRAM_ROLE: "standby",
      STATE_DIR: nonExistentStateDir,
    });
    const gw1 = new ContainerGateway({ config: inertCfg });
    await gw1.start();
    gw1.stop();
    expect(existsSync(nonExistentStateDir)).toBe(false);
    expect(readdirSync(parentTemp)).toEqual([]);

    // 2. Implicit process.env non-primary startup with primary variables unset
    const savedRole = process.env.IDA_TELEGRAM_ROLE;
    const savedStateDir = process.env.STATE_DIR;
    const savedMiniAppUrl = process.env.MINI_APP_URL;
    try {
      process.env.IDA_TELEGRAM_ROLE = "standby";
      process.env.STATE_DIR = nonExistentStateDir;
      delete process.env.MINI_APP_URL;

      const gw2 = new ContainerGateway();
      await gw2.start();
      gw2.stop();
      expect(existsSync(nonExistentStateDir)).toBe(false);
      expect(readdirSync(parentTemp)).toEqual([]);
    } finally {
      if (savedRole === undefined) delete process.env.IDA_TELEGRAM_ROLE;
      else process.env.IDA_TELEGRAM_ROLE = savedRole;
      if (savedStateDir === undefined) delete process.env.STATE_DIR;
      else process.env.STATE_DIR = savedStateDir;
      if (savedMiniAppUrl === undefined) delete process.env.MINI_APP_URL;
      else process.env.MINI_APP_URL = savedMiniAppUrl;
    }
  });

  test("hooks/ask-user-question.js exits 1 naming STATE_DIR/SOCKET_PATH when primary and both are unset, without ~/.claude fallback", async () => {
    const hookScript = join(import.meta.dir, "..", "hooks", "ask-user-question.js");
    const fakeHome = makeTempDir("ida-tg-hook-home-");
    // Even if legacy ~/.claude/channels/telegram directory exists under HOME, hook must not fall back to it
    mkdirSync(join(fakeHome, ".claude", "channels", "telegram"), { recursive: true });

    const runHook = (env: Record<string, string>) =>
      new Promise<{ exitCode: number | null; stdout: string; stderr: string }>((resolve) => {
        const proc = spawn("node", [hookScript], {
          env: {
            PATH: process.env.PATH || "",
            HOME: fakeHome,
            ...env,
          },
          stdio: ["pipe", "pipe", "pipe"],
        });
        let stdout = "";
        let stderr = "";
        proc.stdout.on("data", (d) => (stdout += d.toString()));
        proc.stderr.on("data", (d) => (stderr += d.toString()));
        proc.on("close", (exitCode) => resolve({ exitCode, stdout, stderr }));
        proc.stdin.write(
          JSON.stringify({
            tool_name: "AskUserQuestion",
            tool_input: { questions: [{ question: "Test?", options: [{ label: "Yes" }] }] },
          }) + "\n"
        );
        proc.stdin.end();
      });

    // Primary with both STATE_DIR and SOCKET_PATH unset -> exit 1 naming STATE_DIR and SOCKET_PATH
    const primaryRes = await runHook({ IDA_TELEGRAM_ROLE: "primary" });
    expect(primaryRes.exitCode).toBe(1);
    expect(primaryRes.stderr).toContain("STATE_DIR");
    expect(primaryRes.stderr).toContain("SOCKET_PATH");
    expect(primaryRes.stderr).not.toContain(".claude");

    // Non-primary with both unset -> inert exit 0
    const standbyRes = await runHook({ IDA_TELEGRAM_ROLE: "standby" });
    expect(standbyRes.exitCode).toBe(0);
    expect(standbyRes.stderr).toBe("");
  });
});
