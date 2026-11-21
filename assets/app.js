/* 党课题库前端：manifest → 逐套读取 → 合并去重 → 应用订正 → 按历史时间排序 → 渲染 */
const DATA = 'data/';
const TYPE = { single: '单选题', multiple: '多选题', blank: '填空题', judge: '判断题', concept: '概念' };
const TABS = ['single', 'multiple', 'blank', 'judge', 'concept', 'history', 'timeline', 'review'];
const REVIEW_KEY = 'dangke.review.v1';

const state = { bank: [], concepts: [], conceptDoc: null, conceptLesson: null, history: [], historyDoc: null, sets: [], corrections: [], view: 'single', q: '', ready: false };
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

async function loadJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(url + ' → HTTP ' + r.status);
  return r.json();
}

const timeKey = (q) => (q.time && Number.isFinite(q.time.sort) ? q.time.sort : null);
const seq = (q) => String(q.setId || '') + String(q.no == null ? '' : q.no).padStart(4, '0');

function normalizeStem(s) {
  return String(s == null ? '' : s).replace(/\s+/g, '')
    .replace(/\u201c/g, '"').replace(/\u201d/g, '"')
    .replace(/\uff08/g, '(').replace(/\uff09/g, ')');
}

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
  const byStem = new Map();
  const richness = (q) => (q.time ? 10 : 0) + Math.min(String(q.explain || '').length, 500) / 100 + ((q.options || []).length ? 2 : 0);
  for (const s of sets) {
    for (const q of s.questions || []) {
      const item = Object.assign({}, q, { setId: s.setId, setTitle: s.title || s.setId });
      const key = item.type + '|' + normalizeStem(item.stem);
      const prev = byStem.get(key);
      if (!prev) { byStem.set(key, item); continue; }
      if (richness(item) > richness(prev)) {
        item.originIds = [...(prev.originIds || [prev.id]), prev.id];
        byStem.set(key, item);
      } else {
        prev.originIds = [...(prev.originIds || [prev.id]), item.id];
      }
    }
  }
  return [...byStem.values()];
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

const CHAPTERS = [
  { max: 192106, label: '1921\u5e74\u0037\u6708\u524d' },
  { max: 194909, label: '1921\u5e74\u0037\u6708\u20141949\u5e74\u0039\u6708' },
  { max: 197811, label: '1949\u5e74\u0031\u0030\u6708\u20141978\u5e74\u0031\u0031\u6708' },
  { max: 201210, label: '1978\u5e74\u0031\u0032\u6708\u20142012\u5e74\u0031\u0030\u6708' },
  { max: 99999999, label: '2012\u5e74\u0031\u0031\u6708\u81f3\u4eca' }
];
function chapterLabel(q) {
  const k = timeKey(q);
  if (k === null) return '\u65f6\u95f4\u5f85\u786e\u8ba4';
  for (const c of CHAPTERS) if (k <= c.max) return c.label;
  return CHAPTERS[CHAPTERS.length - 1].label;
}

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

function conceptCard(c) {
  const time = c.time && c.time.label
    ? `<span class="badge" title="${esc(c.time.note || '')}">${esc(c.time.label)}</span>`
    : '';
  const lesson = c.lesson
    ? `<span class="badge" title="${esc(c.lessonTitle || '')}">第 ${esc(c.lesson)} 课</span>`
    : `<span class="badge muted">课次待定</span>`;
  const tags = (c.tags || []).filter((t) => t !== '概念' && !/^第\s*\d+\s*课$/.test(t))
    .map((t) => `<span class="badge muted">${esc(t)}</span>`).join('');
  const marked = !!review()[c.id];
  return `<article class="card concept" data-id="${esc(c.id)}">
  <div class="meta">${time}${lesson}<span class="badge">概念</span><span>第 ${esc(c.no)} 条</span>${tags}</div>
  <p class="stem">${esc(c.stem)}</p>
  <p class="concept-def">${esc(c.answer)}</p>
  ${c.explain ? `<p class="explain">${esc(c.explain)}</p>` : ''}
  <button class="mark${marked ? ' on' : ''}">${marked ? '已标记复习' : '标记复习'}</button>
</article>`;
}

