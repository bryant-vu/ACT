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
        document.getElementById("solve").innerHTML = ""

        var endPointQuestionData = '/api/v1/questions/' + sampleValue
        Plotly.d3.json(endPointQuestionData, function(error, response) {

            if (error) return console.warn(error);

            appendInnerHMTL(response)
        });
};

function appendInnerHMTL(response) {

  d3.select("#solve")
      .append('h2')
      .text("Solve.")

    for (var i = 0; i < response.length; i++){

        d3.select("#question")
              .append('p')
              .text(response[i]['id'])
              .append('p')
              .text(response[i]['statement'])
              .append('li')
              .text(response[i]['a1'])
              .append('li')
              .text(response[i]['a2'])
              .append('li')
              .text(response[i]['a3'])
              .append('li')
              .text(response[i]['a4'])
              .append('li')
              .text(response[i]['a5'])
              .append('div')
              .append('img')
              .attr('src','images/testimage.png')


    }
};
