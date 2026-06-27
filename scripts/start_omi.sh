#!/bin/bash
# Launch the full Omi stack fully detached so it survives shell/session teardown.
# Idempotent: kills any prior instances first. Logs to /tmp/omi-logs.
set -u

ROOT="/mnt/d/dev/addy_wp/omi"
VENV="$ROOT/venv/bin/activate"
PLATFORM="http://localhost:9000"
LOGS="/tmp/omi-logs"

# Optional first arg = laptop's LAN IP (e.g. 192.168.1.143) for phone access.
# When set, the dashboard talks to that IP and CORS/TrustedHost allow it.
LAN_IP="${1:-}"
if [ -n "$LAN_IP" ]; then
  DASH_ORIGIN="http://$LAN_IP:5173"
  DASH_PLATFORM_URL="http://$LAN_IP:9000"
  echo "==> Phone-access mode: dashboard -> $DASH_PLATFORM_URL"
else
  DASH_ORIGIN="http://localhost:5173"
  DASH_PLATFORM_URL="http://localhost:9000"
fi

mkdir -p "$LOGS"

echo "==> Stopping any prior instances..."
pkill -f "omi_platform.cli serve" 2>/dev/null
for a in helix nexus flux vera lumen; do pkill -f "$a serve-agent" 2>/dev/null; done
pkill -f "vite --port 5173" 2>/dev/null
sleep 2

start() {  # name  workdir  command  logfile
  local name="$1" wd="$2" cmd="$3" log="$4"
  ( cd "$wd" && source "$VENV" && setsid nohup bash -c "$cmd" > "$log" 2>&1 < /dev/null & )
  echo "  started $name -> $log"
}

echo "==> Platform..."
start platform "$ROOT/platform" \
  "PLATFORM_DB_URL='sqlite+aiosqlite:///./platform.db' PLATFORM_DASHBOARD_URL='$DASH_ORIGIN' python -m omi_platform.cli serve" \
  "$LOGS/platform.log"

# wait for platform health
for i in $(seq 1 30); do
  curl -s --max-time 3 "$PLATFORM/health" >/dev/null 2>&1 && break
  sleep 1
done

echo "==> Agents..."
start helix "$ROOT/agents/helix" "helix serve-agent --platform $PLATFORM" "$LOGS/helix.log"
start nexus "$ROOT/agents/nexus" "nexus serve-agent --platform $PLATFORM" "$LOGS/nexus.log"
start flux  "$ROOT/agents/flux"  "flux serve-agent --platform $PLATFORM"  "$LOGS/flux.log"
start vera  "$ROOT/agents/vera"  "vera serve-agent --platform $PLATFORM"  "$LOGS/vera.log"
start lumen "$ROOT/agents/lumen" "lumen serve-agent --platform $PLATFORM" "$LOGS/lumen.log"

echo "==> Dashboard..."
# --host binds 0.0.0.0 so other devices (your phone) can load it;
# VITE_PLATFORM_URL makes the app call the laptop's IP, not the phone's localhost.
( cd "$ROOT/dashboard" && VITE_PLATFORM_URL="$DASH_PLATFORM_URL" setsid nohup npm run dev -- --host 0.0.0.0 > "$LOGS/dashboard.log" 2>&1 < /dev/null & )
echo "  started dashboard -> $LOGS/dashboard.log  (origin $DASH_ORIGIN)"

sleep 10
echo "==> Done. Verifying registry..."
curl -s --max-time 5 "$PLATFORM/agents" 2>/dev/null | python3 -c "
import sys,json
try:
    seen={a['name']:a['status'] for a in json.load(sys.stdin)}
    for n,s in sorted(seen.items()): print(f'   {s:8} {n}')
    print('   TOTAL online agents:', sum(1 for s in seen.values() if s=='online'))
except Exception as e:
    print('   registry not ready:', e)
"
