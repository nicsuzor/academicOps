// Mini App client script
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
}

let activeTab = "details";

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const tab = btn.getAttribute("data-tab");
    switchTab(tab);
  });
});

function switchTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));

  document.querySelector(`[data-tab="${tab}"]`)?.classList.add("active");
  document.getElementById(`view-${tab}`)?.classList.add("active");

  if (tab === "questions") loadQuestions();
  if (tab === "review") loadReview();
  if (tab === "anchor") loadAnchor();
}

async function init() {
  if (tg && tg.initData) {
    try {
      await fetch("../api/app/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initData: tg.initData }),
      });
    } catch (e) {
      console.error("Auth failed", e);
    }
  }

  const params = new URLSearchParams(window.location.search);
  const detailsId = params.get("d");
  const requestedTab = params.get("tab");

  if (detailsId) {
    await loadDetails(detailsId);
  } else if (requestedTab && ["details", "questions", "review", "anchor"].includes(requestedTab)) {
    switchTab(requestedTab);
  } else {
    switchTab("anchor");
  }
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function highlightCode(rawCode) {
  const tokenRegex =
    /(\/\/[^\n]*|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|\b(?:const|let|var|function|return|export|import|from|async|await|if|else|for|while|class|interface|type|true|false|null|undefined|def|elif|number|string|boolean)\b|\b\d+(?:\.\d+)?\b)/g;

  let result = "";
  let lastIndex = 0;
  let match;

  while ((match = tokenRegex.exec(rawCode)) !== null) {
    if (match.index > lastIndex) {
      result += escapeHtml(rawCode.slice(lastIndex, match.index));
    }
    const token = match[0];
    const escaped = escapeHtml(token);
    if (token.startsWith("//") || token.startsWith("#")) {
      result += `<span class="hl-comment">${escaped}</span>`;
    } else if (token.startsWith('"') || token.startsWith("'") || token.startsWith("`")) {
      result += `<span class="hl-string">${escaped}</span>`;
    } else if (/^\d/.test(token)) {
      result += `<span class="hl-number">${escaped}</span>`;
    } else {
      result += `<span class="hl-keyword">${escaped}</span>`;
    }
    lastIndex = tokenRegex.lastIndex;
  }

  if (lastIndex < rawCode.length) {
    result += escapeHtml(rawCode.slice(lastIndex));
  }
  return result;
}