function historyCard(h) {
  const tags = (h.tags || []).map((t) => `<span class="badge muted">${esc(t)}</span>`).join('');
  const marked = !!review()[h.id];
  return `<article class="card history" data-id="${esc(h.id)}">
  <div class="meta"><span class="badge">${esc(h.time)}</span><span class="badge">党史</span><span>第 ${esc(h.no)} 条</span>${tags}</div>
  <dl class="facts">
    <div><dt>时间</dt><dd>${esc(h.time)}</dd></div>
    <div><dt>地点</dt><dd>${esc(h.place)}</dd></div>
    <div><dt>人物</dt><dd>${esc(h.people)}</dd></div>
    <div class="fact-main"><dt>事件</dt><dd>${esc(h.event)}</dd></div>
  </dl>
  <p class="impact"><span class="impact-label">影响</span>${esc(h.impact)}</p>
  <button class="mark${marked ? ' on' : ''}">${marked ? '已标记复习' : '标记复习'}</button>
</article>`;
}

function renderHistory() {
  let list = state.history.slice();
  if (state.q) {
    const k = state.q.toLowerCase();
    list = list.filter((h) => [h.time, h.place, h.people, h.event, h.impact, (h.tags || []).join(' ')]
      .join(' ').toLowerCase().includes(k));
  }
  list.sort((a, b) => (a.sort || 0) - (b.sort || 0) || a.no - b.no);
  let html = '';
  if (list.length) {
    html = `<p class="history-intro">${esc((state.historyDoc && state.historyDoc.intro) || '按时间顺序记载。')}</p>`;
  }
  let lastStage = '';
  for (const h of list) {
    if (h.stage !== lastStage) { html += `<h2 class="era">${esc(h.stage)}</h2>`; lastStage = h.stage; }
    html += historyCard(h);
  }
  if (!list.length) html = `<p class="empty">${state.history.length ? '没有匹配的党史事件。' : '党史专栏尚未录入。'}</p>`;
  $('#list').innerHTML = html;
  bindMarks();
  stats();
}

function lessonInfo(no) {
  const lessons = (state.conceptDoc && state.conceptDoc.lessons) || [];
  return lessons.find((l) => l.no === no) || null;
}

function renderConceptIndex() {
  let html = '<div class="lesson-index">';
  for (let n = 1; n <= 11; n++) {
    const l = lessonInfo(n);
    const count = state.concepts.filter((c) => c.lesson === n).length;
    const title = l ? l.title : '待录入';
    html += `<button class="lesson-item${l && count ? '' : ' empty'}" data-lesson="${n}">
      <span class="lesson-no">第 ${n} 课</span>
      <span class="lesson-title">${esc(title)}</span>
      <span class="lesson-count">${count} 条</span>
      <span class="lesson-arrow">›</span>
    </button>`;
  }
  html += '</div>';
  $('#list').innerHTML = html;
  $('#list').querySelectorAll('.lesson-item').forEach((btn) => {
    btn.onclick = () => {
      state.conceptLesson = Number(btn.dataset.lesson);
      state.q = '';
      $('#q').value = '';
      render();
      window.scrollTo({ top: 0 });
    };
  });
  stats();
}

function renderConceptLesson() {
  const no = state.conceptLesson;
  const l = lessonInfo(no);
  let list = state.concepts.filter((c) => c.lesson === no);
  if (state.q) {
    const k = state.q.toLowerCase();
    list = list.filter((c) => [c.stem, c.answer, c.explain, (c.tags || []).join(' ')]
      .join(' ').toLowerCase().includes(k));
  }
  list.sort((a, b) => a.no - b.no);
  const head = `<div class="lesson-bar">
    <button class="back" id="back-index">← 返回目录</button>
    <h2>第 ${no} 课 · ${esc(l ? l.title : '待录入')}</h2>
    <span class="lesson-total">${list.length} 条</span>
  </div>`;
  let body = list.map(conceptCard).join('');
  if (!body) body = `<p class="empty">${l ? '没有匹配的概念。' : '本课概念尚未录入。'}</p>`;
  $('#list').innerHTML = head + body;
  $('#back-index').onclick = () => {
    state.conceptLesson = null;
    state.q = '';
    $('#q').value = '';
    render();
    window.scrollTo({ top: 0 });
  };
  bindMarks();
  stats();
}

function renderConcepts() {
  if (state.conceptLesson == null) { renderConceptIndex(); return; }
  renderConceptLesson();
}

function bindMarks() {
  $('#list').querySelectorAll('.mark').forEach((btn) => {
    btn.onclick = () => {
      const id = btn.closest('.card').dataset.id;
      const r = review();
      if (r[id]) delete r[id]; else r[id] = new Date().toISOString().slice(0, 10);
      saveReview(r);
      render();
    };
  });
}

