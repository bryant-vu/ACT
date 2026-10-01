// Shared question rendering, used by the Homework tab and the
// "Practice with Calculator Programs" tab.

//'Show Answer' turns into the answer right where the button is; click again to hide it.
//The button keeps its width, so the green "Find Similar Questions" button doesn't move.
function showAnswer(button) {

        var showing = !button.classList.contains('answerShown');
        button.textContent = showing ? 'Answer: ' + button.getAttribute('data-answer') : 'Show Answer';
        button.classList.toggle('answerShown', showing);

      };

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
                           button = d.append('button')
                               .attr('class','button')
                               .attr('type','button')
                               .attr('data-answer', response[i]['ans'] || '?')
                               .attr('onclick','showAnswer(this)')
                               .text('Show Answer')
                           // opens the Similar Questions Finder on this question
                           if (response[i]['similar']) {
                               d.append('a')
                                   .attr('class','similarButton')
                                   .attr('href','/api/v1/drill/#' + encodeURIComponent(response[i]['id']))
                                   .attr('target','_blank')
                                   .text('Find Similar Questions')
                           }

                //appends image from Amazon AWS to each id
                q.append('img')
                    .attr('src', 'https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.JPG')
                    //retrieve .jpg file if .JPG file not found
                    .attr('onerror', 'this.oneerror=null;this.src=\"https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.jpg\";')



          }
};
