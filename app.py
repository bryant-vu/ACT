from flask import Flask, render_template, jsonify
from api import question_list, questions

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/api/v1/question_list')
def questions_function():
    dataDict = list(set(question_list()))
    return jsonify(dataDict)


@app.route('/api/v1/questions/<id>')
def question(id):
    outPutList = questions(id)
    return jsonify(outPutList)


if __name__ == '__main__':
    app.run(debug=True)
