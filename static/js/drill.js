// "Similar Questions Finder" tab: pick a question, get practice questions like it in 4 groups.
// Data comes from /api/v1/drill/ (exported by question_bank/tools/build_site.py).
// The URL hash remembers the view: #Dec.2019.35 or #search=slope

const DRILL_API = '/api/v1/drill';
const DRILL_GROUPS = [
  ['closest', 'Closest', 'Same skill, same kind of problem.'],
  ['simpler', 'Simpler', 'Easier building blocks for this skill.'],
  ['harder', 'Harder', 'Multi-step problems that use this skill.'],
  ['borderline', 'Borderline', 'A related skill or a different angle on the same idea.'],
];
const DRILL_PAGE = 6;  // cards shown per group before "Show more"

let drillTests = [];

// Google Analytics events (see layout.html); the page never reloads, so each action is sent here
function drillTrack(name, params) {
  if (window.gtag) gtag('event', name, params);
}

function drillEl(tag, attrs, ...children) {
  const node = document.createElement(tag);
  Object.entries(attrs || {}).forEach(([k, v]) => {
    if (k === 'text') node.textContent = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  });
  children.forEach(c => c && node.appendChild(c));
  return node;
}

async function drillGet(path) {
  const response = await fetch(`${DRILL_API}/${path}`);
  if (!response.ok) throw new Error(response.status);
  return response.json();
}

function drillImage(src, alt) {
  const img = drillEl('img', { src, alt, loading: 'lazy' });
  // website images on S3 are saved as either .JPG or .jpg
  img.addEventListener('error', function retry() {
    img.removeEventListener('error', retry);
    img.src = src.endsWith('.JPG') ? src.slice(0, -4) + '.jpg' : src.slice(0, -4) + '.JPG';
  });
  return img;
}

// "Show Answer" asks the server for this one answer, then toggles it
function drillAnswer(id) {
  const answer = drillEl('span', { class: 'drill-answer' });
  const button = drillEl('button', { class: 'btn btn-outline-success btn-sm', type: 'button', text: 'Show Answer' });
  button.addEventListener('click', async () => {
    if (answer.textContent) {
      answer.hidden = !answer.hidden;
      button.textContent = answer.hidden ? 'Show Answer' : 'Hide Answer';
      return;
    }
    button.disabled = true;
    drillTrack('show_answer', { question_id: id });
    try {
      const data = await drillGet(`answer/${encodeURIComponent(id)}`);
      answer.textContent = `Answer: ${data.answer}`;
      button.textContent = 'Hide Answer';
    } catch (e) {
      answer.textContent = "Couldn't load the answer.";
    }
    button.disabled = false;
  });
  return [button, answer];
}

function drillCard(c, isTarget) {
  const skill = c.skill + (c.multi ? ' \u00b7 multi-step' : '');
  const actions = drillEl('div', { class: 'drill-actions' }, ...drillAnswer(c.id));
  if (!isTarget) {
    actions.appendChild(drillEl('button', {
      class: 'btn btn-outline-primary btn-sm ml-auto', type: 'button', text: 'More like this',
      onclick: () => { drillTrack('more_like_this', { question_id: c.id }); location.hash = c.id; },
    }));
  }
  return drillEl('div', { class: 'drill-card' + (isTarget ? ' target' : '') },
    drillEl('strong', { text: c.label }),
    drillEl('div', { class: 'drill-skill', text: skill }),
    drillImage(c.img, c.label),
    actions);
}

function drillGrid(cards) {
  const row = drillEl('div', { class: 'row' });
  cards.forEach(c => row.appendChild(drillEl('div', { class: 'col-12' }, drillCard(c))));
  return row;
}

function drillSection(title, desc, cards) {
  const section = drillEl('div', { class: 'drill-section' },
    drillEl('h3', { text: `${title} (${cards.length})` }),
    drillEl('div', { class: 'drill-desc', text: desc }));
  const grid = drillGrid(cards.slice(0, DRILL_PAGE));
  section.appendChild(grid);
  let shown = DRILL_PAGE;
  if (cards.length > shown) {
    const more = drillEl('button', { class: 'btn btn-primary btn-lg btn-block drill-show-more', type: 'button' });
    const label = () => {
      const left = cards.length - shown;
      more.textContent = `\u25BC Show ${Math.min(DRILL_PAGE, left)} more ${title} questions (${left} left)`;
    };
    label();
    more.addEventListener('click', () => {
      drillTrack('show_more', { group: title });
      cards.slice(shown, shown + DRILL_PAGE).forEach(c =>
        grid.appendChild(drillEl('div', { class: 'col-12' }, drillCard(c))));
      shown += DRILL_PAGE;
      if (shown >= cards.length) more.remove(); else label();
    });
    section.appendChild(more);
  }
  return section;
}

