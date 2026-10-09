'use strict';
/* SmartSpace web: сцена-плеер. Мост в Python — window.pywebview.api (polling, без колбэков).
   Демо-подмена — ПЕРВОЙ строкой: если страницу открыли в обычном браузере
   (без pywebview), рисуем статичный макет. Живые данные — python main_web.py. */
const $ = (id) => document.getElementById(id);

/* Настоящие контуры Lucide (ISC), inner-SVG из assets/icons. */
const P = {
  search: '<path d="m21 21-4.34-4.34"/><circle cx="11" cy="11" r="8"/>',
  home: '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-6a2 2 0 0 1 2.582 0l7 6A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  sparkles: '<path d="M11.017 2.814a1 1 0 0 1 1.966 0l1.051 5.558a2 2 0 0 0 1.594 1.594l5.558 1.051a1 1 0 0 1 0 1.966l-5.558 1.051a2 2 0 0 0-1.594 1.594l-1.051 5.558a1 1 0 0 1-1.966 0l-1.051-5.558a2 2 0 0 0-1.594-1.594l-5.558-1.051a1 1 0 0 1 0-1.966l5.558-1.051a2 2 0 0 0 1.594-1.594z"/><path d="M20 2v4"/><path d="M22 4h-4"/><circle cx="4" cy="20" r="2"/>',
  layers: '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12"/><path d="M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17"/>',
  sliders: '<path d="M10 5H3"/><path d="M12 19H3"/><path d="M14 3v4"/><path d="M16 17v4"/><path d="M21 12h-9"/><path d="M21 19h-5"/><path d="M21 5h-7"/><path d="M8 10v4"/><path d="M8 12H3"/>',
  shuffle: '<path d="m18 14 4 4-4 4"/><path d="m18 2 4 4-4 4"/><path d="M2 18h1.973a4 4 0 0 0 3.3-1.7l5.454-8.6a4 4 0 0 1 3.3-1.7H22"/><path d="M2 6h1.972a4 4 0 0 1 3.6 2.2"/><path d="M22 18h-6.041a4 4 0 0 1-3.3-1.8l-.359-.45"/>',
  prev: '<path d="M17.971 4.285A2 2 0 0 1 21 6v12a2 2 0 0 1-3.029 1.715l-9.997-5.998a2 2 0 0 1-.003-3.432z"/><path d="M3 20V4"/>',
  next: '<path d="M21 4v16"/><path d="M6.029 4.285A2 2 0 0 0 3 6v12a2 2 0 0 0 3.029 1.715l9.997-5.998a2 2 0 0 0 .003-3.432z"/>',
  play: '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/>',
  pause: '<rect x="14" y="3" width="5" height="18" rx="1"/><rect x="5" y="3" width="5" height="18" rx="1"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
  maximize: '<path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  trash: '<path d="M10 11v6"/><path d="M14 11v6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  zap: '<path d="M15.914 4a1.5 1.5 0 00-2.474-1.561l-9 9A1.5 1.5 0 005.5 14h4.002a.5.5 0 01.471.666L8.086 20a1.5 1.5 0 002.475 1.56l9-9A1.5 1.5 0 0018.5 10h-3.997a.5.5 0 01-.472-.667z"/>',
  code: '<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
  message: '<path d="M2.992 16.342a2 2 0 0 1 .094 1.167l-1.065 3.29a1 1 0 0 0 1.236 1.168l3.413-.998a2 2 0 0 1 1.099.092 10 10 0 1 0-4.777-4.719"/>',
  folder: '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
};
function icon(name, size) {
  size = size || 20;
  return '<svg width="' + size + '" height="' + size + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + (P[name] || P.info) + '</svg>';
}