function formatInlineMarkdown(text) {
  let out = escapeHtml(text);
  // Inline code
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  // Italic
  out = out.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
  // Links
  out = out.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );
  return out;
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Blank line
    if (line.trim() === "") {
      i++;
      continue;
    }

    // Fenced code block
    const fenceMatch = line.match(/^```([a-zA-Z0-9_-]*)\s*$/);
    if (fenceMatch) {
      const lang = fenceMatch[1] || "text";
      i++;
      const codeLines = [];
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length && lines[i].startsWith("```")) {
        i++;
      }
      const highlighted = highlightCode(codeLines.join("\n"));
      blocks.push(
        `<pre class="code-block"><code class="language-${escapeHtml(lang)}">${highlighted}</code></pre>`
      );
      continue;
    }

    // Markdown Table (header row with | followed by separator row |---|)
    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(lines[i + 1])
    ) {
      const parseRow = (r) =>
        r
          .trim()
          .replace(/^\|/, "")
          .replace(/\|$/, "")
          .split("|")
          .map((c) => formatInlineMarkdown(c.trim()));

      const headers = parseRow(lines[i]);
      i += 2; // Skip header and separator
      const rows = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        rows.push(parseRow(lines[i]));
        i++;
      }
      const thead = `<thead><tr>${headers.map((h) => `<th>${h}</th>`).join("")}</tr></thead>`;
      const tbody = `<tbody>${rows
        .map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`)
        .join("")}</tbody>`;
      blocks.push(`<div class="table-wrap"><table class="md-table">${thead}${tbody}</table></div>`);
      continue;
    }

    // Heading
    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      blocks.push(`<h${level}>${formatInlineMarkdown(headingMatch[2])}</h${level}>`);
      i++;
      continue;
    }

    // Horizontal rule
    if (/^(---|\*\*\*|___)\s*$/.test(line.trim())) {
      blocks.push("<hr>");
      i++;
      continue;
    }

    // Expandable blockquote (>!)
    if (line.startsWith(">!")) {
      const quoteLines = [];
      while (i < lines.length && (lines[i].startsWith(">!") || lines[i].startsWith(">"))) {
        quoteLines.push(lines[i].replace(/^>!? ?/, ""));
        i++;
      }
      blocks.push(
        `<details class="expandable-quote"><summary>Details</summary><blockquote>${quoteLines
          .map((q) => formatInlineMarkdown(q))
          .join("<br>")}</blockquote></details>`
      );
      continue;
    }

    // Standard blockquote (>)
    if (line.startsWith(">")) {
      const quoteLines = [];
      while (i < lines.length && lines[i].startsWith(">")) {
        quoteLines.push(lines[i].replace(/^> ?/, ""));
        i++;
      }
      blocks.push(`<blockquote>${quoteLines.map((q) => formatInlineMarkdown(q)).join("<br>")}</blockquote>`);
      continue;
    }

    // Unordered list
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(`<li>${formatInlineMarkdown(lines[i].replace(/^\s*[-*]\s+/, ""))}</li>`);
        i++;
      }
      blocks.push(`<ul>${items.join("")}</ul>`);
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(`<li>${formatInlineMarkdown(lines[i].replace(/^\s*\d+\.\s+/, ""))}</li>`);
        i++;
      }
      blocks.push(`<ol>${items.join("")}</ol>`);
      continue;
    }

    // Paragraph
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !lines[i].startsWith("```") &&
      !lines[i].startsWith("#") &&
      !lines[i].startsWith(">") &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      paraLines.push(formatInlineMarkdown(lines[i]));
      i++;
    }
    if (paraLines.length > 0) {
      blocks.push(`<p>${paraLines.join("<br>")}</p>`);
    } else {
      i++;
    }
  }

  return blocks.join("\n");
}

