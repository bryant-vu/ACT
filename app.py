from flask import Flask, render_template, jsonify, redirect, request, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import urlparse
from api import question_list, questions, question_date
import auth
import mailer
import pandas as pd
from functools import lru_cache
from datetime import date, datetime, timedelta
from pytz import timezone, utc as pytz_utc
import re
import json

app = Flask(__name__)
# Heroku's router adds the real client IP / scheme as the last forwarded value
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
app.config.update(
    SECRET_KEY=auth.secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=auth.ON_HEROKU,
    PERMANENT_SESSION_LIFETIME=timedelta(days=180),   # sliding: each visit renews it
)

# Pages that need a login (the tabs are visible to everyone; clicking one
# sends a logged-out visitor to /login). Home, About and Contact stay public.
PAGES = {
    '/api/v1/homework/': 'Homework',
    '/api/v1/calcpractice/': 'Practice using the Calculator',
    '/api/v1/calcprograms/': 'Calculator Programs',
    '/api/v1/drill/': 'Similar Questions Finder',
    '/api/v1/lessons/': 'Lessons',
}
# path prefix -> who may use it. 'any' = logged-in student or tutor.
ACCESS_RULES = [
    ('/admin', 'any'),            # the route itself checks for the admin user
    ('/api/v1/lessons/', 'tutor'),
    ('/api/v1/homework/', 'any'),
    ('/api/v1/calcpractice/', 'any'),
    ('/api/v1/calcprograms/', 'any'),
    ('/api/v1/drill/', 'any'),
    ('/static/drill/', 'any'),    # question images for tests that aren't on S3
    ('/static/lesson/', 'any'),
]
# what gets written to the activity log (everything else isn't logged)
LOGGED_PREFIXES = [
    ('/api/v1/homework/questions/', 'homework_questions'),
    ('/api/v1/calcpractice/questions/', 'calc_questions'),
    ('/api/v1/drill/question/', 'finder_open'),
    ('/api/v1/drill/answer/', 'show_answer'),
    ('/api/v1/drill/search/', 'finder_search'),
]
PACIFIC = timezone('America/Los_Angeles')

# Lives in the same CSV as the homework assignments, but is served by its own
# page (Practice with Calculator Programs) instead of a Homework checkbox.
CALC_PRACTICE_TOPIC = 'PRACTICE USING CALCULATOR HW'

# "MM.DD Group Class ..." homeworks (e.g. "10.12 Group Class Mon 7p (Sep)") drop off the Homework tab after this long.
# Their rows stay in the CSV.
GROUP_CLASS_MAX_AGE = timedelta(days=183)


@lru_cache(maxsize=1)
def load_csv():
    # encoding_errors='replace' keeps a single bad byte from 500-ing the whole tab
    df = pd.read_csv('data/copy_mathv2.csv', encoding='utf-8', encoding_errors='replace')
    # Normalize all string columns (remove leading/trailing spaces)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return df

def question_date_csv():
    df = load_csv()
    return sorted(df['date'].dropna().unique().tolist())

def is_stale_group_class(topic, today=None):
    # Topic names carry no year, so take the most recent MM.DD on or before today
    m = re.fullmatch(r'(\d{2})\.(\d{2}) Group Class\b.*', topic)
    if not m:
        return False
    today = today or date.today()
    month, day = int(m.group(1)), int(m.group(2))
    try:
        held = date(today.year, month, day)
        if held > today:
            held = date(today.year - 1, month, day)
    except ValueError:
        return False
    return today - held > GROUP_CLASS_MAX_AGE

def question_list_csv():
    df = load_csv()
    topics = df['topic'].dropna().unique().tolist()
    return sorted(t for t in topics
                  if t != CALC_PRACTICE_TOPIC and not is_stale_group_class(t))

def calc_practice_questions():
    df = load_csv()
    rows = df[df['topic'] == CALC_PRACTICE_TOPIC]
    return rows[['id', 'date', 'ans']].to_dict(orient='records')

def card_name(topic):
    # "10.12 Jude" -> "Jude"; "10.12 Group Class Mon 7p (Sep)" -> "Group Class Mon 7p (Sep)"
    m = re.match(r'^\d{2}\.\d{2}\s+(.+)$', topic)
    return m.group(1).strip() if m else topic

def visible_topics(user):
    """The homework topics this user may open, or None for no limit (tutors)."""
    if user['role'] == 'tutor':
        return None
    cards = auth.cards_for(user['name'])
    return [t for t in question_list_csv() if card_name(t) in cards]

