#!/bin/bash
set -e

echo "🚀 Omi Platform — Starting all services..."
echo

# Start platform on port 9000
echo "[1/4] Starting Platform on port 9000..."
cd platform
python -m omi_platform.cli serve &
PLATFORM_PID=$!
sleep 2
echo "✓ Platform online"
echo

# Start Helix on port 8000
echo "[2/4] Starting Helix (Coder) on port 8000..."
cd ../agents/helix
helix serve-agent --platform http://localhost:9000 &
HELIX_PID=$!
sleep 2
echo "✓ Helix registered"
echo

# Start Nexus on port 8001
echo "[3/4] Starting Nexus (DevOps) on port 8001..."
cd ../nexus
nexus serve-agent --platform http://localhost:9000 &
NEXUS_PID=$!
sleep 2
echo "✓ Nexus registered"
echo

# Start Flux on port 8002
echo "[4/6] Starting Flux (Data) on port 8002..."
cd ../flux
flux serve-agent --platform http://localhost:9000 &
FLUX_PID=$!
sleep 2
echo "✓ Flux registered"
echo

# Start Vera on port 8004
echo "[5/6] Starting Vera (Testing/QA) on port 8004..."
cd ../vera
vera serve-agent --platform http://localhost:9000 &
VERA_PID=$!
sleep 2
echo "✓ Vera registered"
echo

# Start Lumen on port 8005
echo "[6/6] Starting Lumen (Documentation) on port 8005..."
cd ../lumen
lumen serve-agent --platform http://localhost:9000 &
LUMEN_PID=$!
sleep 2
echo "✓ Lumen registered"
echo

# Start dashboard on port 5173 (in background)
echo "[+] Starting Dashboard on port 5173..."
cd ../../dashboard
npm run dev > /dev/null 2>&1 &
DASHBOARD_PID=$!
sleep 3
echo "✓ Dashboard online"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Omi Platform is LIVE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
echo "📊 Dashboard:  http://localhost:5173"
echo "🔌 Platform:   http://localhost:9000"
echo "🧠 Helix:      http://localhost:8000"
echo "⚙️  Nexus:      http://localhost:8001"
echo "📈 Flux:       http://localhost:8002"
echo "🧪 Vera:       http://localhost:8004"
echo "📖 Lumen:      http://localhost:8005"
echo
echo "Agents running:"
echo "  • Helix (Code Generation, Review, Search)"
echo "  • Nexus (DevOps, Infrastructure, Kubernetes)"
echo "  • Flux (Data Analysis, SQL, Visualization)"
echo "  • Vera (Testing, Coverage, Test Planning)"
echo "  • Lumen (Documentation, Docstrings, Changelogs)"
echo
echo "Press Ctrl+C to stop all services..."
echo

# Wait for all
wait
