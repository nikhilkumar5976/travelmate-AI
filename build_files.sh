#!/usr/bin/env bash
set -o errexit

echo "BUILD START"
python3 -m pip install -r requirements.txt

if [ -f manage.py ]; then
  python3 manage.py collectstatic --noinput --clear
else
  python3 backend/manage.py collectstatic --noinput --clear
fi

# Ensure root output directory 'staticfiles' exists and is populated for Vercel
mkdir -p staticfiles
if [ -d backend/staticfiles ]; then
  cp -r backend/staticfiles/. staticfiles/ 2>/dev/null || true
fi

echo "BUILD END"