const GROUPS = {
  'GPU и игры': { color: '#8B5CF6', icon: 'zap', pal: 'violet' },
  'Разработка': { color: '#22C55E', icon: 'code', pal: 'green' },
  'Мессенджеры и приложения': { color: '#2DD4BF', icon: 'message', pal: 'teal' },
  'Windows и обновления': { color: '#FF4A1C', icon: 'shield', pal: 'ember' }
};
const PALS = {
  ember: ['#0B0B0B', '#5A0F0A', '#FF4A1C', 'rgba(255,106,43,.35)'],
  violet: ['#0B0B0B', '#2A1065', '#8B5CF6', 'rgba(167,139,250,.35)'],
  green: ['#0B0B0B', '#0B3B24', '#22C55E', 'rgba(74,222,128,.35)'],
  teal: ['#0B0B0B', '#073B3A', '#2DD4BF', 'rgba(94,234,212,.35)']
};
const RISK_RU = { Safe: 'Безопасно', Moderate: 'Умеренно', Advanced: 'Осторожно' };

let RULES = [], META = {}, RESULTS = {}, CHECKED = new Set();
let FOCUS = 'windows_temp', SCANNING = false, SEEN_FINISHED = true, LOGCUR = 0;
let F_RISK = 'all', F_GROUP = 'all', F_Q = '';

function fmt(n) {
  if (n == null) return '—';
  n = +n; if (n < 0) n = 0;
  const u = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  if (i === 0) return Math.round(n) + ' ' + u[i];
  return (n >= 100 ? Math.round(n) : (n >= 10 ? n.toFixed(1) : n.toFixed(2))) + ' ' + u[i];
}
function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }

/* Демо-подмена моста: если страницу открыли в обычном браузере (без pywebview),
   рисуем статичный макет с пометкой. Живые данные — только через python main_web.py. */
if (!window.pywebview || !window.pywebview.api) {
  const GB = 1024 * 1024 * 1024;
  const demoRes = (id, size) => ({ rule_id: id, size_bytes: size, file_count: 1234, paths_found: ['C:\\demo'], paths_total: 1, errors: [] });
  window.pywebview = { api: {
    get_rules: async () => [
      { id: 'telegram_cache', group: 'Мессенджеры и приложения', title: 'Telegram Desktop: кэш медиа', risk: 'Safe', what: 'Превью фото и видео.', why: 'Кэшируется всё просмотренное.', safety: 'Безопасно.', recommend: 'Чисти смело.' },
      { id: 'npm_cache', group: 'Разработка', title: 'Node.js: npm / yarn / pnpm кэш', risk: 'Safe', what: 'Тарболы пакетов.', why: 'install ничего не чистит.', safety: 'Безопасно.', recommend: 'Чисти смело.' },
      { id: 'dx_shader', group: 'GPU и игры', title: 'DirectX Shader Cache', risk: 'Safe', what: 'Шейдеры.', why: 'Копятся от игр.', safety: 'Безопасно.', recommend: 'После обновления драйвера.' }
    ],
    get_groups: async () => Object.keys(GROUPS),
    disk_info: async () => ({ ok: true, total: 111 * GB, used: 103 * GB, free: 8 * GB }),
    scan_state: async () => ({ running: false, done: 3, total: 3, current: '', finished: true, error: '',
      results: [demoRes('telegram_cache', 3210 * 1024 * 1024), demoRes('npm_cache', 2140 * 1024 * 1024), demoRes('dx_shader', 940 * 1024 * 1024)] }),
    scan_start: async () => ({ ok: true }),
    scan_stop: async () => ({ ok: true }),
    clean_start: async () => ({ ok: true }),
    clean_state: async () => ({ running: false, status: '', result: null }),
    log_poll: async (s) => s > 0 ? { lines: [], next: 1 } : { lines: [{ id: 1, t: '00:00:00', text: 'Демо-режим: живые данные — через python main_web.py' }], next: 1 }
  } };
}
const api = window.pywebview.api;

