/* ICPC contest archive — table sorting/filtering and the search box (copied to site/assets/). */
(function () {
  'use strict';
  const REL = document.documentElement.dataset.rel || '';

  /* ---- tables: click a header to sort; tables marked .flt (or 30+ rows) get a filter bar ----
     th[data-f]  -> a drop-down of that column's values
     td[data-v]  -> the value to sort/filter by instead of the text
     td[data-vs] -> several filter values, separated by |                                    */
  const num = s => { const t = s.replace(/[%,\s]/g, ''); return t !== '' && !isNaN(t) ? parseFloat(t) : null; };
  const cellv = c => c ? (c.dataset.v !== undefined ? c.dataset.v : c.textContent).trim() : '';
  const vals = c => c ? (c.dataset.vs !== undefined ? c.dataset.vs.split('|').filter(Boolean) : [cellv(c)]) : [''];
  let hashTable = null;
  document.querySelectorAll('table').forEach(tbl => {
    if (tbl.classList.contains('grid') || tbl.classList.contains('nosort')) return;
    const head = tbl.tHead && tbl.tHead.rows[tbl.tHead.rows.length - 1];
    const body = tbl.tBodies[0];
    if (!head || !body) return;
    const rows = Array.from(body.rows);
    if (rows.length < 2) return;
    const ths = Array.from(head.cells);
    ths.forEach((th, i) => {
      th.classList.add('sortable');
      th.title = (th.title ? th.title + ' — ' : '') + 'click to sort';
      th.addEventListener('click', () => {
        const asc = !th.classList.contains('asc');
        const key = r => cellv(r.cells[i]);
        const allNum = rows.every(r => key(r) === '' || num(key(r)) !== null);
        rows.sort((a, b) => {
          const x = key(a), y = key(b);
          if ((x === '') !== (y === '')) return x === '' ? 1 : -1;      // blanks last, either way
          const d = allNum ? num(x) - num(y) : x.localeCompare(y, undefined, {numeric: true});
          return asc ? d : -d;
        });
        ths.forEach(t => t.classList.remove('asc', 'desc'));
        th.classList.add(asc ? 'asc' : 'desc');
        const frag = document.createDocumentFragment();
        rows.forEach(r => frag.appendChild(r));
        body.appendChild(frag);
      });
    });
    if (!(tbl.classList.contains('flt') || rows.length >= 30)) return;
    const bar = document.createElement('div'); bar.className = 'fbar';
    const box = document.createElement('input');
    box.type = 'search'; box.placeholder = 'Filter ' + rows.length.toLocaleString() + ' rows'; box.autocomplete = 'off';
    box.setAttribute('aria-label', 'Filter rows');
    bar.appendChild(box);
    const sels = [];
    ths.forEach((th, i) => {
      if (!th.hasAttribute('data-f')) return;
      const cnt = new Map();
      rows.forEach(r => { for (const v of vals(r.cells[i])) cnt.set(v, (cnt.get(v) || 0) + 1); });
      if (cnt.size < 2) return;
      const sel = document.createElement('select'); sel.dataset.col = i;
      const label = th.dataset.f || th.textContent.trim();
      sel.setAttribute('aria-label', 'Filter by ' + label);
      const all = document.createElement('option'); all.value = ''; all.textContent = label + ': all'; sel.appendChild(all);
      Array.from(cnt.keys()).sort((a, b) => a.localeCompare(b, undefined, {numeric: true})).forEach(v => {
        const o = document.createElement('option'); o.value = v || '—';
        o.textContent = (v || '—') + ' (' + cnt.get(v) + ')'; sel.appendChild(o);
      });
      bar.appendChild(sel); sels.push(sel);
    });
    const clear = document.createElement('button'); clear.type = 'button'; clear.textContent = 'Clear filters'; clear.hidden = true;
    bar.appendChild(clear);
    const count = document.createElement('span'); count.className = 'fcount'; bar.appendChild(count);
    const wrap = tbl.closest('.tw') || tbl;
    wrap.parentNode.insertBefore(bar, wrap);
    const useHash = !hashTable; if (useHash) hashTable = tbl;
    const apply = () => {
      const q = box.value.trim().toLowerCase(); let n = 0;
      const active = sels.filter(s => s.value);
      rows.forEach(r => {
        let ok = !q || r.textContent.toLowerCase().includes(q);
        if (ok) for (const s of active) {
          const want = s.value === '—' ? '' : s.value;
          if (!vals(r.cells[+s.dataset.col]).includes(want)) { ok = false; break; }
        }
        r.hidden = !ok; if (ok) n++;
      });
      count.textContent = n === rows.length ? rows.length.toLocaleString() + ' rows'
        : n.toLocaleString() + ' of ' + rows.length.toLocaleString() + ' rows';
      clear.hidden = !(q || active.length);
      if (useHash) {
        const h = active.map(s => s.dataset.col + '=' + encodeURIComponent(s.value)).join('&');
        if (h || location.hash.startsWith('#f:')) history.replaceState(null, '', h ? '#f:' + h : location.pathname + location.search);
      }
    };
    if (useHash && location.hash.startsWith('#f:')) location.hash.slice(3).split('&').forEach(kv => {
      const [c, v] = kv.split('='); const s = sels.find(s => s.dataset.col === c); if (s) s.value = decodeURIComponent(v || '');
    });
    let t = null;
    box.addEventListener('input', () => { clearTimeout(t); t = setTimeout(apply, rows.length > 3000 ? 180 : 0); });
    sels.forEach(s => s.addEventListener('change', apply));
    clear.addEventListener('click', () => { box.value = ''; sels.forEach(s => { s.value = ''; }); apply(); });
    apply();
  });

  /* ---- calendar: a link to #d-<date> lights up every contest of that day ---- */
  const day = () => {
    document.querySelectorAll('tr.day').forEach(r => r.classList.remove('day'));
    if (!location.hash.startsWith('#d-')) return;
    const rows = document.querySelectorAll('tr[data-d="' + location.hash.slice(3).replace(/[^0-9-]/g, '') + '"]');
    rows.forEach(r => r.classList.add('day'));
    if (rows.length) rows[0].scrollIntoView({block: 'center'});
  };
  day(); window.addEventListener('hashchange', day);

  /* ---- search: one box in the header of every page; the index loads on first use ---- */
  const q = document.getElementById('q'), out = document.getElementById('hits');
  if (!q || !out) return;
  const HREF = {c: 'contest/', r: 'series/', s: 'problemset/', p: 'problem/', l: 'location/', j: 'judge/', e: 'season/'};
  const KIND = {c: 'contest', r: 'series', s: 'problem set', p: 'problem', l: 'location', j: 'judge', e: 'season'};
  const RANK = {e: 0, r: 1, c: 2, l: 3, j: 4, s: 5, p: 6};
  let idx = null, sel = -1;
  const load = () => idx || (idx = fetch(REL + 'search.json').then(r => r.json()));
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const score = (c, term) => {
    const id = c.id, name = (c.name || '').toLowerCase();
    if (id === term) return 0;
    if (id.startsWith(term)) return 1;
    if (name.startsWith(term)) return 2;
    if (id.includes(term) || name.includes(term)) return 3;
    return 4;
  };
  /* An address in the box finds source pages. source-urls.json ([address, source page, what it serves]) loads only then.
     Addresses are compared without scheme, "www.", a trailing slash or letter case, and a Wayback address counts as the
     page inside it. Best first: the address itself, the same path on another host, addresses below or above it, the same
     file name elsewhere, a part of an address; the rest of the host only when nothing else matches. */
  let srcIdx = null, seq = 0;
  const norm = u => u.trim().replace(/^https?:\/\/web\.archive\.org\/web\/\d+[a-z_]*\//i, '')
    .replace(/^[a-z][a-z0-9+.-]*:\/\//i, '').replace(/^www\./i, '').replace(/#.*$/, '').replace(/\/+$/, '').toLowerCase();
  const parts = n => {
    const i = n.indexOf('/'), path = i < 0 ? '' : n.slice(i), file = path.slice(path.lastIndexOf('/') + 1).replace(/\?.*$/, '');
    return {host: i < 0 ? n : n.slice(0, i), path, file: /\d/.test(file) && file.length >= 8 ? file : ''};
  };
  const loadSrc = () => srcIdx || (srcIdx = fetch(REL + 'source-urls.json').then(r => r.json())
    .then(d => d.map(([url, k, what]) => { const n = norm(url); return Object.assign({url, k, what, n}, parts(n)); })));
  const WHY = ['', 'the same path on another host', 'below this address', 'this address lies below it', 'the same file name elsewhere',
    'contains what you typed', 'on the same host'];
  const sources = async raw => {
    const n = norm(raw), w = parts(n);
    if (n.length < 4) return [];
    const tier = s => s.n === n ? 0
      : w.path.length > 1 && s.path === w.path ? 1
      : s.n.startsWith(n) ? 2
      : n.startsWith(s.n + '/') ? 3
      : w.file && s.file === w.file ? 4
      : n.length >= 6 && s.n.includes(n) ? 5
      : w.host.includes('.') && s.host === w.host ? 6 : 9;
    const found = (await loadSrc()).map(s => [tier(s), s]).filter(x => x[0] < 9)
      .sort((a, b) => a[0] - b[0] || a[1].n.length - b[1].n.length || a[1].n.localeCompare(b[1].n));
    return found.some(x => x[0] < 6) ? found.filter(x => x[0] < 6) : found;
  };
  const srcHtml = (found, most) => found.slice(0, most).map(([t, s]) =>
    `<a href="${REL}source/${s.k}/index.html"><span class="k">source</span><span class="ad">${esc(s.url)}</span>` +
    `<span class="x">${esc(s.what)}${t ? ' · ' + WHY[t] : ''}</span></a>`).join('') +
    (found.length > most ? `<p>${found.length - most} more sources — give more of the address to narrow it down.</p>` : '');
  const run = async () => {
    const raw = q.value.trim(), term = raw.toLowerCase(), my = ++seq;
    if (term.length < 2) { out.classList.remove('open'); out.innerHTML = ''; return; }
    const addr = /:\/\/|^[^\s\/]+\.[a-z]{2,}\/./i.test(raw);                 // an address with a path
    const host = !addr && /^[^\s\/]+\.[a-z]{2,}\/?$/i.test(raw);              // a bare host: a few of its sources, then the rest
    const [data, src] = await Promise.all([load(), addr || host ? sources(raw) : []]);
    if (my !== seq) return;                                                  // a later keystroke has taken over
    const hits = data.filter(c => c.id.includes(term) ||
      (c.name && c.name.toLowerCase().includes(term)) ||
      (c.cms || []).some(x => x === term) || (c.hosts || []).some(h => h.includes(term)) ||
      (c.aliases || []).some(a => a.toLowerCase().includes(term)));
    hits.sort((a, b) => score(a, term) - score(b, term) || RANK[a.t] - RANK[b.t] || a.id.localeCompare(b.id, undefined, {numeric: true}));
    sel = -1;
    const usual = hits.slice(0, 60).map(c =>
      `<a href="${REL}${HREF[c.t]}${esc(c.id)}.html"><span class="k">${KIND[c.t]}</span><span>${esc(c.t === 'p' || c.t === 'l' || c.t === 'j' ? (c.name || c.id) : c.id)}` +
      `${c.name && !(c.t === 'p' || c.t === 'l' || c.t === 'j') ? ' <span class="muted">' + esc(c.name) + '</span>' : ''}</span>` +
      `<span class="x">${esc([c.date, c.extra].filter(Boolean).join(' · '))}</span></a>`).join('') +
      (hits.length > 60 ? `<p>${hits.length - 60} more — keep typing to narrow it down.</p>` : '');
    out.innerHTML = (srcHtml(src, addr ? 12 : 5) + usual) ||
      (addr ? '<p>No source has this address, or one like it.</p>'
            : '<p>Nothing matches. Search knows ids, names, CMS ids, website hosts, aliases and the addresses of sources.</p>');
    out.classList.add('open');
  };
  let st = null;
  q.addEventListener('focus', load);
  q.addEventListener('input', () => { clearTimeout(st); st = setTimeout(run, 120); });
  q.addEventListener('keydown', e => {
    const items = Array.from(out.querySelectorAll('a'));
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!items.length) return;
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items.forEach((a, i) => a.classList.toggle('sel', i === sel));
      items[sel].scrollIntoView({block: 'nearest'});
    } else if (e.key === 'Enter' && items.length) {
      location.href = items[Math.max(sel, 0)].href;
    } else if (e.key === 'Escape') { out.classList.remove('open'); q.blur(); }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.search')) out.classList.remove('open'); });
  document.addEventListener('keydown', e => {
    if (e.key === '/' && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) { e.preventDefault(); q.focus(); }
  });
})();

// Random: the header link and the key r open a random page; of any kind, or of the kind last chosen on
// random.html (kept for the browser session).
(function () {
  const a = document.getElementById('rnd');
  if (!a) return;
  const rel = document.documentElement.dataset.rel || '';
  let kind = 'any';
  try { kind = sessionStorage.getItem('rnd') || 'any'; } catch (e) {}
  a.href = rel + 'random.html#' + kind;
  if (kind !== 'any') a.title = 'Open a random ' + kind + ' page — press r (change the kind on the Random page)';
  document.addEventListener('keydown', e => {
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey && !e.altKey && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName)) a.click();
  });
})();