def questions_csv(filters, only_topics=None):
    df = load_csv()
    if only_topics is not None:
        # a student: exactly the topics they asked for that are theirs, never "everything"
        asked = {f.strip().lower() for f in filters.split(',') if f.strip()}
        mine = {t for t in only_topics if t.strip().lower() in asked}
        result = df[df['topic'].isin(mine)]
    else:
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
    rows = result[['id', 'date', 'ans']].to_dict(orient='records')
    for r in rows:
        # the "Find Similar Questions" button replaces the topic hint in the answer
        if isinstance(r['ans'], str):
            r['ans'] = re.sub(r'\s*\(Topic:.*$', '', r['ans']).strip()
    return rows


@lru_cache(maxsize=1)
def load_drill():
    # Student version of the question matcher (no recent tests),
    # exported by question_bank/tools/build_site.py
    with open('data/drill.json', encoding='utf-8') as f:
        d = json.load(f)
    d['labels'] = {t['name']: t['label'] for t in d['tests']}
    return d

def with_finder_links(rows):
    # questions the Similar Questions Finder knows get a "Find Similar Questions" button.
    # Tests that aren't on S3 send their image path too (served from static/drill/)
    meta = load_drill()['meta']
    for r in rows:
        r['similar'] = r['id'] in meta
        if r['similar'] and meta[r['id']]['img'].startswith('/static/'):
            r['img'] = meta[r['id']]['img']
    return rows

def drill_card(qid):
    d = load_drill()
    m = d['meta'][qid]
    return {'id': qid, 'label': f"{d['labels'][m['t']]} \u00b7 #{m['n']}",
            'skill': m['s'], 'multi': m['m'], 'img': m['img']}


def current_user():
    if 'u' not in session:
        return None
    return {'key': session['u'], 'name': session['n'], 'role': session['r']}

def client_ip():
    return request.remote_addr or ''

def safe_next(target):
    # only same-site paths, so /login can't be used to bounce someone elsewhere
    target = (target or '').strip()
    p = urlparse(target)
    if not target.startswith('/') or target.startswith('//') or '\\' in target or p.scheme or p.netloc:
        return '/'
    return target

def forbidden():
    if request.path in PAGES or request.path.startswith('/admin'):
        return render_template('forbidden.html'), 403
    return jsonify({'error': 'not allowed'}), 403

@app.context_processor
def inject_user():
    user = current_user()
    return {'current_user': user, 'is_tutor': bool(user and user['role'] == 'tutor')}

@app.before_request
def use_main_domain():
    # one address for everyone, so the login cookie is always on the same domain
    if request.host == 'act-math.herokuapp.com':
        return redirect('https://act.bvuedu.com' + request.full_path.rstrip('?'), code=301)
    return None

@app.before_request
def require_login():
    path = request.path
    needs = next((r for prefix, r in ACCESS_RULES if path.startswith(prefix)), None)
    if needs is None:
        return None
    user = current_user()
    if user is None:
        if path in PAGES or path.startswith('/admin'):
            return redirect(url_for('login', next=path))
        return jsonify({'error': 'login required'}), 401
    if needs == 'tutor' and user['role'] != 'tutor':
        return forbidden()
    if path in PAGES:
        auth.record('page', PAGES[path], user, client_ip())
    else:
        for prefix, event in LOGGED_PREFIXES:
            if path.startswith(prefix):
                auth.record(event, path[len(prefix):], user, client_ip())
                break
    return None

@app.after_request
def no_store_private(resp):
    # keep logged-in pages and data out of shared caches
    if any(request.path.startswith(p) for p, _ in ACCESS_RULES) or request.path == '/login':
        resp.headers['Cache-Control'] = 'private, no-store'
    return resp

@app.route('/login', methods=['GET', 'POST'])
def login():
    nxt = safe_next(request.values.get('next'))
    error = None
    if request.method == 'POST':
        ip = client_ip()
        if auth.too_many_attempts(ip):
            error = 'Too many tries. Wait a few minutes and try again.'
        else:
            name = request.form.get('name', '')
            user = auth.check_login(name, request.form.get('password', ''))
            if user:
                session.clear()
                session.update(u=user['key'], n=user['name'], r=user['role'])
                session.permanent = True
                auth.record('login', '', user, ip)
                return redirect(nxt)
            auth.record_failure(ip)
            auth.record('login_failed', auth.normalize(name)[:60], None, ip)
            error = "That name and password don't match. Type your full name with no spaces."
    return render_template('login.html', next=nxt, error=error,
                           requested=request.args.get('requested')), (429 if error and error.startswith('Too') else 200)

