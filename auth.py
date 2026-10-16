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
from datetime import datetime, timedelta

from pytz import timezone as pytz_timezone, utc as pytz_utc

from sqlalchemy import (Column, DateTime, Integer, MetaData, String, Table, Text,
                        create_engine, delete, insert, select, text)

BASE = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.path.join(BASE, 'private')
CONFIG_KEYS = ('STUDENT_PASSWORD', 'TUTOR_PASSWORD', 'ADMIN_USERS', 'ADMIN_PASSWORD',
               'SECRET_KEY', 'DATABASE_URL', 'NOTIFY_TO', 'MAIL_FROM',
               'SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD', 'ANALYTICS_SINCE')


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
               SUM(CASE WHEN event = 'click' THEN 1 ELSE 0 END) AS clicks,
               COUNT(DISTINCT ip) AS ips
        FROM events WHERE name IS NOT NULL
        GROUP BY name, role ORDER BY last_seen DESC""")
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def recent(limit=300, name=None):
    q = select(events).where(events.c.event != 'time').order_by(events.c.id.desc()).limit(limit)
    if name:
        q = q.where(events.c.name == name)
    with engine().connect() as conn:
        return [dict(r._mapping) for r in conn.execute(q)]


def fmt_secs(secs):
    secs = int(secs or 0)
    if secs < 60:
        return '%ds' % secs if secs else '-'
    h, m = divmod(secs // 60, 60)
    return '%dh %02dm' % (h, m) if h else '%dm' % m


def _since():
    since = CONFIG.get('ANALYTICS_SINCE')
    return datetime.fromisoformat(since) if since else None


def _parse_time(detail):
    page, _, secs = (detail or '').rpartition('|')
    try:
        return page, int(secs)
    except ValueError:
        return page, 0


def time_totals():
    """{name: seconds on the site} from the time beacons."""
    out = {}
    with engine().connect() as conn:
        for r in conn.execute(select(events.c.name, events.c.detail).where(events.c.event == 'time')):
            out[r.name] = out.get(r.name, 0) + _parse_time(r.detail)[1]
    return out


def user_detail(name):
    """Time by page and most-clicked things for one person."""
    time_by_page, clicks = {}, {}
    with engine().connect() as conn:
        rows = conn.execute(select(events.c.event, events.c.detail)
                            .where(events.c.name == name, events.c.event.in_(('time', 'click'))))
        for r in rows:
            if r.event == 'time':
                page, secs = _parse_time(r.detail)
                time_by_page[page] = time_by_page.get(page, 0) + secs
            else:
                clicks[r.detail] = clicks.get(r.detail, 0) + 1
    return {'time': [(p, fmt_secs(s)) for p, s in sorted(time_by_page.items(), key=lambda kv: -kv[1])],
            'clicks': sorted(clicks.items(), key=lambda kv: -kv[1])[:25],
            'total': fmt_secs(sum(time_by_page.values()))}


def dashboard(now=None):
    """Numbers for the top of /admin. Students only (tutors and test traffic don't count).

    ANALYTICS_SINCE (UTC, e.g. 2026-10-16T03:00) drops everything earlier, so smoke tests
    before real use don't show up as student activity.
    """
    now = now or datetime.utcnow()
    since = CONFIG.get('ANALYTICS_SINCE')
    since = datetime.fromisoformat(since) if since else None
    with engine().connect() as conn:
        roster = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'student'")).scalar()
        access = {}
        for r in conn.execute(select(homework_access)):
            access.setdefault(r.name, []).append(r.card)
        q = select(events).where(events.c.role == 'student').order_by(events.c.ts)
        if since:
            q = q.where(events.c.ts >= since)
        evs = [dict(r._mapping) for r in conn.execute(q)]

    week = now - timedelta(days=7)
    last_seen, first_seen = {}, {}
    for e in evs:
        last_seen[e['name']] = e['ts']
        first_seen.setdefault(e['name'], e['ts'])
    recent = [e for e in evs if e['ts'] >= week]

    cohort = sorted(access)                       # students who have homework assigned
    opened_hw = {e['name'] for e in evs if e['event'] == 'homework_questions'}
    used_finder = {e['name'] for e in evs if e['event'].startswith('finder') or e['event'] == 'show_answer'}
    funnel = [('On the roster', roster),
              ('Have homework assigned', len(cohort)),
              ('Logged in', len([n for n in cohort if n in last_seen])),
              ('Opened their homework', len([n for n in cohort if n in opened_hw])),
              ('Tried the Finder', len([n for n in cohort if n in used_finder]))]

    attention = []                                # assigned homework, not seen in 7 days
    for n in cohort:
        ls = last_seen.get(n)
        if ls is None or ls < week:
            attention.append({'name': n, 'cards': ', '.join(access[n]), 'last_seen': ls,
                              'days': None if ls is None else (now - ls).days})
    attention.sort(key=lambda a: (a['last_seen'] is not None, a['last_seen'] or now))

    cards = []                                    # per homework card: who could vs did open it
    by_card = {}
    for n, cs in access.items():
        for c in cs:
            by_card.setdefault(c, set()).add(n)
    hw_events = [e for e in evs if e['event'] == 'homework_questions']
    for c, members in sorted(by_card.items()):
        openers = {e['name'] for e in hw_events if e['detail'] == c and e['name'] in members}
        cards.append({'card': c, 'assigned': len(members), 'opened': len(openers),
                      'views': len([e for e in hw_events if e['detail'] == c])})
    cards.sort(key=lambda c: (c['opened'] / c['assigned'], -c['assigned']))

    days = []                                     # active students per day, last 14 days (Pacific)
    pacific = pytz_timezone('America/Los_Angeles')
    def day(ts):
        return pytz_utc.localize(ts).astimezone(pacific).date()
    today = day(now)
    per_day = {}
    for e in evs:
        per_day.setdefault(day(e['ts']), set()).add(e['name'])
    for i in range(13, -1, -1):
        d = today - timedelta(days=i)
        days.append({'label': d.strftime('%m/%d'), 'n': len(per_day.get(d, ()))})

    def count(items):
        out = {}
        for x in items:
            out[x] = out.get(x, 0) + 1
        return sorted(out.items(), key=lambda kv: -kv[1])

    secs_by, time_by_tab, click_counts, click_people = {}, {}, {}, {}
    for e in recent:
        if e['event'] == 'time':
            page, secs = _parse_time(e['detail'])
            secs_by[e['name']] = secs_by.get(e['name'], 0) + secs
            time_by_tab[page] = time_by_tab.get(page, 0) + secs
        elif e['event'] == 'click':
            click_counts[e['detail']] = click_counts.get(e['detail'], 0) + 1
            click_people.setdefault(e['detail'], set()).add(e['name'])
    active = {}
    for e in recent:
        a = active.setdefault(e['name'], {'name': e['name'], 'last': e['ts'], 'hw': 0, 'finder': 0, 'clicks': 0})
        a['last'] = max(a['last'], e['ts'])
        a['hw'] += e['event'] == 'homework_questions'
        a['finder'] += e['event'] in ('finder_open', 'show_answer', 'finder_search')
        a['clicks'] += e['event'] == 'click'
    for a in active.values():
        a['secs'] = secs_by.get(a['name'], 0)
        a['time'] = fmt_secs(a['secs'])
        a['online'] = (now - a['last']) < timedelta(minutes=5)
    active = sorted(active.values(), key=lambda a: a['last'], reverse=True)
    total_secs = sum(secs_by.values())

    r = lambda ev: len([e for e in recent if e['event'] == ev])
    return {
        'since': since, 'roster': roster, 'cohort': len(cohort), 'funnel': funnel,
        'active7': len({e['name'] for e in recent}),
        'logins7': r('login'), 'homework7': r('homework_questions'),
        'finder7': r('finder_open'), 'answers7': r('show_answer'), 'searches7': r('finder_search'),
        'attention': attention, 'cards': cards, 'days': days,
        'max_day': max([d['n'] for d in days] + [1]),
        'tabs': count(e['detail'] for e in recent if e['event'] == 'page'),
        'active': active, 'online_now': len([a for a in active if a['online']]),
        'total_time': fmt_secs(total_secs),
        'avg_time': fmt_secs(total_secs // len(secs_by)) if secs_by else '-',
        'clicks7': len([e for e in recent if e['event'] == 'click']),
        'time_by_tab': [(t, fmt_secs(v)) for t, v in sorted(time_by_tab.items(), key=lambda kv: -kv[1])],
        'top_clicks': [(c, n, len(click_people[c])) for c, n in sorted(click_counts.items(), key=lambda kv: -kv[1])[:15]],
        'total_events': len(evs),
    }
