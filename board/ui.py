"""The live board, as a web page. GIVEN.

Open http://localhost:8080/ while ./run is going and watch it move. This is the
fastest way to see what your build is actually doing — and on day 2, to watch a
failure land in real time instead of reading it out of a log afterwards.

It is a read-only view. It polls /board and /log and draws them. Nothing here
can change the board.
"""

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ground Ops · live board</title>
<style>
:root{
  --ink:#1C0A2E; --ink2:#2A1140; --cream:#FFF6F0;
  --lime:#CDFF3A; --cyan:#2EE6D6; --gold:#FFC93C; --bad:#FF3B6B; --warn:#FFA33C;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  --disp:ui-rounded,"SF Pro Rounded",system-ui,-apple-system,"Segoe UI",sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:
   radial-gradient(60vmax 60vmax at 10% -10%,rgba(255,106,61,.20),transparent 60%),
   radial-gradient(55vmax 55vmax at 105% 110%,rgba(46,230,214,.14),transparent 60%),
   var(--ink);
  color:var(--cream);font-family:var(--disp);min-height:100vh;padding:22px 26px 40px}
.wrap{max-width:1500px;margin:0 auto}
header{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:1.5rem;font-weight:800;letter-spacing:-.01em}
.sub{font-family:var(--mono);font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;opacity:.55}
.stats{margin-left:auto;display:flex;gap:9px;flex-wrap:wrap}
.stat{font-family:var(--mono);font-size:.76rem;font-weight:700;border:2px solid rgba(255,246,240,.22);
  border-radius:999px;padding:.38em .8em;white-space:nowrap}
.stat b{color:var(--lime)}
.stat.hot{border-color:var(--bad);color:var(--bad)} .stat.hot b{color:var(--bad)}
h2{font-family:var(--mono);font-size:.74rem;letter-spacing:.18em;text-transform:uppercase;
  opacity:.55;margin:22px 0 10px;font-weight:700}
