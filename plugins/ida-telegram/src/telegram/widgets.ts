import zlib from "node:zlib";

export const WIDGET_MAX_HTML_BYTES = 32_768;
export const WIDGET_MAX_COMPRESSED_BYTES = 4_096;
export const WIDGET_MAX_DATA_BYTES = 1_024;
export const WIDGET_MAX_CAPTION_CHARS = 1_024;

export interface WidgetValidationOk {
  ok: true;
  rawBytes: number;
  compressedBytes: number;
}

export interface WidgetValidationErr {
  ok: false;
  error: string;
}

export function validateWidgetHtml(html: unknown): WidgetValidationOk | WidgetValidationErr {
  if (typeof html !== "string" || html.length === 0) {
    return { ok: false, error: "Widget html must be a non-empty string" };
  }
  if (html.includes("\0")) {
    return { ok: false, error: "Widget html must not contain NUL bytes" };
  }
  const buf = Buffer.from(html, "utf8");
  if (buf.byteLength > WIDGET_MAX_HTML_BYTES) {
    return {
      ok: false,
      error: `Widget html raw size ${buf.byteLength} B exceeds ${WIDGET_MAX_HTML_BYTES} B limit`,
    };
  }
  const compressedBytes = zlib.deflateSync(buf, { level: 9 }).length;
  if (compressedBytes > WIDGET_MAX_COMPRESSED_BYTES) {
    return {
      ok: false,
      error: `Widget html zlib-9 compressed size ${compressedBytes} B exceeds ${WIDGET_MAX_COMPRESSED_BYTES} B limit`,
    };
  }
  return { ok: true, rawBytes: buf.byteLength, compressedBytes };
}

export function validateWidgetData(label: string, data: unknown): { ok: true } | WidgetValidationErr {
  if (data === undefined) return { ok: true };
  if (typeof data !== "string") {
    return { ok: false, error: `${label} must be a UTF-8 string` };
  }
  const bytes = Buffer.byteLength(data, "utf8");
  if (bytes > WIDGET_MAX_DATA_BYTES) {
    return { ok: false, error: `${label} size ${bytes} B exceeds ${WIDGET_MAX_DATA_BYTES} B limit` };
  }
  return { ok: true };
}

