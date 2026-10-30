const API_PREFIX = '/api/v1/homework';  // CSV endpoints
const ep = (path) => `${API_PREFIX}/${path.replace(/^\/+/, '')}`;


var questionEndPointDate  = ep('question_date/');
Plotly.d3.json(questionEndPointDate, function(error, response) {
    if (error) return console.warn(error);

    a = d3.select("#checkboxesDates")
    for (var i = 0; i < response.length; i++){
                a.append('input')
                .attr('type','checkbox')
                .attr('class','dates')
                .attr('value',response[i])
                .attr('id',response[i])
                a.append('label')
                .attr('for',response[i])
                .text("\u00A0"+response[i]+"\u00A0"+"\u00A0")
    }
});

var questionEndPointTopic = ep('question_list/');

// Assignments are named "MM.DD Name" (or "Lesson N Name"): one card per student or class (group classes first,
// newest class first, then students A-Z),
// with that student's assignments newest first.
function assignmentDate(mmdd) {
    var p = mmdd.split('.'), today = new Date();
    var d = new Date(today.getFullYear(), +p[0] - 1, +p[1]);
    if (d > today) d.setFullYear(d.getFullYear() - 1);  // labels carry no year
    return d;
}

function isGroupClass(name) { return name.indexOf('Group Class') === 0; }

function groupAssignments(topics) {
    var groups = {};
    topics.forEach(function (t) {
        // "Lesson 2 Vince": a training assignment, labeled by lesson, Lesson 1 first
        var m = t.match(/^(\d{2}\.\d{2}|Lesson \d+)\s+(.+)$/), lesson = m && m[1].indexOf('Lesson') === 0;
        var name = m ? m[2] : 'Other', label = !m ? t : lesson ? m[1] : m[1].replace('.', '/');
        var when = !m ? 0 : lesson ? -parseInt(m[1].slice(7), 10) : assignmentDate(m[1]);
        (groups[name] = groups[name] || []).push({ value: t, label: label, date: when });
    });
    var names = Object.keys(groups).sort(function (a, b) {
        var ga = isGroupClass(a), gb = isGroupClass(b);
        if (ga !== gb) return ga ? -1 : 1;
        if (ga) return latest(groups[b]) - latest(groups[a]);
        return a.localeCompare(b);
    });
    return names.map(function (n) {
        return { name: n, items: groups[n].sort(function (a, b) { return b.date - a.date; }) };
    });
    function latest(items) { return Math.max.apply(null, items.map(function (i) { return +i.date; })); }
}

function filterGroups() {
    var q = document.getElementById('nameSearch').value.trim().toLowerCase(), shown = 0;
    document.querySelectorAll('.hwGroup').forEach(function (g) {
        var match = !q || g.getAttribute('data-name').toLowerCase().indexOf(q) !== -1;
        g.style.display = match ? '' : 'none';
        shown += match;
    });
    document.querySelector('.hwNone').style.display = shown ? 'none' : '';
}

Plotly.d3.json(questionEndPointTopic, function(error, response) {
    if (error) return console.warn(error);

    var box = document.getElementById('checkboxesTopics');
    groupAssignments(response).forEach(function (g) {
        var card = document.createElement('div');
        card.className = 'hwGroup' + (isGroupClass(g.name) ? ' groupClass' : '');
        card.setAttribute('data-name', g.name);
        var h = document.createElement('h4');
        h.textContent = g.name;
        var total = document.createElement('span');
        total.className = 'hwTotal';
        h.appendChild(total);
        card.appendChild(h);
        g.items.forEach(function (it) {
            var label = document.createElement('label'), cb = document.createElement('input');
            cb.type = 'checkbox'; cb.className = 'topics'; cb.value = it.value;
            label.appendChild(cb);
            label.appendChild(document.createTextNode(it.label));
            var count = document.createElement('span');
            count.className = 'hwCount'; count.setAttribute('data-topic', it.value);
            label.appendChild(count);
            card.appendChild(label);
        });
        box.appendChild(card);
    });
    var none = document.createElement('div');
    none.className = 'hwNone'; none.style.display = 'none';
    none.textContent = 'No homework under that name.';
    if (!response.length) {  // a student with nothing linked to them yet
        none.style.display = '';
        none.textContent = 'No homework has been assigned to you yet.';
    }
    box.appendChild(none);

    var search = document.getElementById('nameSearch');
    search.addEventListener('input', filterGroups);
    // a link like /api/v1/homework/#Anthony opens straight to that student's card
    if (location.hash) { search.value = decodeURIComponent(location.hash.slice(1)); filterGroups(); }
    showProgress();
});

// "3/12" beside each assignment and "15/40 done" on the card: questions answered right, out of the
// questions with answer buttons. Students only (tutors get {}), and saved per login, so it survives a re-login.
function showProgress() {
    Plotly.d3.json(ep('progress/'), function (error, prog) {
        if (error || !prog) return;
        document.querySelectorAll('.hwGroup').forEach(function (card) {
            var done = 0, all = 0;
            card.querySelectorAll('.hwCount').forEach(function (c) {
                var p = prog[c.getAttribute('data-topic')];
                if (!p) return;
                done += p[0]; all += p[1];
                c.textContent = p[0] + '/' + p[1] + (p[0] === p[1] ? ' \u2713' : '');
                c.classList.toggle('complete', p[0] === p[1]);
            });
            var t = card.querySelector('.hwTotal');
            t.textContent = all ? done + '/' + all + ' done' : '';
            t.classList.toggle('complete', all > 0 && done === all);
        });
    });
}
window.onAnsweredRight = showProgress;

//queries list of questions
function getQuestionData() {
  // Get all checkboxes
  const sampleValue = document.querySelectorAll('.topics,.dates');

  // Collect checked values only
  let checkedValues = [];
  for (let i = 0; i < sampleValue.length; i++) {
    if (sampleValue[i].checked) {
      checkedValues.push(sampleValue[i].value);
    }
  }

  // If nothing selected, alert user (don’t select everything)
  if (checkedValues.length === 0) {
    alert("Choose at least one topic or date.");
    return;
  }

  // Clear current question list
  document.getElementById("question").innerHTML = "";
  document.getElementById("solve").innerHTML = "";

  // Remove duplicates and empty slots
  const selectedValues = [...new Set(checkedValues.filter(v => v))];
  console.log("Sending filters:", selectedValues);

  // Build endpoint with cleaned list
  const endPointQuestionData = ep(
    'questions/' + encodeURIComponent(selectedValues.join(','))
  );

  Plotly.d3.json(endPointQuestionData, function (error, response) {
    if (error) return console.warn(error);
    appendInnerHTML(response);
    document.getElementById('solve').scrollIntoView({ behavior: 'smooth' });
  });
}
