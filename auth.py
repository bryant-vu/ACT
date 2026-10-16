"""Logins for students and tutors, plus the activity log.

The roster (who may log in) and the activity log live in a database:
Heroku Postgres when DATABASE_URL is set, otherwise private/activity.sqlite.
The roster is NOT in this repo (it is public); load it with manage_users.py.
Passwords come from config vars (or private/config.env locally), never from code.
"""
import difflib
import hmac
import os
import re
import time
import unicodedata
from datetime import datetime

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select, text)

BASE = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(BASE, 'private')
CONFIG_KEYS = ('STUDENT_PASSWORD', 'TUTOR_PASSWORD', 'ADMIN_USERS', 'ADMIN_PASSWORD',
               'SECRET_KEY', 'DATABASE_URL', 'NOTIFY_TO', 'MAIL_FROM',
               'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD')


def _load_config():
    cfg = {}
    path = os.path.join(PRIVATE, 'config.env')
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    cfg[k.strip()] = v.strip()
    cfg.update({k: os.environ[k] for k in CONFIG_KEYS if os.environ.get(k)})
    return cfg


CONFIG = _load_config()
ON_HEROKU = bool(os.environ.get('DYNO'))


def secret_key():
    key = CONFIG.get('SECRET_KEY')
    if key:
        return key
    if ON_HEROKU:
        raise RuntimeError('SECRET_KEY config var is not set')
    return 'dev-only-not-secret'


# ---- names -------------------------------------------------------------

def normalize(name):
    """'Elena Stark' / 'elenastark' / 'ELENA STARK' all become 'elenastark'."""
    s = unicodedata.normalize('NFKD', name or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s.lower())


def name_keys(name):
    """Every login key for one TutorBird name. 'Elena (Ellie) Stark' also logs
    in as 'ElenaStark'."""
    keys = {normalize(name), normalize(re.sub(r'\([^)]*\)?', ' ', name))}
    keys.discard('')
    return keys


# ---- database ----------------------------------------------------------

metadata = MetaData()
users = Table('users', metadata,
              Column('key', String(120), primary_key=True),
              Column('name', String(200), nullable=False),
              Column('role', String(10), nullable=False))
homework_access = Table('homework_access', metadata,
                        Column('name', String(200), primary_key=True),
                        Column('card', String(200), primary_key=True))
contacts = Table('contacts', metadata,
                 Column('name', String(200), primary_key=True),
                 Column('email', String(200), primary_key=True))
events = Table('events', metadata,
               Column('id', Integer, primary_key=True, autoincrement=True),
               Column('ts', DateTime, nullable=False, index=True),
               Column('user_key', String(120), index=True),
               Column('name', String(200)),
               Column('role', String(10)),
               Column('event', String(40), nullable=False),
               Column('detail', Text),
               Column('ip', String(64)))

_engine = None


def engine():
    global _engine
    if _engine is None:
        url = CONFIG.get('DATABASE_URL')
        if url:
            if url.startswith('postgres://'):
                url = 'postgresql://' + url[len('postgres://'):]
        else:
            os.makedirs(PRIVATE, exist_ok=True)
            url = 'sqlite:///' + os.path.join(PRIVATE, 'activity.sqlite')
        _engine = create_engine(url, pool_pre_ping=True)
        metadata.create_all(_engine)
    return _engine


def sync_roster(students, tutors, extra_aliases=()):
    """Replace the whole roster. Returns a list of problems (name clashes)."""
    rows, problems = {}, []

    def add(key, name, role):
        if key in rows and rows[key][0] != name:
            problems.append(f'{key!r}: {rows[key][0]} ({rows[key][1]}) vs {name} ({role})')
            if rows[key][1] == 'tutor':
                return
        rows[key] = (name, role)

    for name in students:
        for key in name_keys(name):
            add(key, name, 'student')
    for name in tutors:
        for key in name_keys(name):
            add(key, name, 'tutor')
    for alias, name in extra_aliases:
        role = next((r for k, (n, r) in rows.items() if n == name), None)
        if role:
            add(normalize(alias), name, role)
        else:
            problems.append(f'alias {alias!r} points at unknown name {name!r}')
    with engine().begin() as conn:
        conn.execute(delete(users))
        conn.execute(insert(users), [{'key': k, 'name': n, 'role': r}
                                     for k, (n, r) in rows.items()])
    return problems


def sync_homework(pairs):
    """Replace which Homework cards each student may open: (TutorBird name, card) pairs."""
    rows = [{'name': n, 'card': c} for n, c in sorted(set(pairs))]
    with engine().begin() as conn:
        conn.execute(delete(homework_access))
        if rows:
            conn.execute(insert(homework_access), rows)


def cards_for(name):
    """The Homework cards (names after 'MM.DD ') this student may open."""
    with engine().connect() as conn:
        return {r.card for r in conn.execute(
            select(homework_access.c.card).where(homework_access.c.name == name))}


def sync_contacts(pairs):
    """Replace the email addresses TutorBird has on file: (TutorBird name, email) pairs."""
    rows = [{'name': n, 'email': e.strip().lower()} for n, e in sorted(set(pairs)) if e.strip()]
    with engine().begin() as conn:
        conn.execute(delete(contacts))
        if rows:
            conn.execute(insert(contacts), rows)


def emails_for(name):
    with engine().connect() as conn:
        return {r.email for r in conn.execute(
            select(contacts.c.email).where(contacts.c.name == name))}


_user_rows = {'at': 0, 'rows': []}


