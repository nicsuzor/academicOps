# Telegram HTML Widgets Reference (Bot API 10.4, Profile 1)

Use `send_widget`, `edit_message_widget_data`, and `answer_widget_query` in private chats (`chat_id > 0`) for Live Status trackers, progress panels, and structured multi-field interactions (`ask_user` handles Questions and Decisions automatically via its built-in widget). Group chats (`chat_id < 0`) do not support HTML Widgets; never silently downgrade a widget call there.

## Sandbox Profile 1 & Hard Quotas

| Constraint | Hard Limit | Operational Target & Rule |
| :- | :- | :- |
| Compressed HTML | `<= 4,096 B` (`zlib` level 9) | Keep source tight (`<= 3,696 B` recommended) using compact class names, `--tg-theme-*` tokens, and `const`/`function` minification. |
| Uncompressed HTML | `<= 32,768 B` UTF-8 | No NUL (`\0`) bytes. Rejected locally before network call if exceeded. |
| `public_data` / `chat_data` | `<= 1,024 B` each | Store only compact JSON state keys (e.g. `{ s, pct, steps, note, t }`). Empty string clears; omitting preserves existing value. |
| `width` / `height` | `width`: `200..bubble max`; `height`: `50..600` px | Design naturally for `360px` mobile width and `< 560px` height; omit `height` for responsive reflow via `W.ready()` or set explicit height when fixed geometry is required. Call `W.setResizeAnchor("top")` before toggling expandable blocks. |
| `TelegramWidget.request(p)` | `p <= 64 B`, timeout `15 s` | Requires `allow_queries: true` (defaults `false`). Answer inbound `widget_query` via `answer_widget_query` within `15 s` (`data <= 1,024 B`); there is no automatic background ack. |
| Fonts | `system-ui, sans-serif` | **Strictly** `font-family: system-ui, sans-serif`. Never use `BlinkMacSystemFont`, `Segoe UI`, `Roboto`, or remote web fonts. |
| Graphics & Icons | Inline `<svg>` only | Avoid ambiguous Unicode symbols (`✓`, `⏸`, `⌖`) that render as boxes on some engines; embed tiny inline `<svg>` paths with `stroke="currentColor"`. |
| Network & External Assets | Zero network/external URLs | Never emit `http://`, `https://`, `<script src>`, `<link>`, or external `<img src>`; widget runs inside QuickJS + Profile 1 isolated sandbox. |
| Forbidden Tags & Styles | Never use these | `<input>`, `<select>`, `<textarea>`, `<progress>`, `<meter>`, `overflow: auto`, `overflow: scroll`. Build progress bars with nested `<div>` tracks and buttons/cards with `<button>` / `click` handlers. |

## Security, Forwarding & `WidgetRequestError` Handling

- `allow_queries` defaults to `false`: enable `allow_queries: true` only when `TelegramWidget.request()` actually sends callbacks back to the bot.
- Forwarded or shared widgets (`is_shared` or forwarded message) disable queries on the recipient client; `TelegramWidget.request()` rejects with `WidgetRequestError`.
- Always wrap `TelegramWidget.request(payload)` in `try / catch` and surface `e.code` inline in a visible banner:
  - `TIMEOUT` -> `"Timed out (15s) -- tap to retry"`
  - `NOT_ALLOWED` -> `"Actions disabled on forwarded widgets"`
  - `RATE_LIMITED` -> `"Too many taps -- wait briefly"`
  - Fallback -> `e.message || "Request failed"`

## Starter Template: Live Multi-Step Status Tracker (`<= 1,900 B` zlib-9)

Send once with `send_widget({ html, caption: "Status: ...", chat_data: JSON.stringify(...) })` (`allow_queries: false` for read-only progress, or `true` if `act: 1` query button is enabled), then update silently in place using `edit_message_widget_data({ message_id, chat_data })`:

```json
{
  "t": "Release validation pipeline",
  "s": "running",
  "pct": 60,
  "up": "14:22",
  "note": "Running integration checks",
  "steps": [
    { "l": "Rebase branch and verify clean baseline test suite", "st": "done" },
    {
      "l": "Run full plugin test suite with headless visual verification pass across light and dark mobile viewports",
      "st": "run"
    },
    { "l": "Open pull request for review", "st": "todo" }
  ]
}
```

Status values for top state (`s`): `"running"`, `"done"`, `"blocked"`, `"paused"`. Step statuses (`st`): `"done"`, `"run"`, `"todo"`, `"err"`. Optional `"act": 1` displays a `Refresh` button (`TelegramWidget.request("st:refresh")`, handled by caller + `answer_widget_query`). Notice long step titles wrap naturally across 2 lines with top-aligned icons, and `edit_message_widget_data` returns `{ not_modified: true }` cleanly on idempotent updates:

