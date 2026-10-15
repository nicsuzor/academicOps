import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomBytes } from "node:crypto";

export interface QuestionOption {
  label: string;
  description?: string;
}

export interface QuestionPayload {
  question: string;
  header?: string;
  options: QuestionOption[];
  multiSelect?: boolean;
  allowOther?: boolean;
  turnId?: string;
  chatId?: number;
}

export interface StoredQuestion extends QuestionPayload {
  id: string;
  createdAt: string;
  status: "pending" | "answered";
  selectedOptions?: number[];
  answeredChoice?: string;
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
  turn_id: string;
}

export interface ResolveAnswerResult {
  cardText: string;
  channelEvent: QuestionAnswerEvent;
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
    const turnId = payload.turnId || (payload as { turn_id?: string }).turn_id || `turn_${id}`;
    const stored: StoredQuestion = {
      ...payload,
      turnId,
      id,
      createdAt: new Date().toISOString(),
      status: "pending",
      selectedOptions: [],
    };

    this.questions.set(id, stored);
    this.saveState();

    return {
      questionId: id,
      status: "posted",
      message: `Question ${id} posted to Nic. Do not assume an answer; continue other work or end your turn.`,
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
    optionIndex: number | "done" | "other",
    customText?: string
  ): Promise<ResolveAnswerResult | null> {
    const q = this.questions.get(id);
    if (!q || q.status !== "pending") return null;

    let choice = "";
    if (customText !== undefined && (optionIndex === "other" || typeof optionIndex !== "number")) {
      choice = customText;
    } else if (typeof optionIndex === "number" && !Number.isNaN(optionIndex)) {
      const opt = q.options[optionIndex];
      choice = opt ? opt.label : `Option ${optionIndex + 1}`;
    } else if (optionIndex === "done") {
      const selected = (q.selectedOptions || []).map((i) => q.options[i]?.label).filter(Boolean);
      choice = selected.join(", ") || "None";
    } else if (customText) {
      choice = customText;
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
      turn_id: q.turnId || `turn_${id}`,
    };

    return { cardText, channelEvent, question: q };
  }
}

