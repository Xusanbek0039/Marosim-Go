#!/usr/bin/env bash
# Starts every panel for the local network (LAN demo): one Django app per port, picking the panel by port.
# Usage: bash start-lan.sh        Stop: Ctrl+C
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORTS="8000,8001,8002,8003,3002,3003"

# Prefer the activated environment, then the project's conventional venv locations.
# Normalize Windows paths so environments activated in PowerShell also work in Git Bash.
PYTHON=""
for env_dir in "${VIRTUAL_ENV:-}" "$ROOT/backend/.venv" "$ROOT/.venv" "$ROOT/backend/venv" "$ROOT/venv"; do
  [[ -n "$env_dir" ]] || continue
  env_dir="${env_dir//\\//}"
  for executable in "$env_dir/Scripts/python.exe" "$env_dir/Scripts/python" "$env_dir/bin/python"; do
    if [[ -x "$executable" ]]; then
      PYTHON="$executable"
      break 2
    fi
  done
done
if [[ -z "$PYTHON" ]]; then
  echo "No virtual environment Python found. Create backend/.venv and install backend/requirements.txt, or activate an existing environment." >&2
  exit 1
fi
if ! "$PYTHON" --version >/dev/null 2>&1; then
  echo "Virtual environment Python cannot run: $PYTHON" >&2
  echo "Restore its base Python installation, or recreate the environment and install backend/requirements.txt." >&2
  exit 1
fi

# Windows keeps node/python children alive after the bash parent dies (the venv python.exe is only
# a launcher), so free the ports by the PID that actually listens on them. Python on Windows lets
# several runserver processes share one port (old code keeps answering), and Get-NetTCPConnection
# does not always list them — so also stop every earlier server of this project by its command line.
free_ports() {
  powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort $PORTS -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }
    Get-CimInstance Win32_Process | Where-Object {
      \$_.CommandLine -like '*manage.py runserver 0.0.0.0:800*' -or \$_.CommandLine -like '*manage.py runserver 0.0.0.0:300*' -or \$_.CommandLine -like '*next*start -H 0.0.0.0 -p 300*'
    } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
}
free_ports
trap 'free_ports; exit 0' INT TERM

# Each port serves one panel + the API (as on production, where the subdomain picks the panel):
# 8000 = Super Admin (http://127.0.0.1:8000/ = the marosimgo.uz landing page), 8001 = Admin,
# 8002 = Studio, 8003 = landing (for tunnels), 3002 = User, 3003 = To'yxona.
# User / To'yxona are static builds now (npm run build:panel in frontend-user / frontend-toyxona).
# serve <port> <panel> [panel for 127.0.0.1]; other hosts (e.g. *.trycloudflare.com tunnels) get <panel>
serve() {
  (cd "$ROOT/backend" && PANEL_HOST_SITES="192.168.1.12=$2,localhost=$2,127.0.0.1=${3:-$2}" PANEL_DEFAULT_SITE="$2" \
    "$PYTHON" manage.py runserver "0.0.0.0:$1" --insecure --noreload) &
}
serve 8000 superadmin landing
serve 8001 admin
serve 8002 studio
serve 8003 landing
serve 3002 userlogin
serve 3003 toyxona

# Git Bash's "wait" can return early on Windows: idle until Ctrl+C instead.
while true; do sleep 3600; done
