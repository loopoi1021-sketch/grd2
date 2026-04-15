#!/bin/bash
cd ~/grd2
source ~/.bashrc
source .venv/bin/activate

pkill gunicorn 2>/dev/null
sleep 1

gunicorn app:app \
  --bind 0.0.0.0:5000 \
  --daemon \
  --log-level debug \
  --access-logfile ~/gunicorn-access.log \
  --error-logfile ~/gunicorn-error.log

echo "서버 시작 완료"
echo "로그: tail -f ~/gunicorn-error.log"
