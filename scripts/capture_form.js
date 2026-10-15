// Capture an Add New form (the "Add Activity" drawer in the new Faculty Success view).
// Steps: open the screen's list URL, click the "Add New" leaf element, wait ~3.5 s, then make ONE REAL CLICK inside the
// drawer (e.g. the "Add Activity" heading via the computer tool) — without it, script-dispatched events do not open
// comboboxes. Then run this file and `await captureAll()`; store it with localStorage.__worksCaptureAll = captureAll.toString().
// Returns rows "F | label | id prefix | type | required" and "O | prefix | opt1/opt2/..." (combos over 40 options say MANY).
async function captureAll() {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const fire = (el, types) => types.forEach(t => el.dispatchEvent(new MouseEvent(t, {bubbles: true, cancelable: true, view: window})));
  const labelOf = el => { let n = el; for (let k = 0; k < 6 && n; k++) { n = n.parentElement; const l = n && n.querySelector('label'); if (l) return l.innerText.trim().replace(/\s+/g, ' ').replace(/^This field is required \* /, ''); } return (el.getAttribute('aria-label') || el.getAttribute('placeholder') || '').trim(); };
  const rows = [], combos = [];
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (el.type === 'hidden' || el.type === 'file') continue;
    const id = el.id || ''; if (!id || /^(select-record|search-records|undefined)/.test(id)) continue;
    const prefix = id.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}$/i, '');
    let type = el.tagName === 'TEXTAREA' ? 'textarea' : el.type === 'checkbox' ? 'checkbox' : (el.getAttribute('role') === 'combobox' || el.getAttribute('aria-expanded') !== null) ? 'combo' : 'text';
    if (/^_dt[mdy]_/.test(prefix)) type = 'date';
    const req = !!(el.required || el.getAttribute('aria-required') === 'true' || /\*/.test(labelOf(el)));
    rows.push(['F', labelOf(el).slice(0, 70), prefix, type, req ? 'required' : ''].join(' | '));
    if (type === 'combo' && prefix !== '_country-') combos.push(prefix);   // the country list hangs the renderer
  }
  for (const p of combos) {
    try {
      rows.push(await Promise.race([(async () => {
        const el = document.querySelector(`input[id^="${p}"]`); el.scrollIntoView({block: 'center'});
        fire(el, ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']); await sleep(300);
        const opts = [...document.querySelectorAll('[role=option]')].map(o => o.textContent.trim());
        el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true})); await sleep(120);
        return 'O | ' + p + ' | ' + (opts.length > 40 ? 'MANY ' + opts.length : opts.join('/'));
      })(), new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 2500))]));
    } catch (e) { rows.push('O | ' + p + ' | ERR ' + e.message); }
  }
  return rows;
}
