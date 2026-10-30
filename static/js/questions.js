// Shared question rendering, used by the Homework tab and the
// "Practice with Calculator Programs" tab.

// Question images: the sharp 2x copy from this site (shown at half its pixel size);
// if it's missing, the original on S3 (saved as either .JPG or .jpg)
function addQuestionImage(q, date, id) {
    var s3 = 'https://s3-us-west-1.amazonaws.com/actmath/' + date + '/' + id
    var sharp = '/static/q/' + id + '.png'
    var tries = [s3 + '.JPG', s3 + '.jpg']
    q.append('img')
        .attr('src', sharp)
        .attr('srcset', sharp + ' 2x')
        .on('error', function () {
            var next = tries.shift()
            if (!next) return
            this.removeAttribute('srcset')
            this.src = next
        })
}

//'Show Answer' turns into the answer right where the button is; click again to hide it.
//The button keeps its width, so the green "Find Similar Questions" button doesn't move.
function showAnswer(button) {

        var showing = !button.classList.contains('answerShown');
        button.textContent = showing ? 'Answer: ' + button.getAttribute('data-answer') : 'Show Answer';
        button.classList.toggle('answerShown', showing);

      };

//Clicking a choice asks the server if it is right: green = right, red = wrong.
//Every choice stays clickable, so a student can keep trying after a miss.
function checkChoice(qid, letter) {
        return function () {
                var btn = this;
                if (btn.classList.contains('right') || btn.classList.contains('wrong') || btn.classList.contains('checking')) return;
                btn.classList.add('checking');
                fetch('/api/v1/check', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({id: qid, choice: letter})
                }).then(function (r) { return r.json(); }).then(function (res) {
                        btn.classList.remove('checking');
                        if (res.correct === true) {
                                btn.classList.add('right');
                                var check = btn.closest('strong').querySelector('.doneCheck');
                                if (check) check.style.display = '';
                                if (window.onAnsweredRight) window.onAnsweredRight(qid);
                        }
                        else if (res.correct === false) btn.classList.add('wrong');
                }).catch(function () { btn.classList.remove('checking'); });
        };
}

//appends list of questions
function appendInnerHTML(response) {

        d3.select("#solve")
            .append('h2')
            .text("Solve.")

          for (var i = 0; i < response.length; i++){

                q = d3.select("#question")
                      d =  q.append('div')
                      .append('strong')
                      .text(response[i]['id'])
                      // a check once the student has gotten it right (now or on an earlier visit)
                      var tried = response[i]['tried'] || {}
                      var gotIt = Object.keys(tried).some(function (k) { return tried[k]; })
                      if (response[i]['choices']) {
                          d.append('span').attr('class','doneCheck').text('\u2713')
                              .style('display', gotIt ? null : 'none')
                      }
                      d.append('div')
                           if (response[i]['choices']) {
                               // one button per answer choice; the server says right or wrong
                               var row = d.append('span').attr('class','choiceRow').attr('data-notrack','1')
                               response[i]['choices'].forEach(function (letter) {
                                   row.append('button')
                                       .attr('class','choiceBtn')
                                       .attr('type','button')
                                       .text(letter)
                                       .classed('right', tried[letter] === true)
                                       .classed('wrong', tried[letter] === false)
                                       .on('click', checkChoice(response[i]['id'], letter))
                               })
                           } else {
                           button = d.append('button')
                               .attr('class','button')
                               .attr('type','button')
                               .attr('data-answer', response[i]['ans'] || '?')
                               .attr('onclick','showAnswer(this)')
                               .text('Show Answer')
                           }
                           // the two link buttons stack, together as tall as one choice button
                           var links = (response[i]['similar'] || response[i]['classLink'])
                               ? d.append('span').attr('class','linkStack') : d
                           // Homework: opens the question this one practices from class
                           if (response[i]['classLink']) {
                               links.append('a')
                                   .attr('class','classButton')
                                   .attr('href', response[i]['classLink'])
                                   .attr('target','_blank')
                                   .text('Class Example')
                           }
                           // opens the Similar Questions Finder on this question
                           if (response[i]['similar']) {
                               links.append('a')
                                   .attr('class','similarButton')
                                   .attr('href','/api/v1/drill/#' + encodeURIComponent(response[i]['id']))
                                   .attr('target','_blank')
                                   .text('Find Similar Questions')
                           }

                //questions from tests not on S3 come with their own image path
                if (response[i]['img']) {
                    var img = q.append('img').attr('src', response[i]['img'])
                    // images in static/q, static/drill and the retypeset B04 #55 are saved at 2x density
                    if (/^\/static\/(q|drill)\/|B04\.55/.test(response[i]['img'])) img.attr('srcset', response[i]['img'] + ' 2x')
                    continue
                }

                //appends image from Amazon AWS to each id
                addQuestionImage(q, response[i]['date'], response[i]['id'])



          }
};
