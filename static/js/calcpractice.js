// No checkboxes on this page - the questions load as soon as the tab opens.
// Rendering (Show Answer buttons, S3 images) comes from questions.js.

var calcPracticeEndPoint = '/api/v1/calcpractice/questions/';

Plotly.d3.json(calcPracticeEndPoint, function(error, response) {
    if (error) return console.warn(error);

    appendInnerHTML(response)
});
