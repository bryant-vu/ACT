from flask import Flask, render_template, jsonify
from api import question_list, questions, question_date
import pandas as pd
from functools import lru_cache

app = Flask(__name__)
@lru_cache(maxsize=1)
def load_csv():
    df = pd.read_csv('data/copy_mathv2.csv')
    # Normalize all string columns (remove leading/trailing spaces)
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

def question_date_csv():
    df = load_csv()
    return sorted(df['date'].dropna().unique().tolist())

def question_list_csv():
    df = load_csv()
    print(df['topic'].unique().tolist())   # debug line
    return sorted(df['topic'].dropna().unique().tolist())

def questions_csv(filters):
    df = load_csv()
    # Normalize for case and punctuation consistency
    df['topic_norm'] = df['topic'].astype(str).str.strip().str.lower()
    df['date_norm'] = df['date'].astype(str).str.strip().str.lower()
    # Normalize the filters the same way
    filters = [f.strip().lower() for f in filters.split(',') if f.strip()]
    print("Cleaned filters:", filters)    # Flexible partial match instead of exact isin()
    mask = df['topic_norm'].apply(lambda x: any(f in x for f in filters)) | \
           df['date_norm'].apply(lambda x: any(f in x for f in filters))
    result = df[mask]
    # If nothing selected, just return all
    if result.empty:
        result = df
    return result[['id', 'date', 'ans']].to_dict(orient='records')


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/api/v1/about/')
def about():
    return render_template('about.html')

@app.route('/api/v1/question_date/')
def questions_function_dates():
    s = set(question_date())
    dataDict = list(sorted(s))
    return jsonify(dataDict)

@app.route('/api/v1/question_list/')
def questions_function_topics():
    s = set(question_list())
    dataDict = list(sorted(s))
    return jsonify(dataDict)

@app.route('/api/v1/questions/<data>')
def question(data):
    outPutList = questions(data)
    return jsonify(outPutList)

@app.route('/api/v1/calcprograms/')
def calcprograms():
    return render_template('calcprograms.html')

@app.route('/api/v1/contactme/')
def contactme():
    return render_template('contactme.html')

@app.route('/api/v1/homework/')
def homework():
    return render_template('homework.html')

@app.route('/api/v1/homework/question_date/')
def homework_question_dates(): 
    return jsonify(question_date_csv())

@app.route('/api/v1/homework/question_list/')
def homework_question_topics():
    return jsonify(question_list_csv())

@app.route('/api/v1/homework/questions/<filters>')
def homework_questions(filters):
    print("Filters received:", filters)   #  ← add this
    return jsonify(questions_csv(filters))

if __name__ == '__main__':
    app.run(debug=True)
