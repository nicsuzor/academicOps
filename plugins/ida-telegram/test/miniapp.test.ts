import { describe, expect, test, afterEach } from "bun:test";
import { rmSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { createHmac } from "node:crypto";
import { PluginStore } from "../src/store.js";
import { QuestionBroker } from "../src/telegram/questions.js";
import { PermissionRelay } from "../src/mcp/permissions.js";
import { startWebServer } from "../src/web/server.js";
import type { PluginConfig } from "../src/config.js";

/**
 * Lightweight DOM environment to execute plugins/ida-telegram/app/index.html
 * and plugins/ida-telegram/app/app.js against the live Mini App HTTP server.
 */
class MiniElement {
  public tagName: string;
  public attributes: Map<string, string> = new Map();
  public children: MiniElement[] = [];
  public parent: MiniElement | null = null;
  public style: Record<string, string> = {};
  public value = "";
  public checked = false;
  private _text = "";
  private listeners: Map<string, Array<(e?: any) => any>> = new Map();
  public ownerDocument: MiniDocument | null = null;

  constructor(tagName: string, ownerDocument: MiniDocument | null = null) {
    this.tagName = tagName.toLowerCase();
    this.ownerDocument = ownerDocument;
  }

  public get id(): string {
    return this.attributes.get("id") || "";
  }

  public set id(val: string) {
    this.attributes.set("id", val);
  }

  public get className(): string {
    return this.attributes.get("class") || "";
  }

  public set className(val: string) {
    this.attributes.set("class", val);
  }

  public get classList() {
    const getSet = () =>
      new Set(
        (this.attributes.get("class") || "")
          .split(/\s+/)
          .map((s) => s.trim())
          .filter(Boolean)
      );
    const saveSet = (set: Set<string>) => {
      this.attributes.set("class", Array.from(set).join(" "));
    };
    return {
      add: (...tokens: string[]) => {
        const s = getSet();
        tokens.forEach((t) => s.add(t));
        saveSet(s);
      },
      remove: (...tokens: string[]) => {
        const s = getSet();
        tokens.forEach((t) => s.delete(t));
        saveSet(s);
      },
      contains: (token: string) => getSet().has(token),
    };
  }

  public getAttribute(name: string): string | null {
    return this.attributes.has(name) ? this.attributes.get(name)! : null;
  }

  public setAttribute(name: string, value: string) {
    this.attributes.set(name, String(value));
    if (name === "value") this.value = String(value);
    if (name === "checked") this.checked = true;
    if (name === "style") {
      for (const part of String(value).split(";")) {
        const [k, v] = part.split(":").map((s) => s?.trim());
        if (k && v) this.style[k] = v;
      }
    }
  }

  public addEventListener(event: string, fn: (e?: any) => any) {
    const list = this.listeners.get(event) || [];
    list.push(fn);
    this.listeners.set(event, list);
  }

  public async click() {
    if (this.tagName === "input" && this.getAttribute("type") === "checkbox") {
      this.checked = !this.checked;
    } else if (this.tagName === "input" && this.getAttribute("type") === "radio") {
      const name = this.getAttribute("name");
      if (name && this.ownerDocument) {
        for (const el of this.ownerDocument.querySelectorAll(`input[name="${name}"]`)) {
          el.checked = false;
        }
      }
      this.checked = true;
    }
    const list = this.listeners.get("click") || [];
    for (const fn of list) {
      await fn({ target: this, currentTarget: this, preventDefault() {} });
    }
    const onclick = this.getAttribute("onclick");
    if (onclick && this.ownerDocument?.windowObj) {
      const fn = new Function("window", `with (window) { return ${onclick}; }`);
      await fn(this.ownerDocument.windowObj);
    }
  }

  public get textContent(): string {
    if (this.tagName === "#text") return this._text;
    return this.children.map((c) => c.textContent).join("");
  }

  public set textContent(val: string) {
    this.children = [];
    const textNode = new MiniElement("#text", this.ownerDocument);
    textNode._text = String(val ?? "");
    textNode.parent = this;
    this.children.push(textNode);
  }

  public get innerHTML(): string {
    if (this.tagName === "#text") {
      return this._text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }
    return this.children.map((c) => c.outerHTML).join("");
  }

  public set innerHTML(html: string) {
    this.children = parseHtmlFragment(String(html ?? ""), this.ownerDocument, this);
    if (this.tagName === "textarea") {
      this.value = this.textContent;
    }
  }

  public get outerHTML(): string {
    if (this.tagName === "#text") return this.innerHTML;
    const attrs = Array.from(this.attributes.entries())
      .map(([k, v]) => `${k}="${v}"`)
      .join(" ");
    const open = attrs ? `<${this.tagName} ${attrs}>` : `<${this.tagName}>`;
    if (["input", "br", "hr", "img", "meta", "link"].includes(this.tagName)) {
      return open;
    }
    return `${open}${this.innerHTML}</${this.tagName}>`;
  }

  public querySelectorAll(selector: string): MiniElement[] {
    const results: MiniElement[] = [];
    const visit = (node: MiniElement) => {
      for (const child of node.children) {
        if (child.tagName !== "#text") {
          if (matchesSelectorChain(child, selector)) {
            results.push(child);
          }
          visit(child);
        }
      }
    };
    visit(this);
    return results;
  }

  public querySelector(selector: string): MiniElement | null {
    return this.querySelectorAll(selector)[0] || null;
  }
}

function matchesSingleSelector(el: MiniElement, sel: string): boolean {
  let rem = sel.trim();
  if (!rem) return false;

  // Attribute selectors: [attr="val"] or [attr]
  const attrRegex = /\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]/g;
  let m: RegExpExecArray | null;
  while ((m = attrRegex.exec(sel)) !== null) {
    const attrName = m[1];
    const attrVal = m[2];
    if (attrVal !== undefined) {
      if (el.getAttribute(attrName) !== attrVal) return false;
    } else {
      if (el.getAttribute(attrName) === null) return false;
    }
  }
  rem = rem.replace(attrRegex, "");

  // ID selector: #id
  const idMatch = rem.match(/#([a-zA-Z0-9_-]+)/);
  if (idMatch) {
    if (el.id !== idMatch[1]) return false;
    rem = rem.replace(idMatch[0], "");
  }

  // Class selectors: .cls1.cls2
  const classMatches = rem.match(/\.([a-zA-Z0-9_-]+)/g);
  if (classMatches) {
    for (const cm of classMatches) {
      if (!el.classList.contains(cm.slice(1))) return false;
    }
    rem = rem.replace(/\.([a-zA-Z0-9_-]+)/g, "");
  }

  // Remaining tag name
  if (rem && rem !== "*") {
    if (el.tagName !== rem.toLowerCase()) return false;
  }

  return true;
}

function matchesSelectorChain(el: MiniElement, selectorGroup: string): boolean {
  const selectors = selectorGroup.split(",").map((s) => s.trim()).filter(Boolean);
  for (const sel of selectors) {
    const parts = sel.split(/\s+/).filter(Boolean);
    if (parts.length === 0) continue;
    if (!matchesSingleSelector(el, parts[parts.length - 1])) continue;
    let curr: MiniElement | null = el.parent;
    let matchedAll = true;
    for (let i = parts.length - 2; i >= 0; i--) {
      while (curr && !matchesSingleSelector(curr, parts[i])) {
        curr = curr.parent;
      }
      if (!curr) {
        matchedAll = false;
        break;
      }
      curr = curr.parent;
    }
    if (matchedAll) return true;
  }
  return false;
}

function decodeHtmlEntities(str: string): string {
  return str
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&");
}

function parseHtmlFragment(
  html: string,
  ownerDocument: MiniDocument | null,
  parent: MiniElement | null
): MiniElement[] {
  const root = new MiniElement("fragment", ownerDocument);
  root.parent = parent;
  const stack: MiniElement[] = [root];
  const voidTags = new Set(["meta", "link", "input", "br", "hr", "img"]);

  // Strip HTML comments
  const cleaned = html.replace(/<!--[\s\S]*?-->/g, "");
  const tokenRegex = /<\/?([a-zA-Z0-9-]+)([^>]*)>|([^<]+)/g;
  let match: RegExpExecArray | null;

  while ((match = tokenRegex.exec(cleaned)) !== null) {
    const full = match[0];
    if (match[3] !== undefined) {
      const textVal = decodeHtmlEntities(match[3]);
      if (textVal.length > 0) {
        const textNode = new MiniElement("#text", ownerDocument);
        (textNode as any)._text = textVal;
        const top = stack[stack.length - 1];
        textNode.parent = top;
        top.children.push(textNode);
      }
      continue;
    }

    const tagName = match[1].toLowerCase();
    const attrStr = match[2] || "";
    const isClosing = full.startsWith("</");
    const isSelfClosing = full.endsWith("/>") || voidTags.has(tagName);

    if (isClosing) {
      for (let i = stack.length - 1; i > 0; i--) {
        if (stack[i].tagName === tagName) {
          stack.length = i;
          break;
        }
      }
    } else {
      const el = new MiniElement(tagName, ownerDocument);
      const attrRegex = /([a-zA-Z0-9_:-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?/g;
      let am: RegExpExecArray | null;
      while ((am = attrRegex.exec(attrStr)) !== null) {
        const k = am[1];
        const v = am[2] ?? am[3] ?? am[4] ?? "";
        el.setAttribute(k, decodeHtmlEntities(v));
      }
      const top = stack[stack.length - 1];
      el.parent = top;
      top.children.push(el);
      if (!isSelfClosing) {
        stack.push(el);
      }
    }
  }

  for (const c of root.children) {
    c.parent = parent;
  }
  return root.children;
}

class MiniDocument {
  public root: MiniElement;
  public windowObj: any = null;

  constructor(html: string) {
    this.root = new MiniElement("document", this);
    this.root.children = parseHtmlFragment(html, this, this.root);
  }

  public getElementById(id: string): MiniElement | null {
    return this.root.querySelector(`#${id}`);
  }

  public querySelector(selector: string): MiniElement | null {
    return this.root.querySelector(selector);
  }

  public querySelectorAll(selector: string): MiniElement[] {
    return this.root.querySelectorAll(selector);
  }
}

function generateValidInitData(botToken: string, userId: number): string {
  const nowSeconds = Math.floor(Date.now() / 1000);
  const userJson = JSON.stringify({ id: userId, first_name: "Nic", username: "nicsuzor" });
  const params = new URLSearchParams();
  params.set("auth_date", nowSeconds.toString());
  params.set("query_id", "AAG_MINIAPP_TEST");
  params.set("user", userJson);

  const pairs: string[] = [];
  for (const key of Array.from(params.keys()).sort()) {
    pairs.push(`${key}=${params.get(key)}`);
  }
  const secret = createHmac("sha256", "WebAppData").update(botToken).digest();
  const hash = createHmac("sha256", secret).update(pairs.join("\n")).digest("hex");
  params.set("hash", hash);
  return params.toString();
}

describe("Mini App Tabs (spec_7a9caca5 FR-4.3 to FR-4.7)", () => {
  const botToken = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11";
  const allowedUserId = 8860530746;
  const appDir = join(import.meta.dir, "..", "app");
  let testStateDir = "";
  let httpServer: ReturnType<typeof startWebServer> | null = null;

  afterEach(() => {
    if (httpServer) {
      httpServer.stop(true);
      httpServer = null;
    }
    if (testStateDir && existsSync(testStateDir)) {
      rmSync(testStateDir, { recursive: true, force: true });
    }
  });

  async function bootMiniApp(options: {
    search?: string;
    noAuth?: boolean;
    setup?: (ctx: {
      store: PluginStore;
      broker: QuestionBroker;
      permRelay: PermissionRelay;
      config: PluginConfig;
    }) => Promise<void> | void;
    fetchOverride?: (url: string, init?: RequestInit) => Promise<Response | null>;
  }) {
    testStateDir = join(tmpdir(), "ida-tg-miniapp-" + Math.random().toString(36).slice(2, 9));
    const store = new PluginStore(testStateDir);
    const broker = new QuestionBroker(testStateDir);
    const permRelay = new PermissionRelay();
    const config: PluginConfig = {
      botToken,
      apiBaseUrl: "https://api.telegram.org",
      role: "primary",
      isPrimary: true,
      allowFrom: [allowedUserId],
      maxChatChars: 1200,
      voiceReplies: "off",
      voiceTranscribeCmd: "",
      voiceSpeakCmd: "",
      port: 0,
      stateDir: testStateDir,
      socketPath: join(testStateDir, "bridge.sock"),
      githubToken: "ghp_test_readonly_token",
      miniAppUrl: "https://ida.example.ts.net",
      botCommands: [],
    };

    const emittedEvents: Array<{ event: string; content: string; meta: Record<string, unknown> }> = [];
    const editedCards: Array<{ chatId: number; messageId: number; text: string }> = [];

    if (options.setup) {
      await options.setup({ store, broker, permRelay, config });
    }

    const webContext: any = {
      store,
      broker,
      permRelay,
      config,
      sessionSecret: "miniapp-test-session-secret-32b!",
      emitChannelEvent: (event: string, content: string, meta: Record<string, unknown>) => {
        emittedEvents.push({ event, content, meta });
      },
      resolvePermissionRelay: (id: string, decision: "allow" | "deny") => {
        return permRelay.resolve(id, decision);
      },
      editTelegramCard: async (chatId: number, messageId: number, text: string) => {
        editedCards.push({ chatId, messageId, text });
      },
    };

    httpServer = startWebServer(webContext, appDir);
    const baseUrl = `http://127.0.0.1:${httpServer.port}`;

    const indexHtmlRes = await fetch(`${baseUrl}/app/index.html`);
    const indexHtml = await indexHtmlRes.text();
    const appJsRes = await fetch(`${baseUrl}/app/app.js`);
    const appJs = await appJsRes.text();

    const document = new MiniDocument(indexHtml);
    let sessionCookie = "";

    const appFetch = async (input: string, init?: RequestInit): Promise<Response> => {
      if (options.fetchOverride) {
        const overridden = await options.fetchOverride(input, init);
        if (overridden) return overridden;
      }
      // Resolve like a browser would: relative to the page the app is served from.
      const targetUrl = new URL(input, `${baseUrl}/app/index.html`).toString();
      const headers = new Headers(init?.headers || {});
      if (sessionCookie) {
        headers.set("Cookie", sessionCookie);
      }
      const res = await fetch(targetUrl, { ...init, headers });
      const setCookie = res.headers.get("Set-Cookie");
      if (setCookie) {
        sessionCookie = setCookie.split(";")[0];
      }
      return res;
    };

    const windowObj: any = {
      Telegram: {
        WebApp: {
          initData: options.noAuth ? "" : generateValidInitData(botToken, allowedUserId),
          expand() {},
        },
      },
      location: {
        search: options.search || "",
      },
      navigator: {
        clipboard: {
          writeText: async (_t: string) => {},
        },
      },
      confirm: () => true,
      alert: () => {},
      fetch: appFetch,
      document,
    };
    document.windowObj = windowObj;

    // Execute app.js in the window context and expose top-level functions on windowObj
    const wrappedJs = `
      ${appJs}
      if (typeof switchTab !== "undefined") window.switchTab = switchTab;
      if (typeof loadDetails !== "undefined") window.loadDetails = loadDetails;
      if (typeof loadQuestions !== "undefined") window.loadQuestions = loadQuestions;
      if (typeof loadReview !== "undefined") window.loadReview = loadReview;
      if (typeof loadAnchor !== "undefined") window.loadAnchor = loadAnchor;
      if (typeof answerQuestion !== "undefined") window.answerQuestion = answerQuestion;
      if (typeof submitQuestion !== "undefined") window.submitQuestion = submitQuestion;
      if (typeof closeQuestion !== "undefined") window.closeQuestion = closeQuestion;
      if (typeof resolvePermission !== "undefined") window.resolvePermission = resolvePermission;
      if (typeof submitPrReview !== "undefined") window.submitPrReview = submitPrReview;
    `;
    const runner = new Function("window", "document", "fetch", "confirm", "alert", wrappedJs);
    runner(windowObj, document, appFetch, windowObj.confirm, windowObj.alert);

    // Wait for async init() and initial tab fetches to settle
    await new Promise((r) => setTimeout(r, 80));

    return {
      document,
      window: windowObj,
      store,
      broker,
      permRelay,
      emittedEvents,
      editedCards,
      baseUrl,
    };
  }

  test("1. Details tab renders Markdown as formatted HTML tables and syntax-highlighted code blocks, not raw text (FR-4.3, FR-1.6)", async () => {
    let detailsId = "";
    const { document } = await bootMiniApp({
      setup: ({ store }) => {
        detailsId = store.storeDetails(
          [
            "# Benchmark Report",
            "",
            "Summary of **Tier 3** metrics for `ida-telegram`:",
            "",
            "| Component | Latency | Status |",
            "| --- | --- | --- |",
            "| Formatter | 1.2ms | OK |",
            "| Poller | 4.8ms | OK |",
            "",
            "```ts",
            "const maxChars = 1200;",
            "export function check(n: number) { return n <= maxChars; }",
            "```",
          ].join("\n")
        );
      },
      search: "",
    });

    await document.windowObj.loadDetails(detailsId);
    await new Promise((r) => setTimeout(r, 30));

    const detailsContainer = document.getElementById("details-content");
    expect(detailsContainer).not.toBeNull();
    const mdBody = detailsContainer!.querySelector(".markdown-body");
    expect(mdBody).not.toBeNull();

    // Must NOT dump raw markdown in a monospace pre-wrap div
    expect(mdBody!.getAttribute("style") || "").not.toContain("white-space: pre-wrap");

    // Must render headings and inline formatting
    expect(mdBody!.querySelectorAll("h1").length).toBeGreaterThanOrEqual(1);
    expect(mdBody!.querySelectorAll("strong").length).toBeGreaterThanOrEqual(1);

    // Must render a real HTML <table> with <thead>, <th>, <tbody>, <td> (FR-1.6, FR-4.3)
    const tables = mdBody!.querySelectorAll("table");
    expect(tables.length).toBe(1);
    const ths = tables[0].querySelectorAll("th").map((el) => el.textContent.trim());
    expect(ths).toEqual(["Component", "Latency", "Status"]);
    const tds = tables[0].querySelectorAll("td").map((el) => el.textContent.trim());
    expect(tds).toContain("Formatter");
    expect(tds).toContain("1.2ms");

    // Must render syntax-highlighted code block (<pre><code> with highlight spans) (FR-4.3)
    const codeBlocks = mdBody!.querySelectorAll("pre code");
    expect(codeBlocks.length).toBe(1);
    expect(codeBlocks[0].innerHTML).toContain("hl-");
  });

  test("2. Review tab shows live pending permission requests and PR diffs instead of a static placeholder, edits the chat card on Allow, and emits PR review events (FR-4.4, FR-4.5)", async () => {
    let resolvedDecision: "allow" | "deny" | null = null;
    const samplePrDiff = [
      "diff --git a/plugins/ida-telegram/app/app.js b/plugins/ida-telegram/app/app.js",
      "--- a/plugins/ida-telegram/app/app.js",
      "+++ b/plugins/ida-telegram/app/app.js",
      "@@ -40,3 +40,6 @@",
      "-  loadAnchor();",
      "+  loadReview();",
    ].join("\n");

    const origFetch = globalThis.fetch;
    globalThis.fetch = (async (input: any, init?: any) => {
      const url = typeof input === "string" ? input : input.url;
      if (url.includes("api.github.com/repos/nicsuzor/academicOps/pulls/2920")) {
        return new Response(samplePrDiff, { status: 200, headers: { "Content-Type": "text/plain" } });
      }
      return origFetch(input, init);
    }) as any;

    try {
      const { document, editedCards, emittedEvents } = await bootMiniApp({
        search: "?tab=review",
        setup: ({ permRelay, store }) => {
          permRelay.register(
            "perm_edit_1",
            "Edit",
            {
              file_path: "/workspace/plugins/ida-telegram/app/app.js",
              old_string: "const raw = true;",
              new_string: "const rendered = true;",
            },
            (decision) => {
              resolvedDecision = decision;
            }
          );
          if (typeof (permRelay as any).setMessageInfo === "function") {
            (permRelay as any).setMessageInfo("perm_edit_1", 8860530746, 501, "Permission request: *Edit*");
          }
          if (typeof (store as any).addReview === "function") {
            (store as any).addReview({ repo: "nicsuzor/academicOps", pr: 2920 });
          }
        },
      });

      // Opening with ?tab=review activates the Review view
      const reviewSection = document.getElementById("view-review");
      expect(reviewSection?.classList.contains("active")).toBe(true);

      const reviewContent = document.getElementById("review-content");
      expect(reviewContent).not.toBeNull();
      expect(reviewContent!.textContent).not.toContain("No pending permissions or PR diffs waiting for review.");

      // Shows the pending Edit permission request and its diff lines
      expect(reviewContent!.textContent).toContain("Edit");
      expect(reviewContent!.textContent).toContain("/workspace/plugins/ida-telegram/app/app.js");
      expect(reviewContent!.innerHTML).toContain("diff-add");
      expect(reviewContent!.innerHTML).toContain("diff-sub");

      // Shows the PR diff with file tree and highlighted patch
      expect(reviewContent!.textContent).toContain("nicsuzor/academicOps");
      expect(reviewContent!.textContent).toContain("2920");
      expect(reviewContent!.textContent).toContain("plugins/ida-telegram/app/app.js");

      // Approving the permission resolves the relay AND edits the Telegram chat card to "Allowed via Mini App ✅"
      await document.windowObj.resolvePermission("perm_edit_1", "allow");
      await new Promise((r) => setTimeout(r, 30));
      expect(resolvedDecision).toBe("allow");
      expect(editedCards.length).toBe(1);
      expect(editedCards[0].chatId).toBe(8860530746);
      expect(editedCards[0].messageId).toBe(501);
      expect(editedCards[0].text).toContain("Allowed via Mini App ✅");

      // Requesting changes on the PR emits review_changes to Ida without writing to GitHub directly
      const critiqueBox = document.getElementById("pr-critique-nicsuzor/academicOps-2920");
      if (critiqueBox) {
        critiqueBox.value = "Render Markdown tables in Details";
      }
      await document.windowObj.submitPrReview("changes", "nicsuzor/academicOps", 2920);
      await new Promise((r) => setTimeout(r, 30));

      expect(emittedEvents.some((e) => e.event === "review_changes" && e.meta.pr === 2920)).toBe(true);
    } finally {
      globalThis.fetch = origFetch;
    }
  });

  test("3. Questions tab renders multi-select questions as checkboxes with a submit button, shows header and option descriptions, and accepts free text (FR-4.6)", async () => {
    let multiQid = "";
    let singleQid = "";
    let closeQid = "";
    const { document, editedCards, emittedEvents } = await bootMiniApp({
      search: "?tab=questions",
      setup: async ({ broker }) => {
        const q1 = await broker.askUser({
          header: "Rollout Scope",
          question: "Which environments should receive the build?",
          options: [
            { label: "Staging (Recommended)", description: "Pre-production verification environment" },
            { label: "Canary", description: "10% live traffic slice" },
            { label: "Production", description: "Full fleet rollout" },
          ],
          multiSelect: true,
          allowOther: true,
          chatId: 8860530746,
          turnId: "turn_m1",
        });
        multiQid = q1.questionId;
        broker.setMessageId(multiQid, 701);

        const q2 = await broker.askUser({
          header: "Release Window",
          question: "When should we cut the release?",
          options: [
            { label: "Immediately (Recommended)", description: "Merge and tag now" },
            { label: "Tomorrow morning", description: "Hold for morning triage" },
          ],
          multiSelect: false,
          allowOther: true,
          chatId: 8860530746,
          turnId: "turn_s2",
        });
        singleQid = q2.questionId;
        broker.setMessageId(singleQid, 702);

        const q3 = await broker.askUser({
          header: "Stale Decision",
          question: "Adopt obsolete format?",
          options: [{ label: "Yes" }, { label: "No" }],
          multiSelect: false,
          chatId: 8860530746,
          turnId: "turn_s3",
          sessionId: "session_m3",
        });
        closeQid = q3.questionId;
        broker.setMessageId(closeQid, 703);
      },
    });

    await document.windowObj.switchTab("questions");
    await new Promise((r) => setTimeout(r, 40));

    const qList = document.getElementById("questions-list");
    expect(qList).not.toBeNull();

    // Header and option descriptions are visible
    expect(qList!.textContent).toContain("Rollout Scope");
    expect(qList!.textContent).toContain("Pre-production verification environment");
    expect(qList!.textContent).toContain("10% live traffic slice");

    // Multi-select question renders checkboxes, NOT single-click immediate submit buttons
    const checkboxes = qList!.querySelectorAll(`input[type="checkbox"]`);
    expect(checkboxes.length).toBe(3);

    // Toggling two checkboxes does NOT prematurely submit the question
    await checkboxes[0].click();
    await checkboxes[1].click();
    expect(emittedEvents.length).toBe(0);

    // Submitting the multi-select question sends both selected options
    await document.windowObj.submitQuestion(multiQid, true);
    await new Promise((r) => setTimeout(r, 40));

    expect(emittedEvents.length).toBe(1);
    expect(emittedEvents[0].meta.question_id).toBe(multiQid);
    expect(emittedEvents[0].meta.choice).toBe("Staging (Recommended), Canary");
    expect(editedCards.some((c) => c.messageId === 701 && c.text.includes("Selected: Staging (Recommended), Canary ✅"))).toBe(true);

    // Free-text box resolves the second question with custom text
    const freeText = document.getElementById(`q-text-${singleQid}`);
    expect(freeText).not.toBeNull();
    freeText!.value = "Hold until after the 14:00 deploy freeze";
    await document.windowObj.submitQuestion(singleQid, false);
    await new Promise((r) => setTimeout(r, 40));

    expect(emittedEvents.length).toBe(2);
    expect(emittedEvents[1].meta.question_id).toBe(singleQid);
    expect(emittedEvents[1].meta.choice).toBe("Hold until after the 14:00 deploy freeze");

    // Close third question with a stated reason (removes from Mini App, edits card, emits event)
    await document.windowObj.closeQuestion(closeQid, "answered elsewhere");
    await new Promise((r) => setTimeout(r, 40));

    expect(emittedEvents.length).toBe(3);
    expect(emittedEvents[2].event).toBe("question_closed");
    expect(emittedEvents[2].meta.question_id).toBe(closeQid);
    expect(emittedEvents[2].meta.reason).toBe("answered elsewhere");
    expect(editedCards.some((c) => c.messageId === 703 && c.text.includes("Closed: answered elsewhere"))).toBe(true);

    // Removed from the Mini App DOM
    const allCards = document.querySelectorAll(`[data-qid="${closeQid}"]`);
    expect(allCards.length).toBe(0);
  });

  test("4. Anchor tab shows every field required by FR-4.7: focus, taskId, waitingOn, delegations, pendingQuestions, recentTurns, uptime, and context gauge", async () => {
    const { document } = await bootMiniApp({
      search: "?tab=anchor",
      setup: async ({ store, broker }) => {
        store.setAnchor({
          focus: "Fixing Mini App tabs",
          taskId: "aops_263eba56",
          waitingOn: ["PR #2920 review", "Tailscale funnel check"],
          delegations: ["marsha: runtime QA", "rbg: axiom review"],
          contextTokens: {
            usedTokens: 84000,
            totalTokens: 200000,
            percentage: 42,
          },
        });
        if (typeof (store as any).recordTurn === "function") {
          (store as any).recordTurn("in", "Can you fix the Mini App tabs?");
          (store as any).recordTurn("out", "Claimed aops_263eba56 and updating all four tabs.");
        }
        await broker.askUser({
          question: "Approve Mini App tab layout?",
          options: [{ label: "Yes (Recommended)" }, { label: "No" }],
          chatId: 8860530746,
        });
      },
    });

    await document.windowObj.switchTab("anchor");
    await new Promise((r) => setTimeout(r, 40));

    const anchorView = document.getElementById("view-anchor");
    expect(anchorView).not.toBeNull();
    const text = anchorView!.textContent;

    // Focus and task ID
    expect(document.getElementById("anchor-focus")?.textContent).toBe("Fixing Mini App tabs");
    expect(document.getElementById("anchor-task")?.textContent).toBe("aops_263eba56");

    // Waiting-on items
    expect(text).toContain("PR #2920 review");
    expect(text).toContain("Tailscale funnel check");

    // Running delegations
    expect(text).toContain("marsha: runtime QA");
    expect(text).toContain("rbg: axiom review");

    // Pending questions
    expect(text).toContain("Approve Mini App tab layout?");

    // Recent turns (in and out)
    expect(text).toContain("Can you fix the Mini App tabs?");
    expect(text).toContain("Claimed aops_263eba56 and updating all four tabs.");

    // Uptime
    const uptimeEl = document.getElementById("anchor-uptime");
    expect(uptimeEl).not.toBeNull();
    expect(uptimeEl!.textContent.trim()).toMatch(/\d+[smhd]/);

    // Context gauge
    expect(document.getElementById("anchor-pct")?.textContent).toContain("42%");
  });

  test("5. Decision rendered in the Mini App shows its recommendation and context (FR-4.6)", async () => {
    const { document } = await bootMiniApp({
      search: "?tab=questions",
      setup: async ({ broker }) => {
        // 1. Explicit context and recommendation fields with recommended: true
        await broker.askUser({
          header: "RBG Request Brief",
          question: "Should rbg's brief hand it the original request explicitly? Now it only gets a task id inside the branch name.",
          context: "Run 3 had current instructions but departed on step 1: read PR diff before fetching request.",
          recommendation: "Yes, give the request explicitly so proportion can be judged against original intent.",
          options: [
            { label: "Yes, give the request explicitly", description: "Provides direct request text upfront", recommended: true },
            { label: "No, leave as is", description: "Keep deriving from branch task ID" },
          ],
          chatId: 8860530746,
          turnId: "turn_rbg_1",
        });

        // 2. Question with markdown context, recommendation, and (Recommended) in label
        await broker.askUser({
          header: "Value model weight",
          question: "Raise `urgency` weight on cliff tasks?",
          context: ">! Facts: `aops_5ff43ec0` showed 3 cliff tasks ranked below routine cleanup.",
          recommendation: "Raise to 2.5x to clear cliff tasks before routine work.",
          options: [
            { label: "Raise to 2.5x (Recommended)", description: "Prioritizes due-within-48h tasks immediately" },
            { label: "Keep at 1.5x", description: "Preserve current focus balance" },
          ],
          chatId: 8860530746,
          turnId: "turn_cliff_2",
        });

        // 3. Question without any recommendation
        await broker.askUser({
          header: "Survey",
          question: "Which timezone are you in?",
          options: [
            { label: "UTC+10 (AEST)" },
            { label: "UTC+1 (BST)" },
          ],
          chatId: 8860530746,
          turnId: "turn_neutral_3",
        });
      },
    });

    await document.windowObj.switchTab("questions");
    await new Promise((r) => setTimeout(r, 40));

    const qList = document.getElementById("questions-list");
    expect(qList).not.toBeNull();
    const text = qList!.textContent;

    // Decision 1: Context and recommendation are rendered
    expect(text).toContain("Run 3 had current instructions but departed on step 1: read PR diff before fetching request.");
    expect(text).toContain("Yes, give the request explicitly so proportion can be judged against original intent.");
    expect(qList!.querySelector(".q-recommendation")).not.toBeNull();
    expect(qList!.querySelector(".q-context")).not.toBeNull();

    // Decision 2: Markdown context and recommendation are rendered
    expect(text).toContain("Facts: aops_5ff43ec0 showed 3 cliff tasks ranked below routine cleanup.");
    expect(text).toContain("Raise to 2.5x to clear cliff tasks before routine work.");

    // Decision 3: Neutral question does NOT falsely mark option 0 as Recommended
    const surveyCard = Array.from(qList!.querySelectorAll(".question-card")).find((card) =>
      card.textContent.includes("Which timezone are you in?")
    );
    expect(surveyCard).toBeDefined();
    expect(surveyCard!.querySelector(".rec-badge")).toBeNull();
  });

  test("6. app.js reaches the API by page-relative paths, so the Mini App works behind a path prefix (e.g. /actual/app/)", async () => {
    const appJs = await Bun.file(new URL("../app/app.js", import.meta.url)).text();
    expect(appJs).not.toMatch(/["'`]\/api\//);
    expect(appJs).toMatch(/["'`]\.\.\/api\/app\//);
  });

  test("7. Details page is publicly accessible without session auth, renders Markdown in unauthenticated Mini App, displays error when missing, and leaves other tabs protected", async () => {
    let detailsId = "";
    const { document, baseUrl } = await bootMiniApp({
      noAuth: true,
      search: "",
      setup: ({ store }) => {
        detailsId = store.storeDetails(
          [
            "# Architectural Decision",
            "",
            "Publicly accessible **Tier 3** capability record.",
            "",
            "| Key | Status |",
            "| --- | --- |",
            "| Auth | Public |",
            "| Type | Capability Slug |",
            "",
            "```json",
            '{"public": true, "auth": "none"}',
            "```",
          ].join("\n")
        );
      },
    });

    // 1. Direct unauthenticated HTTP fetch to GET /api/app/details/:id succeeds
    const directRes = await fetch(`${baseUrl}/api/app/details/${detailsId}`);
    expect(directRes.status).toBe(200);
    const directData: any = await directRes.json();
    expect(directData.id).toBe(detailsId);
    expect(directData.markdown).toContain("Architectural Decision");

    // 2. Direct fetch to non-existent details returns 404 Not Found
    const missingRes = await fetch(`${baseUrl}/api/app/details/d_missing_404`);
    expect(missingRes.status).toBe(404);
    const missingData: any = await missingRes.json();
    expect(missingData.error).toBe("Details page not found");

    // 3. Other protected endpoints remain strictly gated by 401 Unauthorized
    const qRes = await fetch(`${baseUrl}/api/app/questions`);
    expect(qRes.status).toBe(401);
    const revRes = await fetch(`${baseUrl}/api/app/review`);
    expect(revRes.status).toBe(401);
    const anchorRes = await fetch(`${baseUrl}/api/app/anchor`);
    expect(anchorRes.status).toBe(401);

    // 4. Mini App with no auth loads and renders the details page via ?d=
    await document.windowObj.loadDetails(detailsId);
    await new Promise((r) => setTimeout(r, 40));

    const detailsContent = document.getElementById("details-content");
    expect(detailsContent).not.toBeNull();
    const mdBody = detailsContent!.querySelector(".markdown-body");
    expect(mdBody).not.toBeNull();
    expect(mdBody!.querySelectorAll("h1").length).toBe(1);
    expect(mdBody!.querySelectorAll("table").length).toBe(1);
    const ths = mdBody!.querySelectorAll("th").map((el) => el.textContent.trim());
    expect(ths).toEqual(["Key", "Status"]);

    // 5. Loading a non-existent details page in the Mini App renders visible error state instead of remaining blank
    await document.windowObj.loadDetails("d_missing_404");
    await new Promise((r) => setTimeout(r, 40));

    expect(detailsContent!.textContent).toContain("d_missing_404");
    expect(detailsContent!.textContent).toContain("Details page not found");
  });

  test("8. Question with details shows a details button that opens its fuller background (AC2)", async () => {
    let migQid = "";
    let simpleQid = "";
    const { document } = await bootMiniApp({
      search: "?tab=questions",
      setup: async ({ broker }) => {
        const q1 = await broker.askUser({
          header: "Database Migration",
          question: "Apply non-reversible schema migration to users table?",
          detail: "### Migration Plan\n- Drops deprecated column `legacy_role`\n- Adds non-nullable `role_id` foreign key\n- Estimated lock time: 420ms",
          recommendation: "Apply during low-traffic maintenance window.",
          options: [
            { label: "Apply now (Recommended)", description: "Low traffic confirmed" },
            { label: "Hold until weekend", description: "Wait for maintenance window" },
          ],
          chatId: 8860530746,
          turnId: "turn_mig_1",
        });
        migQid = q1.questionId;

        const q2 = await broker.askUser({
          header: "Simple Confirmation",
          question: "Proceed with routine log flush?",
          options: [{ label: "Yes (Recommended)" }, { label: "No" }],
          chatId: 8860530746,
          turnId: "turn_flush_2",
        });
        simpleQid = q2.questionId;
      },
    });

    await document.windowObj.switchTab("questions");
    await new Promise((r) => setTimeout(r, 40));

    const qList = document.getElementById("questions-list");
    expect(qList).not.toBeNull();

    const migCard = qList!.querySelector(`[data-qid="${migQid}"]`);
    expect(migCard).not.toBeNull();

    const simpleCard = qList!.querySelector(`[data-qid="${simpleQid}"]`);
    expect(simpleCard).not.toBeNull();

    // The question without details has NO details button
    const simpleDetailsBtn = simpleCard!.querySelector(".btn-details") || simpleCard!.querySelector(".btn-q-details");
    expect(simpleDetailsBtn).toBeNull();

    // The question with details HAS a details button
    const detailsBtn = migCard!.querySelector(".btn-details") || migCard!.querySelector(".btn-q-details");
    expect(detailsBtn).not.toBeNull();
    expect(detailsBtn!.textContent).toContain("Details");

    // Before clicking: details container is hidden
    const detailsBox = migCard!.querySelector(".q-details");
    expect(detailsBox).not.toBeNull();
    expect(detailsBox!.style.display).toBe("none");

    // Click details button to open fuller background
    await detailsBtn!.click();

    // After clicking: details container is open and displays the rendered markdown
    expect(detailsBox!.style.display).not.toBe("none");
    expect(detailsBox!.textContent).toContain("Drops deprecated column legacy_role");
    expect(detailsBox!.textContent).toContain("Estimated lock time: 420ms");
  });
});