async function loadDetails(id) {
  try {
    const res = await fetch(`../api/app/details/${id}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("details-content").innerHTML = `
        <div class="meta-row">
          <span class="mono">${escapeHtml(data.id)}</span>
          <span class="muted">${new Date(data.createdAt).toLocaleTimeString()}</span>
        </div>
        <div class="markdown-body">${renderMarkdown(data.markdown)}</div>
      `;
      switchTab("details");
    } else {
      let errMsg = "Details page not found";
      try {
        const errData = await res.json();
        if (errData?.error) errMsg = errData.error;
      } catch {}
      document.getElementById("details-content").innerHTML = `
        <div class="meta-row">
          <span class="mono">${escapeHtml(id)}</span>
        </div>
        <p class="muted">${escapeHtml(errMsg)}</p>
      `;
      switchTab("details");
    }
  } catch (e) {
    console.error("Failed to load details", e);
    document.getElementById("details-content").innerHTML = `
      <div class="meta-row">
        <span class="mono">${escapeHtml(id)}</span>
      </div>
      <p class="muted">Failed to load details: ${escapeHtml(String(e))}</p>
    `;
    switchTab("details");
  }
}

async function loadQuestions() {
  try {
    const res = await fetch("../api/app/questions");
    if (res.ok) {
      const data = await res.json();
      const list = data.questions || [];
      document.getElementById("q-badge").textContent = list.length;
      const container = document.getElementById("questions-list");

      if (list.length === 0) {
        container.innerHTML = '<div class="card"><p class="muted">No pending questions.</p></div>';
        return;
      }

      container.innerHTML = list
        .map((q) => {
          const isMulti = Boolean(q.multiSelect);
          const inputType = isMulti ? "checkbox" : "radio";
          const headerHtml = q.header ? `<div class="q-header">${escapeHtml(q.header)}</div>` : "";

          // Context block (explicit field)
          const contextHtml = q.context
            ? `<div class="q-context">${renderMarkdown(q.context)}</div>`
            : "";

          // Recommendation block
          const recHtml = q.recommendation
            ? `<div class="q-recommendation"><strong>Recommendation:</strong> ${formatInlineMarkdown(q.recommendation)}</div>`
            : "";

          const optionsHtml = (q.options || [])
            .map((opt, idx) => {
              const isRec = Boolean(
                opt.recommended || /\(recommended\)/i.test(opt.label)
              );
              const recBadge = isRec ? '<span class="rec-badge">Recommended</span>' : "";
              const descHtml = opt.description
                ? `<div class="opt-desc muted">${escapeHtml(opt.description)}</div>`
                : "";
              return `
                <label class="q-option">
                  <input type="${inputType}" name="q-opt-${escapeHtml(q.id)}" value="${idx}">
                  <div class="opt-body">
                    <div class="opt-title">
                      <span>${idx + 1}. ${escapeHtml(opt.label)}</span>
                      ${recBadge}
                    </div>
                    ${descHtml}
                  </div>
                </label>
              `;
            })
            .join("");

          const otherHtml =
            q.allowOther !== false
              ? `
                <div class="q-other-box">
                  <label class="muted" for="q-text-${escapeHtml(q.id)}">Or answer in your own words:</label>
                  <textarea id="q-text-${escapeHtml(q.id)}" class="q-freetext" rows="2" placeholder="Type a custom answer..."></textarea>
                </div>
              `
              : "";

          const metaParts = [];
          if (q.createdAt || q.created_at) metaParts.push(`Asked ${escapeHtml(q.createdAt || q.created_at)}`);
          if (q.turnId || q.turn_id) metaParts.push(`Turn ${escapeHtml(q.turnId || q.turn_id)}`);
          if (q.sessionId || q.session_id) metaParts.push(`Session ${escapeHtml(q.sessionId || q.session_id)}`);
          const metaHtml = metaParts.length > 0 ? `<div class="q-meta muted" style="font-size:0.75rem;margin-bottom:0.4rem;">${metaParts.join(" · ")}</div>` : "";

          const detailText = q.detail || q.details;
          const hasDetails = Boolean(detailText || q.detailsId || q.details_id);

          const detailsHtml = hasDetails
            ? `
              <div id="q-details-${escapeHtml(q.id)}" class="q-details card-details" style="display:none;">
                ${detailText ? renderMarkdown(detailText) : ""}
              </div>
            `
            : "";

          const detailsBtnHtml = hasDetails
            ? `<button class="btn btn-secondary btn-details btn-q-details" type="button" onclick="toggleQuestionDetails('${escapeHtml(q.id)}')">🔍 Details</button>`
            : "";

          return `
            <div class="card question-card" data-qid="${escapeHtml(q.id)}" data-details-id="${escapeHtml(q.detailsId || q.details_id || "")}">
              ${headerHtml}
              ${metaHtml}
              <h3>${formatInlineMarkdown(q.question || "")}</h3>
              ${contextHtml}
              ${recHtml}
              ${detailsHtml}
              <div class="q-options-list">
                ${optionsHtml}
              </div>
              ${otherHtml}
              <div class="actions-row">
                <button class="btn btn-primary" onclick="submitQuestion('${escapeHtml(q.id)}', ${isMulti})">
                  ${isMulti ? "Submit Selection" : "Submit Answer"}
                </button>
                ${detailsBtnHtml}
                <button class="btn btn-secondary btn-close-q" onclick="closeQuestion('${escapeHtml(q.id)}')">
                  Dismiss
                </button>
              </div>
            </div>
          `;
        })
        .join("");
    }
  } catch (e) {
    console.error("Failed to load questions", e);
  }
}

async function toggleQuestionDetails(qid) {
  const detailsEl = document.getElementById(`q-details-${qid}`);
  if (!detailsEl) return;
  const isHidden = detailsEl.style.display === "none" || !detailsEl.classList.contains("open");
  if (isHidden) {
    detailsEl.style.display = "block";
    detailsEl.classList.add("open");
    const card = document.querySelector(`.question-card[data-qid="${qid}"]`);
    const detailsId = card?.getAttribute("data-details-id");
    if (detailsId && !detailsEl.textContent.trim()) {
      try {
        const res = await fetch(`../api/app/details/${detailsId}`);
        if (res.ok) {
          const data = await res.json();
          detailsEl.innerHTML = renderMarkdown(data.markdown);
        } else {
          let errMsg = `Failed to load details (${res.status})`;
          try {
            const errData = await res.json();
            if (errData.error) errMsg = errData.error;
          } catch {}
          detailsEl.innerHTML = `<p class="muted">${escapeHtml(errMsg)}</p>`;
        }
      } catch (e) {
        console.error("Failed to load details for question", e);
        detailsEl.innerHTML = `<p class="muted">Failed to load details: ${escapeHtml(String(e))}</p>`;
      }
    }
  } else {
    detailsEl.style.display = "none";
    detailsEl.classList.remove("open");
  }
}

async function openQuestionDetails(qid) {
  const detailsEl = document.getElementById(`q-details-${qid}`);
  if (detailsEl) {
    detailsEl.style.display = "block";
    detailsEl.classList.add("open");
  }
}

if (typeof window !== "undefined") {
  window.toggleQuestionDetails = toggleQuestionDetails;
  window.openQuestionDetails = openQuestionDetails;
}

async function closeQuestion(qid, reason) {
  try {
    let promptReason = reason;
    if (!promptReason && typeof prompt === "function") {
      promptReason = prompt("Reason for closing this question (e.g. answered elsewhere, no longer needed, replaced by a newer question):");
    }
    const trimmed = typeof promptReason === "string" ? promptReason.trim() : "";
    if (!trimmed) {
      return;
    }
    const res = await fetch("../api/app/questions/close", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: qid, reason: trimmed }),
    });
    if (res.ok) {
      await loadQuestions();
    }
  } catch (e) {
    console.error("Failed to close question", e);
  }
}

async function submitQuestion(qid, isMultiSelect) {
  try {
    const inputs = document.querySelectorAll(`input[name="q-opt-${qid}"]`);
    const selectedIndices = [];
    inputs.forEach((inp) => {
      if (inp.checked) {
        selectedIndices.push(parseInt(inp.getAttribute("value") || inp.value, 10));
      }
    });

    const textEl = document.getElementById(`q-text-${qid}`);
    const customText = textEl && textEl.value ? textEl.value.trim() : "";

    const payload = { questionId: qid };
    if (isMultiSelect && selectedIndices.length > 0) {
      payload.optionIndices = selectedIndices;
      if (customText) payload.customText = customText;
    } else if (customText) {
      payload.optionIndex = "other";
      payload.customText = customText;
    } else if (selectedIndices.length > 0) {
      payload.optionIndex = selectedIndices[0];
    } else {
      return;
    }

    const res = await fetch("../api/app/questions/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      await loadQuestions();
    }
  } catch (e) {
    console.error("Failed to submit question", e);
  }
}

async function answerQuestion(qid, optIndex) {
  try {
    const res = await fetch("../api/app/questions/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionId: qid, optionIndex: optIndex }),
    });
    if (res.ok) {
      await loadQuestions();
    }
  } catch (e) {
    console.error("Failed to answer question", e);
  }
}

function formatDiffHtml(diffText) {
  const lines = String(diffText || "").split("\n");
  return lines
    .map((line) => {
      const escaped = escapeHtml(line);
      if (line.startsWith("+") && !line.startsWith("+++")) {
        return `<div class="diff-line diff-add">${escaped}</div>`;
      }
      if (line.startsWith("-") && !line.startsWith("---")) {
        return `<div class="diff-line diff-sub">${escaped}</div>`;
      }
      if (line.startsWith("@@")) {
        return `<div class="diff-line diff-hunk">${escaped}</div>`;
      }
      return `<div class="diff-line">${escaped}</div>`;
    })
    .join("");
}

async function loadReview() {
  try {
    const params = new URLSearchParams(window.location.search);
    const qs = new URLSearchParams();
    if (params.get("repo")) qs.set("repo", params.get("repo"));
    if (params.get("pr")) qs.set("pr", params.get("pr"));
    if (params.get("base")) qs.set("base", params.get("base"));
    if (params.get("head")) qs.set("head", params.get("head"));
    const querySuffix = qs.toString() ? `?${qs.toString()}` : "";

    const res = await fetch(`../api/app/review${querySuffix}`);
    if (!res.ok) return;
    const data = await res.json();
    const permissions = data.permissions || [];
    const reviews = data.reviews || [];
    const container = document.getElementById("review-content");

    if (permissions.length === 0 && reviews.length === 0) {
      container.innerHTML =
        '<div class="card"><p class="muted">No pending permissions or PR diffs waiting for review.</p></div>';
      return;
    }

    const permCards = permissions
      .map((p) => {
        const parsed = p.parsed || {};
        let bodyHtml = "";
        if (parsed.type === "diff") {
          bodyHtml = `
            <div class="meta-row"><span class="mono">${escapeHtml(parsed.filePath || "")}</span></div>
            <div class="diff-view">${formatDiffHtml(parsed.diff || "")}</div>
          `;
        } else if (parsed.type === "script") {
          bodyHtml = `
            <div class="script-header">
              <span class="muted">Bash Command</span>
              <button class="btn-copy" onclick="navigator.clipboard?.writeText(${escapeHtml(JSON.stringify(parsed.script || ""))})">Copy</button>
            </div>
            <pre class="diff-view mono">${escapeHtml(parsed.script || "")}</pre>
          `;
        } else {
          bodyHtml = `<pre class="diff-view mono">${escapeHtml(parsed.formattedJson || "")}</pre>`;
        }

        return `
          <div class="card" data-permid="${escapeHtml(p.id)}">
            <div class="meta-row">
              <h3>Permission: <span class="mono">${escapeHtml(p.toolName)}</span></h3>
              <span class="muted">${escapeHtml(p.id)}</span>
            </div>
            ${bodyHtml}
            <div class="actions-row">
              <button class="btn btn-success" onclick="resolvePermission('${escapeHtml(p.id)}', 'allow')">Allow ✅</button>
              <button class="btn btn-danger" onclick="resolvePermission('${escapeHtml(p.id)}', 'deny')">Deny ❌</button>
            </div>
          </div>
        `;
      })
      .join("");

    const prCards = reviews
      .map((rev) => {
        const files = rev.files || [];
        const fileTreeHtml =
          files.length > 0
            ? `<ul class="file-tree">${files
                .map((f) => `<li class="mono">${escapeHtml(f.path)}</li>`)
                .join("")}</ul>`
            : '<p class="muted">No diff files available.</p>';

        const patchesHtml = files
          .map(
            (f) => `
              <div class="pr-file-block">
                <div class="pr-file-header mono">${escapeHtml(f.path)}</div>
                <div class="diff-view">${formatDiffHtml(f.patch)}</div>
              </div>
            `
          )
          .join("");

        const prLabel = rev.prNumber ? `#${rev.prNumber}` : `${rev.base || "base"}...${rev.head || "head"}`;
        const critiqueId = `pr-critique-${rev.repo}-${rev.prNumber || 0}`;

        return `
          <div class="card" data-pr="${escapeHtml(rev.repo)}#${rev.prNumber || 0}">
            <h3>PR Diff: <span class="mono">${escapeHtml(rev.repo)} ${escapeHtml(prLabel)}</span></h3>
            <div class="anchor-section">
              <h4>Changed Files (${files.length})</h4>
              ${fileTreeHtml}
            </div>
            <div class="pr-patches">
              ${patchesHtml}
            </div>
            <div class="q-other-box">
              <textarea id="${escapeHtml(critiqueId)}" class="q-freetext" rows="2" placeholder="Optional review comments or change requests (or send a voice note in chat)..."></textarea>
            </div>
            <div class="actions-row">
              <button class="btn btn-success" onclick="submitPrReview('approve', '${escapeHtml(rev.repo)}', ${rev.prNumber || 0})">Approve ✅</button>
              <button class="btn btn-danger" onclick="submitPrReview('changes', '${escapeHtml(rev.repo)}', ${rev.prNumber || 0})">Request Changes 💬</button>
            </div>
          </div>
        `;
      })
      .join("");

    container.innerHTML = permCards + prCards;
  } catch (e) {
    console.error("Failed to load review tab", e);
  }
}