function drillShowNumbers(testName, currentId) {
  const box = document.getElementById('drill-nums');
  box.innerHTML = '';
  const test = drillTests.find(t => t.name === testName);
  if (!test) return;
  test.questions.forEach(([id, n]) => {
    box.appendChild(drillEl('button', {
      type: 'button', class: id === currentId ? 'current' : '', text: n, title: `${test.label} #${n}`,
      onclick: () => { location.hash = id; },
    }));
  });
}

async function drillShowQuestion(id) {
  const result = document.getElementById('drill-result');
  result.innerHTML = '';
  let data;
  try {
    data = await drillGet(`question/${encodeURIComponent(id)}`);
  } catch (e) {
    result.appendChild(drillEl('p', { class: 'drill-note', text: `Couldn't find question ${id}.` }));
    return;
  }
  const test = drillTests.find(t => t.questions.some(([qid]) => qid === id));
  if (test) {
    document.getElementById('drill-test').value = test.name;
    drillShowNumbers(test.name, id);
  }
  drillTrack('open_question', { question_id: id, test: data.target.label.split(' \u00b7 ')[0] });
  const top = drillEl('div', { class: 'drill-section' }, drillEl('h3', { text: 'Your question' }));
  top.appendChild(drillEl('div', { class: 'row' },
    drillEl('div', { class: 'col-12' }, drillCard(data.target, true))));
  result.appendChild(top);
  let any = false;
  DRILL_GROUPS.forEach(([key, title, desc]) => {
    const cards = data.groups[key] || [];
    if (cards.length) { any = true; result.appendChild(drillSection(title, desc, cards)); }
  });
  if (!any) result.appendChild(drillEl('p', { class: 'drill-note', text: 'No similar questions yet.' }));
  // "More like this" is clicked far down the page: bring the new question into view
  if (window.scrollY > result.offsetTop) result.scrollIntoView({ behavior: 'smooth' });
}

async function drillShowSearch(query) {
  const result = document.getElementById('drill-result');
  result.innerHTML = '';
  document.getElementById('drill-search').value = query;
  document.querySelectorAll('#drill-nums .current').forEach(b => b.classList.remove('current'));
  const data = await drillGet(`search/${encodeURIComponent(query)}`);
  drillTrack('search', { search_term: query, results: data.total });  // GA4's standard search event
  const shown = data.results.length < data.total ? ` (showing the first ${data.results.length})` : '';
  const section = drillEl('div', { class: 'drill-section' },
    drillEl('h3', { text: `${data.total} question${data.total === 1 ? '' : 's'} match “${query}”${shown}` }),
    drillEl('div', { class: 'drill-desc', text: 'Ordered by question number. Pick one to see questions like it.' }));
  section.appendChild(drillGrid(data.results));
  result.appendChild(section);
}

function drillRoute() {
  const hash = decodeURIComponent(location.hash.slice(1));
  if (hash.startsWith('search=')) drillShowSearch(hash.slice(7));
  else if (hash) drillShowQuestion(hash);
}

async function drillInit() {
  drillTests = await drillGet('tests/');
  const select = document.getElementById('drill-test');
  drillTests.forEach(t => select.appendChild(drillEl('option', { value: t.name, text: t.label })));
  select.value = drillTests[drillTests.length - 1].name;  // most recent test
  drillShowNumbers(select.value);
  select.addEventListener('change', () => drillShowNumbers(select.value));

  document.getElementById('drill-search-form').addEventListener('submit', e => {
    e.preventDefault();
    const query = document.getElementById('drill-search').value.trim();
    if (!query) return;
    // an exact question ID opens that question
    const id = drillTests.flatMap(t => t.questions).map(([qid]) => qid)
      .find(qid => qid.toLowerCase() === query.toLowerCase());
    location.hash = id ? id : 'search=' + query;
  });
  window.addEventListener('hashchange', drillRoute);
  drillRoute();
}

drillInit();
