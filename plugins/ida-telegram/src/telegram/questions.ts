import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

export interface QuestionOption {
  label: string;
  description?: string;
  recommended?: boolean;
}

export interface QuestionPayload {
  question: string;
  header?: string;
  context?: string;
  recommendation?: string;
  options: QuestionOption[];
  multiSelect?: boolean;
  allowOther?: boolean;
  turnId?: string;
  turn_id?: string;
  sessionId?: string;
  session_id?: string;
  text?: string;
  chatId?: number;
}

export interface StoredQuestion extends QuestionPayload {
  id: string;
  text: string;
  createdAt: string;
  created_at: string;
  status: "pending" | "answered" | "closed";
  sessionId?: string;
  session_id?: string;
  turnId?: string;
  turn_id?: string;
  selectedOptions?: number[];
  answeredChoice?: string;
  closedReason?: string;
  closedAt?: string;
  messageId?: number;
  promptMessageId?: number;
}

export interface QuestionButton {
  text: string;
  callbackData: string;
}

export interface QuestionCard {
  text: string;
  buttons: QuestionButton[];
}

export interface QuestionAnswerEvent {
  event: "question_answered";
  question_id: string;
  question: string;
  choice: string;
  turn_id?: string;
  session_id?: string;
}

export interface QuestionClosedEvent {
  event: "question_closed";
  question_id: string;
  question: string;
  reason: string;
  turn_id?: string;
  session_id?: string;
}

export interface ResolveAnswerResult {
  cardText: string;
  channelEvent: QuestionAnswerEvent;
  question: StoredQuestion;
}

export interface CloseQuestionResult {
  cardText: string;
  channelEvent: QuestionClosedEvent;
  question: StoredQuestion;
}

export class QuestionBroker {
  private stateDir: string;
  private questionsFilePath: string;
  private questions: Map<string, StoredQuestion> = new Map();

  constructor(stateDir: string) {
    this.stateDir = stateDir;
    this.questionsFilePath = join(stateDir, "questions.json");
    this.loadState();
  }

  private loadState() {
    if (existsSync(this.questionsFilePath)) {
      try {
        const raw = readFileSync(this.questionsFilePath, "utf-8");
        const list: StoredQuestion[] = JSON.parse(raw);
        for (const q of list) {
          if (!q.text && q.question) q.text = q.question;
          if (!q.created_at && q.createdAt) q.created_at = q.createdAt;
          if (!q.createdAt && q.created_at) q.createdAt = q.created_at;
          if (!q.turn_id && q.turnId) q.turn_id = q.turnId;
          if (!q.turnId && q.turn_id) q.turnId = q.turn_id;
          if (!q.session_id && q.sessionId) q.session_id = q.sessionId;
          if (!q.sessionId && q.session_id) q.sessionId = q.session_id;
          this.questions.set(q.id, q);
        }
      } catch {
        // Corrupted file, fallback to empty
      }
    }
  }

  private saveState() {
    if (!existsSync(this.stateDir)) {
      mkdirSync(this.stateDir, { recursive: true });
    }
    const list = Array.from(this.questions.values());
    writeFileSync(this.questionsFilePath, JSON.stringify(list, null, 2), "utf-8");
  }

  public async askUser(payload: QuestionPayload): Promise<{
    questionId: string;
    status: "posted";
    message: string;
  }> {
    const id = "q_" + randomBytes(4).toString("hex");
    const turnId = payload.turnId || payload.turn_id;
    const sessionId = payload.sessionId || payload.session_id;
    const text = payload.text || payload.question;
    const createdAt = new Date().toISOString();
    const stored: StoredQuestion = {
      ...payload,
      id,
      text,
      question: text,
      createdAt,
      created_at: createdAt,
      status: "pending",
      selectedOptions: [],
      ...(turnId ? { turnId, turn_id: turnId } : {}),
      ...(sessionId ? { sessionId, session_id: sessionId } : {}),
    };

    this.questions.set(id, stored);
    this.saveState();

    return {
      questionId: id,
      status: "posted",
      message: `Question ${id} posted to the user. Do not assume an answer; continue other work or end your turn.`,
    };
  }

  public setMessageId(id: string, messageId: number) {
    const q = this.questions.get(id);
    if (q) {
      q.messageId = messageId;
      this.saveState();
    }
  }

  public setPromptMessageId(id: string, promptMessageId: number) {
    const q = this.questions.get(id);
    if (q) {
      q.promptMessageId = promptMessageId;
      this.saveState();
    }
  }

  public findQuestionByPromptMessageId(promptMessageId: number): StoredQuestion | undefined {
    for (const q of this.questions.values()) {
      if (q.status === "pending" && q.promptMessageId === promptMessageId) {
        return q;
      }
    }
    return undefined;
  }

  public getPendingQuestions(): StoredQuestion[] {
    return Array.from(this.questions.values()).filter((q) => q.status === "pending");
  }

  public getQuestion(id: string): StoredQuestion | undefined {
    return this.questions.get(id);
  }

