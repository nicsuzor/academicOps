import { describe, expect, test, afterEach } from "bun:test";
import { FeedbackManager } from "../src/telegram/feedback.js";
import { rmSync, existsSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

describe("Feedback: Upvote/downvote and learning loop", () => {
  const testStateDir = join(tmpdir(), "ida-telegram-fb-test-" + Math.random().toString(36).substring(7));

  afterEach(() => {
    if (existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  test("upvote records to feedback store and emits no channel event", async () => {
    const manager = new FeedbackManager(testStateDir);

    const result = await manager.handleUpvote({
      turnId: "turn_up_1",
      messageId: 201,
      messageExcerpt: "A crisp briefing with key metrics.",
    });

    expect(result.buttonText).toBe("👍 saved");
    expect(result.emitsChannelEvent).toBe(false);

    // Verify written to trace sink
    const traces = manager.getTraces();
    expect(traces.length).toBe(1);
    expect(traces[0].rating).toBe("up");
    expect(traces[0].turnId).toBe("turn_up_1");
  });

  test("downvote swaps keyboard to critique options", () => {
    const manager = new FeedbackManager(testStateDir);
    const keyboard = manager.getDownvoteCritiqueKeyboard(202);

    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Too verbose")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Wrong premise")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Poor logic")))).toBe(true);
    expect(keyboard.some((row) => row.some((btn) => btn.text.includes("Say why")))).toBe(true);
  });

  test("critique selection emits exactly one feedback_down channel event to Ida", async () => {
    const manager = new FeedbackManager(testStateDir);

    const result = await manager.handleCritique({
      turnId: "turn_down_1",
      messageId: 203,
      messageExcerpt: "A verbose explanation exceeding budget.",
      critique: "Too verbose",
    });

    expect(result.emitsChannelEvent).toBe(true);
    expect(result.channelEvent).toBeDefined();
    expect(result.channelEvent?.event).toBe("feedback_down");
    expect(result.channelEvent?.critique).toBe("Too verbose");
    expect(result.channelEvent?.turn_id).toBe("turn_down_1");
    expect(result.channelEvent?.message_excerpt).toContain("verbose explanation");
  });
});