@app.route('/request-login', methods=['POST'])
def request_login():
    """Someone clicked "Request Login Info" and typed their full name or email.

    - An exact EMAIL match (an address TutorBird has on file for a student): the
      login info goes to that address, for every student it is on file for.
    - An exact NAME match: the login info goes to the address(es) TutorBird has
      on file for that student, never to the typed address, so typing a
      classmate's name can't get the password sent to an outsider.
    - Anything else (near-miss name, unknown email, tutors, no address on file):
      forwarded to the owner, with the typed email as Reply-To.
    The page answers the same way in every case, so it doesn't reveal who is on
    the roster or which addresses are on file.
    """
    ip = client_ip()
    name = re.sub(r'\s+', ' ', request.form.get('name', '')).strip()[:80]
    email = request.form.get('email', '').strip().lower()[:120]

    def again(msg, status=400):
        return render_template('login.html', next='/', error=msg, show_request=True,
                               req_name=name, req_email=email), status

    if not name and not email:
        return again('Please type your full name or your email.')
    if email and not re.fullmatch(r"[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+", email):
        return again("That doesn't look like an email address.")

    by_email = auth.students_for_email(email) if email else []
    exact = auth.find_user(name) if name else None
    send_to, logins, reason = [], [], None
    if by_email:
        # the typed address is on file; if they also gave a name that is one of those students, use only that one
        who = [exact['name']] if exact and exact['name'] in by_email else by_email
        send_to, logins = [email], [(n, auth.login_id(n)) for n in who]
    elif exact and exact['role'] == 'student':
        send_to = sorted(auth.emails_for(exact['name']))
        logins = [(exact['name'], auth.login_id(exact['name']))]
        if not send_to:
            reason = 'that student has no email on file in TutorBird'
    elif exact:
        reason = 'the name is a tutor account'
    else:
        reason = 'no exact match on name or email'

    target = (logins[0][0] if len(logins) == 1 else email) if logins else None
    if auth.too_many_requests(ip, email, target):
        return again('Too many requests. Please wait a while and try again.', 429)

    outcome, match = 'forwarded', exact and {'name': exact['name'], 'role': exact['role'], 'score': 1.0}
    if reason is None:
        password = auth.CONFIG.get('STUDENT_PASSWORD', '')
        if password and all([mailer.send_login_info(a, logins, password) for a in send_to]):
            outcome = 'sent'
        else:
            reason = 'the email could not be sent'
    if outcome != 'sent':
        if not email:
            # nothing to reply to: ask for an email instead of sending Bryant an unanswerable note
            return again("We couldn't find that name. Please also type your email so Bryant can reply.")
        if match is None and name:
            m = auth.closest_user(name)
            match = m
        mailer.notify_owner(name, email, match, reason)
    auth.record('request_login', f"{name[:60] or '-'} / {email[:60] or '-'}: {outcome}", None, ip)
    return redirect('/login?requested=1')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def pacific(dt):
    if isinstance(dt, str):
        dt = datetime.strptime(dt[:19], '%Y-%m-%d %H:%M:%S')
    return pytz_utc.localize(dt).astimezone(PACIFIC).strftime('%m/%d %I:%M %p') if dt else ''

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    user = current_user()
    if not auth.is_admin(user):
        return forbidden()
    if request.method == 'POST' and auth.check_admin_password(request.form.get('password', '')):
        session['admin'] = True
    if not session.get('admin'):
        return render_template('admin.html', locked=True)
    who = request.args.get('user') or None
    events = auth.recent(300, who)
    for e in events:
        e['when'] = pacific(e['ts'])
    summary = auth.summary()
    for s in summary:
        s['last_seen'] = pacific(s['last_seen'])
    return render_template('admin.html', locked=False, summary=summary, events=events, who=who)


@app.route('/')
def index():
    return render_template('home.html')

@app.route('/api/v1/about/')
def about():
    # the About tab now points to the About page on bvuedu.com; keep old links working
    return redirect('https://www.bvuedu.com/st_about')

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
    return jsonify(with_finder_links(outPutList))

@app.route('/api/v1/calcprograms/')
def calcprograms():
    return render_template('calcprograms.html')

@app.route('/api/v1/contactme/')
def contactme():
    return render_template('contactme.html')

