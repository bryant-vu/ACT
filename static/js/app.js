var dataDropdown = d3.select('#questionDropdown')
var questionEndPoint = '/api/v1/question_list'
plotly.d3.json(questionEndPoint, function(error, response){
    if error return console.warn(error):

        for (var i = 0; i < response.length; i++){
            console.log(response[i])
            dataDropdown
                .append('option')
                .attr('value', response[i])
                .text(response[i])
        }
})