/* ---------- навигация ---------- */
const NAVICONS = { search: 'search', home: 'home', recs: 'sparkles', library: 'layers', settings: 'sliders' };
const SOON = {
  recs: ['Рекомендации', 'В web-прототипе работают Главная и Поиск. Топ безопасного — в десктопной версии (python main.py).'],
  library: ['Библиотека', 'Анализ диска (топ-100) — в десктопной версии (python main.py).'],
  settings: ['Настройки', 'Спецфайлы и команды — в десктопной версии (python main.py).']
};
function goto(page) {
  document.querySelectorAll('.nav').forEach(b => b.classList.toggle('active', b.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  if (page === 'home' || page === 'search') $('page-' + page).classList.add('active');
  else {
    $('page-soon').classList.add('active');
    $('soonTitle').textContent = SOON[page][0];
    $('soonText').textContent = SOON[page][1];
  }
}

/* ---------- сцена ---------- */
function setBg(pal) {
  const c = PALS[pal] || PALS.ember, b = document.querySelector('.bg-b');
  b.style.background = 'linear-gradient(135deg, ' + c[0] + ' 0%, ' + c[1] + ' 55%, ' + c[2] + ' 100%)';
  b.style.opacity = '1';
  setTimeout(() => {
    const a = document.querySelector('.bg-a');
    a.style.background = b.style.background;
    document.querySelector('.glow').style.background =
      'radial-gradient(closest-side at 62% 46%, ' + c[3] + ', transparent 70%)';
    b.style.opacity = '0';
  }, 520);
}
function setFocus(id) {
  const m = META[id];
  if (!m) return;
  FOCUS = id;
  const g = GROUPS[m.group] || GROUPS['Windows и обновления'];
  $('hero').textContent = m.title;
  const cov = $('cover');
  cov.style.background = 'linear-gradient(135deg, ' + g.color + ', #111)';
  cov.innerHTML = icon(g.icon, 30);
  cov.style.color = '#fff';
  const r = RESULTS[id];
  $('pill').textContent = r && r.size_bytes > 0 ? m.title + ' • ' + fmt(r.size_bytes) : m.title + ' • нажми play';
  setBg(g.pal);
}
function cycleFocus(d) {
  const ids = RULES.map(r => r.id).filter(id => {
    const r = RESULTS[id];
    return !r || r.size_bytes > 0;
  });
  const list = ids.length ? ids : RULES.map(r => r.id);
  let i = list.indexOf(FOCUS);
  if (i < 0) i = 0;
  setFocus(list[(i + d + list.length) % list.length]);
}

/* ---------- облако и коллекции ---------- */
function renderCloud() {
  const box = $('cloud');
  box.innerHTML = '';
  const ind = [0, 24, 48, 24], op = [0.55, 0.85, 1.0, 0.7];
  Object.keys(GROUPS).forEach((g, i) => {
    const m = GROUPS[g];
    const b = document.createElement('button');
    b.className = 'cloud-it';
    b.style.marginLeft = ind[i] + 'px';
    b.style.opacity = op[i];
    b.innerHTML = '<span class="bd" style="background:linear-gradient(135deg,' + m.color + ',#111)">' + icon(m.icon, 28) + '</span><span class="nm">' + esc(g) + '</span>';
    b.style.color = '#fff';
    b.onclick = () => { focusBiggest(g); };
    box.appendChild(b);
  });
  const c = $('colls');
  c.innerHTML = '';
  Object.keys(GROUPS).forEach(g => {
    const m = GROUPS[g];
    const b = document.createElement('button');
    b.className = 'coll';
    b.innerHTML = '<span class="ava" style="background:linear-gradient(135deg,' + m.color + ',#111)">' + esc(g[0]) + '</span><span><span class="nm">' + esc(g) + '</span><br><span class="sb" data-g="' + esc(g) + '">—</span></span>';
    b.onclick = () => { F_GROUP = g; $('groupSel').value = g; goto('search'); renderCards(); };
    c.appendChild(b);
  });
}
function focusBiggest(group) {
  const c = RULES.filter(r => r.group === group);
  if (!c.length) return;
  c.sort((a, b) => ((RESULTS[b.id] || {}).size_bytes || -1) - ((RESULTS[a.id] || {}).size_bytes || -1));
  setFocus(c[0].id);
}

/* ---------- карточки ---------- */
function matches(m) {
  if (F_RISK !== 'all' && m.risk !== F_RISK) return false;
  if (F_GROUP !== 'all' && m.group !== F_GROUP) return false;
  if (F_Q && (m.title + ' ' + m.group + ' ' + m.what).toLowerCase().indexOf(F_Q) < 0) return false;
  return true;
}
function renderCards() {
  const box = $('cards');
  box.innerHTML = '';
  let lastG = null, sel = 0, selN = 0;
  RULES.forEach(m => {
    if (!matches(m)) return;
    if (m.group !== lastG) {
      lastG = m.group;
      const h = document.createElement('div');
      h.className = 'ghead';
      h.textContent = m.group.toUpperCase();
      box.appendChild(h);
    }
    const r = RESULTS[m.id] || {};
    const size = r.size_bytes || 0, cnt = r.file_count || 0;
    if (CHECKED.has(m.id) && size > 0) { sel += size; selN++; }
    const d = document.createElement('div');
    d.className = 'card';
    d.innerHTML =
      '<div class="row1"><input type="checkbox" data-id="' + m.id + '"' + (CHECKED.has(m.id) ? ' checked' : '') + '>' +
      '<span class="tt">' + esc(m.title) + '</span>' +
      '<span class="badge ' + m.risk + '">' + RISK_RU[m.risk] + '</span>' +
      '<span class="sz">' + fmt(size) + '</span></div>' +
      '<div class="ds">Файлов: ' + cnt.toLocaleString('ru-RU') + ' • ' + esc(m.what) + '</div>' +
      '<div class="detail"><b>Почему копится:</b> ' + esc(m.why) + '<br><b>Безопасность:</b> ' + esc(m.safety) +
      '<br><b>Рекомендация:</b> ' + esc(m.recommend) + '</div>' +
      '<div class="row2"><button class="mini" data-more="' + m.id + '">Подробнее</button>' +
      '<button class="mini" data-open="' + esc(JSON.stringify([m.id])) + '">Открыть папку</button></div>';
    box.appendChild(d);
  });
  box.querySelectorAll('input[type=checkbox]').forEach(cb => {
    cb.onchange = () => { cb.checked ? CHECKED.add(cb.dataset.id) : CHECKED.delete(cb.dataset.id); updateSel(); };
  });
  box.querySelectorAll('[data-more]').forEach(b => {
    b.onclick = () => b.closest('.card').classList.toggle('open');
  });
  box.querySelectorAll('[data-open]').forEach(b => {
    b.onclick = async () => {
      const id = JSON.parse(b.dataset.open)[0];
      const r = RESULTS[id];
      if (r && r.paths_found && r.paths_found.length) await api.open_path(r.paths_found[0]);
    };
  });
  updateSel();
}
function updateSel() {
  let s = 0, n = 0;
  CHECKED.forEach(id => {
    const r = RESULTS[id];
    if (r && r.size_bytes > 0) { s += r.size_bytes; n++; }
  });
  $('selLbl').textContent = 'Выбрано: ' + fmt(s) + ' (' + n + ' кат.)';
  $('cleanBtn').textContent = s > 0 ? 'Освободить ' + fmt(s) + ' → в Корзину' : 'Выбрать кэши выше ↑';
  return { s, n };
}

/* ---------- транспорт и раунды ---------- */
async function transport(act) {
  if (act === 'play') {
    const st = await api.scan_state().catch(() => null);
    if (st && st.running) await api.scan_stop();
    else { SEEN_FINISHED = false; await api.scan_start(); }
  } else if (act === 'repeat') { SEEN_FINISHED = false; await api.scan_start(); }
  else if (act === 'shuffle') { selectSafe(); goto('search'); }
  else if (act === 'prev') cycleFocus(-1);
  else if (act === 'next') cycleFocus(1);
}
async function rounds(act) {
  if (act === 'open') {
    const r = RESULTS[FOCUS];
    if (r && r.paths_found && r.paths_found.length) await api.open_path(r.paths_found[0]);
  } else if (act === 'safe') { selectSafe(); goto('search'); }
  else if (act === 'clear') { CHECKED.clear(); renderCards(); }
  else if (act === 'details') {
    F_Q = ''; $('searchInput').value = '';
    const m = META[FOCUS];
    if (m) { F_GROUP = m.group; $('groupSel').value = m.group; }
    goto('search'); renderCards();
  } else if (act === 'trash') startClean(false);
}
function selectSafe() {
  CHECKED.clear();
  RULES.forEach(m => {
    const r = RESULTS[m.id];
    if (m.risk === 'Safe' && r && r.size_bytes > 0) CHECKED.add(m.id);
  });
  renderCards();
}
async function startClean(perm) {
  const ids = RULES.map(r => r.id).filter(id => CHECKED.has(id) && (RESULTS[id] || {}).size_bytes > 0);
  if (!ids.length) return;
  let sum = 0;
  ids.forEach(id => { sum += RESULTS[id].size_bytes; });
  const msg = perm ? 'БЕЗВОЗВРАТНО удалить ' + fmt(sum) + '? Восстановить нельзя!'
    : 'Переместить ' + fmt(sum) + ' в Корзину?';
  if (!confirm(msg)) return;
  $('cleanStatus').textContent = 'Очистка выполняется…';
  const r = await api.clean_start(ids, !!perm).catch(e => ({ ok: false, error: String(e) }));
  if (!r.ok) { $('cleanStatus').textContent = 'Ошибка: ' + (r.error || ''); return; }
  const iv = setInterval(async () => {
    const st = await api.clean_state();
    if (!st.running) {
      clearInterval(iv);
      const res = st.result || {};
      $('cleanStatus').textContent = res.error ? 'Ошибка: ' + res.error
        : 'Готово: ' + fmt(res.freed || 0) + ', пропущено: ' + (res.skipped || 0);
      SEEN_FINISHED = false;
      api.scan_start();
    }
  }, 600);
}

/* ---------- опросы ---------- */
async function pollState() {
  let st = null;
  try { st = await api.scan_state(); } catch (e) { return; }
  SCANNING = !!st.running;
  $('playGlyph').innerHTML = icon(SCANNING ? 'pause' : 'play', 26);
  document.querySelector('.tc.main').style.color = '#111';
  const total = st.total || 1;
  const pct = Math.round(100 * st.done / total);
  $('pfill').style.width = pct + '%';
  $('ppct').textContent = pct + '%';
  $('readyLbl').textContent = st.running ? ('Сканирование ' + st.done + '/' + st.total + ': ' + st.current) : 'Готов';
  if (st.results && st.results.length) {
    RESULTS = {};
    const perGroup = {};
    st.results.forEach(r => {
      RESULTS[r.rule_id] = r;
      const g = perGroup[r.group] || (perGroup[r.group] = { n: 0, s: 0 });
      if (r.paths_total > 0) { g.n++; g.s += r.size_bytes; }
    });
    document.querySelectorAll('#colls .sb').forEach(el => {
      const g = perGroup[el.dataset.g];
      el.textContent = g && g.s > 0 ? fmt(g.s) : '—';
    });
    renderCards();
    if (st.finished && !SEEN_FINISHED) {
      SEEN_FINISHED = true;
      selectSafe();
      const big = st.results.filter(r => r.size_bytes > 0).sort((a, b) => b.size_bytes - a.size_bytes);
      if (big.length) setFocus(big[0].rule_id);
    }
  }
  try {
    const d = await api.disk_info();
    if (d.ok) {
      const sel = updateSel();
      $('statusText').textContent = 'Свободно ' + fmt(d.free) + ' из ' + fmt(d.total) + ' • Выбрано ' + fmt(sel.s);
    }
  } catch (e) { /* тихо */ }
}
async function pollLog() {
  let r = null;
  try { r = await api.log_poll(LOGCUR); } catch (e) { return; }
  if (!r || !r.lines || !r.lines.length) return;
  LOGCUR = r.next;
  const box = $('log');
  const nearBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 60;
  r.lines.forEach(l => {
    const d = document.createElement('div');
    d.textContent = '[' + l.t + '] ' + l.text;
    box.appendChild(d);
  });
  while (box.children.length > 300) box.removeChild(box.firstChild);
  if (nearBottom) box.scrollTop = box.scrollHeight;
}

/* ---------- старт ---------- */
async function boot() {
  document.querySelectorAll('.nav .ic').forEach((el, i) => {
    el.innerHTML = icon(['search', 'home', 'sparkles', 'layers', 'sliders'][i], 20);
  });
  document.querySelectorAll('.nav').forEach(b => { b.onclick = () => goto(b.dataset.page); });
  document.querySelectorAll('.tc[data-act]').forEach(b => {
    if (b.classList.contains('main')) return; // у play свой глиф (playGlyph), не затирать
    const acts = { shuffle: 'shuffle', prev: 'prev', next: 'next', repeat: 'repeat' };
    const a = b.dataset.act;
    b.innerHTML = icon(acts[a] || a, 22);
    b.onclick = () => transport(a);
  });
  $('playGlyph').innerHTML = icon('play', 26);
  document.querySelector('.tc.main').onclick = () => transport('play');
  const rmap = { open: 'maximize', safe: 'shield', clear: 'x', details: 'info', trash: 'trash' };
  document.querySelectorAll('.rd').forEach(b => {
    b.innerHTML = icon(rmap[b.dataset.act], 20);
    b.onclick = () => rounds(b.dataset.act);
  });
  $('spark').innerHTML = icon('sparkles', 14);
  $('spark').style.color = '#ffe600';
  $('spark').style.display = 'inline-flex';
  $('pill').onclick = () => goto('search');
  $('cover').innerHTML = icon('shield', 30);
  $('cover').style.cssText += 'background:linear-gradient(135deg,#FF4A1C,#111);color:#fff;';
  $('logToggle').onclick = () => {
    const b = $('bottom');
    const hidden = b.style.display === 'none';
    b.style.display = hidden ? '' : 'none';
    $('logToggle').textContent = hidden ? 'Закрыть' : 'Показать лог';
  };
  $('searchInput').oninput = e => { F_Q = e.target.value.trim().toLowerCase(); renderCards(); };
  $('riskSel').onchange = e => { F_RISK = e.target.value; renderCards(); };
  $('groupSel').onchange = e => { F_GROUP = e.target.value; renderCards(); };
  $('btnRescan').onclick = () => { SEEN_FINISHED = false; api.scan_start(); };
  $('btnSafe').onclick = () => selectSafe();
  $('btnAll').onclick = () => {
    if ([...CHECKED].length || true) {
      const adv = RULES.filter(m => m.risk === 'Advanced' && (RESULTS[m.id] || {}).size_bytes > 0);
      if (adv.length && !confirm('Есть категории «Осторожно» (' + adv.length + '). Выбрать всё?')) return;
    }
    CHECKED.clear();
    RULES.forEach(m => { if ((RESULTS[m.id] || {}).size_bytes > 0) CHECKED.add(m.id); });
    renderCards();
  };
  $('btnNone').onclick = () => { CHECKED.clear(); renderCards(); };
  $('cleanBtn').onclick = () => startClean(false);
  $('permBtn').onclick = () => startClean(true);

  RULES = await api.get_rules();
  META = {};
  RULES.forEach(m => { META[m.id] = m; });
  const gs = $('groupSel');
  (await api.get_groups().catch(() => [])) .forEach(g => {
    const o = document.createElement('option');
    o.value = g; o.textContent = g;
    gs.appendChild(o);
  });
  renderCloud();
  setFocus('windows_temp');
  renderCards();
  setInterval(pollState, 400);
  setInterval(pollLog, 700);
  pollState();
  pollLog();
}
document.addEventListener('DOMContentLoaded', boot);
