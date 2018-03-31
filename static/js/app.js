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

function getQuestionData() {

        sampleValue = document.getElementById("questionDropdown").value;

        document.getElementById("question").innerHTML = ""
        document.getElementById("questionAnswers").innerHTML = ""

        var endPointQuestionData = '/api/v1/questions/' + sampleValue
        Plotly.d3.json(endPointQuestionData, function(error, response) {

            if (error) return console.warn(error);

            appendInnerHMTL(response)
        });
};

function appendInnerHMTL(response) {

    d3.select("#question")
    .append('p')
    .text(response[0]['Question'])

    d3.select("#questionAnswers")
    .append('li')
    .text(response[0]['Answer_1'])
    .append('li')
    .text(response[0]['Answer_2'])
    .append('li')
    .text(response[0]['Answer_3'])
    .append('li')
    .text(response[0]['Answer_5'])
};
