// Lessons tab: each lesson's topics and the questions shown in class, in teaching order.

function el(tag, attrs, text) {
  const e = document.createElement(tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  if (text) e.textContent = text;
  return e;
}

// Website questions are on S3 (saved as either .JPG or .jpg): show our sharp 2x copy (at half
// its pixel size) first, and fall back to the S3 original if it's missing. Images in
// static/q, static/drill and the retypeset B04 #55 are 2x; other lesson images are 1x.
function lessonImage(q) {
  const website = q.img.match(/\/actmath\/[^/]+\/(.+)\.jpg$/i);
  const src = website ? `/static/q/${website[1]}.png` : q.img;
  const img = el('img', { src, alt: q.id, loading: 'lazy' });
  if (website || /^\/static\/(q|drill)\/|B04\.55/.test(src)) img.srcset = `${src} 2x`;
  const tries = website ? [q.img, q.img.endsWith('.JPG') ? q.img.slice(0, -4) + '.jpg' : q.img.slice(0, -4) + '.JPG'] : [];
  img.addEventListener('error', () => {
    const next = tries.shift();
    if (!next) return;
    img.removeAttribute('srcset');
    img.src = next;
  });
  return img;
}

// "Show Answer" fetches this one answer from the Finder, then toggles it in place
function answerButton(qid) {
  const button = el('button', { class: 'button', type: 'button' }, 'Show Answer');
  let answer = null;
  button.onclick = async function () {
    if (!answer) {
      try {
        answer = (await (await fetch('/api/v1/drill/answer/' + encodeURIComponent(qid))).json()).answer;
      } catch (e) { answer = '?'; }
    }
    const showing = !button.classList.contains('answerShown');
    button.textContent = showing ? 'Answer: ' + answer : 'Show Answer';
    button.classList.toggle('answerShown', showing);
  };
  return button;
}

// Topic buttons (lighter blue, under the lesson buttons) show one topic of the lesson, or all of them
function showLesson(les, picker, button, topic) {
  picker.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === button));
  const topics = document.getElementById('topicPicker');
  topics.innerHTML = '';
  const all = el('button', { class: 'button', type: 'button' }, 'All topics');
  all.onclick = () => showLesson(les, picker, button);
  topics.appendChild(all);
  les.topics.forEach(function (t, i) {
    const b = el('button', { class: 'button', type: 'button' }, (i + 1) + '. ' + t.topic + (t.detail ? ': ' + t.detail : ''));
    b.onclick = () => showLesson(les, picker, button, i);
    topics.appendChild(b);
  });
  const shown = topic == null ? all : topics.children[topic + 1];
  topics.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === shown));

  const root = document.getElementById('lesson');
  root.innerHTML = '';
  root.appendChild(el('h2', {}, les.title));
  les.topics.forEach(function (t, i) {
    if (topic != null && i !== topic) return;
    const h = el('h3', { class: 'lessonTopic' }, (i + 1) + '. ' + t.topic + (t.detail ? ': ' : ''));
    if (t.detail) h.appendChild(el('small', {}, t.detail));
    root.appendChild(h);
    if (t.note) root.appendChild(el('p', { class: 'lessonNote' }, t.note));
    t.questions.forEach(function (q) {
      const d = el('div', { class: 'lessonQ' + (q.extra ? ' lessonExtra' : '') });
      d.appendChild(el('strong', {}, q.id + (q.extra ? ' (additional practice)' : '')));
      const buttons = el('div');
      if (q.qid) buttons.appendChild(answerButton(q.qid));
      if (q.similar) {
        buttons.appendChild(el('a', { class: 'similarButton', target: '_blank',
          href: '/api/v1/drill/#' + encodeURIComponent(q.qid) }, 'Find Similar Questions'));
      }
      d.appendChild(buttons);
      if (q.img) d.appendChild(lessonImage(q));
      root.appendChild(d);
    });
  });
  // #Lesson 6 shows the whole lesson, #Lesson 6/3 only its 3rd topic
  history.replaceState(null, '', '#' + encodeURIComponent(les.title) + (topic == null ? '' : '/' + (topic + 1)));
}

// Search box: matches topic names, details and question IDs across all lessons
function setupSearch(lessons, picker, buttons) {
  const box = document.getElementById('lessonSearch');
  const results = document.getElementById('searchResults');
  box.oninput = function () {
    results.innerHTML = '';
    const words = box.value.toLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) return;
    const hits = [];
    lessons.forEach(function (les, li) {
      les.topics.forEach(function (t, ti) {
        const text = [les.title, t.topic, t.detail || ''].concat(t.questions.map(q => q.id)).join(' ').toLowerCase();
        if (words.every(w => text.includes(w))) hits.push([li, ti]);
      });
    });
    if (!hits.length) results.appendChild(el('p', { class: 'lessonNote' }, 'No topics match.'));
    hits.forEach(function ([li, ti]) {
      const t = lessons[li].topics[ti];
      const b = el('a', { href: '#' },
        lessons[li].title + ' › ' + (ti + 1) + '. ' + t.topic + (t.detail ? ': ' + t.detail : ''));
      b.onclick = function (e) {
        e.preventDefault();
        box.value = '';
        results.innerHTML = '';
        showLesson(lessons[li], picker, buttons[li], ti);
      };
      results.appendChild(b);
    });
  };
  // Enter opens the first match
  box.onkeydown = function (e) {
    const first = results.querySelector('a');
    if (e.key === 'Enter' && first) first.click();
  };
}

fetch('/api/v1/lessons/data/').then(r => r.json()).then(function (lessons) {
  const picker = document.getElementById('lessonPicker');
  const buttons = lessons.map(function (les) {
    const b = el('button', { class: 'button', type: 'button' }, les.title);
    b.onclick = () => showLesson(les, picker, b);
    picker.appendChild(b);
    return b;
  });
  setupSearch(lessons, picker, buttons);
  const [want, n] = decodeURIComponent(location.hash.slice(1)).split('/');
  const i = Math.max(0, lessons.findIndex(l => l.title === want));
  const topic = n > 0 && lessons[i] && n <= lessons[i].topics.length ? n - 1 : undefined;
  if (lessons.length) showLesson(lessons[i], picker, buttons[i], topic);
});