// Review mode: a link ending in ?review=1 switches it on for this browser, and so does the header's Review button once
// review mode is open to everyone. Everything else is in assets/review.js, which is loaded only while review mode is on.
(function () {
  let a = document.getElementById('rv');
  const root = document.documentElement, rel = root.dataset.rel || '';
  let on = false;
  try {
    if (/[?&]review=1(&|$)/.test(location.search)) localStorage.setItem('rv-on', '1');
    on = localStorage.getItem('rv-on') === '1';
  } catch (e) {}
  function click(e) {
    e.preventDefault();
    if (window.RV) return window.RV.panel();
    if (root.classList.contains('rv')) return;
    try { localStorage.setItem('rv-on', '1'); } catch (x) {}
    start(true);
  }
  function start(open) {
    root.classList.add('rv');
    if (!a) {
      a = Object.assign(document.createElement('a'), { id: 'rv', href: '#', textContent: 'Review' });
      const nav = document.querySelector('header.site nav');
      if (nav) nav.append(a);
      a.addEventListener('click', click);
    }
    document.head.append(Object.assign(document.createElement('link'), { rel: 'stylesheet', href: rel + 'assets/review.css' }));
    const load = (src, then) => document.head.append(Object.assign(document.createElement('script'), { src: rel + 'assets/' + src, onload: then }));
    load('units.js', () => load('review.js', () => { if (open && window.RV) window.RV.panel(); }));
  }
  if (a) a.addEventListener('click', click);
  if (on) start(false);
})();