  public toggleOption(id: string, optionIndex: number): QuestionCard | null {
    const q = this.questions.get(id);
    if (!q || q.status !== "pending" || !q.multiSelect) return null;

    const selected = new Set(q.selectedOptions || []);
    if (selected.has(optionIndex)) {
      selected.delete(optionIndex);
    } else {
      selected.add(optionIndex);
    }
    q.selectedOptions = Array.from(selected).sort((a, b) => a - b);
    this.saveState();
    return this.renderQuestionCard(id);
  }

  public renderQuestionCard(id: string): QuestionCard | null {
    const q = this.questions.get(id);
    if (!q) return null;

    let text = q.header ? `**${q.header}**\n\n` : "";
    text += q.question;

    if (q.context) {
      text += `\n\n>! ${q.context}`;
    }

    if (q.recommendation) {
      text += `\n\n**Recommendation:** ${q.recommendation}`;
    }

    if (q.options.some((opt) => opt.description)) {
      const optionLines = q.options.map((opt, idx) =>
        opt.description ? `${idx + 1}. **${opt.label}** — ${opt.description}` : `${idx + 1}. **${opt.label}**`
      );
      text += `\n\n${optionLines.join("\n")}`;
    }

    const buttons: QuestionButton[] = [];

    if (q.multiSelect) {
      q.options.forEach((opt, idx) => {
        const isSelected = q.selectedOptions?.includes(idx);
        const prefix = isSelected ? "☑" : "☐";
        buttons.push({
          text: `${prefix} ${opt.label}`,
          callbackData: `q:${id}:0:${idx}`,
        });
      });
      buttons.push({
        text: "✅ Done",
        callbackData: `q:${id}:0:done`,
      });
    } else {
      q.options.forEach((opt, idx) => {
        buttons.push({
          text: `${idx + 1}. ${opt.label}`,
          callbackData: `q:${id}:0:${idx}`,
        });
      });
    }

    if (q.allowOther !== false) {
      buttons.push({
        text: "✏️ Other",
        callbackData: `q:${id}:0:other`,
      });
    }

    return { text, buttons };
  }

  public async resolveAnswer(
    id: string,
    optionIndex?: number | "done" | "other",
    customText?: string,
    optionIndices?: number[]
  ): Promise<ResolveAnswerResult | null> {
    const q = this.questions.get(id);
    if (!q || q.status !== "pending") return null;

    let choice = "";
    const trimmedCustom = customText !== undefined ? customText.trim() : "";

    if (Array.isArray(optionIndices) && optionIndices.length > 0) {
      q.selectedOptions = optionIndices;
      const selected = optionIndices.map((i) => q.options[i]?.label).filter(Boolean);
      if (trimmedCustom) {
        selected.push(trimmedCustom);
      }
      choice = selected.join(", ") || "None";
    } else if (trimmedCustom && (optionIndex === "other" || typeof optionIndex !== "number")) {
      choice = trimmedCustom;
    } else if (typeof optionIndex === "number" && !Number.isNaN(optionIndex)) {
      const opt = q.options[optionIndex];
      choice = opt ? opt.label : `Option ${optionIndex + 1}`;
    } else if (optionIndex === "done") {
      const selected = (q.selectedOptions || []).map((i) => q.options[i]?.label).filter(Boolean);
      if (trimmedCustom) {
        selected.push(trimmedCustom);
      }
      choice = selected.join(", ") || "None";
    } else if (trimmedCustom) {
      choice = trimmedCustom;
    }

    q.status = "answered";
    q.answeredChoice = choice;
    this.saveState();

    const qLines = q.question.split("\n");
    qLines[0] = `**${qLines[0]}**`;
    const formattedQuestion = qLines.join("\n");
    const headerPrefix = q.header ? `**${q.header}**\n\n` : "";
    const cardText = `${headerPrefix}${formattedQuestion}\n\nSelected: ${choice} ✅`;
    const channelEvent: QuestionAnswerEvent = {
      event: "question_answered",
      question_id: id,
      question: q.question,
      choice,
      ...(q.turnId || q.turn_id ? { turn_id: q.turnId || q.turn_id } : {}),
      ...(q.sessionId || q.session_id ? { session_id: q.sessionId || q.session_id } : {}),
    };

    return { cardText, channelEvent, question: q };
  }

  public async closeQuestion(id: string, reason: string): Promise<CloseQuestionResult | null> {
    const trimmedReason = reason?.trim();
    if (!trimmedReason) {
      throw new Error("Missing reason: closing a question requires an explicit stated reason");
    }
    const q = this.questions.get(id);
    if (!q || q.status !== "pending") return null;

    q.status = "closed";
    q.closedReason = trimmedReason;
    q.closedAt = new Date().toISOString();
    this.saveState();

    const qLines = q.question.split("\n");
    qLines[0] = `**${qLines[0]}**`;
    const formattedQuestion = qLines.join("\n");
    const headerPrefix = q.header ? `**${q.header}**\n\n` : "";
    const cardText = `${headerPrefix}${formattedQuestion}\n\nClosed: ${trimmedReason}`;
    const channelEvent: QuestionClosedEvent = {
      event: "question_closed",
      question_id: id,
      question: q.question,
      reason: trimmedReason,
      ...(q.turnId || q.turn_id ? { turn_id: q.turnId || q.turn_id } : {}),
      ...(q.sessionId || q.session_id ? { session_id: q.sessionId || q.session_id } : {}),
    };

    return { cardText, channelEvent, question: q };
  }
}

