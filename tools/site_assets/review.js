/* Review mode: confirm, correct and add to what the archive says (DEFINITIONS.md, Review mode).

   site.js loads this file only when review mode is on. Every reviewable unit on a page is a
   <span class="u" data-u="unit" data-v="value" [data-of="which one"]> written by the generator
   (tools/review_units.py); the page's object is named by <h1 data-at="kind/id">.

   Marks are kept in this browser (localStorage) until "Submit review" hands them as JSON to the issue
   form of REPO: in the link itself when they fit, by copy and paste when not. Nothing is sent from here. */
(function () {
  'use strict';
  const REPO = window.RV_REPO || 'icpc-contest-archive/reviews';
  const KEY = 'icpc-review', LIMIT = 50000, KEEP_SENT_DAYS = 60;
  // GitHub carries a link of 5,000 characters through its sign-in page; a longer one loses the review there, and
  // from 7,100 it is refused (measured 2026-11-13, not documented). A review that fits goes in the link, the rest is pasted.
  const LINK_MAX = 4500;
  const doc = document, root = doc.documentElement, rel = root.dataset.rel || '';
  const UN = window.RV_UNITS || {};
  const h1 = doc.querySelector('h1[data-at]');
  const AT = h1 ? h1.dataset.at : null, KIND = AT ? AT.split('/')[0] : null;
  // what a source added from each section of a contest page can be
  const ROLES = {
    website: [['web', 'website']],
    results: [['scoreboard', 'scoreboard'], ['frozen_scoreboard', 'frozen scoreboard'], ['standings', 'standings'],
              ['rankings', 'rankings'], ['teams', 'team list']],
    problems: [['problemset', 'problem set'], ['problem', 'single problem'], ['editorial', 'editorial']],
    other: [['report', 'report or news item'], ['teams', 'team list']],
  };

  // ---------- small helpers ----------
  // Put kids into a parent, skipping the ones that are not there. (The browser's own append() would write the word "null".)
  function add(parent, ...kids) {
    for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) parent.append(kid);
    return parent;
  }
  function el(tag, attrs, ...kids) {
    const e = doc.createElement(tag);
    for (const k in attrs || {}) {
      const v = attrs[k];
      if (v == null || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else e.setAttribute(k, v === true ? '' : v);
    }
    return add(e, ...kids);
  }
  const btn = (text, onclick, cls, title) => el('button', { type: 'button', class: cls || 'rvb', title: title, onclick: onclick, text: text });
  const short = (s, n) => { s = s == null ? '' : String(s); n = n || 60; return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const def = (kind, unit) => (UN[kind] && UN[kind][unit]) || (UN['*'] && UN['*'][unit]) || { l: unit, m: false, h: '' };
  const kindOf = at => at.split('/')[0];
  const pageOf = at => { const k = kindOf(at), id = at.slice(k.length + 1); return k === 'site' ? 'index.html' : k === 'source' ? 'source/' + id + '/index.html' : k + '/' + id + '.html'; };
  const today = () => new Date().toISOString().slice(0, 10);
  function valueText(i) {
    if (i.file) return i.file.name + ' (file)';
    const t = i.to;
    if (t && typeof t === 'object') return (t.roles || []).join(', ') + (t.scope ? ', ' + t.scope : '') + (t.url ? ' ' + t.url : '');
    return t == null ? '' : String(t);
  }
  function describe(i) {
    const d = def(kindOf(i.at), i.unit);
    if (i.do === 'confirm') return d.l + ': ' + (i.ofl && i.saw === i.of ? i.ofl : short(i.saw));
    if (i.do === 'correct') return d.l + ': ' + (i.saw ? short(i.saw, 40) + ' → ' : '') + short(valueText(i));
    return d.l + ': + ' + short(valueText(i));
  }

  // which one, for the list: the name when the generator gave one, else the id or address; nothing when the line already says it
  const which = i => i.do === 'add' && i.unit === 'source' ? i.of : i.ofl ? (i.saw === i.of ? '' : i.ofl) : (i.of && i.of !== i.saw && i.of !== i.to ? i.of : '');

  // ---------- state: this browser only ----------
  let st = { items: [], sent: [], n: 0 };
  function load() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY));
      st = { items: (s && s.items) || [], sent: (s && s.sent) || [], n: (s && s.n) || 0 };
    } catch (e) { st = { items: [], sent: [], n: 0 }; }
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(st)); return true; }
    catch (e) { toast('This browser refused to store the review (' + e.name + '). Marks will be lost when the page closes.'); return false; }
  }
  // Other tabs may have changed the list: always read it again before changing it.
  function change(fn) {
    load(); fn();
    st.sent = st.sent.filter(s => s.t > Date.now() - KEEP_SENT_DAYS * 864e5);
    save(); render();
  }
  const same = (i, at, unit, of) => i.at === at && i.unit === unit && (i.of || '') === (of || '');
  function put(item, replace) {
    change(() => {
      if (replace) st.items = st.items.filter(i => !(same(i, item.at, item.unit, item.of) && i.do !== 'add') && !(same(i, item.at, item.unit, item.of) && replace === 'all'));
      item.id = ++st.n;
      st.items.push(item);
    });
  }
  const drop = id => change(() => { st.items = st.items.filter(i => i.id !== id); });

  // ---------- the page: controls on every unit ----------
  const units = () => AT ? Array.from(doc.querySelectorAll('main .u[data-u]')) : [];
  const single = e => !e.classList.contains('ua');
  const mine = e => st.items.filter(i => same(i, AT, e.dataset.u, e.dataset.of));

  function decorate() {
    if (!AT) return;
    doc.querySelectorAll('main details').forEach(d => { if (d.querySelector('.u')) d.open = true; });  // folded lists are reviewed unfolded
    for (const e of units()) {
      const u = e.dataset.u, d = def(KIND, u), c = el('span', { class: 'rvc' });
      if (!single(e)) {                      // a slot: one more of something
        const label = e.textContent.trim();
        e.textContent = '';
        e.append(el('span', { class: 'rvadds' }), btn('+ ' + label, () => u === 'source' && KIND === 'contest' ? sourceForm(e) : form(e, 'add'), 'rvb add'));
        continue;
      }
      if (e.dataset.v === '') c.append(btn('+ add', () => form(e, 'add'), 'rvb add', 'Add: ' + d.l));
      else {
        c.append(btn('✓', () => agree(e), 'rvb ok', 'Confirm: ' + d.l));
        c.append(btn('✎', () => form(e, 'correct'), 'rvb fix', 'Correct: ' + d.l));
        if (u === 'source' && KIND === 'contest' && !(e.closest('tr') || doc).querySelector('.u[data-u=division]')) c.append(btn('⋯', () => sourceMore(e), 'rvb', 'Division of this source'));
      }
      e.after(c);
    }
    const bar = el('div', { class: 'rvbar', id: 'rvbar' });
    const lede = h1.nextElementSibling && h1.nextElementSibling.matches('p.lede, p.rvo') ? h1.nextElementSibling : h1;
    lede.after(bar);
  }

  function agree(e) {
    const had = mine(e).find(i => i.do === 'confirm');
    if (had) return drop(had.id);
    put({ do: 'confirm', at: AT, unit: e.dataset.u, of: e.dataset.of, ofl: e.dataset.l, saw: e.dataset.v }, true);
  }

  function confirmAll() {
    const open = units().filter(e => single(e) && e.dataset.v !== '' && !mine(e).length);
    change(() => {
      for (const e of open) st.items.push({ id: ++st.n, do: 'confirm', at: AT, unit: e.dataset.u, of: e.dataset.of, ofl: e.dataset.l, saw: e.dataset.v });
    });
    toast(open.length + ' facts on this page marked as confirmed.');
  }

  // ---------- render: marks on the page, the count in the header ----------
  function render() {
    const rv = doc.getElementById('rv');
    if (rv) { rv.textContent = 'Review' + (st.items.length ? ' · ' + st.items.length : ''); rv.classList.add('on'); rv.title = st.items.length + ' pending — open the review'; }
    if (AT) {
      for (const e of units()) {
        const its = mine(e);
        e.classList.remove('rv-ok', 'rv-fix', 'rv-stale');
        const c = single(e) ? e.nextElementSibling : null;
        if (c && c.classList.contains('rvc')) c.querySelectorAll('.rvm').forEach(x => x.remove());
        if (!single(e)) {
          const box = e.querySelector('.rvadds');
          box.textContent = '';
          for (const i of its) box.append(mark(i, '+ ' + short(valueText(i), 70)));
          continue;
        }
        for (const i of its) {
          if (i.do === 'confirm') e.classList.add('rv-ok');
          else { e.classList.add('rv-fix'); if (c) c.append(mark(i, (i.do === 'add' ? '+ ' : '→ ') + short(valueText(i), 70))); }
          if (i.saw != null && i.saw !== e.dataset.v) e.classList.add('rv-stale');
        }
        const ok = c && c.querySelector('.rvb.ok');
        if (ok) ok.setAttribute('aria-pressed', e.classList.contains('rv-ok'));
      }
      // extra items of a source row (division) and of the page as a whole (duplicate, remark)
      const bar = doc.getElementById('rvbar');
      if (bar) {
        bar.textContent = '';
        const open = units().filter(e => single(e) && e.dataset.v !== '' && !mine(e).length).length;
        if (open) bar.append(twoStep('Confirm everything shown (' + open + ')', 'Confirm all ' + open + ' facts on this page?', confirmAll));
        bar.append(btn('Duplicate…', () => form(null, 'correct', 'duplicate')), btn('Remark…', () => form(null, 'correct', 'remark')));
        const shown = new Set(units().map(e => e.dataset.u + '|' + (e.dataset.of || '')));
        for (const i of st.items) if (i.at === AT && !shown.has(i.unit + '|' + (i.of || ''))) bar.append(mark(i, describe(i) + (i.of ? ' (' + short(i.of, 40) + ')' : '')));
      }
    }
    if (panelOpen()) drawPanel();
  }
  function mark(i, text) {
    return el('span', { class: 'rvm' + (i.do === 'add' ? ' add' : ''), title: i.why || '' }, text,
      btn('✕', () => drop(i.id), 'rvx', 'Remove from the review'));
  }
  function twoStep(label, question, yes) {
    const box = el('span', { class: 'rv2' });
    const first = () => { box.textContent = ''; box.append(btn(label, ask)); };
    const ask = () => { box.textContent = ''; box.append(el('span', { text: question + ' ' }), btn('Yes', yes, 'rvb ok'), btn('No', first)); };
    first();
    return box;
  }

  // ---------- forms ----------
  let modal = null;
  function closeModal() { if (modal) { modal.remove(); modal = null; } }
  function openModal(title, body, wide) {
    closeModal();
    modal = el('div', { class: 'rvmodal', onclick: e => { if (e.target === modal) closeModal(); } },
      el('div', { class: 'rvcard' + (wide ? ' wide' : ''), role: 'dialog', 'aria-label': title },
        el('div', { class: 'rvhead' }, el('b', { text: title }), btn('✕', closeModal, 'rvx', 'Close')), body));
    doc.body.append(modal);
    const f = modal.querySelector('input:not([type=radio]):not([type=file]), textarea, select');
    if (f) f.focus();
  }
  const field = (label, input, hint) => el('label', { class: 'rvf' }, el('span', { text: label }), input, hint ? el('small', { text: hint }) : null);

  // correct a unit, add a value to an empty one, add one more to a slot, or (e == null) a duplicate/remark on the page
  function form(e, what, anyUnit, at) {
    const unit = e ? e.dataset.u : anyUnit, of = e ? e.dataset.of : undefined, where = at || AT;
    const d = def(e ? KIND : '*', unit), saw = e && single(e) ? e.dataset.v : '';
    const old = e ? (single(e) ? mine(e).find(i => i.do !== 'confirm') : null) : st.items.find(i => same(i, where, unit));
    const long = unit === 'remark' || unit === 'none' || unit === 'ran' || (unit === 'contest' && KIND === 'series') || unit === 'member';
    const val = el(long ? 'textarea' : 'input', { class: 'rvin', placeholder: d.h, rows: long ? 3 : null });
    val.value = old ? valueText(old) : what === 'correct' && !long ? saw : '';
    const why = el('input', { class: 'rvin', placeholder: 'a link, or a few words' });
    if (old) why.value = old.why || '';
    const err = el('p', { class: 'rverr' });
    const needWhy = what === 'correct' && unit !== 'remark';
    const ok = () => {
      const to = val.value.trim(), w = why.value.trim();
      if (!to) return void (err.textContent = 'Please fill in the first field.');
      if (what === 'correct' && saw && to === saw && unit !== 'ran') return void (err.textContent = 'That is what the archive already says. To agree with it, use ✓.');
      if (needWhy && !w) return void (err.textContent = 'Please say how you know: a link or a few words.');
      const item = { do: what, at: where, unit: unit, of: of, to: to };
      if (e && e.dataset.l) item.ofl = e.dataset.l;
      if (what === 'correct' && e) item.saw = saw;
      if (w) item.why = w;
      put(item, !e || single(e) ? 'all' : false);
      closeModal();
    };
    const body = el('form', { novalidate: true, onsubmit: ev => { ev.preventDefault(); ok(); } },
      what === 'correct' && saw ? el('p', { class: 'rvsaw' }, 'The archive says: ', el('b', { text: saw })) : null,
      field(unit === 'remark' ? 'Remark' : unit === 'duplicate' ? 'It duplicates' : what === 'correct' ? (long ? 'What is wrong' : 'It should be') : 'Add', val, long ? d.h : null),
      unit === 'remark' ? null : field(needWhy ? 'How do you know?' : 'How do you know? (optional)', why),
      err, el('div', { class: 'rvacts' }, el('button', { type: 'submit', class: 'rvb go', text: 'Add to review' }), btn('Cancel', closeModal)));
    openModal((what === 'correct' ? 'Correct: ' : 'Add: ') + d.l, body);
  }

  // division of one source row
  function sourceMore(e) {
    const url = e.dataset.of, row = e.closest('tr') || doc;
    const one = (unit, label) => btn(label, () => {
      closeModal();
      const fake = el('span', { class: 'u ua', 'data-u': unit, 'data-of': url, 'data-v': '' });
      form(fake, 'add');
    });
    openModal('Source ' + short(url, 50), el('div', {},
      el('p', {}, one('division', 'Say which division it covers'))));
  }

  // add a source to a section of a contest page: an address, or a file the reviewer has
  function sourceForm(e) {
    const sec = e.dataset.of, roles = ROLES[sec] || ROLES.results;
    const role = el('select', { class: 'rvin' }, roles.map(r => el('option', { value: r[0], text: r[1] })));
    const scope = el('input', { class: 'rvin', placeholder: 'e.g. Division 1 — leave empty when it covers the whole contest' });
    const url = el('input', { class: 'rvin', type: 'url', placeholder: 'https://' });
    const file = el('input', { type: 'file' });
    const why = el('input', { class: 'rvin', placeholder: 'anything we should know' });
    const pick = (v, label, checked) => el('label', { class: 'rvr' }, el('input', { type: 'radio', name: 'rvw', value: v, checked: checked,
      onchange: () => { url.parentElement.hidden = v !== 'url'; file.parentElement.hidden = v !== 'file'; } }), ' ' + label);
    const err = el('p', { class: 'rverr' });
    const fileNote = 'The site does not upload the file. It notes the name, size and checksum; you attach the file itself on GitHub when you submit.';
    const ok = async () => {
      const how = body.querySelector('input[name=rvw]:checked').value;
      const item = { do: 'add', at: AT, unit: 'source', of: sec, to: { roles: [role.value] } };
      if (scope.value.trim()) item.to.scope = scope.value.trim();
      if (why.value.trim()) item.why = why.value.trim();
      if (how === 'url') {
        const u = url.value.trim();
        if (!/^https?:\/\/[^\s/]+\.[^\s]+$/i.test(u)) return void (err.textContent = 'Please give a full address, starting with http:// or https://.');
        const have = units().some(x => x.dataset.u === 'source' && x.dataset.of === u);
        if (have) return void (err.textContent = 'This contest already lists that address. Use ✓ on its row to confirm it.');
        item.to.url = u;
      } else {
        const f = file.files[0];
        if (!f) return void (err.textContent = 'Please choose the file.');
        if (f.size > 25 * 1024 * 1024) return void (err.textContent = 'GitHub takes at most 25 MB per file. Please add a remark saying where the file can be had.');
        err.textContent = 'Reading the file…';
        try { item.file = { name: f.name, size: f.size, sha256: await sha256(f) }; }
        catch (x) { return void (err.textContent = 'Could not read the file: ' + x.message); }
      }
      put(item, false);
      closeModal();
    };
    const body = el('form', { novalidate: true, onsubmit: ev => { ev.preventDefault(); ok(); } },
      field('What it is', role), field('Division', scope),
      el('div', { class: 'rvf' }, el('span', { text: 'Where it is' }), pick('url', 'An address', true), pick('file', 'A file I have')),
      field('Address', url), field('File', file, fileNote), field('Remark (optional)', why),
      err, el('div', { class: 'rvacts' }, el('button', { type: 'submit', class: 'rvb go', text: 'Add to review' }), btn('Cancel', closeModal)));
    file.parentElement.hidden = true;
    openModal('Add a source to ' + AT.split('/')[1] + ', ' + sec, body);
  }
  async function sha256(f) {
    if (!(window.crypto && crypto.subtle)) throw new Error('this browser gives no checksum here (the page must be served over https)');
    const h = await crypto.subtle.digest('SHA-256', await f.arrayBuffer());
    return Array.from(new Uint8Array(h), b => b.toString(16).padStart(2, '0')).join('');
  }

  // ---------- the pending list ----------
  let panel = null;
  const panelOpen = () => !!panel;
  function togglePanel() { if (panel) { panel.remove(); panel = null; } else { panel = el('aside', { class: 'rvpanel', 'aria-label': 'Review' }); doc.body.append(panel); drawPanel(); } }
  function drawPanel() {
    const n = st.items.length, by = new Map();
    for (const i of st.items) (by.get(i.at) || by.set(i.at, []).get(i.at)).push(i);
    const list = el('div', { class: 'rvlist' });
    for (const [at, its] of by) {
      list.append(el('h3', {}, at === 'site' ? 'The archive as a whole' : el('a', { href: rel + pageOf(at), text: at })));
      list.append(el('ul', {}, its.map(i => el('li', { class: i.do }, el('span', { class: 'rvk', text: { confirm: '✓', correct: '✎', add: '+' }[i.do] }),
        el('span', { class: 'rvt', title: i.why || '' }, describe(i), which(i) ? el('small', { text: ' ' + short(which(i), 44) }) : null),
        btn('✕', () => drop(i.id), 'rvx', 'Remove from the review')))));
    }
    const pick = el('input', { type: 'file', accept: '.json,application/json', hidden: true, onchange: ev => loadFile(ev.target.files[0]) });
    panel.textContent = '';
    add(panel,
      el('div', { class: 'rvhead' }, el('b', { text: 'Review' }), btn('✕', togglePanel, 'rvx', 'Close')),
      el('p', { class: 'rvsum', text: n ? n + ' pending. They are kept in this browser until you submit.' : 'Nothing pending. Use ✓, ✎ and + on any page to mark what is right, wrong or missing.' }),
      n ? el('p', {}, btn('Submit review', () => submit(0), 'rvb go big')) : null,
      list,
      el('div', { class: 'rvtools' },
        btn('Add a remark', () => form(null, 'correct', 'remark', AT || 'site')),
        n ? btn('Save to a file', saveFile) : null, btn('Load from a file', () => pick.click()), pick),
      sentBox(),
      el('p', { class: 'rvfoot' }, btn('Leave review mode', leave), el('small', { text: ' Pending marks are kept.' })));
  }
  function sentBox() {
    const sent = st.sent;
    if (!sent.length) return null;
    return el('details', { class: 'rvsent' }, el('summary', { text: 'Sent: ' + sent.length + (sent.length === 1 ? ' review' : ' reviews') }),
      el('ul', {}, sent.map(s => el('li', {}, new Date(s.t).toISOString().slice(0, 10) + ' · ' + s.items.length + ' items ',
        btn('Put back', () => change(() => { st.sent = st.sent.filter(x => x.t !== s.t); for (const i of s.items) { i.id = ++st.n; st.items.push(i); } }), 'rvb', 'It was not submitted after all: make these pending again')))));
  }
  function leave() {
    try { localStorage.removeItem('rv-on'); } catch (e) {}
    location.replace(location.pathname + location.hash);
  }
  function saveFile() {
    const a = el('a', { download: 'icpc-review-' + today() + '.json',
      href: URL.createObjectURL(new Blob([JSON.stringify({ review: 1, pending: st.items }, null, 1)], { type: 'application/json' })) });
    doc.body.append(a); a.click(); a.remove();
  }
  function loadFile(f) {
    if (!f) return;
    f.text().then(t => {
      const got = (JSON.parse(t).pending || []).filter(i => i && i.do && i.at && i.unit);
      change(() => {
        const have = new Set(st.items.map(i => JSON.stringify([i.do, i.at, i.unit, i.of, i.to, i.file])));
        for (const i of got) if (!have.has(JSON.stringify([i.do, i.at, i.unit, i.of, i.to, i.file]))) { i.id = ++st.n; st.items.push(i); }
      });
      toast(got.length + ' items read from the file.');
    }).catch(() => toast('That file is not a saved review.'));
  }

  // ---------- submit: the link carries the review when it fits; else copy, open the form, paste ----------
  const q = JSON.stringify;
  const only = (i, keys) => { const o = {}; for (const k of keys) if (i[k] != null && i[k] !== '') o[k] = i[k]; return o; };
  // encodeURIComponent, but the characters a query may hold stay as they are: a link is short of room
  const enc = s => encodeURIComponent(s).replace(/%2C/g, ',').replace(/%3A/g, ':').replace(/%2F/g, '/').replace(/%40/g, '@');
  const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');
  function parts() {   // one issue holds 65,536 characters: a review larger than LIMIT goes in several
    const out = [[]]; let size = 0;
    for (const i of st.items) {
      const n = q(only(i, ['at', 'unit', 'of', 'saw', 'to', 'file', 'why'])).length + 3;
      if (size + n > LIMIT && out[out.length - 1].length) { out.push([]); size = 0; }
      out[out.length - 1].push(i); size += n;
    }
    return out;
  }
  let built = '';
  // The review as JSON, grouped by page so that it is short, one fact per line (DEFINITIONS.md, Review mode):
  //   "confirm": {page: {unit: value}}, "correct": {page: {unit: {saw, to, why}}}, "add": {page: [{unit, of, to, file, why}]}
  // A unit the object has several of is written "unit which-one".
  function text(items, k, n) {
    const files = items.filter(i => i.file).map(i => i.file.name);
    const name = i => i.unit + (i.of ? ' ' + i.of : '');
    const group = (what, open, close, line) => {
      const by = new Map();
      for (const i of items) if (i.do === what) (by.get(i.at) || by.set(i.at, []).get(i.at)).push(i);
      return by.size ? q(what) + ':{\n' + [...by].map(([at, its]) => q(at) + ':' + open + '\n' + its.map(line).join(',\n') + close).join(',\n') + '}' : null;
    };
    const body = [
      group('confirm', '{', '}', i => q(name(i)) + ':' + q(i.saw)),
      group('correct', '{', '}', i => q(name(i)) + ':' + q(only(i, ['saw', 'to', 'why']))),
      group('add', '[', ']', i => q(only(i, ['unit', 'of', 'to', 'file', 'why']))),
    ].filter(Boolean);
    return '{' + (files.length ? '"reminder":' + q('Attach ' + plural(files.length, 'file') + ' in the box Files below: ' + files.join(', ')) + ',\n' : '')
      + '"review":2,"site":' + q(built) + (n > 1 ? ',"part":[' + (k + 1) + ',' + n + ']' : '') + ',"count":' + items.length + ',\n' + body.join(',\n') + '}';
  }
  async function submit(k) {
    load();
    if (!st.items.length) return;
    if (!built) { try { built = (await (await fetch(rel + 'build.json')).json()).built || ''; } catch (e) { built = ''; } }
    const all = parts(), n = all.length, items = all[Math.min(k, n - 1)];
    const files = items.filter(i => i.file).map(i => i.file.name);
    const title = 'Review: ' + plural(items.length, 'item') + (files.length ? ', ' + plural(files.length, 'file') + ' to attach' : '') + (n > 1 ? ' (part ' + (k + 1) + ' of ' + n + ')' : '');
    const json = text(items, k, n);
    const form = 'https://github.com/' + REPO + '/issues/new?template=review.yml&title=' + enc(title);
    const filled = form + '&review=' + enc(json);
    const byLink = n === 1 && filled.length <= LINK_MAX;   // short enough for the link to carry it
    const said = el('span', { class: 'rvsaid' });
    const box = el('textarea', { class: 'rvin rvjson', readonly: true, rows: 5, onfocus: e => e.target.select() });
    box.value = json;
    const copy = btn('Copy review', async () => {
      let ok = false;
      try { await navigator.clipboard.writeText(json); ok = true; }
      catch (e) { box.closest('details').open = true; box.focus(); box.select(); try { ok = doc.execCommand('copy'); } catch (x) {} }
      said.textContent = ok ? 'Copied ' + plural(items.length, 'item') : 'This browser would not copy. The text is selected below: copy it with Ctrl+C or ⌘C.';
      copy.textContent = 'Copy again';
    }, byLink ? 'rvb' : 'rvb go');
    const done = () => {
      const ids = new Set(items.map(i => i.id));
      change(() => { st.sent.push({ t: Date.now(), title: title, items: st.items.filter(i => ids.has(i.id)) }); st.items = st.items.filter(i => !ids.has(i.id)); });
      closeModal();
      if (st.items.length) submit(0); else toast('Marked as sent. Nothing is pending now.');
    };
    const open = (href, note) => el('li', {}, el('a', { class: 'rvb go', href: href, target: '_blank', rel: 'noopener', text: 'Open GitHub’s form' }), el('small', { text: note }));
    const attach = files.length ? el('li', {}, 'Drag ' + (files.length === 1 ? 'this file' : 'these files') + ' into the box “Files”:', el('ul', {}, files.map(f => el('li', { text: f })))) : null;
    const press = el('li', { text: 'Choose your connection to the contests and press GitHub’s Submit.' });
    openModal('Submit review' + (n > 1 ? ', part ' + (k + 1) + ' of ' + n : '') + ': ' + plural(items.length, 'item') + (files.length ? ', ' + plural(files.length, 'file') : ''),
      el('div', { class: 'rvsub' },
        n > 1 ? el('p', { class: 'rvsaw', text: 'This review is too large for one GitHub issue, so it goes in ' + n + ' parts, one after the other.' }) : null,
        byLink
          ? [el('ol', {}, open(filled, ' opens in a new tab with your review filled in'), attach, press),
             el('p', { class: 'rvalt' }, 'Is the box “Paste your review here” empty on GitHub? ', copy, ' and paste it there. ', said)]
          : el('ol', {}, el('li', {}, copy, ' ', said), open(form, ' opens in a new tab'),
              el('li', { text: 'Click in the box “Paste your review here” and paste.' }), attach, press),
        el('details', {}, el('summary', { text: byLink ? 'What is sent' : 'What is copied' }), box),
        el('div', { class: 'rvacts' }, btn('I submitted it', done, 'rvb ok'), btn('Not yet', closeModal))), true);
  }

  // ---------- messages ----------
  let toastT = 0;
  function toast(msg) {
    let t = doc.getElementById('rvtoast');
    if (!t) { t = el('div', { id: 'rvtoast', role: 'status' }); doc.body.append(t); }
    t.textContent = msg; t.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 5000);
  }

  // ---------- start ----------
  load();
  decorate();
  render();
  window.RV = { panel: togglePanel };
  window.addEventListener('storage', e => { if (e.key === KEY) { load(); render(); } });
  doc.addEventListener('keydown', e => { if (e.key === 'Escape') { if (modal) closeModal(); else if (panel) togglePanel(); } });
})();
