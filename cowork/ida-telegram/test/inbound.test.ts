import { describe, expect, test } from "bun:test";
import { parseInboundUpdate, type TelegramUpdate } from "../src/telegram/inbound.js";

describe("Inbound completeness: Updates routing and parsing", () => {
  const allowFrom = [12345678];

  test("drops updates from users not in allowFrom", () => {
    const update: TelegramUpdate = {
      update_id: 1,
      message: {
        message_id: 101,
        date: Date.now(),
        chat: { id: 99999999, type: "private" },
        from: { id: 99999999, is_bot: false, first_name: "Attacker" },
        text: "Hello",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).toBeNull();
  });

  test("processes text message from allowFrom user into channel event", () => {
    const update: TelegramUpdate = {
      update_id: 2,
      message: {
        message_id: 102,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "Please inspect the latest commit.",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("message");
    expect(result?.content).toBe("Please inspect the latest commit.");
    expect(result?.meta.message_id).toBe(102);
  });

  test("extracts quoted_text for quote-replies", () => {
    const update: TelegramUpdate = {
      update_id: 3,
      message: {
        message_id: 103,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "Yes, proceed with option A.",
        reply_to_message: {
          message_id: 99,
          date: Date.now() - 60000,
          chat: { id: 12345678, type: "private" },
          text: "Here are the two proposals for review:\nOption A: Proceed immediately\nOption B: Postpone",
        },
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.meta.reply_to_message_id).toBe(99);
    expect(result?.meta.quoted_text).toContain("Option A: Proceed immediately");
  });

  test("delivers message reaction updates with target excerpt", () => {
    const update: TelegramUpdate = {
      update_id: 4,
      message_reaction: {
        chat: { id: 12345678, type: "private" },
        message_id: 88,
        user: { id: 12345678, is_bot: false, first_name: "Nic" },
        date: Date.now(),
        old_reaction: [],
        new_reaction: [{ type: "emoji", emoji: "🔥" }],
      },
    };

    const result = parseInboundUpdate(update, allowFrom, (msgId) => `Previous message text for ${msgId}`);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("reaction");
    expect(result?.content).toBe("reacted 🔥 to 88");
    expect(result?.meta.added).toBe("🔥");
    expect(result?.meta.target_message_id).toBe(88);
    expect(result?.meta.target_excerpt).toBe("Previous message text for 88");
  });

  test("delivers non-question button tap events", () => {
    const update: TelegramUpdate = {
      update_id: 5,
      callback_query: {
        id: "cb_1",
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        message: {
          message_id: 77,
          date: Date.now(),
          chat: { id: 12345678, type: "private" },
          text: "Actions",
        },
        data: "custom_action:deploy_test",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("button_tap");
    expect(result?.meta.callback_prefix).toBe("custom_action");
    expect(result?.meta.payload).toBe("deploy_test");
  });

  test("delivers bot commands as channel events", () => {
    const update: TelegramUpdate = {
      update_id: 6,
      message: {
        message_id: 104,
        date: Date.now(),
        chat: { id: 12345678, type: "private" },
        from: { id: 12345678, is_bot: false, first_name: "Nic" },
        text: "/status detailed",
      },
    };

    const result = parseInboundUpdate(update, allowFrom);
    expect(result).not.toBeNull();
    expect(result?.event).toBe("bot_command");
    expect(result?.content).toBe("/status detailed");
    expect(result?.meta.command).toBe("/status");
  });
});