function render() {
  const view = state.view;
  document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('active', b.dataset.view === view));
  if (!state.ready) { $('#list').innerHTML = '<p class="empty">正在加载题库…</p>'; return; }
  const onConceptIndex = view === 'concept' && state.conceptLesson == null;
  const onHistory = view === 'history';
  $('#q').disabled = onConceptIndex;
  $('#q').placeholder = onConceptIndex
    ? '选择课程后可搜索'
    : (onHistory ? '搜索时间 / 地点 / 人物 / 事件 / 影响' : '搜索题干 / 答案 / 解析 / 概念 / 关键词');
  if (view === 'concept') { renderConcepts(); return; }
  if (view === 'history') { renderHistory(); return; }
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
  const grouped = (arr) => {
    let out = '', last = '';
    for (const q of arr) {
      const chapter = chapterLabel(q);
      if (chapter !== last) { out += `<h2 class="era">${chapter}</h2>`; last = chapter; }
      out += card(q);
    }
    return out;
  };
  if (view === 'timeline' || TYPE[view] || view === 'review') {
    html = grouped(dated);
  } else {
    html = dated.map(card).join('');
  }
  if (undated.length) {
    html += `<h2 class="era">\u65f6\u95f4\u5f85\u786e\u8ba4\uff08${undated.length} \u9898\uff09</h2>` + undated.map(card).join('');
  }
  if (!html) html = '<p class="empty">没有匹配的题目。</p>';
  $('#list').innerHTML = html;
  bindMarks();
  stats();
}

function stats() {
  const undated = state.bank.filter((q) => timeKey(q) === null).length;
  const marked = Object.keys(review()).length;
  const cn = state.concepts.length;
  const hn = state.history.length;
  $('#stats').textContent = `共 ${state.bank.length} 题 · ${cn} 条概念 · ${hn} 条党史 · ${state.sets.length} 套 · 时间待定 ${undated} 题 · 已标记复习 ${marked} 个`;
  $('#sets').textContent = state.sets.length
    ? '已并入：' + state.sets.map((s) => `${s.setId}（${(s.questions || []).length} 题）`).join('、')
      + (cn ? `；概念：${(state.conceptDoc && state.conceptDoc.lessons ? state.conceptDoc.lessons.length : 0)}/11 课（${cn} 条）` : '')
      + (hn ? `；党史：${hn} 条` : '')
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
  let conceptDoc = null;
  try { conceptDoc = await loadJSON(DATA + 'concepts.json'); } catch (e) { console.warn('无 concepts.json'); }
  const concepts = (conceptDoc && conceptDoc.items) || [];
  let historyDoc = null;
  try { historyDoc = await loadJSON(DATA + 'history.json'); } catch (e) { console.warn('无 history.json'); }
  const history = (historyDoc && historyDoc.events) || [];
  sets.sort((a, b) => String(a.setId).localeCompare(String(b.setId)));
  const bank = mergeSets(sets);
  const n = applyCorrections(bank, corrections);
  sortByTime(bank);
  state.bank = bank; state.sets = sets; state.corrections = corrections;
  state.concepts = concepts; state.conceptDoc = conceptDoc;
  state.history = history; state.historyDoc = historyDoc;
  state.ready = true;
  console.log(`已加载 ${sets.length} 套 / ${bank.length} 题 / ${concepts.length} 条概念 / ${history.length} 条党史，应用订正 ${n} 条`);
  render();
}

function initNav() {
  const hash = (location.hash || '').slice(1);
  state.view = TABS.includes(hash) ? hash : 'single';
  $('#tabs').onclick = (e) => {
    const b = e.target.closest('button[data-view]');
    if (!b) return;
    state.view = b.dataset.view;
    if (state.view === 'concept') { state.conceptLesson = null; state.q = ''; $('#q').value = ''; }
    location.hash = state.view;
    render();
  };
  $('#q').oninput = (e) => { state.q = e.target.value.trim(); render(); };
  window.addEventListener('hashchange', () => {
    const h = (location.hash || '').slice(1);
    if (TABS.includes(h)) {
      state.view = h;
      if (h === 'concept') { state.conceptLesson = null; state.q = ''; $('#q').value = ''; }
      render();
    }
  });
}

initNav();
render();
boot();
