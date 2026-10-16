#!/bin/bash
# One command to load the student/tutor roster, emails and homework links.
#
#   ./update_roster.sh          load private/*.txt into the LOCAL test database
#   ./update_roster.sh --live   load them into the LIVE Heroku Postgres (act-math)
#
# The files in private/ come from TutorBird. To refresh them from TutorBird,
# ask Claude: "refresh the ACT roster" (skill: act-roster-refresh).
set -euo pipefail
cd "$(dirname "$0")"
PY=.venv/bin/python

if [ "${1:-}" = "--live" ]; then
  echo "Loading the roster into the LIVE database (Heroku Postgres, app act-math)..."
  export DATABASE_URL="$(heroku config:get DATABASE_URL -a act-math 2>/dev/null)"
  if [ -z "$DATABASE_URL" ]; then echo "No DATABASE_URL: is the Heroku Postgres add-on there?"; exit 1; fi
fi
$PY manage_users.py sync
echo
$PY manage_users.py status
