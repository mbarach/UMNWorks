// Create one Works record through the "Add Activity" drawer (new Faculty Success view).
// Install like apply_record.js: run this file in the page, then
//   localStorage.__worksPrepare = prepareCreate.toString(); localStorage.__worksFinish = finishCreate.toString()
// Per record: navigate to the screen's list URL, wait 3 s, click the "Add New" leaf element from script, wait 3.5 s,
// make ONE REAL CLICK inside the drawer (its heading, via the computer tool), then run prepareCreate(FIELDS, VALUES)
// with the proposal's `fields` and the card's `values`. It sets every combobox, checkbox and month combobox and returns
// "SET ..." plus one "TYPE <prefix> <value>" line per text field left to type (titles, years, days, free text), because
// Works drops script-set text on Save. For each TYPE line: throwaway screenshot (scale 0.1), click the input whose id
// starts with <prefix>, type the value, press Tab. Then run finishCreate(): clicks Save, waits for the drawer to close,
// and reports "SAVED newest <recordId>" from the list, or "NOT SAVED <validation text>".
async function prepareCreate(FIELDS, VALUES) {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  const fire = (el, types) => types.forEach(t => el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window})));
  const shown = i => i.parentElement.parentElement.innerText.trim();
  async function setCombo(prefix, text) {
    const i = document.querySelector(`input[id^="${prefix}"]`); if (!i) throw new Error("no input " + prefix);
    i.scrollIntoView({block: "center"}); i.focus(); fire(i, ["pointerdown","mousedown","pointerup","mouseup","click"]); await sleep(400);
    if (i.getAttribute("aria-expanded") !== "true") { i.dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowDown", code: "ArrowDown", keyCode: 40, which: 40, bubbles: true})); await sleep(400); }
    const opt = [...document.querySelectorAll("[role=option]")].find(o => o.textContent.trim() === text);
    if (!opt) throw new Error(`option '${text}' not found for ${prefix}; have: ` + [...document.querySelectorAll("[role=option]")].map(o => o.textContent.trim()).join("/"));
    opt.click(); await sleep(700);      // let the list close before the next combobox is opened
    if (!shown(i).split("\n").map(s => s.trim()).includes(text)) throw new Error(`${prefix} shows '${shown(i)}', wanted '${text}'`);
    return `${prefix} ${text}`;
  }
  const toType = [], done = [];
  for (const f of FIELDS) {
    const v = VALUES[f.name];
    if (f.type === "checkbox") {      // the card always carries an explicit true/false; false unticks a Works default
      if (v === undefined || v === null) continue;
      const c = document.querySelector(`input[id^="${f.prefix}"]`); if (!c) throw new Error("no checkbox " + f.prefix);
      if (c.checked !== !!v) { c.click(); await sleep(200); } if (c.checked !== !!v) throw new Error(`${f.prefix} checked ${c.checked}, wanted ${!!v}`);
      done.push(`${f.prefix} ${!!v}`); continue;
    }
    if (v === undefined || v === null || v === "" || v === false) continue;
    if (f.type === "note" || f.type === "checkgroup") continue;
    if (f.type === "combo") done.push(await setCombo(f.prefix, v));
    else if (f.type === "date") {
      const m = String(v).match(/^(?:([A-Za-z]+)\.?\s+)?(?:(\d{1,2}),?\s+)?(\d{4})$/) || String(v).match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
      if (!m) throw new Error("date not understood: " + v);
      let month = null, day = null, year;
      if (String(v).includes("/")) { month = MONTHS[+m[1]-1]; day = m[2]; year = m[3]; } else { year = m[3]; day = m[2] || null; if (m[1]) month = MONTHS.find(x => x.toLowerCase().startsWith(m[1].toLowerCase().slice(0,3))); }
      if (month) done.push(await setCombo(`_dtm_${f.prefix}-`, month));
      toType.push(`_dty_${f.prefix}- ${year}`); if (day) toType.push(`_dtd_${f.prefix}- ${+day}`);
    } else toType.push(`${f.prefix} ${v}`);
  }
  return ["SET " + done.join(" ; "), ...toType.map(t => "TYPE " + t)];
}
async function finishCreate() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const before = new Set([...document.querySelectorAll("[role=row][data-dm-id]")].map(r => r.getAttribute("data-dm-id")));
  // An open dropdown list swallows the first click on Save, and closing it from script can hang the renderer:
  // press a REAL Escape key (computer tool) before calling this, and if the result says the drawer is still
  // open, click the Save button for real at the coordinates in the result.
  if (document.querySelectorAll("[role=option]").length) return "NOT SAVED a dropdown list is open; press Escape for real, then retry";
  const drawerOpen = () => [...document.querySelectorAll("*")].some(e => e.children.length === 0 && e.textContent.trim() === "Add Activity");
  const save = [...document.querySelectorAll("button")].filter(b => /^save$/i.test(b.textContent.trim())).pop(); if (!save) throw new Error("no Save button");
  save.click();
  let closed = false;
  for (let t = 0; t < 16 && !closed; t++) { await sleep(500); closed = !drawerOpen(); }
  if (!closed) {      // the labels themselves say "This field is required *", so look only for inputs flagged invalid
    const bad = [...document.querySelectorAll("input[aria-invalid=true], .error, [class*=invalid]")].map(e => (e.id || e.className || "").toString().slice(0, 30));
    const b = save.getBoundingClientRect();
    return "NOT SAVED drawer still open; flagged: " + (bad.join(" ; ") || "none visible") + "; Save button at " + Math.round(b.x + b.width / 2) + "," + Math.round(b.y + b.height / 2);
  }
  await sleep(1500);
  const after = [...document.querySelectorAll("[role=row][data-dm-id]")].map(r => r.getAttribute("data-dm-id"));
  const fresh = after.filter(id => !before.has(id));
  return "SAVED newest " + (fresh[0] || after[0] || "unknown") + (fresh.length ? "" : " (no new row seen yet)");
}
