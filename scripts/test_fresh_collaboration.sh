#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     TESTING FRESH AGENT COLLABORATION                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Test 1: Direct collaboration question
echo "📢 Test 1: Asking about agent collaboration"
RESULT=$(curl -s -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Can you collaborate with other agents on this platform? List their names and what they do."
  }')

AGENT=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); agent=data.get('agent_id','unknown').split('-')[0].upper(); print(agent)")
STATUS=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['status'])")
echo "   Agent: $AGENT | Status: $STATUS"
echo ""
echo "   Response:"
echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); content=data['content'][:600]; print('   ' + content.replace('\n', '\n   '))"

echo ""
echo "---"
echo ""

# Test 2: Delegation test
echo "📢 Test 2: Complex task requiring collaboration"
RESULT=$(curl -s -X POST http://localhost:9000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I want to deploy an app. First ask Flux what data analysis tools it has, then ask Nexus how to containerize the app."
  }')

AGENT=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); agent=data.get('agent_id','unknown').split('-')[0].upper(); print(agent)")
STATUS=$(echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['status'])")
echo "   Agent: $AGENT | Status: $STATUS"
echo ""
echo "   Response:"
echo $RESULT | python3 -c "import sys, json; data=json.load(sys.stdin); content=data['content'][:600]; print('   ' + content.replace('\n', '\n   '))"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ FRESH COLLABORATION TEST COMPLETE                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
