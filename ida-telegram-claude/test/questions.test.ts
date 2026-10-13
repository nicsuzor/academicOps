import { describe, expect, test, afterEach } from "bun:test";
import { QuestionBroker } from "../src/telegram/questions.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Questions are never assumed: Asynchronous Broker and Hook", () => {
  const testStateDir = join(tmpdir(), "ida-telegram-q-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("ask_user creates a persistent question, formats buttons with recommendation first, and returns immediately", async () => {
    const broker = new QuestionBroker(testStateDir);

    const questionInput = {
      question: "Which component should we prioritize?",
      options: [
        { label: "Port Formatter (Recommended)", description: "High impact on readability" },
        { label: "Refactor Poller", description: "Better backoff" },
      ],
      allowOther: false,
      turnId: "turn_123",
      chatId: 12345678,
    };

    const immediateResult = await broker.askUser(questionInput);

    expect(immediateResult.questionId).toBeDefined();
    expect(immediateResult.status).toBe("posted");
    expect(immediateResult.message).toContain("Do not assume an answer; continue other work or end your turn.");

    // Check keyboard structure
    const card = broker.renderQuestionCard(immediateResult.questionId);
    expect(card).not.toBeNull();
    expect(card?.buttons.length).toBe(2);
    // Vertical order preserved, recommendation first
    expect(card?.buttons[0].text).toContain("1. Port Formatter (Recommended)");
    expect(card?.buttons[1].text).toContain("2. Refactor Poller");
    // Callback data adheres to Telegram 64-byte limit
    expect(card?.buttons[0].callbackData.length).toBeLessThanOrEqual(64);
  });

  test("questions persist across restarts and can be resolved late", async () => {
    // Session 1: Create question
    const broker1 = new QuestionBroker(testStateDir);
    const result = await broker1.askUser({
      question: "Choose deployment strategy",
      options: [{ label: "Blue-Green" }, { label: "Canary" }],
      turnId: "turn_456",
      chatId: 12345678,
    });
    const qid = result.questionId;

    // Simulate restart (Session 2 reinstantiates broker with same state dir)
    const broker2 = new QuestionBroker(testStateDir);
    const pending = broker2.getPendingQuestions();
    expect(pending.some((q) => q.id === qid)).toBe(true);

    // Nic taps option 2: Canary
    const resolution = await broker2.resolveAnswer(qid, 1); // index 1 is Canary
    expect(resolution).not.toBeNull();
    expect(resolution?.cardText).toContain("Selected: Canary ✅");
    expect(resolution?.channelEvent.choice).toBe("Canary");
    expect(resolution?.channelEvent.turn_id).toBe("turn_456");

    // Question is no longer pending
    expect(broker2.getPendingQuestions().some((q) => q.id === qid)).toBe(false);
  });

  test("handles multiSelect questions with toggles and Done button", async () => {
    const broker = new QuestionBroker(testStateDir);
    const result = await broker.askUser({
      question: "Select enabled features",
      options: [{ label: "Logging" }, { label: "Tracing" }, { label: "Metrics" }],
      multiSelect: true,
      turnId: "turn_789",
      chatId: 12345678,
    });

    const card = broker.renderQuestionCard(result.questionId);
    expect(card?.buttons.some((b) => b.text.includes("☐ Logging"))).toBe(true);
    expect(card?.buttons.some((b) => b.text.includes("Done"))).toBe(true);
  });
});
