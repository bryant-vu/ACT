// Shared question rendering, used by the Homework tab and the
// "Practice with Calculator Programs" tab.

//show or hide the answer when the 'Show Answer' button is clicked.
//The button stays put (so the green "Find Similar Questions" button doesn't move)
//and the answer appears to the right of the buttons.
function showAnswer(i) {

        var button = document.getElementsByClassName('button')[i];
        var answer = document.getElementsByClassName('shownAnswer')[i];
        var showing = answer.style.display === 'none';
        answer.style.display = showing ? 'inline-block' : 'none';
        button.value = showing ? 'Hide Answer' : 'Show Answer';

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
                           button = d.append('input')
                               .attr('class','button')
                               .attr('type','button')
                               .attr('value','Show Answer')
                               .attr('onclick','showAnswer('+ i + ')')
                           // opens the Similar Questions Finder on this question
                           // (its own class: showAnswer() counts elements with class 'button')
                           if (response[i]['similar']) {
                               d.append('a')
                                   .attr('class','similarButton')
                                   .attr('href','/api/v1/drill/#' + encodeURIComponent(response[i]['id']))
                                   .attr('target','_blank')
                                   .text('Find Similar Questions')
                           }
                           shownAnswer = d.append('div')
                               .attr('class','shownAnswer')
                               .text(response[i]['ans'])
                               document.getElementsByClassName('shownAnswer')[i].style.display='none';

                //appends image from Amazon AWS to each id
                q.append('img')
                    .attr('src', 'https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.JPG')
                    //retrieve .jpg file if .JPG file not found
                    .attr('onerror', 'this.oneerror=null;this.src=\"https://s3-us-west-1.amazonaws.com/actmath/' + response[i]['date'] + '/' + response[i]['id'] + '.jpg\";')



          }
};
