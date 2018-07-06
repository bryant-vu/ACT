from flask import Flask, render_template, jsonify
from api import question_list, questions

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/api/v1/about/')
def about():
    return render_template('about.html')

@app.route('/api/v1/question_list/')
def questions_function():
    s = set(question_list())
    dataDict = list(sorted(s))
    return jsonify(dataDict)

@app.route('/api/v1/questions/<topic>')
def question(topic):
    outPutList = questions(topic)
    return jsonify(outPutList)

@app.route('/api/v1/calcprograms/')
def calcprograms():
    return render_template('calcprograms.html')

@app.route('/api/v1/contactme/')
def contactme():
    return render_template('contactme.html')

@app.route('/api/v1/changepoll/')
def changepoll():
    return render_template('changepoll.html')

@app.route('/api/v1/donate/')
def donate():
    return render_template('donate.html')

if __name__ == '__main__':
    app.run(debug=True)
