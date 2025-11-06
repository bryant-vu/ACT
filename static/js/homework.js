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

//display answer when 'Show Answer' button is clicked
function showAnswer(i) {

        document.getElementsByClassName('button')[i].style.display="none";
        document.getElementsByClassName('shownAnswer')[i].style.display='table'

      };

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
  });
}

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