def closest_user(text):
    """The roster entry closest to what someone typed, with how sure we are.

    Returns {'name', 'key', 'role', 'score', 'confident'} or None. 'confident'
    needs a near-exact match that clearly beats the next different person."""
    key = normalize(text)
    if len(key) < 4:
        return None
    if time.time() - _user_rows['at'] > 300:
        with engine().connect() as conn:
            _user_rows['rows'] = [(r.key, r.name, r.role) for r in conn.execute(select(users))]
        _user_rows['at'] = time.time()
    best = {}
    for k, name, role in _user_rows['rows']:
        if k == key:
            score = 1.0
        else:
            m = difflib.SequenceMatcher(None, key, k)
            score = m.ratio() if m.quick_ratio() >= 0.7 else 0.0
        if name not in best or score > best[name][0]:
            best[name] = (score, k, role)
    ranked = sorted(((sc, n, k, r) for n, (sc, k, r) in best.items()), reverse=True)
    if not ranked or ranked[0][0] < 0.6:
        return None
    score, name, k, role = ranked[0]
    second = ranked[1][0] if len(ranked) > 1 else 0.0
    return {'name': name, 'key': k, 'role': role, 'score': round(score, 3),
            'confident': score == 1.0 or (score >= 0.88 and score - second >= 0.03)}


def login_id(name):
    """What to tell someone to type as their login: the name with no spaces."""
    base = re.sub(r'\([^)]*\)?', ' ', name) if '(' in name else name
    return re.sub(r'\s+', '', base).strip() or re.sub(r'\s+', '', name)


_requests = {}   # rate limits for "Request Login Info": key -> [timestamps]


def students_for_email(email):
    """Students (TutorBird names) this exact address is on file for."""
    with engine().connect() as conn:
        names = [r.name for r in conn.execute(
            select(contacts.c.name).where(contacts.c.email == email.strip().lower()))]
    out = []
    for n in sorted(set(names)):
        u = find_user(n)
        if u and u['role'] == 'student':
            out.append(u['name'])
    return out


def too_many_requests(ip, email, target=None):
    now = time.time()

    def over(key, limit, window):
        recent = [t for t in _requests.get(key, []) if now - t < window]
        _requests[key] = recent
        return len(recent) >= limit

    # per address too, so nobody can use the form to pile emails onto one family
    keys = ['ip:' + ip, 'all'] + (['email:' + email] if email else []) + (['target:' + target] if target else [])
    limits = {'ip:' + ip: (5, 3600), 'all': (150, 86400)}
    if any(over(k, *limits.get(k, (3, 86400))) for k in keys):
        return True
    for k in keys:
        _requests[k].append(now)
    return False


def find_user(name):
    key = normalize(name)
    if not key:
        return None
    with engine().connect() as conn:
        row = conn.execute(select(users).where(users.c.key == key)).first()
    return {'key': row.key, 'name': row.name, 'role': row.role} if row else None


# ---- login -------------------------------------------------------------

_DUMMY = 'x' * 16


def _same(a, b):
    return hmac.compare_digest(a.encode('utf-8'), b.encode('utf-8'))


def check_login(name, password):
    """The user dict if name + password are right, else None."""
    user = find_user(name)
    expected = None
    if user:
        expected = CONFIG.get('TUTOR_PASSWORD' if user['role'] == 'tutor' else 'STUDENT_PASSWORD')
    ok = _same(password or '', expected or _DUMMY)
    return user if (user and expected and ok) else None


_failures = {}
MAX_FAILURES, WINDOW = 8, 600


def too_many_attempts(ip):
    recent = [t for t in _failures.get(ip, []) if time.time() - t < WINDOW]
    _failures[ip] = recent
    return len(recent) >= MAX_FAILURES


def record_failure(ip):
    _failures.setdefault(ip, []).append(time.time())


def is_admin(user):
    admins = {normalize(n) for n in CONFIG.get('ADMIN_USERS', 'bryantvu').split(',')}
    return bool(user) and user['key'] in admins


def check_admin_password(password):
    expected = CONFIG.get('ADMIN_PASSWORD')
    if not expected:
        return not ON_HEROKU   # no admin password set: open locally, closed on Heroku
    return _same(password or '', expected)


# ---- activity log ------------------------------------------------------

def record(event, detail='', user=None, ip=None):
    """Never raises: a logging problem must not break a page."""
    try:
        with engine().begin() as conn:
            conn.execute(insert(events).values(
                ts=datetime.utcnow(), event=event, detail=(detail or '')[:300], ip=ip,
                user_key=user['key'] if user else None,
                name=user['name'] if user else None,
                role=user['role'] if user else None))
    except Exception as e:   # noqa: BLE001
        print('activity log failed:', e)


def summary():
    q = text("""
        SELECT name, role, MAX(ts) AS last_seen,
               SUM(CASE WHEN event = 'login' THEN 1 ELSE 0 END) AS logins,
               SUM(CASE WHEN event = 'homework_questions' THEN 1 ELSE 0 END) AS homework,
               SUM(CASE WHEN event = 'finder_open' THEN 1 ELSE 0 END) AS finder_opens,
               SUM(CASE WHEN event = 'show_answer' THEN 1 ELSE 0 END) AS answers,
               SUM(CASE WHEN event = 'finder_search' THEN 1 ELSE 0 END) AS searches,
               COUNT(DISTINCT ip) AS ips
        FROM events WHERE name IS NOT NULL
        GROUP BY name, role ORDER BY last_seen DESC""")
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def recent(limit=300, name=None):
    q = select(events).order_by(events.c.id.desc()).limit(limit)
    if name:
        q = q.where(events.c.name == name)
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]
