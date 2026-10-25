"""Load the student/tutor roster into the login database.

  python3 manage_users.py sync          # private/students.txt, tutors.txt, aliases.tsv, homework_map.tsv, contacts.txt
  python3 manage_users.py check "Name"  # who would this login resolve to?
  python3 manage_users.py status        # how many rows are in the target database

Local runs write private/activity.sqlite. To load the live site, point it at
Heroku Postgres:

  DATABASE_URL=$(heroku config:get DATABASE_URL -a act-math) python3 manage_users.py sync

private/aliases.tsv (optional) has one "login<TAB>TutorBird name" per line, for
names that were typed oddly in TutorBird.

private/contacts.txt has one "TutorBird name|email;email" per line: the addresses
TutorBird has for each student. "Request Login Info" only auto-sends to one of these.

Homework: a student sees only the Homework cards linked to them. A card is the
part of a topic after "MM.DD " (e.g. "Jude", "Group Class Mon 7p (Sep)"). Cards
named for a student's full name, or a first name only one student has, link
automatically. Everything else goes in private/homework_map.tsv, one
"card<TAB>TutorBird name" per line (a group class has one line per member).
"""
import collections
import os
import re
import sys

import pandas as pd

import auth


def read_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith('#')]


def homework_cards():
    df = pd.read_csv(os.path.join(auth.BASE, 'data', 'copy_mathv2.csv'),
                     encoding='utf-8', encoding_errors='replace')
    cards = set()
    for t in df['topic'].dropna().unique():
        m = re.match(r'^(?:\d{2}\.\d{2}|Lesson \d+)\s+(.+)$', str(t).strip())
        if m:
            cards.add(m.group(1).strip())
    return sorted(cards)


def link_homework(students, tutors):
    """(name, card) pairs for the homework table, plus cards nobody is linked to."""
    first = collections.Counter(auth.normalize(n.split()[0]) for n in set(students))
    pairs, unresolved = set(), []
    manual = [tuple(ln.split('\t', 1)) for ln in read_lines(os.path.join(auth.PRIVATE, 'homework_map.tsv'))]
    mapped_cards = {c for c, _ in manual}
    known = set(students)
    for card, name in manual:
        if name in known:
            pairs.add((name, card))
        else:
            unresolved.append(f'homework_map.tsv: {name!r} is not a TutorBird student ({card})')
    for card in homework_cards():
        if card in mapped_cards:
            continue
        key = auth.normalize(card)
        hits = [n for n in set(students) if auth.normalize(n) == key]
        if not hits and not card.startswith('Group Class'):
            hits = [n for n in set(students)
                    if auth.normalize(n.split()[0]) == key and first[key] == 1]
        if hits:
            pairs.update((n, card) for n in hits)
        else:
            cands = sorted(n for n in set(students) if auth.normalize(n.split()[0]) == key)
            unresolved.append(f'card {card!r}: no student linked' + (f' (first-name matches: {", ".join(cands)})' if cands else ''))
    return pairs, unresolved


def main(argv):
    if len(argv) >= 2 and argv[1] == 'sync':
        students = read_lines(os.path.join(auth.PRIVATE, 'students.txt'))
        tutors = read_lines(os.path.join(auth.PRIVATE, 'tutors.txt'))
        aliases = [tuple(ln.split('\t', 1)) for ln in read_lines(os.path.join(auth.PRIVATE, 'aliases.tsv'))]
        problems = auth.sync_roster(students, tutors, aliases)
        print(f'{len(set(students))} students, {len(set(tutors))} tutors loaded')
        for p in problems:
            print('  PROBLEM:', p)
        pairs, unresolved = link_homework(students, tutors)
        auth.sync_homework(pairs)
        contact_pairs = []
        for ln in read_lines(os.path.join(auth.PRIVATE, 'contacts.txt')):
            name, _, emails = ln.partition('|')
            contact_pairs += [(name.strip(), e) for e in emails.split(';') if e.strip()]
        known = set(students) | set(tutors)
        for n in sorted({n for n, _ in contact_pairs} - known):
            print('  CONTACT for unknown name:', n)
        auth.sync_contacts([(n, e) for n, e in contact_pairs if n in known])
        print(f'{len(contact_pairs)} email addresses on file for {len({n for n, _ in contact_pairs})} names')
        print(f'{len(pairs)} homework links across {len({c for _, c in pairs})} cards')
        for u in unresolved:
            print('  UNLINKED:', u)
    elif len(argv) >= 2 and argv[1] == 'status':
        from sqlalchemy import func, select
        where = 'Heroku Postgres' if auth.CONFIG.get('DATABASE_URL') else 'local file private/activity.sqlite'
        print('database:', where)
        with auth.engine().connect() as conn:
            for t in (auth.users, auth.contacts, auth.homework_access, auth.events):
                print(f'  {t.name}: {conn.execute(select(func.count()).select_from(t)).scalar()} rows')
    elif len(argv) >= 3 and argv[1] == 'check':
        print(auth.find_user(argv[2]) or 'no such login')
    else:
        print(__doc__)


if __name__ == '__main__':
    main(sys.argv)
