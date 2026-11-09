#!/usr/bin/env bash
# Starts Django + toyxona + user panels for the local network (LAN demo).
# Usage: bash start-lan.sh        Stop: Ctrl+C
ROOT="$(cd "$(dirname "$0")" && pwd)"

# 8000 = Super Admin panel + API, 8001 = Admin panel + API (Django picks the panel by host)
(cd "$ROOT/backend" && venv/Scripts/python manage.py runserver 0.0.0.0:8000 --insecure) &
(cd "$ROOT/backend" && PANEL_HOST_SITES="192.168.1.12=admin,localhost=admin,127.0.0.1=admin" \
  venv/Scripts/python manage.py runserver 0.0.0.0:8001 --insecure --noreload) &
(cd "$ROOT/frontend-toyxona" && npx next start -H 0.0.0.0 -p 3003) &
(cd "$ROOT/frontend-user" && npx next start -H 0.0.0.0 -p 3002) &

trap 'kill 0' INT TERM EXIT
wait
