// In-page helper for editing one Works record (see CLAUDE.md "Writing data").
// Install once per browser profile (persists across page loads on digitalmeasures.com):
//   localStorage.__worksApply = applyRecord.toString()   (run this file's text, then that line)
// Then per record, after navigating to its edit URL:
//   const f = new Function("return " + localStorage.__worksApply)(); await f({intl: "No", scale: "International"})
// Field keys: intl, scale, aacsb (combobox option text), teaching (bool), start/end (date text like
// "2023", "Sep 2023", "Sep 15 2023", "9/15/2023"). Throws before Save if a field does not show the
// requested value; returns "SAVED ..." or "NOT SAVED ...".
// New view (2026-10-15): Save returns to the screen list within a second and shows no banner; the helper treats
// leaving the /records/<id> URL as saved. Confirm on the list: the row's "Last Saved" cell shows today.
// CAVEAT (2026-10-13): setDate shows the typed year/day but Works drops script-set TEXT values on Save
// unless a combobox on the form changes afterwards. For year/day/free text, type with real keystrokes
// instead (see CLAUDE.md). Comboboxes and checkboxes through this helper are reliable.
async function applyRecord(WRITES) {
const sleep = ms => new Promise(r => setTimeout(r, ms));
const FIELDS = { intl: "_international-", scale: "_scope-", aacsb: "_classification-", teaching: "_related_teaching-" };
const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const shown = i => i.parentElement.parentElement.innerText.trim();
const fire = (el, types) => types.forEach(t => el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window})));
async function setCombo(prefix, text) {
  const i = document.querySelector(`input[id^="${prefix}"]`); if (!i) throw new Error("no input " + prefix);
  i.scrollIntoView({block: "center"}); i.focus();
  fire(i, ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]); await sleep(400);
  if (i.getAttribute("aria-expanded") !== "true") { i.dispatchEvent(new KeyboardEvent("keydown", {key: "ArrowDown", code: "ArrowDown", keyCode: 40, which: 40, bubbles: true})); await sleep(400); }
  const opt = [...document.querySelectorAll("[role=option]")].find(o => o.textContent.trim() === text);
  if (!opt) throw new Error(`option '${text}' not found for ${prefix}; have: ` + [...document.querySelectorAll("[role=option]")].map(o => o.textContent.trim()).join("/"));
  opt.click(); await sleep(400);
  const s = shown(i); if (!new RegExp("(^|\\n)" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(\\n|$)").test(s)) throw new Error(`${prefix} shows '${s}', wanted '${text}'`);
  return `${prefix} ${text}`;
}
async function setCheckbox(prefix, want) {
  const c = document.querySelector(`input[id^="${prefix}"]`); if (!c) throw new Error("no checkbox " + prefix);
  c.scrollIntoView({block: "center"}); if (c.checked !== want) { c.click(); await sleep(300); }
  if (c.checked !== want) throw new Error(`${prefix} checked=${c.checked}, wanted ${want}`);
  return `${prefix} ${want}`;
}
function setNative(input, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setter.call(input, value); input.dispatchEvent(new Event("input", {bubbles: true})); input.dispatchEvent(new Event("change", {bubbles: true}));
}
// Dates: `which` is "start" or "end"; ids are _dtm_<which>- (month combobox), _dtd_<which>- (day), _dty_<which>- (year).
async function setDate(which, text) {
  const m = text.match(/^(?:([A-Za-z]+)\.?\s+)?(?:(\d{1,2}),?\s+)?(\d{4})$/) || text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) throw new Error("date not understood: " + text);
  let month = null, day = null, year;
  if (text.includes("/")) { month = MONTHS[+m[1] - 1]; day = m[2]; year = m[3]; }
  else { year = m[3]; day = m[2] || null; if (m[1]) { month = MONTHS.find(x => x.toLowerCase().startsWith(m[1].toLowerCase().slice(0, 3))); if (!month) throw new Error("month not understood: " + m[1]); } }
  const out = [];
  const y = document.querySelector(`input[id^="_dty_${which}-"]`); if (!y) throw new Error("no year input for " + which);
  y.scrollIntoView({block: "center"}); y.focus(); setNative(y, year); await sleep(200); if (y.value !== year) throw new Error("year not set"); out.push("year " + year);
  if (month) { out.push(await setCombo(`_dtm_${which}-`, month)); }
  if (day) { const d = document.querySelector(`input[id^="_dtd_${which}-"]`); d.focus(); setNative(d, String(+day)); await sleep(200); if (String(+d.value) !== String(+day)) throw new Error("day not set"); out.push("day " + day); }
  return out.join(",");
}
const results = [];

for (const [k, v] of Object.entries(WRITES)) {
  if (k === "teaching") results.push(await setCheckbox(FIELDS.teaching, !!v));
  else if (k === "start" || k === "end") results.push(await setDate(k, v));
  else results.push(await setCombo(FIELDS[k], v));
}
const save = [...document.querySelectorAll("button")].find(b => /^save$/i.test(b.textContent.trim())); if (!save) throw new Error("no Save button");
save.click();
let saved = false;
for (let t = 0; t < 16 && !saved; t++) { await sleep(500); saved = document.body.innerText.includes("Record has been saved") || !/\/records\/\d+/.test(location.pathname); }
const err = saved ? "" : (document.body.innerText.match(/[^\n]*(required|invalid|error)[^\n]*/i) || [""])[0].trim().slice(0, 120);
return (saved ? "SAVED " : "NOT SAVED " + err + " ; ") + results.join(" ; ");
}
