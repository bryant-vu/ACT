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

function showLesson(les, picker, button) {
  picker.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === button));
  const root = document.getElementById('lesson');
  root.innerHTML = '';
  root.appendChild(el('h2', {}, les.title));
  les.topics.forEach(function (t, i) {
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
  history.replaceState(null, '', '#' + encodeURIComponent(les.title));
}

fetch('/api/v1/lessons/data/').then(r => r.json()).then(function (lessons) {
  const picker = document.getElementById('lessonPicker');
  const buttons = lessons.map(function (les) {
    const b = el('button', { class: 'button', type: 'button' }, les.title);
    b.onclick = () => showLesson(les, picker, b);
    picker.appendChild(b);
    return b;
  });
  const want = decodeURIComponent(location.hash.slice(1));
  const i = Math.max(0, lessons.findIndex(l => l.title === want));
  if (lessons.length) showLesson(lessons[i], picker, buttons[i]);
});
