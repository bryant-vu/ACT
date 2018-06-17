var questionEndPoint = '/api/v1/question_list'

Plotly.d3.json(questionEndPoint, function(error, response) {
    if (error) return console.warn(error);

    for (var i = 0; i < response.length; i++){
        d3.select("#questionDropdown")
              .append('option')
              .attr('value', response[i])
              .text(response[i])
    }

});

//display answer when 'Show Answer' button is clicked
function showAnswer(i) {

        document.getElementsByClassName('button')[i].style.display="none";
        document.getElementsByClassName('shownAnswer')[i].style.display='table'

      }

//queries topic list and questions
function getQuestionData() {

        sampleValue = document.getElementById("questionDropdown").value;

        document.getElementById("question").innerHTML = ""
        document.getElementById("solve").innerHTML = ""

        var endPointQuestionData = '/api/v1/questions/' + sampleValue
        Plotly.d3.json(endPointQuestionData, function(error, response) {

            if (error) return console.warn(error);

            appendInnerHMTL(response)
        });
};

//appends list of questions when topic is chosen from dropdown menu
function appendInnerHMTL(response) {

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
