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

// Assignments are named "MM.DD Name": one card per student or class (group classes first,
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
        var m = t.match(/^(\d{2}\.\d{2})\s+(.+)$/);
        var name = m ? m[2] : 'Other', label = m ? m[1].replace('.', '/') : t;
        (groups[name] = groups[name] || []).push({ value: t, label: label, date: m ? assignmentDate(m[1]) : 0 });
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
        // "Show all" checks every assignment in this card and loads them
        var all = document.createElement('button');
        all.type = 'button';
        all.textContent = g.items.length > 1 ? 'Show all ' + g.items.length : 'Show';
        all.onclick = function () {
            document.querySelectorAll('.topics').forEach(function (c) { c.checked = card.contains(c); });
            getQuestionData();
        };
        h.appendChild(all);
        card.appendChild(h);
        g.items.forEach(function (it) {
            var label = document.createElement('label'), cb = document.createElement('input');
            cb.type = 'checkbox'; cb.className = 'topics'; cb.value = it.value;
            label.appendChild(cb);
            label.appendChild(document.createTextNode(it.label));
            card.appendChild(label);
        });
        box.appendChild(card);
    });
    var none = document.createElement('div');
    none.className = 'hwNone'; none.style.display = 'none';
    none.textContent = 'No homework under that name.';
    box.appendChild(none);

    var search = document.getElementById('nameSearch');
    search.addEventListener('input', filterGroups);
    // a link like /api/v1/homework/#Anthony opens straight to that student's card
    if (location.hash) { search.value = decodeURIComponent(location.hash.slice(1)); filterGroups(); }
});

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
