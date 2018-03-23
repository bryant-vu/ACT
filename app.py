from flask import Flask, render_template, jsonify
from api import questions

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/api/v1/questions')
def question():
    outPutList = questions()
    return jsonify(outPutList)


if __name__ == '__main__':
    app.run(debug=True)
