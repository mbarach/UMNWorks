// Scrape a Works list view (original view, all columns turned on via Select Columns > Select All).
// Run in the page via the Chrome extension javascript_tool. Stores JSON in window.__dump and
// returns a one-line summary. Fetch the JSON afterwards in slices: window.__dump.slice(a, b).
// Each gridcell's text is "value, Header Name, , column N of M, row R of T"; "Empty" means blank.
(() => {
  const hdrs = Array.from(document.querySelectorAll('th,[role=columnheader]'))
    .map(h => h.textContent.trim().replace(/\s+/g, ' ')).filter(Boolean);
  const uniq = [...new Set(hdrs)].sort((a, b) => b.length - a.length);
  const rows = {};
  document.querySelectorAll('[role=row][data-dm-id]').forEach(r => {
    const id = r.dataset.dmId;
    const rec = {};
    r.querySelectorAll('[role=gridcell]').forEach(c => {
      const t = c.textContent.trim().replace(/\s+/g, ' ');
      const m = t.match(/^(.*), column (\d+) of (\d+), row (\d+) of (\d+)$/);
      if (!m) return;
      let v = m[1].replace(/, $/, '');
      let h = null;
      for (const u of uniq) {
        if (v.toLowerCase().endsWith(', ' + u.toLowerCase())) { h = u; v = v.slice(0, -(u.length + 2)); break; }
      }
      if (!h) h = 'col' + m[2];
      if (v === 'Empty') v = '';
      rec._row = +m[4];
      rec[h] = v;
    });
    rows[id] = rec;
  });
  window.__dump = JSON.stringify({ screen: location.pathname.replace(/.*screens\//, ''), headers: uniq, rows });
  return 'len=' + window.__dump.length + ' nrows=' + Object.keys(rows).length;
})()