@app.route('/api/v1/calcpractice/')
def calcpractice():
    return render_template('calcpractice.html')

@app.route('/api/v1/calcpractice/questions/')
def calcpractice_questions():
    return jsonify(with_finder_links(calc_practice_questions()))

@app.route('/api/v1/homework/')
def homework():
    return render_template('homework.html')

@app.route('/api/v1/homework/question_date/')
def homework_question_dates():
    # the date filter would reach other students' questions, so students don't get it
    if visible_topics(current_user()) is not None:
        return jsonify([])
    return jsonify(question_date_csv())

@app.route('/api/v1/homework/question_list/')
def homework_question_topics():
    mine = visible_topics(current_user())
    return jsonify(question_list_csv() if mine is None else mine)

@lru_cache(maxsize=1)
def load_class_questions():
    # homework question -> the question worked on in class,
    # exported by question_bank/lesson_plan/build.py
    with open('data/class_questions.json', encoding='utf-8') as f:
        return json.load(f)

@lru_cache(maxsize=1)
def load_custom_questions():
    # homework questions from tests not on the site (custom lesson images in static/lesson/),
    # exported by question_bank/lesson_plan/build.py
    with open('data/custom_questions.json', encoding='utf-8') as f:
        return json.load(f)

def with_custom_images(rows):
    custom = load_custom_questions()
    for r in rows:
        if r['id'] in custom:
            r['img'] = custom[r['id']]
    return rows

def with_class_links(rows):
    # homework questions practicing a class question get a "Similar Question from Class" button:
    # the Finder page for that question, or a custom lesson image in static/lesson/
    pairs, meta = load_class_questions(), load_drill()['meta']
    for r in rows:
        cls = pairs.get(r['id'])
        if cls and cls.startswith('img:'):
            r['classLink'] = '/static/lesson/' + cls[4:]
        elif cls and cls != r['id'] and cls in meta:
            r['classLink'] = '/api/v1/drill/#' + cls
    return rows

@app.route('/api/v1/homework/questions/<filters>')
def homework_questions(filters):
    print("Filters received:", filters)   #  ← add this
    rows = questions_csv(filters, only_topics=visible_topics(current_user()))
    return jsonify(with_class_links(with_custom_images(with_finder_links(rows))))

@lru_cache(maxsize=1)
def load_lessons():
    # lesson questions in teaching order, exported by question_bank/lesson_plan/build.py
    with open('data/lessons.json', encoding='utf-8') as f:
        return json.load(f)

@app.route('/api/v1/lessons/')
def lessons():
    return render_template('lessons.html')

@app.route('/api/v1/lessons/data/')
def lessons_data():
    meta = load_drill()['meta']
    out = json.loads(json.dumps(load_lessons()))
    for les in out:
        for t in les['topics']:
            for q in t['questions']:
                qid = q.get('qid')
                q['similar'] = qid in meta
                if qid in meta and 'img' not in q:
                    q['img'] = meta[qid]['img']
    return jsonify(out)

@app.route('/api/v1/drill/')
def drill():
    return render_template('drill.html')

@app.route('/api/v1/drill/tests/')
def drill_tests():
    d = load_drill()
    return jsonify([{'name': t['name'], 'label': t['label'],
                     'questions': [[i, d['meta'][i]['n']] for i in t['ids']]}
                    for t in d['tests']])

@app.route('/api/v1/drill/question/<qid>')
def drill_question(qid):
    d = load_drill()
    if qid not in d['meta']:
        return jsonify({'error': 'Question not found'}), 404
    return jsonify({'target': drill_card(qid),
                    'groups': {k: [drill_card(i) for i in ids]
                               for k, ids in d['matches'][qid].items()}})

@app.route('/api/v1/drill/answer/<qid>')
def drill_answer(qid):
    # answers are sent one at a time, only when a student clicks "Show Answer"
    d = load_drill()
    if qid not in d['answers']:
        return jsonify({'error': 'Question not found'}), 404
    return jsonify({'answer': d['answers'][qid]})

@app.route('/api/v1/drill/search/<query>')
def drill_search(query):
    d = load_drill()
    words = query.lower().split()
    hits = [i for i, text in d['search'].items() if words and all(w in text for w in words)]
    hits.sort(key=lambda i: (d['meta'][i]['n'], i))  # lower numbers are usually easier
    return jsonify({'total': len(hits), 'results': [drill_card(i) for i in hits[:60]]})

if __name__ == '__main__':
    app.run(debug=True)
