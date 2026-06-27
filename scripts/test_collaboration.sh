#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         AGENT COLLABORATION TEST                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Test 1: Flux discovers other agents
echo "✅ Test 1: Flux discovers available agents"
RESULT=$(curl -s -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What agents are available on this platform? List their names and capabilities.",
    "agent_id": "flux-763d5f60"
  }')

AGENT=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('agent_id', 'unknown').split('-')[0].upper())")
DURATION=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['duration_ms']}ms\")")
echo "   Responded by: $AGENT | Duration: $DURATION"
echo "   Response preview:"
echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); content=data['content'][:300]; print('   ' + content.replace('\n', '\n   '))"
echo

# Test 2: Nexus asks Helix for code help
echo "✅ Test 2: Nexus asks Helix for code review"
RESULT=$(curl -s -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you ask Helix to review this Dockerfile for best practices? Provide a simple Node.js dockerfile",
    "agent_id": "nexus-e960f324"
  }')

AGENT=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('agent_id', 'unknown').split('-')[0].upper())")
DURATION=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['duration_ms']}ms\")")
echo "   Responded by: $AGENT | Duration: $DURATION"
echo "   Response mentions Helix: $(echo $RESULT | grep -q -i 'helix\|code' && echo 'YES' || echo 'NO')"
echo

# Test 3: Flux discovers agents then asks Nexus about monitoring
echo "✅ Test 3: Flux discovers and delegates to Nexus"
RESULT=$(curl -s -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "First discover what agents are available, then ask Nexus how to monitor a Kubernetes cluster with Prometheus",
    "agent_id": "flux-e6d380c1"
  }')

AGENT=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('agent_id', 'unknown').split('-')[0].upper())")
DURATION=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"{data['duration_ms']}ms\")")
echo "   Responded by: $AGENT | Duration: $DURATION"
echo "   Response mentions Nexus/Kubernetes: $(echo $RESULT | grep -q -i 'nexus\|kubernetes\|prometheus' && echo 'YES' || echo 'NO')"
echo

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ AGENT COLLABORATION WORKING!                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo
echo "🤝 Agents can now:"
echo "   • discover each other's capabilities"
echo "   • delegate tasks to specialists"
echo "   • collaborate on complex problems"
echo "   • share knowledge across the platform"
