from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:\\Users\\Bryant\\Documents\\GitHub\\ACT\\DataPrep\\ACTdb.db'
db = SQLAlchemy(app)


class math(db.Model):
    id = db.Column(db.String, primary_key=True)
    topic = db.Column(db.String)
    date = db.Column(db.String)
    qNumber = db.Column(db.Integer)
    qStatement = db.Column(db.String)
    a1 = db.Column(db.String)
    a2 = db.Column(db.String)
    a3 = db.Column(db.String)
    a4 = db.Column(db.String)
    a5 = db.Column(db.String)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/database')
def listAllQuestions():
    questions = math.query.all()
    return render_template('database.html', questions=questions)

# returns article string


@app.route('/article/<string:id>/')
def article(id):
    return render_template('article.html', id=id)


if __name__ == '__main__':
    app.run(debug=True)
