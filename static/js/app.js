var questionEndPointDate = '/api/v1/question_date'

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

var questionEndPointTopic = '/api/v1/question_list'

Plotly.d3.json(questionEndPointTopic, function(error, response) {
    if (error) return console.warn(error);

    a = d3.select("#checkboxesTopics")
    for (var i = 0; i < response.length; i++){
                a.append('input')
                .attr('type','checkbox')
                .attr('class','topics')
                .attr('value',response[i])
                .attr('id',response[i])
                a.append('label')
                .attr('for',response[i])
                .text("\u00A0"+response[i]+"\u00A0"+"\u00A0")
    }
});

//'Show Answer' turns into the answer right where the button is; click again to hide it.
//The button keeps its width, so the green "Find Similar Questions" button doesn't move.
function showAnswer(button) {

        var showing = !button.classList.contains('answerShown');
        button.textContent = showing ? 'Answer: ' + button.getAttribute('data-answer') : 'Show Answer';
        button.classList.toggle('answerShown', showing);

      };

//queries list of questions
function getQuestionData() {

        //return checkbox values
        var sampleValue = document.querySelectorAll('.topics,.dates');

        //initiate array
        var checkedValues = [];

        //search for checked values and append to new array
        for (var i = 0; i < sampleValue.length; i++) {
          if(sampleValue[i].checked) {
            checkedValues[i] = sampleValue[i].value;
          }
        }

        //initiate arrays to return all values if none are checked
        var date = document.querySelectorAll('.dates:checked');
        var topic = document.querySelectorAll('.topics:checked');

        //append all date values if none checked
        if(date.length == 0) {
          var allDates = document.getElementsByClassName('dates');
          for (var i = 0; i < allDates.length; i++) {
            checkedValues[i+checkedValues.length] = allDates[i].value;
          }
        }
        //append all topic values if none checked
        if(topic.length == 0) {
          var allTopics = document.getElementsByClassName('topics');
          for (var i = 0; i < allTopics.length; i++) {
            checkedValues[i+checkedValues.length] = allTopics[i].value;
          }
        }

        //error message if nothing is checked
        if(date.length == 0 && topic.length == 0) {
          checkedValues = [];
          alert("Choose a topic")
        }

        //clear #question and #solve tags
        document.getElementById("question").innerHTML = ""
        document.getElementById("solve").innerHTML = ""

        var endPointQuestionData = '/api/v1/questions/' + checkedValues
        Plotly.d3.json(endPointQuestionData, function(error, response) {

            if (error) return console.warn(error);

            appendInnerHTML(response)
        });
};

//appends list of questions when topic is chosen from dropdown menu
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

