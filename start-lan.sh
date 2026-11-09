#!/usr/bin/env bash
# Starts Django (Super Admin, Admin, Studio) + toyxona + user panels for the local network (LAN demo).
# Usage: bash start-lan.sh        Stop: Ctrl+C
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORTS="8000,8001,8002,3002,3003"

# Windows keeps node/python children alive after the bash parent dies (the venv python.exe is only
# a launcher), so free the ports by the PID that actually listens on them.
free_ports() {
  powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort $PORTS -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
}
free_ports
trap 'free_ports; exit 0' INT TERM

# 8000 = Super Admin, 8001 = Admin, 8002 = Studio (each also serves the API; Django picks the panel by host)
(cd "$ROOT/backend" && venv/Scripts/python manage.py runserver 0.0.0.0:8000 --insecure --noreload) &
(cd "$ROOT/backend" && PANEL_HOST_SITES="192.168.1.12=admin,localhost=admin,127.0.0.1=admin" \
  venv/Scripts/python manage.py runserver 0.0.0.0:8001 --insecure --noreload) &
(cd "$ROOT/backend" && PANEL_HOST_SITES="192.168.1.12=studio,localhost=studio,127.0.0.1=studio" \
  venv/Scripts/python manage.py runserver 0.0.0.0:8002 --insecure --noreload) &
(cd "$ROOT/frontend-toyxona" && npx next start -H 0.0.0.0 -p 3003) &
(cd "$ROOT/frontend-user" && npx next start -H 0.0.0.0 -p 3002) &

# Git Bash's "wait" can return early on Windows: idle until Ctrl+C instead.
while true; do sleep 3600; done
