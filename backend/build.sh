#!/usr/bin/env bash
set -o errexit

if [ -f requirements.txt ]; then
  pip install -r requirements.txt
elif [ -f ../requirements.txt ]; then
  pip install -r ../requirements.txt
fi

python manage.py collectstatic --no-input
python manage.py migrate

mkdir -p staticfiles
if [ -d backend/staticfiles ]; then
  cp -r backend/staticfiles/. staticfiles/ 2>/dev/null || true
fi
