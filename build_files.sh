#!/bin/bash
echo "BUILD START"
python3 -m pip install -r requirements.txt
python3 backend/manage.py collectstatic --noinput --clear
echo "BUILD END"