.grid{display:grid;gap:11px}
.gates{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.slots{grid-template-columns:repeat(auto-fit,minmax(160px,1fr))}
.pieces{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.cell{border:2.5px solid rgba(255,246,240,.2);border-radius:14px;padding:12px 14px;
  background:rgba(255,246,240,.04);transition:border-color .3s,background .3s}
.cell .id{font-family:var(--mono);font-size:.78rem;font-weight:700;letter-spacing:.1em;opacity:.55}
.cell .who{font-family:var(--mono);font-size:1.15rem;font-weight:700;margin-top:5px}
.cell .meta{font-family:var(--mono);font-size:.7rem;opacity:.5;margin-top:3px}
.cell.free{border-style:dashed;border-color:rgba(255,201,60,.5);background:rgba(255,201,60,.05)}
.cell.free .who{color:var(--gold);opacity:.65}
.cell.on{border-color:var(--lime);background:rgba(205,255,58,.11)} .cell.on .who{color:var(--lime)}
.cell.late{border-color:var(--bad);background:rgba(255,59,107,.14);animation:beat 1.1s infinite}
.cell.late .who{color:var(--bad)}
.cell.shut{border-color:var(--bad);border-style:dashed;background:rgba(255,59,107,.07)}
.cell.shut .who{color:var(--bad);opacity:.7}
@keyframes beat{0%,100%{background:rgba(255,59,107,.10)}50%{background:rgba(255,59,107,.26)}}
.cell.up{border-color:var(--cyan);background:rgba(46,230,214,.09)} .cell.up .who{color:var(--cyan);font-size:.95rem}
.cell.down{border-color:var(--bad);background:rgba(255,59,107,.12)} .cell.down .who{color:var(--bad);font-size:.95rem}
table{width:100%;border-collapse:collapse;font-family:var(--mono);font-size:.82rem}
th{text-align:left;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;opacity:.45;
  padding:0 10px 7px;font-weight:700}
td{padding:7px 10px;border-top:1px solid rgba(255,246,240,.09)}
tr.late td{color:var(--bad)} tr.held td{color:var(--warn)} tr.placed td .st{color:var(--lime)}
.pill{font-size:.72rem;font-weight:700;border-radius:6px;padding:.16em .5em;border:1.5px solid currentColor}
.log{font-family:var(--mono);font-size:.76rem;line-height:1.75;max-height:330px;overflow:auto;
  border:2px solid rgba(255,246,240,.13);border-radius:12px;padding:11px 14px;background:rgba(0,0,0,.22)}
.log div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.log .t{opacity:.4;margin-right:.7em}
.log .a{color:var(--cyan);margin-right:.7em}
.log .a.HARNESS{color:var(--bad);font-weight:700}
.log .e{color:var(--cream);opacity:.85}
.log .e.claim_ok,.log .e.slot_ok{color:var(--lime)}
.log .e.claim_rejected,.log .e.slot_rejected{color:var(--bad);font-weight:700}
.log .e.fallback{color:var(--gold);font-weight:700}
.log .e.delay,.log .e.close_runway,.log .e.clock_skew{color:var(--bad);font-weight:700}
.log .e.duplicate_merged{opacity:.45}
.two{display:grid;grid-template-columns:1.15fr .85fr;gap:24px;align-items:start}
@media(max-width:1000px){.two{grid-template-columns:1fr}}
.dead{color:var(--bad);font-family:var(--mono);font-size:.8rem;margin-top:8px}
.chatter{float:right;font-family:var(--mono);font-size:.66rem;letter-spacing:.08em;
  opacity:.6;cursor:pointer;text-transform:none;font-weight:600;display:flex;gap:.4em;align-items:center}
.chatter input{accent-color:var(--lime);cursor:pointer}
</style></head><body><div class="wrap">

<header>
  <h1>KHI · Ground Ops</h1>
  <span class="sub" id="mode">live board</span>
  <div class="stats">
    <span class="stat">clock <b id="clock">–</b></span>
    <span class="stat" id="skewPill" style="display:none">skew <b id="skew">–</b></span>
    <span class="stat">writes <b id="writes">–</b></span>
    <span class="stat" id="ratePill">rate <b id="rate">–</b>/s</span>
    <span class="stat">flights <b id="nflights">–</b></span>
  </div>
</header>

<h2>Gates</h2>
<div class="grid gates" id="gates"></div>

<h2>Runway slots</h2>
<div class="grid slots" id="slots"></div>

<h2>The pieces</h2>
<div class="grid pieces" id="pieces"></div>

<div class="two">
  <div>
    <h2>Flights</h2>
    <table><thead><tr><th>flight</th><th>kind</th><th>eta</th><th>gate</th><th>slot</th>
      <th>status</th><th>last touched by</th></tr></thead><tbody id="flights"></tbody></table>
  </div>
  <div>
    <h2>Board log <label class="chatter"><input type="checkbox" id="chatter"> show feed chatter</label></h2>
    <div class="log" id="log"></div>
  </div>
</div>

</div>
<script>
let PIECES = {};                 // filled from /pieces — the team's real addresses
let lastWrites = null, lastT = null;

const el = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[<>&]/g, c => ({"<":"&lt;",">":"&gt;","&":"&amp;"}[c]));

async function tick(){
  let b;
  try { b = await (await fetch("/board")).json(); }
  catch { el("mode").textContent = "board not reachable"; return; }
  el("mode").textContent = "live board";

  el("clock").textContent  = "+" + b.now + " min";
  el("writes").textContent = b.writes;
  el("nflights").textContent = Object.keys(b.flights).length;
  if (b.flights.__skew__ === undefined && b.now !== undefined) {}

  const now = performance.now();
  if (lastWrites !== null) {
    const r = (b.writes - lastWrites) / ((now - lastT) / 1000);
    el("rate").textContent = r.toFixed(1);
    el("ratePill").classList.toggle("hot", r > 8);
  }
  lastWrites = b.writes; lastT = now;

  // gates
  el("gates").innerHTML = Object.entries(b.gates).map(([g, who]) => {
    const f = who ? b.flights[who] : null;
    const late = f && f.delay_min > 0;
    const cls = !who ? "free" : (late ? "late" : "on");
    return `<div class="cell ${cls}"><div class="id">${g}</div>
      <div class="who">${who ? esc(who) : "— free —"}</div>
      <div class="meta">${f ? (late ? "+" + f.delay_min + " MIN LATE · " : "") + esc(f.status) : "available"}</div></div>`;
  }).join("");

  // slots
  el("slots").innerHTML = Object.entries(b.slots).map(([s, who]) => {
    const shut = b.closed_slots.includes(s);
    const cls = shut ? "shut" : (who ? "on" : "free");
    return `<div class="cell ${cls}"><div class="id">${s}</div>
      <div class="who">${shut ? "CLOSED" : (who ? esc(who) : "— free —")}</div>
      <div class="meta">${shut ? "runway shut" : (who ? "issued" : "available")}</div></div>`;
  }).join("");

  // flights
  el("flights").innerHTML = Object.values(b.flights)
    .sort((a, x) => a.id.localeCompare(x.id)).map(f => {
      const cls = f.delay_min > 0 ? "late" : (["held","divert"].includes(f.status) ? "held" : "placed");
      return `<tr class="${cls}"><td>${esc(f.id)}</td><td>${esc(f.kind)}</td>
        <td>${f.eta_min}${f.delay_min ? " (+" + f.delay_min + ")" : ""}</td>
        <td>${esc(f.gate) || "–"}</td><td>${esc(f.slot) || "–"}</td>
        <td class="st">${esc(f.status)}${f.reason ? " · " + esc(f.reason) : ""}</td>
        <td>${esc(f.decided_by) || "–"}</td></tr>`;
    }).join("");

  // log
  try {
    let lg = (await (await fetch("/log?n=120")).json()).log;
    if (!el("chatter").checked)
      lg = lg.filter(e => e.event !== "duplicate_merged" && e.event !== "inbound");
    el("log").innerHTML = lg.slice(-40).reverse().map(e => {
      const extra = Object.entries(e).filter(([k]) => !["t","actor","event"].includes(k))
        .map(([k, v]) => `${k}=${esc(v)}`).join(" ");
      return `<div><span class="t">+${e.t}</span><span class="a ${esc(e.actor)}">${esc(e.actor)}</span>
        <span class="e ${esc(e.event)}">${esc(e.event)}</span> <span style="opacity:.55">${extra}</span></div>`;
    }).join("");
  } catch {}
}

function short(u){ return String(u).replace(/^https?:\/\//, ""); }

async function pieces(){
  if (!Object.keys(PIECES).length) {
    try { PIECES = (await (await fetch("/pieces")).json()).pieces; } catch { return; }
  }
  const cells = await Promise.all(Object.entries(PIECES).map(async ([name, url]) => {
    try {
      const j = await (await fetch(`${url}/health`, {signal: AbortSignal.timeout(1800)})).json();
      return `<div class="cell up"><div class="id">${name}</div>
        <div class="who">answering</div><div class="meta">${esc(short(url))}</div></div>`;
    } catch {
      return `<div class="cell down"><div class="id">${name}</div>
        <div class="who">no answer</div><div class="meta">${esc(short(url))}</div></div>`;
    }
  }));
  el("pieces").innerHTML = cells.join("");
}

tick(); pieces();
setInterval(tick, 700);
setInterval(pieces, 3000);
</script></body></html>
"""