```html
<!DOCTYPE html><html><head><meta charset="utf-8"><style>
:root{color-scheme:light dark;--bg:var(--tg-theme-bg-color,light-dark(#fff,#182533));--sc:var(--tg-theme-secondary-bg-color,light-dark(#f2f4f7,#202e3d));--tx:var(--tg-theme-text-color,light-dark(#14171a,#f2f5f8));--ht:var(--tg-theme-hint-color,light-dark(#67737e,#8d9dad));--ac:var(--tg-theme-button-color,light-dark(#2481cc,#4b96e6));--at:var(--tg-theme-button-text-color,#fff);--bd:light-dark(rgba(20,23,26,.1),rgba(255,255,255,.1));--ob:light-dark(#e7f6ec,#183a28);--ot:light-dark(#1b7a3d,#69db92);--wb:light-dark(#fff5e6,#3b2e19);--wt:light-dark(#b25e09,#f6ad55);--eb:light-dark(#fdeceb,#3e1e1e);--et:var(--tg-theme-destructive-text-color,light-dark(#c93b32,#ff7b72))}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;font-size:13px;line-height:1.35;background:var(--bg);color:var(--tx);padding:12px 18px max(22px,env(safe-area-inset-bottom,22px)) max(22px,var(--tg-content-safe-area-corner-left,22px))}
.tp{display:flex;align-items:center;gap:8px;margin-bottom:5px}.pl{font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:4px 7px;border-radius:6px;background:var(--sc);color:var(--ac)}.pl.dn{background:var(--ob);color:var(--ot)}.pl.bk{background:var(--eb);color:var(--et)}.pl.ps{background:var(--wb);color:var(--wt)}
.mt{font-size:11px;color:var(--ht);margin-left:auto}h1{font-size:15px;font-weight:600;line-height:1.28;margin-bottom:8px}
.pr{display:flex;align-items:center;gap:8px;margin-bottom:9px}.tr{flex:1;height:6px;border-radius:99px;background:var(--sc);overflow:hidden}.fl{height:100%;background:var(--ac);border-radius:99px;transition:width .25s}.fl.dn{background:var(--ot)}.fl.bk{background:var(--et)}.pc{font-size:11px;font-weight:600;color:var(--ht);min-width:30px;text-align:right}
.er{display:none;background:var(--eb);color:var(--et);border-radius:8px;padding:7px 10px;font-size:12px;margin-bottom:8px}.er.sh{display:block}
.ss{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}.st{display:flex;align-items:flex-start;gap:8px;padding:6px 8px;border:1px solid var(--bd);border-radius:9px}
.ic{width:15px;height:15px;margin-top:2px;flex:none;display:flex;align-items:center;justify-content:center;color:var(--ht)}.ic.done{color:var(--ot)}.ic.run{color:var(--ac)}.ic.err{color:var(--et)}
.sl{flex:1;min-width:0;font-size:12.5px;line-height:1.32;word-break:break-word;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.st.todo .sl{color:var(--ht)}.ft{display:flex;align-items:center;justify-content:space-between;gap:8px;font-size:11.5px;color:var(--ht);padding-right:max(0px,calc(var(--tg-content-safe-area-corner-right,0px) - 8px))}
.bt{display:none;border:0;border-radius:7px;background:var(--sc);color:var(--tx);font-size:11.5px;font-weight:600;padding:5px 9px;cursor:pointer}.bt.sh{display:inline-block}
</style></head><body>
<div class="tp"><span class="pl" id="pl">RUNNING</span><span class="mt" id="up"></span></div>
<h1 id="ti"></h1>
<div class="pr"><div class="tr"><div class="fl" id="fl"></div></div><span class="pc" id="pc">0%</span></div>
<div class="er" id="er"></div><div class="ss" id="ss"></div>
<div class="ft"><span id="nt"></span><button class="bt" id="rf">Refresh</button></div>
<script>
const W=window.TelegramWidget,$=i=>document.getElementById(i),E=s=>String(s).replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));
const I={done:'<svg viewBox="0 0 12 12" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M2 6.5 4.8 9.2 10 3"/></svg>',run:'<svg viewBox="0 0 12 12" width="10" height="10" fill="currentColor"><circle cx="6" cy="6" r="4"/></svg>',todo:'<svg viewBox="0 0 12 12" width="10" height="10" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="6" cy="6" r="3.8"/></svg>',err:'<svg viewBox="0 0 12 12" width="11" height="11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 3 9 9M9 3 3 9"/></svg>'};
let err="",busy=0;function st(){try{return W&&W.chatData?JSON.parse(W.chatData):{}}catch{return{}}}
function draw(){const d=st(),md=d.s||"running",pct=Math.max(0,Math.min(100,Number(d.pct||0)));if(d.err)err=d.err;
const cls=md==="done"?" dn":md==="blocked"?" bk":md==="paused"?" ps":"";
$("pl").className="pl"+cls;$("pl").textContent=md.toUpperCase();$("up").textContent=d.up||"";$("ti").textContent=d.t||"Status";
$("fl").className="fl"+cls;$("fl").style.width=pct+"%";$("pc").textContent=pct+"%";
$("er").textContent=err;$("er").className="er"+(err?" sh":"");
$("ss").innerHTML=(d.steps||[]).map(x=>'<div class="st '+(x.st||"todo")+'"><span class="ic '+(x.st||"todo")+'">'+(I[x.st]||I.todo)+'</span><span class="sl">'+E(x.l||"")+'</span></div>').join("");
$("nt").textContent=busy?"Refreshing…":(d.note||"");$("rf").className="bt"+(d.act?" sh":"");$("rf").disabled=busy}
$("rf").addEventListener("click",async()=>{if(!W||busy)return;busy=1;err="";draw();try{await W.request("st:refresh")}catch(e){err=e&&e.name==="WidgetRequestError"?(e.code==="TIMEOUT"?"Timed out (15s) \\u2014 tap to retry":e.code==="NOT_ALLOWED"?"Actions disabled on forwarded widgets":e.code==="RATE_LIMITED"?"Too many taps \\u2014 wait briefly":e.message):"Request failed"}finally{busy=0;draw()}});
if(W){W.onEvent("chatDataChanged",draw);W.ready()}draw();
</script></body></html>
```
