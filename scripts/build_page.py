"""Render the audit artifact page from audit.json.

Usage: python3 build_page.py AUDIT_DIR   -> writes AUDIT_DIR/audit_page.html
Publish the result with the Artifact tool, capabilities {db: {}, user: {}}. The page stores each
decision at db path answers/<recordId>; Claude reads them back with ArtifactData (list "answers").
"""
import json, sys, pathlib, html

TEMPLATE = r"""<title>Works Field Audit</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Public+Sans:wght@400;500;600&display=swap">
<style>__CSS__</style>
<div class="wrap">
  <h1>Works Field Audit</h1>
  <p class="lede">Every record in Works that is missing one of the fields you asked about, grouped by screen. Tick a choice and it saves on its own. When you're done, say so in chat and Claude applies the answers to Works.</p>
  <div class="topbar">
    <div class="progress"><div class="status" id="status">Loading…</div><div class="bar"><i id="barfill"></i></div></div>
    <label class="status" style="display:inline-flex;gap:6px;align-items:center;cursor:pointer"><input type="checkbox" id="onlyOpen" checked> Show only undecided</label>
    <button id="acceptAll" type="button" hidden>Accept every dashed suggestion</button>
  </div>
  <div class="alert" id="dbwarn" hidden>Answers can't be saved in this view (not signed in, or no data access). Open the page from your own Claude account.</div>
  <div class="note" id="summary"></div>
  <div id="sections"></div>
  <p class="foot">Dashed boxes are Claude's guess from the city or country on the record; nothing is saved until you click it or press the accept button. "Leave blank" records your decision to skip. Works does not define "international activity"; its International Engagement Summary screen asks in what countries activities took place, so the suggestions treat virtual events as No. The "Related to Teaching and Learning" checkbox, per its help text, only adds the record to your Teaching and Learning Portfolio (it prints to the Annual Activity Report either way); boxes show the current Works value, change only the ones that should flip. Works date convention (Quick Start Guide): start date only = ongoing, end date only = single event, both = a span. Items with a start date and no end date are listed as ongoing and only need an end date if they have actually ended.</p>
</div>
<script>
const AUDIT = __AUDIT_JSON__;
const SCALE_OPTS = ["International","National","Regional","State","Local"];
const answers = {};   // recordId -> {field: value}
let db = null;
const $ = (s, el=document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

const asked = AUDIT.filter(r => Object.values(r.flags).some(f => f.ask));
const byScreen = {};
for (const r of AUDIT) (byScreen[r.screen] ||= {name: r.screenName, recs: []}).recs.push(r);

function radio(rid, field, opts, cur, suggest) {
  return opts.map(o => `<label class="${o===suggest?'sug':''}"><input type="radio" name="${rid}-${field}" value="${esc(o)}" ${cur===o?'checked':''}>${esc(o)}</label>`).join("")
       + `<label><input type="radio" name="${rid}-${field}" value="__leave" ${cur==='__leave'?'checked':''}>Leave blank</label>`;
}
function renderRec(r) {
  const a = answers[r.id] || {};
  const qs = [];
  const f = r.flags;
  if (f.intl?.ask) qs.push(`<div class="q" data-f="intl"><span class="lbl">International activity?</span>${radio(r.id,"intl",["Yes","No"],a.intl,f.intl.suggest)}</div>`);
  if (f.scale?.ask) qs.push(`<div class="q" data-f="scale"><span class="lbl">Scale</span>${radio(r.id,"scale",SCALE_OPTS,a.scale,"")}</div>`);
  if (f.aacsb?.ask) qs.push(`<div class="q" data-f="aacsb"><span class="lbl">AACSB classification</span>${radio(r.id,"aacsb",["Basic or Discovery Scholarship","Applied or Integration/Application Scholarship","Teaching and Learning Scholarship"],a.aacsb,"Basic or Discovery Scholarship")}</div>`);
  if (f.start?.ask) qs.push(`<div class="q" data-f="start"><span class="lbl">Dates: end date only${f.start.hint?' ('+esc(f.start.hint)+')':''}, which Works reads as a single event</span><label class="sug"><input type="checkbox" id="${r.id}-start-leave" ${a.start==='__leave'?'checked':''}>Single event, keep as is</label><span class="hint">or it spanned a period, starting</span><input type="text" id="${r.id}-start" placeholder="2023, Sep 2023, or 9/15/2023" value="${esc(a.start && a.start!=='__leave' ? a.start : '')}"></div>`);
  if (f.teaching?.toggle) qs.push(`<div class="q" data-f="teaching"><label><input type="checkbox" id="${r.id}-teaching" ${(a.teaching ?? (r.current.teaching==='True'))?'checked':''}>Also include in Teaching and Learning Portfolio</label><span class="cur">Works now: ${r.current.teaching||'unset'}</span></div>`);
  if (f.end?.ongoing) qs.push(`<div class="q" data-f="end"><span class="ongoing">No end date (ongoing).</span><input type="text" id="${r.id}-end" placeholder="End date, if it ended" value="${esc(a.end||'')}"></div>`);
  const done = isDone(r);
  return `<div class="rec ${done?'done':''}" id="rec-${r.id}" data-id="${r.id}">
    <div class="who"><div class="title"><span class="year">${esc(r.year)}</span>${esc(r.title)}</div><div class="ctx">${esc(r.context)}</div></div>
    <div class="qs">${qs.join("")}</div></div>`;
}
function isDone(r) {
  const a = answers[r.id] || {};
  return Object.entries(r.flags).filter(([k,f]) => f.ask).every(([k]) => a[k] !== undefined && a[k] !== "");
}
function render() {
  const host = $("#sections"); host.innerHTML = "";
  for (const [sid, s] of Object.entries(byScreen)) {
    const askRecs = s.recs.filter(r => Object.values(r.flags).some(f => f.ask));
    const toggleOnly = s.recs.filter(r => !askRecs.includes(r) && Object.values(r.flags).some(f => f.toggle || f.ongoing));
    if (!askRecs.length && !toggleOnly.length) continue;
    const sec = document.createElement("section");
    sec.innerHTML = `<div class="sec-head"><h2>${esc(s.name)}</h2><span class="count">${askRecs.length} to decide${toggleOnly.length?` · ${toggleOnly.length} more with toggles only`:''}</span></div>`
      + askRecs.map(renderRec).join("")
      + (toggleOnly.length ? `<details><summary style="cursor:pointer;color:var(--muted);margin:6px 0">Records with nothing missing (teaching toggle / ongoing only)</summary>${toggleOnly.map(renderRec).join("")}</details>` : "");
    host.appendChild(sec);
  }
  updateStatus();
}
function updateStatus() {
  const done = asked.filter(isDone).length;
  $("#status").textContent = `${done} of ${asked.length} records decided`;
  $("#barfill").style.width = (asked.length ? 100*done/asked.length : 0) + "%";
  const onlyOpen = $("#onlyOpen").checked;
  for (const r of asked) { const el = document.getElementById("rec-" + r.id); if (!el) continue; const d = isDone(r); el.classList.toggle("done", d); el.hidden = onlyOpen && d; }
  for (const sec of document.querySelectorAll("section")) sec.hidden = onlyOpen && ![...sec.querySelectorAll(".rec")].some(el => !el.hidden && !el.closest("details"));
  const sug = asked.filter(r => r.flags.intl?.suggest && (answers[r.id]?.intl === undefined)).length;
  const b = $("#acceptAll"); b.hidden = sug === 0; b.textContent = `Accept ${sug} dashed suggestion${sug===1?'':'s'} (international yes/no)`;
}
const pending = {};
async function save(rid, patch) {
  answers[rid] = Object.assign(answers[rid] || {}, patch);
  updateStatus();
  if (!db) return;
  const body = Object.assign({}, answers[rid], {updatedAt: new Date().toISOString()});
  pending[rid] = (pending[rid] || Promise.resolve()).then(() => db.doc("answers/" + rid).set(body)).catch(e => { console.log("save failed", rid, e.code, e.message); $("#dbwarn").hidden = false; });
}
document.addEventListener("change", ev => {
  const rec = ev.target.closest(".rec"); if (!rec) return;
  const rid = rec.dataset.id; const q = ev.target.closest(".q"); const f = q?.dataset.f;
  if (!f) return;
  if (f === "intl" || f === "scale" || f === "aacsb") save(rid, {[f]: ev.target.value});
  else if (f === "start") {
    // getElementById: record ids start with a digit, which a #selector cannot parse
    const leave = document.getElementById(rid + "-start-leave").checked; const v = document.getElementById(rid + "-start").value.trim();
    save(rid, {start: leave ? "__leave" : v});
  } else if (f === "teaching") save(rid, {teaching: ev.target.checked});
  else if (f === "end") save(rid, {end: ev.target.value.trim()});
});
$("#onlyOpen").addEventListener("change", updateStatus);
$("#acceptAll").addEventListener("click", () => {
  for (const r of asked) if (r.flags.intl?.suggest && answers[r.id]?.intl === undefined) {
    const el = document.querySelector(`input[name="${r.id}-intl"][value="${r.flags.intl.suggest}"]`); if (el) el.checked = true;
    save(r.id, {intl: r.flags.intl.suggest});
  }
});
const counts = {intl: asked.filter(r=>r.flags.intl?.ask).length, scale: asked.filter(r=>r.flags.scale?.ask).length, start: asked.filter(r=>r.flags.start?.ask).length};
$("#summary").innerHTML = `<b>What's missing:</b> international yes/no on ${counts.intl} records, scale on ${counts.scale} presentations. <b>Dates:</b> ${counts.start} records carry an end date only. The Works Quick Start Guide says end date only means a single event, start only means ongoing, both means a span. So those ${counts.start} are fine if they were one-time events; confirm or add a start date. <b>Already complete:</b> AACSB classification is set on every record that has the field (${AUDIT.filter(r=>r.current.aacsb).length} records).`;
render();
(async () => {
  db = await (window.claude?.use ? claude.use("db") : Promise.resolve(null));
  if (!db) { $("#dbwarn").hidden = false; return; }
  try {
    const snap = await db.collection("answers").get();
    snap.docs.forEach(d => { const {updatedAt, ...rest} = d.data() || {}; answers[d.id] = rest; });
    render();
  } catch (e) { console.log("load failed", e.code, e.message); $("#dbwarn").hidden = false; }
})();
</script>
"""

def main(audit_dir):
    audit_dir = pathlib.Path(audit_dir)
    audit = json.loads((audit_dir / "audit.json").read_text(encoding="utf-8"))
    slim = [{k: r[k] for k in ("id","screen","screenName","title","year","context","current","flags")} for r in audit]
    css = (pathlib.Path(__file__).with_name("page_style.css")).read_text(encoding="utf-8")
    page = TEMPLATE.replace("__CSS__", "\n" + css).replace("__AUDIT_JSON__", json.dumps(slim, ensure_ascii=False).replace("</", "<\\/"))
    (audit_dir / "audit_page.html").write_text(page, encoding="utf-8")
    print("wrote", audit_dir / "audit_page.html", len(page), "bytes")

if __name__ == "__main__":
    main(sys.argv[1])