export function formatLocal24hTime(date: Date = new Date()): string {
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

export function buildSettledWidgetChatData(
  status: "answered" | "deferred" | "closed" | "awaiting_reply",
  label: string,
  note?: string
): string {
  const payload: Record<string, string> = {
    s: status,
    lbl: label.length > 320 ? `${label.slice(0, 317)}...` : label,
    t: formatLocal24hTime(),
  };
  if (note) {
    payload.note = note.length > 320 ? `${note.slice(0, 317)}...` : note;
  }
  const serialized = JSON.stringify(payload);
  if (Buffer.byteLength(serialized, "utf8") <= WIDGET_MAX_DATA_BYTES) {
    return serialized;
  }
  return JSON.stringify({ s: status, lbl: payload.lbl.slice(0, 120), t: payload.t });
}

export interface WidgetPromptOption {
  label: string;
  description?: string;
  recommended?: boolean;
  pros?: string[];
  cons?: string[];
}

export interface WidgetPromptInput {
  id: string;
  question: string;
  header?: string;
  context?: string;
  kind?: "question" | "decision";
  stakes?: string;
  multiSelect?: boolean;
  allowOther?: boolean;
  allowDefer?: boolean;
  options: WidgetPromptOption[];
}

const SVG_D_CHK = `<path d="M2 6.5 4.8 9.2 10 3"/>`;
const SVG_D_DN = `<path d="M2.5 4.5 6 8 9.5 4.5"/>`;
const SVG_D_UP = `<path d="M2.5 7.5 6 4 9.5 7.5"/>`;
const SVG_D_PS = `<rect x="2.5" y="2" width="2.6" height="8" rx=".8"/><rect x="6.9" y="2" width="2.6" height="8" rx=".8"/>`;

function escHtml(s: string | undefined): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildWidgetCaption(input: WidgetPromptInput): string {
  const prefix = input.header?.trim() ? `${input.header.trim()}: ` : "";
  const firstLine = input.question.split("\n")[0]?.trim() || "Interactive prompt";
  const raw = `${prefix}${firstLine}`;
  return raw.length > 200 ? `${raw.slice(0, 197)}...` : raw;
}

function stripSpoilerAndMarkdown(text: string): string {
  return text
    .replace(/^>!\s*/gm, "")
    .replace(/`([^`]+)`/g, "$1")
    .trim();
}

export function buildQuestionWidget(input: WidgetPromptInput): {
  html: string;
  chatData: string;
  caption: string;
  compressedBytes: number;
} {
  const isDec = input.kind === "decision";
  const multi = !isDec && Boolean(input.multiSelect);
  const hasT = input.options.some((o) => (o.pros?.length || 0) + (o.cons?.length || 0) > 0);
  const ps = hasT ? 2 : 3;
  const hasPg = input.options.length > ps;
  const allowDef = Boolean(input.allowDefer);
  const allowOth = input.allowOther !== false;

  const recIdx = input.options.findIndex((o) => o.recommended || /\(recommended\)/i.test(o.label));
  const initSel = isDec ? (recIdx >= 0 ? recIdx : 0) : -1;

  const optsJson = JSON.stringify(
    input.options.map((o, i) => {
      const row: Record<string, unknown> = { i, l: o.label };
      if (o.description) row.d = o.description;
      if (o.recommended || /\(recommended\)/i.test(o.label)) row.r = 1;
      if (hasT && o.pros?.length) row.p = o.pros;
      if (hasT && o.cons?.length) row.c = o.cons;
      return row;
    })
  );

  const cssVars =
    `--bg:var(--tg-theme-bg-color,light-dark(#fff,#182533));` +
    `--sc:var(--tg-theme-secondary-bg-color,light-dark(#f2f4f7,#202e3d));` +
    `--tx:var(--tg-theme-text-color,light-dark(#14171a,#f2f5f8));` +
    `--ht:var(--tg-theme-hint-color,light-dark(#67737e,#8d9dad));` +
    `--ac:var(--tg-theme-button-color,light-dark(#2481cc,#4b96e6));` +
    `--at:var(--tg-theme-button-text-color,#fff);` +
    `--bd:light-dark(#14171a1a,#ffffff1a);` +
    `--sl:light-dark(#edf5fd,#1b3550);` +
    `--ob:light-dark(#e7f6ec,#183a28);--ot:light-dark(#1b7a3d,#69db92);` +
    `--wb:light-dark(#fff5e6,#3b2e19);--wt:light-dark(#b25e09,#f6ad55);` +
    `--eb:light-dark(#fdeceb,#3e1e1e);--et:var(--tg-theme-destructive-text-color,light-dark(#c93b32,#ff7b72))`;

  const trCss = hasT
    ? `.m{background:var(--sc);border-radius:7px;color:var(--ac);padding:5px 8px;min-height:28px;flex:none;margin-left:4px;display:inline-flex;align-items:center;gap:4px}` +
      `.tr{margin-top:6px;padding-top:6px;border-top:1px solid var(--bd);font-size:11.5px;line-height:1.35;display:none;gap:3px;flex-direction:column}.tr.op{display:flex}.pr{color:var(--ot)}.cn{color:var(--et)}`
    : "";

  const pgCss = hasPg
    ? `.pg{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:12px;color:var(--ht)}` +
      `.pb{background:var(--sc);border-radius:7px;color:var(--tx);padding:5px 9px}.pb:disabled{opacity:.45}`
    : "";

  const needSg = !isDec && !multi;
  const sgCss = needSg ? `.sg{display:none;font-size:12px;color:var(--ac);margin-bottom:6px}.sg.sh{display:block}` : "";

  const css =
    `:root{color-scheme:light dark;${cssVars}}` +
    `*{box-sizing:border-box;margin:0;padding:0}` +
    `body{font-family:system-ui,sans-serif;font-size:13.5px;line-height:1.38;background:var(--bg);color:var(--tx);padding:12px 18px max(22px,env(safe-area-inset-bottom,22px)) max(22px,var(--tg-content-safe-area-corner-left,22px))}` +
    `.m,.pb,.b{border:0;cursor:pointer;font-weight:600;font-size:11.5px}` +
    `.lb,.dt,.rc{font-weight:600}` +
    `.tp{display:flex;align-items:center;gap:8px;margin-bottom:5px}` +
    `.pl,.rc{font-size:10px;line-height:1;border-radius:5px;padding:3px 6px}` +
    `.pl{font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:4px 7px;background:var(--sc);color:var(--ac)}` +
    `.mt{font-size:11px;color:var(--ht);margin-left:auto}` +
    `h1{font-size:15px;font-weight:600;line-height:1.28;margin-bottom:4px}` +
    `.sb,.ds,.dd{font-size:12px;line-height:1.33;color:var(--ht)}` +
    `.sb{margin-bottom:8px}.ds{margin-top:3px}.dd{margin-top:2px}` +
    `.er{display:none;background:var(--eb);color:var(--et);border-radius:8px;padding:7px 10px;font-size:12px;margin-bottom:8px}.er.sh{display:block}` +
    sgCss +
    `.os{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}` +
    `.o{border:1px solid var(--bd);border-radius:10px;padding:8px 10px;cursor:pointer}` +
    `.o.on{border-color:var(--ac);background:var(--sl);box-shadow:inset 0 0 0 1px var(--ac)}` +
    `.rw{display:flex;align-items:flex-start;gap:8px}` +
    `.id{width:16px;height:16px;border-radius:4px;border:2px solid var(--ht);margin-top:1px;flex:none;display:flex;align-items:center;justify-content:center;color:var(--at)}.id.rd{border-radius:50%}` +
    `.o.on .id{border-color:var(--ac);background:var(--ac)}.o.on .id.rd::after{content:"";width:6px;height:6px;border-radius:50%;background:var(--at)}` +
    `.bd{flex:1;min-width:0}.lb{font-size:13px;line-height:1.25;display:block}` +
    `.rc{display:inline-block;margin-top:3px;background:var(--ob);color:var(--ot)}` +
    trCss +
    pgCss +
    `.ft{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding-right:max(0px,calc(var(--tg-content-safe-area-corner-right,0px) - 8px))}` +
    `.u2{display:flex;gap:6px;width:100%}` +
    `.b{border-radius:9px;padding:8px 12px;font-size:13px;line-height:1.15;white-space:nowrap}` +
    `.pri{width:100%;background:var(--ac);color:var(--at);overflow:hidden;text-overflow:ellipsis}.pri:disabled{background:var(--sc);color:var(--ht)}` +
    `.gh{background:var(--sc);color:var(--tx);flex:1;text-align:center}` +
    `.dn{border-radius:10px;padding:10px 11px;background:var(--ob);display:none;gap:9px;align-items:flex-start}` +
    `.dn.sh{display:flex}.dn.wt{background:var(--wb)}.dn.wt .dm{color:var(--wt)}.dm{color:var(--ot);margin-top:2px;flex:none;display:flex}` +
    `.dt{font-size:13px;line-height:1.3}`;

  const utilCount = (allowDef ? 1 : 0) + (allowOth ? 1 : 0);
  const goHtml = isDec || multi ? `<button class="b pri" id="go"></button>` : "";
  const utilBtns =
    (allowDef ? `<button class="b gh" id="df">Defer</button>` : "") +
    (allowOth ? `<button class="b gh" id="ot">Other…</button>` : "");
  const utilRow = utilCount > 0 ? (goHtml && utilCount > 1 ? `<div class="u2">${utilBtns}</div>` : utilBtns) : "";
  const pgHtml = hasPg
    ? `<div class="pg" id="pg"><button class="b pb" id="pv">‹ Prev</button><span id="pl"></span><button class="b pb" id="nx">Next ›</button></div>`
    : "";

  const subText = input.context ? stripSpoilerAndMarkdown(input.context) : "";
  const subHtml = subText ? `<p class="sb">${escHtml(subText)}</p>` : "";
  const topMeta = escHtml(input.stakes || (multi ? "Multi-select" : isDec ? "Decision" : "Tap an option"));
  const badgeText = escHtml(input.header || (isDec ? "DECISION" : "QUESTION"));
  const qLines = input.question.split("\n");
  const titleText = stripSpoilerAndMarkdown(qLines[0] || input.question);
  const extraBody = !subHtml && qLines.length > 1 ? `<p class="sb">${escHtml(stripSpoilerAndMarkdown(qLines.slice(1).join(" ")))}</p>` : subHtml;

  const baseState = isDec
    ? `let sel=${initSel},exp=${!hasPg && initSel >= 0 ? `{${initSel}:1}` : "{}"},busy=0,err="";`
    : multi
      ? `let pk=new Set(),busy=0,err="";`
      : `let sel=-1,busy=0,err="";`;

  const script =
    `const W=window.TelegramWidget,H=W&&W.HapticFeedback,Q=${JSON.stringify(input.id)},O=${optsJson},` +
    `S=(p,f)=>'<svg viewBox="0 0 12 12" width="11" height="11" '+(f?'fill="currentColor">':'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">')+p+'</svg>',` +
    `C=S('${SVG_D_CHK}'),D=S('${SVG_D_DN}'),U=S('${SVG_D_UP}'),P=S('${SVG_D_PS}',1);` +
    `${baseState}${hasPg ? "let pg=0;" : ""}` +
    `const $=i=>document.getElementById(i),E=s=>String(s).replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));` +
    `function st(){try{return W&&W.chatData?JSON.parse(W.chatData):{}}catch{return{}}}` +
    `function hhmm(){const d=new Date();return String(d.getHours()).padStart(2,"0")+":"+String(d.getMinutes()).padStart(2,"0")}` +
    `function draw(){` +
    `const s=st();if(s.err)err=s.err;$("er").textContent=err;$("er").className="er"+(err?" sh":"");` +
    `${needSg ? `$("sg").className="sg"+(busy?" sh":"");` : ""}` +
    `const md=s.s;` +
    `if(md==="answered"||md==="deferred"||md==="closed"||md==="awaiting_reply"){` +
    `$("os").style.display="none";${hasPg ? '$("pg").style.display="none";' : ""}$("ft").style.display="none";${needSg ? `$("sg").className="sg";` : ""}` +
    `$("dc").className="dn sh"+(md==="awaiting_reply"||md==="deferred"?" wt":"");` +
    `$("dm").innerHTML=md==="deferred"?P:(md==="awaiting_reply"?"…":C);` +
    `$("dt").textContent=md==="deferred"?"Deferred":md==="awaiting_reply"?"Awaiting reply in chat":md==="closed"?"Closed: "+(s.note||"Resolved"):("Selected: "+(s.lbl||"Recorded"));` +
    `$("dn").textContent=s.note||(md==="awaiting_reply"?"Reply directly in chat to answer":"Recorded · "+(s.t||hhmm()));return}` +
    `${isDec ? "if(typeof s.sel==='number')sel=s.sel;if(s.exp)exp=Object.assign({},exp,s.exp);" : multi ? "if(Array.isArray(s.pk))pk=new Set(s.pk);" : "if(typeof s.sel==='number')sel=s.sel;"}` +
    `${hasPg ? `const ps=${ps},pgs=Math.max(1,Math.ceil(O.length/ps));if(pg>=pgs)pg=pgs-1;const sl=O.slice(pg*ps,(pg+1)*ps);$("pl").textContent=(pg+1)+" / "+pgs;$("pv").disabled=pg===0;$("nx").disabled=pg>=pgs-1;` : "const sl=O;"}` +
    `$("os").innerHTML=sl.map(o=>{const on=${multi ? "pk.has(o.i)" : "sel===o.i"};${hasT ? "const ht=o.p||o.c,op=!!exp[o.i];" : ""}` +
    `return '<div class="o'+(on?" on":"")+'" data-i="'+o.i+'"><div class="rw"><span class="id ${multi ? "" : "rd"}">${multi ? "'+(on?C:'')'" : ""}</span><div class="bd"><span class="lb">'+E(o.l)+'</span>'+(o.r?'<span class="rc">Recommended</span>':"")+(o.d?'<div class="ds">'+E(o.d)+'</div>':"")+${hasT ? `(ht?'<div class="tr'+(op?" op":"")+'">'+(o.p?o.p.map(x=>'<div class="pr">+ '+E(x)+'</div>').join(""):"")+(o.c?o.c.map(x=>'<div class="cn">− '+E(x)+'</div>').join(""):"")+'</div>':"")` : `""`}+'</div>'+${hasT ? `(ht?'<button class="m" data-t="'+o.i+'">'+(op?"Less "+U:"Why "+D)+"</button>":"")` : `""`}+'</div></div>'}).join("");` +
    `${isDec ? `const cur=O[sel],lb=cur?cur.l:"";$("go").disabled=busy||!cur;$("go").textContent=busy?"Sending…":(cur?(cur.r?"Accept recommendation":"Choose: "+(lb.length>22?lb.slice(0,21)+"…":lb)):"Choose");` : ""}` +
    `${multi ? `$("go").disabled=busy||!pk.size;$("go").textContent=busy?"Sending…":(pk.size?"Submit ("+pk.size+")":"Select options");` : ""}` +
    `${allowDef ? `$("df").disabled=busy;` : ""}${allowOth ? `$("ot").disabled=busy;` : ""}` +
    `}` +
    `const EM={TIMEOUT:"Timed out (15s) \\u2014 retry",NOT_ALLOWED:"Forwarded widget disabled",RATE_LIMITED:"Slow down \\u2014 retry"};` +
    `async function req(p){if(!W)return;busy=1;err="";draw();try{H&&H.notificationOccurred("success");await W.request(p)}catch(e){err=e&&e.name==="WidgetRequestError"?(EM[e.code]||e.message):"Request failed"}finally{busy=0;draw()}}` +
    `$("os").addEventListener("click",e=>{` +
    `${hasT ? `const tb=e.target.closest("[data-t]");if(tb){e.stopPropagation();if(W&&typeof W.setResizeAnchor==="function")W.setResizeAnchor("top");const i=+tb.dataset.t;exp[i]=!exp[i];draw();return}` : ""}` +
    `const el=e.target.closest("[data-i]");if(!el||busy)return;const i=+el.dataset.i;` +
    `${multi ? `pk.has(i)?pk.delete(i):pk.add(i);H&&H.selectionChanged();draw();` : isDec ? `sel=i;H&&H.selectionChanged();draw();` : `sel=i;req("q:"+Q+":opt:"+i);`}` +
    `});` +
    `${isDec ? `$("go").addEventListener("click",()=>{if(O[sel])req("q:"+Q+":opt:"+sel)});` : ""}` +
    `${multi ? `$("go").addEventListener("click",()=>{if(pk.size)req("q:"+Q+":m:"+[...pk].reduce((a,i)=>a+(1<<i),0).toString(36))});` : ""}` +
    `${hasPg ? `$("pv").addEventListener("click",()=>{if(pg>0){pg--;draw()}});$("nx").addEventListener("click",()=>{pg++;draw()});` : ""}` +
    `${allowDef ? `$("df").addEventListener("click",()=>req("q:"+Q+":defer"));` : ""}` +
    `${allowOth ? `$("ot").addEventListener("click",()=>req("q:"+Q+":other"));` : ""}` +
    `if(W){W.onEvent("chatDataChanged",draw);W.ready()}if(st().busy)busy=1;draw();`;

  // Fix multi-select checkmark interpolation expression in map cleanly:
  const fixedScript = script.replace(`'+(on?C:'')'`, `'+(on?C:"")+'`);

  const html =
    `<!DOCTYPE html><html><head><meta charset="utf-8"><style>${css}</style></head><body>` +
    `<div class="tp"><span class="pl">${badgeText}</span><span class="mt">${topMeta}</span></div>` +
    `<h1>${escHtml(titleText)}</h1>${extraBody}` +
    `<div class="er" id="er"></div>${needSg ? `<div class="sg" id="sg">Sending…</div>` : ""}` +
    `<div class="dn" id="dc"><span class="dm" id="dm"></span><div><div class="dt" id="dt"></div><div class="dd" id="dn"></div></div></div>` +
    `<div class="os" id="os"></div>${pgHtml}` +
    `<div class="ft" id="ft">${goHtml}${utilRow}</div>` +
    `<script>${fixedScript}</script></body></html>`;

  const check = validateWidgetHtml(html);
  if (!check.ok) {
    throw new Error(check.error);
  }

  return {
    html,
    chatData: JSON.stringify({ s: "open" }),
    caption: buildWidgetCaption(input),
    compressedBytes: check.compressedBytes,
  };
}

export function formatQuestionRichMarkdown(input: WidgetPromptInput): string {
  const parts: string[] = [];
  if (input.header) {
    parts.push(`### ${input.header}`);
  }
  parts.push(`**${input.question}**`);
  if (input.context) {
    parts.push(input.context);
  }
  const hasDetails = input.options.some((o) => o.description || o.pros?.length || o.cons?.length);
  if (hasDetails) {
    const optionLines = input.options.map((o, idx) => {
      const rec = o.recommended || /\(recommended\)/i.test(o.label) ? " *(Recommended)*" : "";
      const head = `${idx + 1}. **${o.label}**${rec}${o.description ? ` — ${o.description}` : ""}`;
      const pros = o.pros?.map((p) => `   + ${p}`).join("\n") || "";
      const cons = o.cons?.map((c) => `   − ${c}`).join("\n") || "";
      return [head, pros, cons].filter(Boolean).join("\n");
    });
    parts.push(`<details>\n<summary>Options & trade-offs</summary>\n\n${optionLines.join("\n\n")}\n\n</details>`);
  }
  if (input.stakes) {
    parts.push(`<footer>Stakes: ${escHtml(input.stakes)}</footer>`);
  }
  return parts.join("\n\n");
}
