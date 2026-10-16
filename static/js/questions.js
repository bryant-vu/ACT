// Shared question rendering, used by the Homework tab and the
// "Practice with Calculator Programs" tab.

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
                        if (res.correct === true) btn.classList.add('right');
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
                      d.append('div')
                           if (response[i]['choices']) {
                               // one button per answer choice; the server says right or wrong
                               var row = d.append('span').attr('class','choiceRow').attr('data-notrack','1')
                               response[i]['choices'].forEach(function (letter) {
                                   row.append('button')
                                       .attr('class','choiceBtn')
                                       .attr('type','button')
                                       .text(letter)
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
                    q.append('img').attr('src', response[i]['img'])
                    continue
                }

                //appends image from Amazon AWS to each id
                q.append('img')
                    .attr('src', 'https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.JPG')
                    //retrieve .jpg file if .JPG file not found
                    .attr('onerror', 'this.oneerror=null;this.src=\"https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.jpg\";')



          }
};
