import { describe, expect, test, mock } from "bun:test";
import {
  discoverCandidates,
  aggregateTelemetryUsage,
  formatProposalMatrix,
  parseAllocationReply,
  validateCustomCommand,
  persistBotCommands,
  loadPersistedBotCommands,
  syncLiveMenus,
  type CandidateCommand,
  type PersonaAllocation,
} from "../src/telegram/proposal.js";
import {
  PRIME_COMMANDS,
  STRATEGIC_COMMANDS,
  RESERVED_COMMANDS,
  resolveBotCommands,
  getBareCommandBehavior,
  type TelegramBotCommand,
  type IdaCommandSpec,
} from "../src/telegram/commands.js";
import { TelegramBotClient } from "../src/telegram/bot.js";
import { loadConfig } from "../src/config.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Telegram Menu Proposal Skill (US-3, BAC-1 through BAC-7)", () => {
  // BAC-1 / AC-3.1: Candidate discovery
  test("BAC-1 / AC-3.1: Candidate discovery enumerates skills and workflows, normalizes names, includes coordination skills, and filters reserved/headless commands", async () => {
    const tempDir = mkdtempSync(join(tmpdir(), "ida-tg-discovery-"));
    const skillsDir = join(tempDir, "plugins", "mock-plugin", "skills");
    mkdirSync(join(skillsDir, "strategic-review"), { recursive: true });
    writeFileSync(
      join(skillsDir, "strategic-review", "SKILL.md"),
      `---\nname: strategic-review\ndescription: Modular multi-agent dialectical review\n---\n# Strategic Review\n`
    );

    mkdirSync(join(skillsDir, "reify"), { recursive: true });
    writeFileSync(
      join(skillsDir, "reify", "SKILL.md"),
      `---\nname: reify\ndescription: Compose dispatchable tasks on the graph\n---\n# Reify\n`
    );

    mkdirSync(join(skillsDir, "dispatch"), { recursive: true });
    writeFileSync(
      join(skillsDir, "dispatch", "SKILL.md"),
      `---\nname: dispatch\ndescription: Start polecat workers on queued tasks\n---\n# Dispatch\n`
    );

    // Reserved commands that must be filtered out
    mkdirSync(join(skillsDir, "start"), { recursive: true });
    writeFileSync(join(skillsDir, "start", "SKILL.md"), `---\nname: start\ndescription: Reserved start\n---\n`);
    mkdirSync(join(skillsDir, "help"), { recursive: true });
    writeFileSync(join(skillsDir, "help", "SKILL.md"), `---\nname: help\ndescription: Reserved help\n---\n`);

    // Headless worker commands that must be filtered out
    mkdirSync(join(skillsDir, "pull"), { recursive: true });
    writeFileSync(join(skillsDir, "pull", "SKILL.md"), `---\nname: pull\ndescription: Headless worker pull\n---\n`);
    mkdirSync(join(skillsDir, "dump"), { recursive: true });
    writeFileSync(join(skillsDir, "dump", "SKILL.md"), `---\nname: dump\ndescription: Headless worker dump\n---\n`);

    // Workflows dir
    const workflowsDir = join(tempDir, "workflows");
    mkdirSync(workflowsDir, { recursive: true });
    writeFileSync(
      join(workflowsDir, "wf-daily.md"),
      `---\ntitle: Daily Note Workflow\ndescription: Run daily note truth maintenance\n---\n`
    );

    const candidates = await discoverCandidates({
      pluginRoots: [join(tempDir, "plugins", "mock-plugin")],
      workflowsDirs: [workflowsDir],
      telemetryUsage: { "strategic-review": 12, reify: 8, dispatch: 5, "wf-daily": 3 },
    });

    const candidateCommands = candidates.map((c) => c.command);

    // Assert reify and dispatch are included
    expect(candidateCommands).toContain("reify");
    expect(candidateCommands).toContain("dispatch");

    // Assert kebab-case normalized to snake_case
    expect(candidateCommands).toContain("strategic_review");
    expect(candidateCommands).not.toContain("strategic-review");

    // Assert workflow is included
    expect(candidateCommands).toContain("wf_daily");

    // Assert reserved and headless commands are excluded
    expect(candidateCommands).not.toContain("start");
    expect(candidateCommands).not.toContain("help");
    expect(candidateCommands).not.toContain("pull");
    expect(candidateCommands).not.toContain("dump");

    // Assert usage counts are attached
    const sr = candidates.find((c) => c.command === "strategic_review");
    expect(sr?.usageCount).toBe(12);
  });

  // BAC-2: Telemetry ingestion
  test("BAC-2: Telemetry ingestion calculates accurate invocation frequencies from span storage", () => {
    const testSpans = [
      { name: "Skill: ida:decide", attributes: { "skill.id": "ida:decide" } },
      { name: "Skill: ida:decide", attributes: { "skill.id": "ida:decide" } },
      { name: "Skill: ida:reify", attributes: { "skill.id": "ida:reify" } },
      { name: "Skill: ida:strategic-review", attributes: { "skill.id": "ida:strategic-review" } },
      { name: "Telegram turn update", attributes: { event: "bot_command", command: "/decide" } },
      { name: "Telegram turn update", attributes: { event: "bot_command", command: "reify" } },
      { name: "Other span", attributes: { event: "message" } },
    ];

    const counts = aggregateTelemetryUsage(testSpans);
    // decide had 2 skill spans + 1 bot_command = 3
    expect(counts["decide"]).toBe(3);
    // reify had 1 skill span + 1 bot_command = 2
    expect(counts["reify"]).toBe(2);
    // strategic-review had 1 skill span
    expect(counts["strategic-review"] || counts["strategic_review"]).toBe(1);
  });

  // BAC-3: Proposal formatting & 100-command limit
  test("BAC-3: Proposal formatting renders candidate skills with usage counts, allocations, and per-bot placement", () => {
    const candidates: CandidateCommand[] = [
      {
        command: "decide",
        description: "Walk through open decisions",
        skill: "ida:decide",
        type: "skill",
        usageCount: 15,
        currentAllocation: "prime",
        bareAction: "Invoke /ida:decide",
      },
      {
        command: "strategic_review",
        description: "Modular multi-agent dialectical review",
        skill: "ida:strategic-review",
        type: "skill",
        usageCount: 10,
        currentAllocation: "strategic",
        bareAction: "Invoke /ida:strategic-review",
      },
      {
        command: "daily",
        description: "Update daily note and reply on Telegram",
        skill: "ida:daily",
        type: "skill",
        usageCount: 22,
        currentAllocation: "both",
        bareAction: "Invoke /ida:daily",
      },
      {
        command: "wf_tdd",
        description: "Test driven development cycle",
        skill: "wf-tdd",
        type: "workflow",
        usageCount: 4,
        currentAllocation: "none",
        bareAction: "Execute workflow wf-tdd",
      },
    ];

    const formatted = formatProposalMatrix(candidates);
    expect(formatted).toContain("/decide");
    expect(formatted).toContain("15");
    expect(formatted).toContain("[Prime]");
    expect(formatted).toContain("/strategic_review");
    expect(formatted).toContain("10");
    expect(formatted).toContain("[Strategic]");
    expect(formatted).toContain("/daily");
    expect(formatted).toContain("22");
    expect(formatted).toContain("[Both]");
    expect(formatted).toContain("/wf_tdd");
    expect(formatted).toContain("[None]");

    // Check limit enforcement: 101 commands triggers warning/cap
    const excessCandidates: CandidateCommand[] = Array.from({ length: 105 }, (_, i) => ({
      command: `cmd_${i}`,
      description: `Description ${i}`,
      skill: `skill_${i}`,
      type: "skill",
      usageCount: 1,
      currentAllocation: "both",
      bareAction: `Invoke cmd_${i}`,
    }));
    const excessFormatted = formatProposalMatrix(excessCandidates);
    expect(excessFormatted).toContain("Telegram API Limit Alert");
  });

  // BAC-4 / AC-3.2: Interactive intake (structured multi-choice vs natural language)
  test("BAC-4 / AC-3.2: Structured multi-choice selections and free-text replies resolve identically", () => {
    const currentAllocations: Record<string, PersonaAllocation> = {
      decide: "prime",
      strategic_review: "strategic",
      daily: "strategic",
      hydrate: "prime",
      reify: "prime",
    };

    // 1. Structured input
    const structuredInput = {
      daily: "both",
      hydrate: "none",
      reify: "both",
      strategic_review: "strategic",
      decide: "prime",
    };
    const structuredResult = parseAllocationReply(structuredInput, currentAllocations);

    // 2. Free-text natural language input
    const freeTextInput = "put daily on both, remove hydrate from prime, and add reify to both";
    const freeTextResult = parseAllocationReply(freeTextInput, currentAllocations);

    expect(structuredResult.daily).toBe("both");
    expect(structuredResult.hydrate).toBe("none");
    expect(structuredResult.reify).toBe("both");
    expect(freeTextResult.daily).toBe("both");
    expect(freeTextResult.hydrate).toBe("none");
    expect(freeTextResult.reify).toBe("both");
    expect(freeTextResult.strategic_review).toBe("strategic");
    expect(freeTextResult.decide).toBe("prime");
  });

  // BAC-5 / AC-3.3: Custom & composite command creation & validation
  test("BAC-5 / AC-3.3: Custom / composite command creation validates names, descriptions, and captures bare actions", () => {
    // Valid custom command
    const validSpec = {
      command: "/my_custom_task",
      description: "Run custom task pipeline",
      skill: "ida:custom",
      bareAction: "Invoke /ida:custom on active topic",
    };
    const validRes = validateCustomCommand(validSpec);
    expect(validRes.valid).toBe(true);
    expect(validRes.commandSpec?.command).toBe("my_custom_task");
    expect(validRes.commandSpec?.description).toBe("Run custom task pipeline");
    expect(validRes.commandSpec?.bareAction).toBe("Invoke /ida:custom on active topic");

    // Invalid: reserved name
    const reservedRes = validateCustomCommand({
      command: "start",
      description: "Should fail because start is reserved",
      bareAction: "Invoke start",
    });
    expect(reservedRes.valid).toBe(false);
    expect(reservedRes.error).toContain("reserved");

    // Invalid: contains hyphens / uppercase / symbols
    const invalidCharsRes = validateCustomCommand({
      command: "invalid-hyphen!",
      description: "Should fail on non [a-z0-9_]",
      bareAction: "Invoke invalid",
    });
    expect(invalidCharsRes.valid).toBe(false);
    expect(invalidCharsRes.error).toContain("lowercase alphanumeric and underscores");

    // Invalid: > 32 characters
    const tooLongRes = validateCustomCommand({
      command: "this_is_an_excessively_long_command_name_that_exceeds_thirty_two_chars",
      description: "Too long",
      bareAction: "Invoke long",
    });
    expect(tooLongRes.valid).toBe(false);
    expect(tooLongRes.error).toContain("32 characters");

    // Invalid: empty description
    const emptyDescRes = validateCustomCommand({
      command: "valid_name",
      description: "",
      bareAction: "Invoke action",
    });
    expect(emptyDescRes.valid).toBe(false);
    expect(emptyDescRes.error).toContain("description");
  });

  // BAC-6: Persistence & startup precedence
  test("BAC-6: Approved configurations are persisted, surviving restarts and superseding static fallbacks", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-persist-"));
    const customConfig = {
      prime: [
        { command: "decide", description: "Walk through decisions" },
        { command: "my_action", description: "Custom prime action" },
      ],
      strategic: [
        { command: "strategize", description: "Strategic reasoning" },
        { command: "my_action", description: "Custom strategic action" },
      ],
    };

    // Persist configuration
    await persistBotCommands(stateDir, customConfig);

    // Verify loading from persistent storage
    const loaded = await loadPersistedBotCommands(stateDir);
    expect(loaded).toEqual(customConfig);

    // Startup precedence verification:
    // With TELEGRAM_BOT_COMMANDS pointing to this custom json or stateDir, resolveBotCommands returns dynamic commands
    const customJson = JSON.stringify(customConfig);
    const resolvedPrime = resolveBotCommands("prime", customJson);
    expect(resolvedPrime).toEqual(customConfig.prime);

    const resolvedStrategic = resolveBotCommands("strategic", customJson);
    expect(resolvedStrategic).toEqual(customConfig.strategic);

    // Check config loader with TELEGRAM_BOT_COMMANDS
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_ALLOW_FROM: "12345",
      STATE_DIR: stateDir,
      IDA_TELEGRAM_PERSONA: "prime",
      TELEGRAM_BOT_COMMANDS: customJson,
    });
    expect(config.botCommands).toEqual(customConfig.prime);
  });

  // BAC-7 / AC-3.4: Live command synchronization
  test("BAC-7 / AC-3.4: Live command synchronization invokes Telegram setMyCommands across authorized chat scopes", async () => {
    const stateDir = mkdtempSync(join(tmpdir(), "ida-tg-sync-"));
    const config = loadConfig({
      TELEGRAM_BOT_TOKEN: "test-token",
      IDA_TELEGRAM_ROLE: "primary",
      TELEGRAM_ALLOW_FROM: "1001,1002",
      STATE_DIR: stateDir,
      IDA_TELEGRAM_PERSONA: "prime",
    });

    const apiCalls: Array<{ method: string; payload: Record<string, unknown> }> = [];
    const origFetch = globalThis.fetch;
    globalThis.fetch = mock(async (url: string | URL | Request, init?: RequestInit) => {
      const urlStr = String(url);
      const method = urlStr.split("/").pop() || "";
      const payload = init?.body ? JSON.parse(String(init.body)) : {};
      apiCalls.push({ method, payload });
      return new Response(JSON.stringify({ ok: true, result: true }), { status: 200 });
    }) as unknown as typeof fetch;

    try {
      const broker = new QuestionBroker(stateDir);
      const permRelay = new PermissionRelay();
      const botClient = new TelegramBotClient(config, broker, permRelay, () => {});

      const updatedCommands: TelegramBotCommand[] = [
        { command: "decide", description: "Walk through open decisions" },
        { command: "reify", description: "Compose dispatchable tasks" },
        { command: "dispatch", description: "Start polecat workers" },
        { command: "daily", description: "Update daily note and reply" },
      ];

      const syncResult = await syncLiveMenus({ prime: botClient }, { prime: updatedCommands });
      expect(syncResult.prime).toBe(true);

      const setMyCommandsCalls = apiCalls.filter((c) => c.method === "setMyCommands");
      // Must have called setMyCommands for each chat in allowFrom (1001, 1002)
      expect(setMyCommandsCalls.length).toBe(2);
      expect(setMyCommandsCalls[0].payload).toEqual({
        commands: updatedCommands,
        scope: { type: "chat", chat_id: 1001 },
      });
      expect(setMyCommandsCalls[1].payload).toEqual({
        commands: updatedCommands,
        scope: { type: "chat", chat_id: 1002 },
      });
    } finally {
      globalThis.fetch = origFetch;
    }
  });
});
