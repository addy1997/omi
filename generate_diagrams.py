import json
import base64

# Create SVG diagrams for the technical design

# Diagram 1: High-Level System Architecture
architecture_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 700" width="1200" height="700">
  <defs>
    <style>
      .box { fill: #e8f4f8; stroke: #2c3e50; stroke-width: 2; }
      .header-box { fill: #34495e; stroke: #2c3e50; stroke-width: 2; }
      .agent-box { fill: #d5f4e6; stroke: #27ae60; stroke-width: 2; }
      .text-dark { fill: #2c3e50; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
      .text-light { fill: #fff; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
      .text-small { fill: #34495e; font-family: Arial, sans-serif; font-size: 12px; }
      .arrow { stroke: #2c3e50; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
      .label { fill: #666; font-family: Arial, sans-serif; font-size: 11px; }
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#2c3e50" />
    </marker>
  </defs>

  <!-- Client Layer -->
  <text x="600" y="30" text-anchor="middle" class="text-dark" font-size="16">CLIENT LAYER</text>
  
  <rect x="50" y="50" width="140" height="60" class="box" rx="5"/>
  <text x="120" y="75" text-anchor="middle" class="text-dark">Web UI</text>
  <text x="120" y="92" text-anchor="middle" class="text-small">(React)</text>
  
  <rect x="250" y="50" width="140" height="60" class="box" rx="5"/>
  <text x="320" y="75" text-anchor="middle" class="text-dark">Mobile App</text>
  <text x="320" y="92" text-anchor="middle" class="text-small">(Native)</text>
  
  <rect x="450" y="50" width="140" height="60" class="box" rx="5"/>
  <text x="520" y="75" text-anchor="middle" class="text-dark">CLI / Scripts</text>
  <text x="520" y="92" text-anchor="middle" class="text-small">(REST)</text>

  <rect x="650" y="50" width="140" height="60" class="box" rx="5"/>
  <text x="720" y="75" text-anchor="middle" class="text-dark">Dashboard</text>
  <text x="720" y="92" text-anchor="middle" class="text-small">(WebSocket)</text>

  <!-- Arrows to Platform -->
  <path d="M 120 110 L 120 150" class="arrow"/>
  <path d="M 320 110 L 320 150" class="arrow"/>
  <path d="M 520 110 L 520 150" class="arrow"/>
  <path d="M 720 110 L 720 150" class="arrow"/>

  <!-- Platform Box -->
  <rect x="50" y="150" width="900" height="450" class="header-box" rx="8"/>
  <text x="500" y="175" text-anchor="middle" class="text-light" font-size="18" font-weight="bold">OMI PLATFORM (Port 9000)</text>

  <!-- API Gateway -->
  <rect x="80" y="195" width="200" height="80" class="box" rx="5"/>
  <text x="180" y="220" text-anchor="middle" class="text-dark" font-weight="bold">API Gateway</text>
  <text x="180" y="240" text-anchor="middle" class="text-small">• CORS, Security Headers</text>
  <text x="180" y="255" text-anchor="middle" class="text-small">• JWT Auth</text>

  <!-- Router -->
  <rect x="330" y="195" width="200" height="80" class="box" rx="5"/>
  <text x="430" y="220" text-anchor="middle" class="text-dark" font-weight="bold">Route Manager</text>
  <text x="430" y="240" text-anchor="middle" class="text-small">• Explicit routing</text>
  <text x="430" y="255" text-anchor="middle" class="text-small">• Capability matching</text>

  <!-- Task Executor -->
  <rect x="580" y="195" width="200" height="80" class="box" rx="5"/>
  <text x="680" y="220" text-anchor="middle" class="text-dark" font-weight="bold">Task Executor</text>
  <text x="680" y="240" text-anchor="middle" class="text-small">• HTTP to agents</text>
  <text x="680" y="255" text-anchor="middle" class="text-small">• Timeout handling</text>

  <!-- Registry -->
  <rect x="80" y="310" width="180" height="80" class="box" rx="5"/>
  <text x="170" y="335" text-anchor="middle" class="text-dark" font-weight="bold">Agent Registry</text>
  <text x="170" y="355" text-anchor="middle" class="text-small">• Registration</text>
  <text x="170" y="370" text-anchor="middle" class="text-small">• Heartbeat tracking</text>

  <!-- Storage -->
  <rect x="310" y="310" width="180" height="80" class="box" rx="5"/>
  <text x="400" y="335" text-anchor="middle" class="text-dark" font-weight="bold">Storage</text>
  <text x="400" y="355" text-anchor="middle" class="text-small">• TaskRecord</text>
  <text x="400" y="370" text-anchor="middle" class="text-small">• AgentRecord</text>

  <!-- Observability -->
  <rect x="540" y="310" width="180" height="80" class="box" rx="5"/>
  <text x="630" y="335" text-anchor="middle" class="text-dark" font-weight="bold">Observability</text>
  <text x="630" y="355" text-anchor="middle" class="text-small">• Cost tracking</text>
  <text x="630" y="370" text-anchor="middle" class="text-small">• Metrics</text>

  <!-- Authentication -->
  <rect x="770" y="310" width="140" height="80" class="box" rx="5"/>
  <text x="840" y="335" text-anchor="middle" class="text-dark" font-weight="bold">Auth (JWT)</text>
  <text x="840" y="355" text-anchor="middle" class="text-small">• Token issue</text>
  <text x="840" y="370" text-anchor="middle" class="text-small">• Validation</text>

  <!-- Database Layer -->
  <rect x="80" y="425" width="830" height="60" class="box" rx="5"/>
  <text x="495" y="450" text-anchor="middle" class="text-dark" font-weight="bold">SQLAlchemy + SQLite/PostgreSQL</text>
  <text x="495" y="468" text-anchor="middle" class="text-small">TaskRecord | AgentRecord | UsageRecord</text>

  <!-- Arrows within platform -->
  <path d="M 180 275 L 180 310" class="arrow"/>
  <path d="M 430 275 L 400 310" class="arrow"/>
  <path d="M 680 275 L 630 310" class="arrow"/>
  <path d="M 170 390 L 200 425" class="arrow"/>
  <path d="M 400 390 L 400 425" class="arrow"/>
  <path d="M 630 390 L 600 425" class="arrow"/>

  <!-- Agents -->
  <rect x="100" y="630" width="120" height="50" class="agent-box" rx="5"/>
  <text x="160" y="650" text-anchor="middle" class="text-dark">Agent 1</text>
  <text x="160" y="668" text-anchor="middle" class="text-small">:8001</text>

  <rect x="280" y="630" width="120" height="50" class="agent-box" rx="5"/>
  <text x="340" y="650" text-anchor="middle" class="text-dark">Agent 2</text>
  <text x="340" y="668" text-anchor="middle" class="text-small">:8002</text>

  <rect x="460" y="630" width="120" height="50" class="agent-box" rx="5"/>
  <text x="520" y="650" text-anchor="middle" class="text-dark">Agent 3</text>
  <text x="520" y="668" text-anchor="middle" class="text-small">:8003</text>

  <rect x="640" y="630" width="120" height="50" class="agent-box" rx="5"/>
  <text x="700" y="650" text-anchor="middle" class="text-dark">Agent N</text>
  <text x="700" y="668" text-anchor="middle" class="text-small">:XXXX</text>

  <!-- Arrows from platform to agents -->
  <path d="M 160 630 L 160 590" class="arrow"/>
  <path d="M 340 630 L 340 590" class="arrow"/>
  <path d="M 520 630 L 520 590" class="arrow"/>
  <path d="M 700 630 L 700 590" class="arrow"/>

  <!-- Connection labels -->
  <text x="140" y="615" text-anchor="middle" class="label">HTTP POST /run</text>
  <text x="320" y="615" text-anchor="middle" class="label">HTTP POST /run</text>
  <text x="500" y="615" text-anchor="middle" class="label">HTTP POST /run</text>
  <text x="680" y="615" text-anchor="middle" class="label">HTTP POST /run</text>
</svg>'''

# Diagram 2: Task Routing Decision Tree
routing_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 900" width="1000" height="900">
  <defs>
    <style>
      .decision { fill: #fff9e6; stroke: #f39c12; stroke-width: 2; }
      .process { fill: #e8f4f8; stroke: #2c3e50; stroke-width: 2; }
      .success { fill: #d5f4e6; stroke: #27ae60; stroke-width: 2; }
      .fail { fill: #fadbd8; stroke: #e74c3c; stroke-width: 2; }
      .text-dark { fill: #2c3e50; font-family: Arial, sans-serif; font-size: 13px; font-weight: bold; }
      .text-small { fill: #34495e; font-family: Arial, sans-serif; font-size: 11px; }
      .arrow { stroke: #34495e; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
      .label { fill: #666; font-family: Arial, sans-serif; font-size: 10px; font-weight: bold; }
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#34495e" />
    </marker>
  </defs>

  <!-- Title -->
  <text x="500" y="30" text-anchor="middle" class="text-dark" font-size="16">Task Routing Decision Flow</text>

  <!-- Task Arrives -->
  <rect x="350" y="50" width="300" height="60" class="process" rx="5"/>
  <text x="500" y="75" text-anchor="middle" class="text-dark">Task Arrives</text>
  <text x="500" y="92" text-anchor="middle" class="text-small">message, agent_id, metadata, context</text>

  <!-- Decision 1: Agent ID -->
  <path d="M 500 110 L 500 150" class="arrow"/>
  <polygon points="500,150 490,135 510,135" fill="#f39c12"/>
  
  <rect x="350" y="150" width="300" height="70" class="decision" rx="5"/>
  <text x="500" y="175" text-anchor="middle" class="text-dark">Is agent_id specified?</text>
  <text x="500" y="195" text-anchor="middle" class="text-small">(Explicit routing)</text>

  <!-- YES path -->
  <path d="M 350 185 L 200 185 L 200 270" class="arrow"/>
  <text x="280" y="175" class="label">YES</text>

  <rect x="100" y="270" width="200" height="60" class="success" rx="5"/>
  <text x="200" y="295" text-anchor="middle" class="text-dark">Route to Agent</text>
  <text x="200" y="310" text-anchor="middle" class="text-small">Direct (no LLM)</text>

  <!-- NO path -->
  <path d="M 500 220 L 500 260" class="arrow"/>
  <text x="520" y="240" class="label">NO</text>

  <!-- Decision 2: Capability -->
  <rect x="350" y="260" width="300" height="70" class="decision" rx="5"/>
  <text x="500" y="285" text-anchor="middle" class="text-dark">Capability in metadata?</text>
  <text x="500" y="305" text-anchor="middle" class="text-small">task.metadata["capability"]</text>

  <!-- Capability YES -->
  <path d="M 650" y="295 L 800 295 L 800 370" class="arrow"/>
  <text x="720" y="285" class="label">YES</text>

  <rect x="700" y="370" width="200" height="60" class="success" rx="5"/>
  <text x="800" y="395" text-anchor="middle" class="text-dark">Match Agents</text>
  <text x="800" y="410" text-anchor="middle" class="text-small">By capability tag</text>

  <!-- Capability NO -->
  <path d="M 500 330 L 500 380" class="arrow"/>
  <text x="520" y="360" class="label">NO</text>

  <!-- Decision 3: Keywords -->
  <rect x="350" y="380" width="300" height="70" class="decision" rx="5"/>
  <text x="500" y="405" text-anchor="middle" class="text-dark">Keywords in message?</text>
  <text x="500" y="425" text-anchor="middle" class="text-small">write, test, review, deploy, etc.</text>

  <!-- Keywords YES -->
  <path d="M 350 415 L 200 415 L 200 490" class="arrow"/>
  <text x="280" y="405" class="label">YES</text>

  <rect x="100" y="490" width="200" height="60" class="success" rx="5"/>
  <text x="200" y="515" text-anchor="middle" class="text-dark">Match Agents</text>
  <text x="200" y="530" text-anchor="middle" class="text-small">By inferred capability</text>

  <!-- Keywords NO -->
  <path d="M 500 450 L 500 500" class="arrow"/>
  <text x="520" y="480" class="label">NO</text>

  <!-- LLM Route -->
  <rect x="350" y="500" width="300" height="70" class="decision" rx="5"/>
  <text x="500" y="525" text-anchor="middle" class="text-dark">LLM Route (Fallback)</text>
  <text x="500" y="545" text-anchor="middle" class="text-small">Claude Haiku: "Pick best agent"</text>

  <!-- LLM Result -->
  <path d="M 500 570 L 500 600" class="arrow"/>
  <rect x="350" y="600" width="300" height="70" class="success" rx="5"/>
  <text x="500" y="625" text-anchor="middle" class="text-dark">Route Decision Made</text>
  <text x="500" y="645" text-anchor="middle" class="text-small">Agent selected, check if ONLINE</text>

  <!-- Final Check -->
  <path d="M 500 670 L 500 700" class="arrow"/>
  <rect x="350" y="700" width="300" height="70" class="decision" rx="5"/>
  <text x="500" y="725" text-anchor="middle" class="text-dark">Agent status = ONLINE?</text>
  <text x="500" y="745" text-anchor="middle" class="text-small">(Registry check)</text>

  <!-- Success -->
  <path d="M 650 735 L 800 735" class="arrow"/>
  <text x="720" y="725" class="label">YES</text>
  <rect x="700" y="700" width="200" height="70" class="success" rx="5"/>
  <text x="800" y="725" text-anchor="middle" class="text-dark">Execute Task</text>
  <text x="800" y="745" text-anchor="middle" class="text-small">Send to agent HTTP /run</text>

  <!-- Failure -->
  <path d="M 350 735 L 200 735" class="arrow"/>
  <text x="280" y="725" class="label">NO</text>
  <rect x="0" y="700" width="200" height="70" class="fail" rx="5"/>
  <text x="100" y="725" text-anchor="middle" class="text-dark">FAILED</text>
  <text x="100" y="745" text-anchor="middle" class="text-small">No agent available</text>
</svg>'''

# Diagram 3: Agent Lifecycle State Machine
agent_lifecycle_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 600" width="900" height="600">
  <defs>
    <style>
      .state-box { fill: #e8f4f8; stroke: #2c3e50; stroke-width: 2; }
      .state-online { fill: #d5f4e6; stroke: #27ae60; stroke-width: 3; }
      .state-offline { fill: #fadbd8; stroke: #e74c3c; stroke-width: 3; }
      .state-error { fill: #f4d4d8; stroke: #c0392b; stroke-width: 3; }
      .text-dark { fill: #2c3e50; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
      .text-small { fill: #34495e; font-family: Arial, sans-serif; font-size: 11px; }
      .transition { stroke: #34495e; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
      .label { fill: #555; font-family: Arial, sans-serif; font-size: 10px; font-style: italic; }
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#34495e" />
    </marker>
  </defs>

  <!-- Title -->
  <text x="450" y="30" text-anchor="middle" class="text-dark" font-size="16">Agent Lifecycle State Machine</text>

  <!-- Unregistered State -->
  <rect x="50" y="80" width="180" height="80" class="state-box" rx="8"/>
  <text x="140" y="110" text-anchor="middle" class="text-dark">UNREGISTERED</text>
  <text x="140" y="130" text-anchor="middle" class="text-small">Agent not running</text>
  <text x="140" y="145" text-anchor="middle" class="text-small">or not joined</text>

  <!-- Arrow 1 -->
  <path d="M 230 120 Q 330 80 400 100" class="transition" stroke-dasharray="5,5"/>
  <text x="310" y="85" text-anchor="middle" class="label">agent.register()</text>

  <!-- ONLINE State -->
  <rect x="400" y="50" width="180" height="120" class="state-online" rx="8"/>
  <text x="490" y="85" text-anchor="middle" class="text-dark" font-size="15">ONLINE</text>
  <text x="490" y="105" text-anchor="middle" class="text-small">✓ Registered</text>
  <text x="490" y="120" text-anchor="middle" class="text-small">✓ Heartbeat fresh</text>
  <text x="490" y="135" text-anchor="middle" class="text-small">✓ Ready for tasks</text>

  <!-- Tasks processing loop -->
  <circle cx="490" cy="300" r="50" fill="none" stroke="#3498db" stroke-width="2" stroke-dasharray="5,5"/>
  <text x="490" y="300" text-anchor="middle" class="text-dark" font-size="12">Tasks</text>
  <text x="490" y="318" text-anchor="middle" class="text-small">Processed</text>

  <!-- Arrow to tasks -->
  <path d="M 490 170 L 490 250" class="transition"/>
  <text x="510" y="210" class="label">Every 30s</text>
  <text x="510" y="225" class="label">Heartbeat</text>

  <!-- Arrow back from tasks -->
  <path d="M 540 300 Q 590 200 530 170" class="transition"/>
  <text x="580" y="235" class="label">Update</text>
  <text x="580" y="250" class="label">last_heartbeat</text>

  <!-- OFFLINE State -->
  <rect x="650" y="80" width="180" height="120" class="state-offline" rx="8"/>
  <text x="740" y="115" text-anchor="middle" class="text-dark" font-size="15">OFFLINE</text>
  <text x="740" y="135" text-anchor="middle" class="text-small">✗ Heartbeat stale</text>
  <text x="740" y="150" text-anchor="middle" class="text-small">✗ No routing to agent</text>
  <text x="740" y="165" text-anchor="middle" class="text-small">(90s+ no ping)</text>

  <!-- Arrow to OFFLINE -->
  <path d="M 580 110 L 650 110" class="transition"/>
  <text x="615" y="100" text-anchor="middle" class="label">No heartbeat</text>
  <text x="615" y="115" text-anchor="middle" class="label">90+ seconds</text>

  <!-- Arrow back to ONLINE -->
  <path d="M 650 130 Q 590 200 580 130" class="transition"/>
  <text x="600" y="180" text-anchor="middle" class="label">Agent restarts,</text>
  <text x="600" y="195" text-anchor="middle" class="label">heartbeats resume</text>

  <!-- DEREGISTERED State -->
  <rect x="650" y="280" width="180" height="80" class="state-box" rx="8"/>
  <text x="740" y="310" text-anchor="middle" class="text-dark">DEREGISTERED</text>
  <text x="740" y="330" text-anchor="middle" class="text-small">Manually removed</text>
  <text x="740" y="345" text-anchor="middle" class="text-small">from registry</text>

  <!-- Arrow from OFFLINE to DEREGISTERED -->
  <path d="M 740 200 L 740 280" class="transition"/>
  <text x="760" y="240" text-anchor="middle" class="label">Manual admin</text>
  <text x="760" y="255" text-anchor="middle" class="label">deregister</text>

  <!-- Task execution detail box -->
  <rect x="50" y="280" width="300" height="180" fill="none" stroke="#ddd" stroke-width="1" stroke-dasharray="3,3" rx="5"/>
  <text x="200" y="300" text-anchor="middle" class="text-dark" font-size="12">Task Execution Detail</text>
  
  <text x="70" y="325" class="text-small">1. Platform checks agent in registry</text>
  <text x="70" y="345" class="text-small">2. Status must be ONLINE</text>
  <text x="70" y="365" class="text-small">3. HTTP POST /run sent to agent</text>
  <text x="70" y="385" class="text-small">4. Agent processes task</text>
  <text x="70" y="405" class="text-small">5. Result returned to platform</text>
  <text x="70" y="425" class="text-small">6. Result stored and tracked</text>
  <text x="70" y="445" class="text-small">7. Response sent to client</text>
</svg>'''

# Diagram 4: Task Execution Lifecycle
execution_lifecycle_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 850" width="1000" height="850">
  <defs>
    <style>
      .step-box { fill: #e8f4f8; stroke: #2c3e50; stroke-width: 2; }
      .db-box { fill: #f4e4d4; stroke: #d35400; stroke-width: 2; }
      .process-box { fill: #d5f4e6; stroke: #27ae60; stroke-width: 2; }
      .text-dark { fill: #2c3e50; font-family: Arial, sans-serif; font-size: 13px; font-weight: bold; }
      .text-small { fill: #34495e; font-family: Arial, sans-serif; font-size: 10px; }
      .step-num { fill: #fff; background: #2c3e50; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; }
      .arrow { stroke: #34495e; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
    </style>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <polygon points="0 0, 10 3, 0 6" fill="#34495e" />
    </marker>
  </defs>

  <!-- Title -->
  <text x="500" y="30" text-anchor="middle" class="text-dark" font-size="16">Task Execution Lifecycle (8 Steps)</text>

  <!-- Step 1: Task Submitted -->
  <rect x="350" y="60" width="300" height="60" class="step-box" rx="5"/>
  <circle cx="380" cy="90" r="18" fill="#2c3e50"/>
  <text x="380" y="95" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">1</text>
  <text x="470" y="85" class="text-dark">Task Submitted</text>
  <text x="470" y="105" class="text-small">Client → Platform</text>

  <!-- Step 2: Save Task -->
  <path d="M 500 120 L 500 155" class="arrow"/>
  <rect x="350" y="155" width="300" height="60" class="db-box" rx="5"/>
  <circle cx="380" cy="185" r="18" fill="#d35400"/>
  <text x="380" y="190" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">2</text>
  <text x="470" y="175" class="text-dark">Save to DB</text>
  <text x="470" y="195" class="text-small">TaskRecord (PENDING)</text>

  <!-- Step 3: Route Task -->
  <path d="M 500 215 L 500 250" class="arrow"/>
  <rect x="350" y="250" width="300" height="60" class="process-box" rx="5"/>
  <circle cx="380" cy="280" r="18" fill="#27ae60"/>
  <text x="380" y="285" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">3</text>
  <text x="470" y="270" class="text-dark">Route Task</text>
  <text x="470" y="290" class="text-small">4-level cascade → Agent</text>

  <!-- Decision Diamond -->
  <path d="M 500 310 L 600 350 L 500 390 L 400 350 Z" fill="#fff9e6" stroke="#f39c12" stroke-width="2"/>
  <text x="500" y="355" text-anchor="middle" class="text-dark" font-size="12">Agent</text>
  <text x="500" y="370" text-anchor="middle" class="text-dark" font-size="12">Found?</text>

  <!-- No path (FAILED) -->
  <path d="M 400 350 L 200 350" class="arrow"/>
  <text x="300" y="340" text-anchor="middle" class="text-small">NO</text>
  <rect x="50" y="320" width="150" height="60" class="step-box" rx="5"/>
  <text x="125" y="345" text-anchor="middle" class="text-dark" font-weight="bold">FAILED</text>
  <text x="125" y="365" text-anchor="middle" class="text-small">No agent available</text>

  <!-- Yes path -->
  <path d="M 500 390 L 500 425" class="arrow"/>
  <text x="520" y="410" text-anchor="middle" class="text-small">YES</text>

  <!-- Step 4: Call Agent -->
  <rect x="350" y="425" width="300" height="60" class="step-box" rx="5"/>
  <circle cx="380" cy="455" r="18" fill="#2c3e50"/>
  <text x="380" y="460" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">4</text>
  <text x="470" y="445" class="text-dark">Call Agent /run</text>
  <text x="470" y="465" class="text-small">HTTP POST (timeout: 300s)</text>

  <!-- Step 5: Result or Error -->
  <path d="M 500 485 L 500 520" class="arrow"/>
  <path d="M 350 545 L 200 545 L 200 640" class="arrow"/>
  <text x="280" y="540" text-anchor="middle" class="text-small">FAILURE</text>
  
  <path d="M 650 545 L 800 545 L 800 640" class="arrow"/>
  <text x="720" y="540" text-anchor="middle" class="text-small">SUCCESS</text>

  <!-- Error Box -->
  <rect x="100" y="640" width="200" height="60" class="step-box" rx="5"/>
  <circle cx="130" cy="670" r="18" fill="#2c3e50"/>
  <text x="130" y="675" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">5E</text>
  <text x="200" y="655" text-anchor="middle" class="text-dark">Error Result</text>
  <text x="200" y="675" text-anchor="middle" class="text-small">status: FAILED</text>

  <!-- Success Box -->
  <rect x="700" y="640" width="200" height="60" class="process-box" rx="5"/>
  <circle cx="730" cy="670" r="18" fill="#27ae60"/>
  <text x="730" y="675" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">5S</text>
  <text x="800" y="655" text-anchor="middle" class="text-dark">Parse Result</text>
  <text x="800" y="675" text-anchor="middle" class="text-small">status: COMPLETED</text>

  <!-- Converge arrows -->
  <path d="M 200 700 L 500 735" class="arrow"/>
  <path d="M 800 700 L 500 735" class="arrow"/>

  <!-- Step 6: Store Result -->
  <rect x="350" y="735" width="300" height="60" class="db-box" rx="5"/>
  <circle cx="380" cy="765" r="18" fill="#d35400"/>
  <text x="380" y="770" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">6</text>
  <text x="470" y="750" class="text-dark">Store Result to DB</text>
  <text x="470" y="770" class="text-small">Update TaskRecord</text>

  <!-- Step 7: Record Usage -->
  <path d="M 500 795 L 500 830" class="arrow"/>
  <rect x="350" y="830" width="300" height="60" class="db-box" rx="5" style="stroke-dasharray: 4,4"/>
  <circle cx="380" cy="860" r="18" fill="#d35400"/>
  <text x="380" y="865" text-anchor="middle" class="text-small" fill="#fff" font-weight="bold">7</text>
  <text x="470" y="845" class="text-dark">Record Usage</text>
  <text x="470" y="865" class="text-small">tokens, cost, duration</text>
</svg>'''

# Write SVG files
with open('/mnt/d/dev/addy_wp/omi/diagrams/01-architecture.svg', 'w') as f:
    f.write(architecture_svg)

with open('/mnt/d/dev/addy_wp/omi/diagrams/02-routing.svg', 'w') as f:
    f.write(routing_svg)

with open('/mnt/d/dev/addy_wp/omi/diagrams/03-agent-lifecycle.svg', 'w') as f:
    f.write(agent_lifecycle_svg)

with open('/mnt/d/dev/addy_wp/omi/diagrams/04-execution-lifecycle.svg', 'w') as f:
    f.write(execution_lifecycle_svg)

print("✓ Generated 4 SVG diagrams")
print("  - 01-architecture.svg")
print("  - 02-routing.svg")
print("  - 03-agent-lifecycle.svg")
print("  - 04-execution-lifecycle.svg")
