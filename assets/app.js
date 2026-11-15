/* 党课题库前端：manifest → 逐套读取 → 合并去重 → 应用订正 → 按历史时间排序 → 渲染 */
const DATA = 'data/';
const TYPE = { single: '单选题', multiple: '多选题', blank: '填空题', judge: '判断题' };
const TABS = ['single', 'multiple', 'blank', 'judge', 'timeline', 'review'];
const REVIEW_KEY = 'dangke.review.v1';

const state = { bank: [], sets: [], corrections: [], view: 'single', q: '' };
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

async function loadJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(url + ' → HTTP ' + r.status);
  return r.json();
}

const timeKey = (q) => (q.time && Number.isFinite(q.time.sort) ? q.time.sort : null);
const seq = (q) => String(q.setId || '') + String(q.no == null ? '' : q.no).padStart(4, '0');

function sortByTime(list) {
  return list.sort((a, b) => {
    const ka = timeKey(a), kb = timeKey(b);
    if (ka === null && kb === null) return seq(a).localeCompare(seq(b));
    if (ka === null) return 1;
    if (kb === null) return -1;
    return ka !== kb ? ka - kb : seq(a).localeCompare(seq(b));
  });
}

function mergeSets(sets) {
  const byId = new Map();
  for (const s of sets) {
    for (const q of s.questions || []) {
      byId.set(q.id, Object.assign({}, q, { setId: s.setId, setTitle: s.title || s.setId }));
    }
  }
  return [...byId.values()];
}

function applyCorrections(bank, corrections) {
  const byId = new Map(bank.map((q) => [q.id, q]));
  let n = 0;
  for (const c of corrections) {
    const q = byId.get(c.id);
    if (!q) { console.warn('订正目标不存在：', c.id); continue; }
    q[c.field] = c.value; n++;
  }
  return n;
}

const review = () => { try { return JSON.parse(localStorage.getItem(REVIEW_KEY) || '{}'); } catch (e) { return {}; } };
const saveReview = (o) => localStorage.setItem(REVIEW_KEY, JSON.stringify(o));

const eraLabel = (sort) => Math.floor(Math.floor(sort / 10000) / 10) * 10 + '年代';

function card(q) {
  const t = q.time && q.time.label
    ? `<span class="badge" title="${esc(q.time.note || '')}">${esc(q.time.label)}</span>`
    : `<span class="badge muted">时间待定</span>`;
  const opts = (q.options || []).length
    ? `<ul class="opts">${q.options.map((o) => `<li>${esc(o)}</li>`).join('')}</ul>` : '';
  const marked = !!review()[q.id];
  return `<article class="card" data-id="${esc(q.id)}">
  <div class="meta">${t}<span class="badge">${TYPE[q.type] || q.type}</span><span>${esc(q.setId)} · 第 ${esc(q.no)} 题</span></div>
  <p class="stem">${esc(q.stem)}</p>${opts}
  <details><summary>答案与解析</summary>
    <p class="answer">答案：${esc(q.answer)}</p>
    <p class="explain">${esc(q.explain)}</p>
    ${q.time && q.time.note ? `<p class="note">时间注记：${esc(q.time.note)}</p>` : ''}
  </details>
  <button class="mark${marked ? ' on' : ''}">${marked ? '已标记复习' : '标记复习'}</button>
</article>`;
}

function render() {
  const view = state.view;
  document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
  let list = state.bank.slice();
  if (TYPE[view]) list = list.filter((q) => q.type === view);
  if (view === 'review') { const r = review(); list = list.filter((q) => r[q.id]); }
  if (state.q) {
    const k = state.q.toLowerCase();
    list = list.filter((q) => [q.stem, q.answer, q.explain, (q.options || []).join(' '), (q.tags || []).join(' ')]
      .join(' ').toLowerCase().includes(k));
  }
  sortByTime(list);
  const dated = list.filter((q) => timeKey(q) !== null);
  const undated = list.filter((q) => timeKey(q) === null);

  let html = '';
  if (view === 'timeline') {
    let lastEra = '';
    for (const q of dated) {
      const e = eraLabel(timeKey(q));
      if (e !== lastEra) { html += `<h2 class="era">${e}</h2>`; lastEra = e; }
      html += card(q);
    }
  } else {
    html = dated.map(card).join('');
  }
  if (undated.length) {
    html += `<h2 class="era">时间待定（${undated.length} 题，可在 corrections.json 补时间）</h2>`
      + undated.map(card).join('');
  }
  if (!html) html = '<p class="empty">没有匹配的题目。</p>';
  $('#list').innerHTML = html;
  $('#list').querySelectorAll('.mark').forEach((btn) => {
    btn.onclick = () => {
      const id = btn.closest('.card').dataset.id;
      const r = review();
      if (r[id]) delete r[id]; else r[id] = new Date().toISOString().slice(0, 10);
      saveReview(r);
      render();
    };
  });
  stats();
}

function stats() {
  const undated = state.bank.filter((q) => timeKey(q) === null).length;
  const marked = Object.keys(review()).length;
  $('#stats').textContent = `共 ${state.bank.length} 题 · ${state.sets.length} 套 · 时间待定 ${undated} 题 · 已标记复习 ${marked} 题`;
  $('#sets').textContent = state.sets.length
    ? '已并入：' + state.sets.map((s) => `${s.setId}（${(s.questions || []).length} 题）`).join('、')
    : '';
}

async function boot() {
  let manifest = { sets: [] };
  try { manifest = await loadJSON(DATA + 'manifest.json'); } catch (e) { console.error(e); }
  let corrections = [];
  try { corrections = (await loadJSON(DATA + 'corrections.json')).corrections || []; } catch (e) { console.warn('无 corrections.json'); }
  const sets = [];
  for (const f of manifest.sets || []) {
    try { sets.push(await loadJSON(DATA + 'sets/' + f)); } catch (e) { console.error('跳过套题 ' + f, e); }
  }
  sets.sort((a, b) => String(a.setId).localeCompare(String(b.setId)));
  const bank = mergeSets(sets);
  const n = applyCorrections(bank, corrections);
  sortByTime(bank);
  state.bank = bank; state.sets = sets; state.corrections = corrections;
  const hash = (location.hash || '').slice(1);
  state.view = TABS.includes(hash) ? hash : 'single';
  $('#tabs').onclick = (e) => {
    const b = e.target.closest('button[data-view]');
    if (!b) return;
    state.view = b.dataset.view;
    location.hash = state.view;
    render();
  };
  $('#q').oninput = (e) => { state.q = e.target.value.trim(); render(); };
  window.addEventListener('hashchange', () => {
    const h = (location.hash || '').slice(1);
    if (TABS.includes(h)) { state.view = h; render(); }
  });
  console.log(`已加载 ${sets.length} 套 / ${bank.length} 题，应用订正 ${n} 条`);
  render();
}
boot();
