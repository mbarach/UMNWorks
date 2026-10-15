"""Render the sync page: resume parse check, Add cards, Fill cards, Works-only review. One artifact, db-backed answers.
CLI: python3 -I scripts/build_sync_page.py AUDIT_DIR -> AUDIT_DIR/sync_page.html
Publish with capabilities {db: {}, user: {}}. Answers live at answers/<cardId>; card ids are parse-<resumeId>,
add-<proposalId>, fill-<recordId>, review-<proposalId> (see read_sync_answers.py for the shapes).
"""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = r"""<title>Works Sync Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=Public+Sans:wght@400;500;600&display=swap">
<style>__CSS__
.flt { display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
.flt button { border: 0; border-radius: 0; padding: 5px 10px; }
.flt button[aria-pressed=true] { background: var(--accent); color: #fff; }
.jump { flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: center; font-size: .82rem; }
.jump a { color: var(--accent); text-decoration: none; padding: 2px 8px; border: 1px solid var(--line); border-radius: 999px; background: var(--surface); }
.jump a.sec { font-weight: 600; }
.jump a.off { opacity: .4; }
.jump .sep { color: var(--muted); margin: 0 2px; }
section, .sub { scroll-margin-top: 120px; }
h3.subh { font-family: var(--display); font-weight: 500; font-size: 1.05rem; margin: 16px 0 6px; }
h3.subh .count { color: var(--muted); font-size: .85rem; font-family: var(--body); font-weight: 400; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; margin-bottom: 8px; }
.card.done { border-color: var(--ok); }
.card.done .body { display: none; }
.card .oneline { display: none; color: var(--muted); font-size: .9rem; }
.card.done .oneline { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.card .oneline a { color: var(--accent); cursor: pointer; margin-left: auto; text-decoration: underline; }
.card .title { font-weight: 600; }
.card .title .ctx { font-weight: 400; color: var(--muted); font-size: .85rem; }
.card .year { font-variant-numeric: tabular-nums; color: var(--accent); font-weight: 600; margin-right: 6px; }
.fields { display: grid; grid-template-columns: minmax(0, 16em) minmax(0, 1fr); gap: 6px 12px; align-items: center; margin-top: 8px; }
.fields .fname { font-size: .85rem; color: var(--muted); }
.fields .req::after { content: " *"; color: var(--accent); }
.fields input[type=text], .fields select, .fields textarea { font: inherit; font-size: .9rem; padding: 4px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--fg); width: 100%; box-sizing: border-box; }
.fields .fnote { grid-column: 2; font-size: .8rem; color: var(--muted); margin-top: -4px; }
.fields .ftext { font-size: .9rem; color: var(--muted); }
.src { font-size: .85rem; color: var(--muted); font-style: italic; margin-top: 4px; }
.actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; align-items: center; }
.actions label { display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px; border: 1px solid var(--line); border-radius: 6px; cursor: pointer; font-size: .9rem; }
.actions label:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); }
.actions input[type=radio] { accent-color: var(--accent); margin: 0; }
.qs { display: flex; flex-direction: column; gap: 8px; min-width: 0; margin-top: 8px; }
section > .lede { margin-bottom: 10px; }
@media (max-width: 640px) { .fields { grid-template-columns: 1fr; } .fields .fnote { grid-column: 1; } }
</style>
<div class="wrap">
  <h1>Works Sync Review</h1>
  <p class="lede">Works account: <b id="acct">__NAME__</b>. Four steps, top to bottom. Everything saves as you go; nothing is written to Works until you say "done" in chat, and only what you ticked.</p>
  <div class="topbar">
    <div class="progress"><div class="status" id="status">Loading…</div><div class="bar"><i id="barfill"></i></div></div>
    <div class="flt" role="group" aria-label="Show"><button type="button" id="flt-undecided" aria-pressed="true">Undecided</button><button type="button" id="flt-decided" aria-pressed="false">Decided</button><button type="button" id="flt-all" aria-pressed="false">All</button></div>
    <button type="button" id="download" title="Save your answers as a file, for when the page cannot store them">Download answers</button>
    <nav class="jump" id="jump" aria-label="Jump to a section"></nav>
  </div>
  <div class="alert" id="dbwarn" hidden>Answers can't be saved in this view (not signed in, or no data access). Open the page from your own Claude account.</div>
  <div class="note" id="warnings" hidden></div>
  <div id="sections"></div>
  <p class="foot">Step 1 edits do not re-run the matching; if you corrected a year or venue, Claude re-runs it before applying. Dates: start only = ongoing, end only = a single event, both = a span (Works Quick Start Guide). Fields marked * are required by Works before a record can be saved. "I will delete it by hand" is noted for you; the tool never deletes.</p>
</div>
<script>
const DATA = __DATA_JSON__;
const answers = {}; let db = null; let filter = "undecided";
const $ = (s, el=document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const SCALE_OPTS = ["International","National","Regional","State","Local"];

// ---- card model: every card has id, section, and one of r (resume item), p (proposal), a (audit record)
const cards = [];
for (const r of DATA.resume) cards.push({id: "parse-" + r.id, section: "parse", r});
for (const p of DATA.proposals) cards.push({id: (p.action === "create" ? "add-" : "review-") + p.id, section: p.action === "create" ? "add" : "review", p});
for (const a of DATA.audit) if (Object.values(a.flags).some(f => f.ask || f.toggle || f.ongoing)) cards.push({id: "fill-" + a.id, section: "fill", a});
const KIND_LABELS = {publication: "Publications", presentation: "Presentations", honor: "Honors", grant: "Grants", service: "Service", position: "Positions", education: "Education", other: "Other"};
const KIND_ORDER = Object.keys(KIND_LABELS);
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
function groupCards(key, cs) {
  const label = c => key === "fill" ? c.a.screenName : (KIND_LABELS[(c.r || c.p).kind] || "Other");
  const order = c => key === "fill" ? 0 : KIND_ORDER.indexOf((c.r || c.p).kind);
  const groups = new Map();
  for (const c of cs) { const l = label(c); if (!groups.has(l)) groups.set(l, {label: l, slug: slug(l), order: order(c), cards: []}); groups.get(l).cards.push(c); }
  return [...groups.values()].sort((a, b) => a.order - b.order || a.label.localeCompare(b.label));
}
const SECTIONS = [["parse", "1. Check the resume parse", "Fix anything misread. Drop an item that is not real. Each line shows the resume text it came from."],
                  ["add", "2. Add to Works", "Each card is the Works form for that screen, in Works' order with Works' own options. Fill the blanks, then tick Add or Skip."],
                  ["fill", "3. Fill gaps", "Existing Works records missing a field."],
                  ["review", "4. Only in Works", "Items your resume does not mention."]];

// An Add card can be pointed at another screen: then its fields are that form's fields (blank, except names in common).
function screenOf(c) { return answers[c.id]?.screen || c.p.screen; }
function fieldsFor(c) {
  const sid = screenOf(c);
  if (sid === c.p.screen || !DATA.forms[sid]) return c.p.fields;
  const old = Object.fromEntries(c.p.fields.map(f => [f.name, f.value]));
  return DATA.forms[sid].fields.map(f => Object.assign({}, f, {value: f.name in old ? old[f.name] : (f.default ?? null), note: f.note || ""}));
}
function droppedInParse(c) { return c.section === "add" && answers["parse-" + c.p.resume_id]?.keep === false; }
function addComplete(c, a) {
  const fields = fieldsFor(c), vals = a.values || {};
  if (!fields.every(f => !f.required || String(vals[f.name] ?? "") !== "")) return false;
  const one = DATA.forms[screenOf(c)]?.require_one_of || [];
  return !one.length || one.some(n => String(vals[n] ?? "") !== "");
}
function isDone(c) {
  if (droppedInParse(c)) return true;
  const a = answers[c.id];
  if (!a) return false;
  if (c.section === "parse") return a.keep !== undefined;
  if (c.section === "add") return a.decision === "skip" || (a.decision === "add" && addComplete(c, a));
  if (c.section === "review") return !!a.decision;
  return Object.entries(c.a.flags).filter(([k, f]) => f.ask).every(([k]) => a[k] !== undefined && a[k] !== "");
}
function oneLine(c) {
  const a = answers[c.id] || {};
  if (c.section === "parse") return a.keep ? "kept" : "dropped";
  if (c.section === "add") return droppedInParse(c) ? "dropped in step 1, so not added" : a.decision === "add" ? "will be added" : "skipped";
  if (c.section === "review") return {keep: "keep in Works", add_to_resume: "add to resume", delete_by_hand: "delete by hand"}[a.decision];
  return Object.entries(a).filter(([k]) => k !== "updatedAt").map(([k, v]) => `${k}: ${v === "__leave" ? "leave blank" : v}`).join(", ");
}
function fieldInput(f, val) {
  if (f.type === "combo") return `<select data-field="${esc(f.name)}"><option value="">—</option>${f.options.map(o => `<option ${val===o?'selected':''}>${esc(o)}</option>`).join("")}</select>`;
  if (f.type === "checkbox") return `<span><input type="checkbox" data-field="${esc(f.name)}" ${val?'checked':''}></span>`;
  if (f.type === "textarea") return `<textarea data-field="${esc(f.name)}" rows="2">${esc(val)}</textarea>`;
  if (f.type === "note") return `<span class="ftext">${esc(val || "—")}</span>`;
  if (f.type === "checkgroup") return `<span class="ftext">${f.options.length ? "Options on the Works form: " + esc(f.options.join(", ")) : "Set on the Works form after creation"}</span>`;
  return `<input type="text" data-field="${esc(f.name)}" value="${esc(val)}" placeholder="${f.type==='date'?'2024, Jun 2024, or 6/15/2024':''}">`;
}
function renderCard(c) {
  const a = answers[c.id] || {}; let head = "", body = "";
  if (c.section === "parse") {
    const r = c.r;
    head = `<span class="year">${esc(r.year ?? "")}</span>${esc(r.kind)}: ${esc(r.title || r.venue)}`;
    body = `<div class="src">from the resume (${esc(r.ref)}): “${esc(r.source_text)}”</div>
      <div class="fields"><span class="fname">Title</span><input type="text" data-k="title" value="${esc(a.title ?? r.title)}">
      <span class="fname">Venue</span><input type="text" data-k="venue" value="${esc(a.venue ?? r.venue)}">
      <span class="fname">Year</span><input type="text" data-k="year" value="${esc(a.year ?? r.year ?? "")}"></div>
      <div class="actions"><label><input type="radio" name="${c.id}-keep" value="1" ${a.keep===true?'checked':''}>Correct, keep</label><label><input type="radio" name="${c.id}-keep" value="0" ${a.keep===false?'checked':''}>Not a real item, drop</label></div>`;
  } else if (c.section === "add") {
    const p = c.p, vals = a.values || {}; const sid = screenOf(c);
    head = `Add a ${esc(p.kind)} to ${esc(DATA.forms[sid]?.name || p.screenName)}: ${esc(p.title_line)}`;
    const screenSel = `<div class="fields"><span class="fname">Target screen</span><select data-screen>${Object.entries(DATA.forms).map(([id, f]) => `<option value="${esc(id)}" ${id===sid?'selected':''}>${esc(f.name)}</option>`).join("")}</select></div>`;
    body = screenSel + `<div class="fields">${fieldsFor(c).map(f => `<span class="fname ${f.required?'req':''}">${esc(f.name)}</span>${fieldInput(f, vals[f.name] ?? f.value ?? "")}${f.note?`<span class="fnote">${esc(f.note)}</span>`:""}`).join("")}</div>
      <div class="actions"><label><input type="radio" name="${c.id}-d" value="add" ${a.decision==='add'?'checked':''}>Add to Works</label><label><input type="radio" name="${c.id}-d" value="skip" ${a.decision==='skip'?'checked':''}>Skip</label><span class="hint" id="${c.id}-req"></span></div>`;
  } else if (c.section === "review") {
    head = esc(c.p.title_line);
    body = `<div class="actions">${[["keep","Keep in Works"],["add_to_resume","Add to my resume"],["delete_by_hand","I will delete it by hand"]].map(([v,l]) => `<label><input type="radio" name="${c.id}-d" value="${v}" ${a.decision===v?'checked':''}>${l}</label>`).join("")}</div>`;
  } else {
    const r = c.a, f = r.flags, qs = [];
    const radio = (field, opts, cur, sug) => opts.map(o => `<label class="${o===sug?'sug':''}"><input type="radio" name="${c.id}-${field}" value="${esc(o)}" ${cur===o?'checked':''}>${esc(o)}</label>`).join("") + `<label><input type="radio" name="${c.id}-${field}" value="__leave" ${cur==='__leave'?'checked':''}>Leave blank</label>`;
    if (f.intl?.ask) qs.push(`<div class="q" data-f="intl"><span class="lbl">International activity?</span>${radio("intl",["Yes","No"],a.intl,f.intl.suggest)}</div>`);
    if (f.scale?.ask) qs.push(`<div class="q" data-f="scale"><span class="lbl">Scale</span>${radio("scale",SCALE_OPTS,a.scale,"")}</div>`);
    if (f.aacsb?.ask) qs.push(`<div class="q" data-f="aacsb"><span class="lbl">AACSB classification</span>${radio("aacsb",["Basic or Discovery Scholarship","Applied or Integration/Application Scholarship","Teaching and Learning Scholarship"],a.aacsb,"Basic or Discovery Scholarship")}</div>`);
    if (f.start?.ask) qs.push(`<div class="q" data-f="start"><span class="lbl">End date only (single event)</span><label class="sug"><input type="checkbox" data-k="start-leave" ${a.start==='__leave'?'checked':''}>Single event, keep as is</label><span class="hint">or it spanned a period, starting</span><input type="text" data-k="start" placeholder="2023, Sep 2023, or 9/15/2023" value="${esc(a.start && a.start!=='__leave' ? a.start : '')}"></div>`);
    if (f.teaching?.toggle) qs.push(`<div class="q" data-f="teaching"><label><input type="checkbox" data-k="teaching" ${(a.teaching ?? (r.current.teaching==='True'))?'checked':''}>Also include in Teaching and Learning Portfolio</label><span class="cur">Works now: ${esc(r.current.teaching||'unset')}</span></div>`);
    if (f.end?.ongoing) qs.push(`<div class="q" data-f="end"><span class="ongoing">No end date (ongoing).</span><input type="text" data-k="end" placeholder="End date, if it ended" value="${esc(a.end||'')}"></div>`);
    head = `<span class="year">${esc(r.year)}</span>${esc(r.title)} <span class="ctx">${esc(r.context)}</span>`;
    body = `<div class="qs">${qs.join("")}</div>`;
  }
  return `<div class="card ${isDone(c)?'done':''}" id="card-${c.id}" data-id="${c.id}"><div class="title">${head}</div><div class="oneline"><span>${esc(oneLine(c))}</span><a data-change>change</a></div><div class="body">${body}</div></div>`;
}
function render() {
  const host = $("#sections"); host.innerHTML = "";
  for (const [key, title, lede] of SECTIONS) {
    const cs = cards.filter(c => c.section === key); if (!cs.length) continue;
    const sec = document.createElement("section"); sec.dataset.section = key; sec.id = "sec-" + key;
    const groups = groupCards(key, cs);
    sec.innerHTML = `<div class="sec-head"><h2>${title}</h2><span class="count" data-count></span></div><p class="lede">${lede}</p>`
      + groups.map(g => `<div class="sub" id="sub-${key}-${g.slug}"><h3 class="subh">${esc(g.label)} <span class="count" data-subcount></span></h3>${g.cards.map(renderCard).join("")}</div>`).join("");
    host.appendChild(sec);
  }
  $("#jump").innerHTML = SECTIONS.filter(([key]) => cards.some(c => c.section === key)).map(([key, title], i) =>
    `${i ? '<span class="sep">·</span>' : ''}<a class="sec" href="#sec-${key}" data-for="sec-${key}">${esc(title.replace(/^\d\. /, ""))}</a>`
    + groupCards(key, cards.filter(c => c.section === key)).map(g => `<a href="#sub-${key}-${g.slug}" data-for="sub-${key}-${g.slug}">${esc(g.label)}</a>`).join("")).join("");
  if (DATA.warnings.length) { const w = $("#warnings"); w.hidden = false; w.textContent = "Check: " + DATA.warnings.join(" · "); }
  updateStatus();
}
function updateStatus() {
  const done = cards.filter(isDone).length;
  $("#status").textContent = `${done} decided · ${cards.length - done} undecided`;
  $("#barfill").style.width = (cards.length ? 100*done/cards.length : 0) + "%";
  $("#flt-undecided").textContent = `Undecided (${cards.length - done})`; $("#flt-decided").textContent = `Decided (${done})`; $("#flt-all").textContent = "All";
  for (const c of cards) { const el = document.getElementById("card-" + c.id); if (!el) continue; const d = isDone(c); el.classList.toggle("done", d && !el.dataset.open); el.hidden = filter === "undecided" ? (d && !el.dataset.open) : filter === "decided" ? !d : false; if (d) el.querySelector(".oneline span").textContent = oneLine(c); }
  for (const sub of document.querySelectorAll(".sub")) { const vis = [...sub.querySelectorAll(".card")].filter(e => !e.hidden); sub.hidden = vis.length === 0; sub.querySelector("[data-subcount]").textContent = `(${vis.length})`; }
  for (const sec of document.querySelectorAll("section")) { const vis = [...sec.querySelectorAll(".card")].filter(e => !e.hidden); sec.hidden = vis.length === 0; sec.querySelector("[data-count]").textContent = `${vis.length} shown`; }
  for (const a of document.querySelectorAll("#jump a")) { const t = document.getElementById(a.dataset.for); a.classList.toggle("off", !t || t.hidden); }
  for (const c of cards.filter(c => c.section === "add")) { const el = document.getElementById(c.id + "-req"); if (!el) continue; const a = answers[c.id] || {}; const missing = fieldsFor(c).filter(f => f.required && String(a.values?.[f.name] ?? "") === "").map(f => f.name); const one = DATA.forms[screenOf(c)]?.require_one_of || []; if (one.length && !one.some(n => String(a.values?.[n] ?? "") !== "")) missing.push("one of: " + one.join(" / ")); el.textContent = a.decision === "add" && missing.length ? "Still needed: " + missing.join(", ") : ""; }
}
const pending = {};
function save(cid, patch) {
  answers[cid] = Object.assign(answers[cid] || {}, patch); updateStatus();
  if (!db) return;
  const body = Object.assign({}, answers[cid], {updatedAt: new Date().toISOString()});
  pending[cid] = (pending[cid] || Promise.resolve()).then(() => db.doc("answers/" + cid).set(body)).catch(e => { console.log("save failed", cid, e.code, e.message); $("#dbwarn").hidden = false; });
}
document.addEventListener("change", ev => {
  const card = ev.target.closest(".card"); if (!card) return; const cid = card.dataset.id; const c = cards.find(x => x.id === cid); const t = ev.target;
  if (c.section === "parse") { if (t.name === cid + "-keep") save(cid, {keep: t.value === "1"}); else if (t.dataset.k) save(cid, {[t.dataset.k]: t.value.trim()}); }
  else if (c.section === "add") {
    if (t.dataset.screen !== undefined) { save(cid, {screen: t.value, values: {}}); const fresh = document.createElement("div"); fresh.innerHTML = renderCard(c); card.replaceWith(fresh.firstElementChild); updateStatus(); return; }
    const values = Object.assign({}, answers[cid]?.values || {});
    for (const el of card.querySelectorAll("[data-field]")) values[el.dataset.field] = el.type === "checkbox" ? el.checked : el.value.trim();
    if (t.name === cid + "-d") save(cid, {decision: t.value, values, screen: screenOf(c)}); else if (t.dataset.field) save(cid, {values, screen: screenOf(c)});
  }
  else if (c.section === "review") { if (t.name === cid + "-d") save(cid, {decision: t.value}); }
  else { const q = t.closest(".q"); const f = q?.dataset.f; if (!f) return;
    if (f === "intl" || f === "scale" || f === "aacsb") save(cid, {[f]: t.value});
    else if (f === "start") { const leave = card.querySelector('[data-k="start-leave"]').checked; const v = card.querySelector('[data-k="start"]').value.trim(); save(cid, {start: leave ? "__leave" : v}); }
    else if (f === "teaching") save(cid, {teaching: t.checked});
    else if (f === "end") save(cid, {end: t.value.trim()}); }
});
$("#download").addEventListener("click", async () => {
  const data = JSON.stringify(answers, null, 1);
  const dl = window.claude?.use ? await claude.use("downloads") : null;     // the artifact viewer mediates file saves
  if (dl) { try { await dl.save({filename: "works-answers.json", data}); return; } catch (e) { console.log("download declined", e.code, e.message); return; } }
  const blob = new Blob([data], {type: "application/json"});
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "works-answers.json"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
});
document.addEventListener("click", ev => {
  const a = ev.target.closest("[data-change]"); if (a) { const card = a.closest(".card"); card.dataset.open = "1"; card.classList.remove("done"); return; }
  const b = ev.target.closest(".flt button"); if (b) { filter = b.id.replace("flt-", ""); for (const x of document.querySelectorAll(".flt button")) x.setAttribute("aria-pressed", String(x === b)); for (const el of document.querySelectorAll(".card")) delete el.dataset.open; updateStatus(); }
});
render();
(async () => {
  db = await (window.claude?.use ? claude.use("db") : Promise.resolve(null));
  if (!db) { $("#dbwarn").hidden = false; return; }
  try { const snap = await db.collection("answers").get(); snap.docs.forEach(d => { const {updatedAt, ...rest} = d.data() || {}; answers[d.id] = rest; }); render(); }
  catch (e) { console.log("load failed", e.code, e.message); $("#dbwarn").hidden = false; }
})();
</script>
"""

def render(resume_items, proposals, audit, warnings, config, forms=None):
    slim_audit = [{k: r[k] for k in ("id", "screen", "screenName", "title", "year", "context", "current", "flags")} for r in audit]
    data = {"resume": resume_items, "proposals": proposals, "audit": slim_audit, "warnings": warnings, "forms": forms or {}}
    css = (HERE / "page_style.css").read_text(encoding="utf-8")
    return (TEMPLATE.replace("__CSS__", "\n" + css).replace("__NAME__", str(config.get("name", "")).replace("<", "&lt;"))
            .replace("__DATA_JSON__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))

def main(audit_dir):
    d = pathlib.Path(audit_dir); root = HERE.parent
    load = lambda p, default=None: json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    page = render(load(d / "resume_items.json", []), load(d / "proposals.json", []), load(d / "audit.json", []),
                  load(d / "normalize_warnings.json", []), load(root / "local" / "config.json", {}), load(root / "screens" / "forms.json", {}))
    (d / "sync_page.html").write_text(page, encoding="utf-8")
    print("wrote", d / "sync_page.html", len(page), "bytes")

if __name__ == "__main__":
    main(sys.argv[1])
