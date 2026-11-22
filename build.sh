#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

mkdir -p staticfiles
if [ -d backend/staticfiles ]; then
  cp -r backend/staticfiles/. staticfiles/ 2>/dev/null || true
fi
