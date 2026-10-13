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
  if (tab === "anchor") loadAnchor();
}

async function init() {
  if (tg && tg.initData) {
    try {
      await fetch("/api/app/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ initData: tg.initData }),
      });
    } catch (e) {
      console.error("Auth failed", e);
    }
  }

  // Check URL params for details id
  const params = new URLSearchParams(window.location.search);
  const detailsId = params.get("d");
  if (detailsId) {
    loadDetails(detailsId);
  } else {
    loadAnchor();
  }
}

async function loadDetails(id) {
  try {
    const res = await fetch(`/api/app/details/${id}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById("details-content").innerHTML = `
        <div class="meta-row">
          <span class="mono">${data.id}</span>
          <span class="muted">${new Date(data.createdAt).toLocaleTimeString()}</span>
        </div>
        <div class="markdown-body" style="white-space: pre-wrap; font-family: monospace;">${escapeHtml(data.markdown)}</div>
      `;
      switchTab("details");
    }
  } catch (e) {
    console.error("Failed to load details", e);
  }
}

async function loadQuestions() {
  try {
    const res = await fetch("/api/app/questions");
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
        .map(
          (q) => `
        <div class="card" data-qid="${q.id}">
          <h3>${escapeHtml(q.question)}</h3>
          <div style="margin: 12px 0;">
            ${(q.options || [])
              .map(
                (opt, idx) => `
              <button class="btn btn-outline" style="margin-bottom: 6px; width: 100%; text-align: left;" onclick="answerQuestion('${q.id}', ${idx})">
                ${idx + 1}. ${escapeHtml(opt.label)}
              </button>
            `
              )
              .join("")}
          </div>
        </div>
      `
        )
        .join("");
    }
  } catch (e) {
    console.error("Failed to load questions", e);
  }
}

async function answerQuestion(qid, optIndex) {
  try {
    const res = await fetch("/api/app/questions/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ questionId: qid, optionIndex: optIndex }),
    });
    if (res.ok) {
      loadQuestions();
    }
  } catch (e) {
    console.error("Failed to answer question", e);
  }
}

async function loadAnchor() {
  try {
    const res = await fetch("/api/app/anchor");
    if (res.ok) {
      const data = await res.json();
      document.getElementById("anchor-focus").textContent = data.focus || "Stand by";
      document.getElementById("anchor-task").textContent = data.taskId || "-";
      document.getElementById("q-badge").textContent = data.pendingQuestions || 0;

      const pct = data.contextTokens?.percentage || 0;
      document.getElementById("anchor-pct").textContent = `${pct}%`;
      document.getElementById("anchor-gauge").style.width = `${pct}%`;
    }
  } catch (e) {
    console.error("Failed to load anchor", e);
  }
}

document.getElementById("btn-stop")?.addEventListener("click", async () => {
  if (confirm("Stop current session turn and ask Ida to report?")) {
    await fetch("/api/app/stop", { method: "POST" });
    alert("Stop signal sent to Ida.");
  }
});

function escapeHtml(str) {
  return (str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

init();