async function resolvePermission(permId, decision) {
  try {
    const res = await fetch("../api/app/review/permission", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ permId, decision }),
    });
    if (res.ok) {
      await loadReview();
    }
  } catch (e) {
    console.error("Failed to resolve permission", e);
  }
}

async function submitPrReview(action, repo, pr) {
  try {
    const critiqueEl = document.getElementById(`pr-critique-${repo}-${pr}`);
    const critique = critiqueEl && critiqueEl.value ? critiqueEl.value.trim() : "";
    const res = await fetch("../api/app/review/pr", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, repo, pr, critique }),
    });
    if (res.ok) {
      await loadReview();
    }
  } catch (e) {
    console.error("Failed to submit PR review", e);
  }
}

function formatUptime(seconds) {
  const s = Math.max(1, Number(seconds || 0));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const remS = s % 60;
  if (m < 60) return `${m}m ${remS}s`;
  const h = Math.floor(m / 60);
  const remM = m % 60;
  return `${h}h ${remM}m`;
}

async function loadAnchor() {
  try {
    const res = await fetch("../api/app/anchor");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("anchor-focus").textContent = data.focus || "Stand by";
      document.getElementById("anchor-task").textContent = data.taskId || "-";
      document.getElementById("q-badge").textContent = data.pendingQuestions || 0;

      const uptimeEl = document.getElementById("anchor-uptime");
      if (uptimeEl) {
        uptimeEl.textContent = formatUptime(data.uptimeSeconds);
      }

      const waitingList = document.getElementById("anchor-waiting-on");
      if (waitingList) {
        const items = data.waitingOn || [];
        waitingList.innerHTML =
          items.length > 0
            ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
            : '<li class="muted">None</li>';
      }

      const delegationsList = document.getElementById("anchor-delegations");
      if (delegationsList) {
        const items = data.delegations || [];
        delegationsList.innerHTML =
          items.length > 0
            ? items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
            : '<li class="muted">None</li>';
      }

      const questionsList = document.getElementById("anchor-questions");
      if (questionsList) {
        const qItems = data.pendingQuestionItems || [];
        questionsList.innerHTML =
          qItems.length > 0
            ? qItems
                .map(
                  (q) =>
                    `<li><strong>${escapeHtml(q.header || q.id)}:</strong> ${escapeHtml(q.question)}</li>`
                )
                .join("")
            : '<li class="muted">None</li>';
      }

      const turnsContainer = document.getElementById("anchor-turns");
      if (turnsContainer) {
        const turns = data.recentTurns || [];
        turnsContainer.innerHTML =
          turns.length > 0
            ? turns
                .map(
                  (t) => `
                  <div class="turn-row">
                    <span class="turn-dir turn-${escapeHtml(t.direction)}">${t.direction === "in" ? "IN" : "OUT"}</span>
                    <span class="turn-text">${escapeHtml(t.text)}</span>
                  </div>
                `
                )
                .join("")
            : '<p class="muted">No recent turns recorded.</p>';
      }

      const ct = data.contextTokens;
      const pct =
        typeof ct?.percentage === "number"
          ? ct.percentage
          : ct?.usedTokens && ct?.totalTokens
            ? Math.min(100, Math.round((ct.usedTokens / ct.totalTokens) * 100))
            : 0;
      const used = ct?.usedTokens;
      const total = ct?.totalTokens;
      document.getElementById("anchor-pct").textContent =
        used !== undefined && total !== undefined ? `${pct}% (${used} / ${total})` : `${pct}%`;
      document.getElementById("anchor-gauge").style.width = `${pct}%`;
    }
  } catch (e) {
    console.error("Failed to load anchor", e);
  }
}

document.getElementById("btn-stop")?.addEventListener("click", async () => {
  if (confirm("Stop current session turn and ask Ida to report?")) {
    await fetch("../api/app/stop", { method: "POST" });
    alert("Stop signal sent to Ida.");
  }
});

init();
