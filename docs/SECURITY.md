# Omi Platform — Security Model

## Overview

Omi is designed with **defense-in-depth**: multiple security layers prevent exploitation at each level.

```
┌─────────────────────────────────────────────────────┐
│ Frontend (React Dashboard)                          │
│ ✓ No API keys stored                                │
│ ✓ All secrets on backend only                       │
└─────────────┬───────────────────────────────────────┘
              │ HTTPS + JWT
┌─────────────┴───────────────────────────────────────┐
│ Platform API Gateway (FastAPI)                      │
│ ✓ JWT authentication required                       │
│ ✓ CORS restricted to dashboard URL only             │
│ ✓ Rate limiting: 100 req/min per IP                 │
│ ✓ Input validation: < 10KB messages                 │
│ ✓ Security headers: HSTS, X-Frame-Options, etc.     │
└─────────────┬───────────────────────────────────────┘
              │ API Keys (secure env vars)
┌─────────────┴───────────────────────────────────────┐
│ Agents (Helix, Nexus, Flux)                         │
│ ✓ Stateless (no local secrets)                      │
│ ✓ Shell execution in Docker sandbox                 │
│ ✓ 512MB memory limit, 50% CPU throttled             │
│ ✓ Output truncated to 10KB                          │
└─────────────┬───────────────────────────────────────┘
              │
┌─────────────┴───────────────────────────────────────┐
│ External Services                                   │
│ ✓ Gemini API (Google)                               │
│ ✓ Anthropic API (Claude)                            │
│ ✓ GitHub API                                        │
│ ✓ PostgreSQL database                               │
└─────────────────────────────────────────────────────┘
```

---

## Threat Model

### 1. **API Key Exposure** 🔐

**Risk:** Attacker gains access to API keys (Anthropic, GitHub, Gemini)

**Mitigations:**
- Keys stored only in `.env` (never in git, never in frontend)
- Keys passed as env vars to agents, not in responses
- Platform gateway handles all API calls (not frontend)
- Keys rotated on schedule
- Exposure alerts configured in secret manager

**Remaining Risk:** If server is compromised, keys are exposed. Mitigation: use short-lived credentials (API tokens with expiration), managed secret rotation.

---

### 2. **Unauthorized API Access** 🔓

**Risk:** Attacker submits tasks without authentication

**Mitigations:**
- All endpoints require JWT Bearer token
- `/auth/token` validates username/password
- WebSocket requires token in query params
- Rate limiting: 100 req/min per IP
- Tokens expire after 24 hours

**Test:** 
```bash
curl http://localhost:9000/health  # ✓ Works (no auth required)
curl -X POST http://localhost:9000/tasks  # ✗ 401 Unauthorized
curl -X POST http://localhost:9000/tasks \
  -H "Authorization: Bearer $TOKEN"  # ✓ Works
```

---

### 3. **Code Injection in Tasks** 💣

**Risk:** Attacker submits task with shell commands: `; rm -rf /`

**Mitigations:**
- Tasks are **not directly executed as shell**
- Tasks sent to LLM (Claude/Ollama), which generates code
- LLM-generated code runs in Docker sandbox
- Subprocess execution has forbidden patterns blacklist:
  - `rm -rf /`
  - `sudo`
  - `mkfs`
  - `:(){:|:&};:` (fork bomb)
  - `dd if=/dev/zero`
- Docker limits: 512MB RAM, 50% CPU, network disabled

**Test:**
```bash
# This is safe — sent to LLM, not executed directly
curl -X POST http://localhost:9000/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "$(rm -rf /)",
    "agent_id": "helix"
  }'
# LLM will ignore the injection; Docker sandbox prevents execution
```

---

### 4. **Cross-Site Request Forgery (CSRF)** 🎯

**Risk:** Attacker tricks user's browser into submitting malicious task

**Mitigations:**
- CORS restricted to dashboard URL only (no credentials in cookies)
- JWT tokens in `Authorization` header (not cookies)
- Frontend validates token before each request
- Rate limiting prevents brute force

**Protected:** ✓ — CORS prevents cross-origin task submission

---

### 5. **Information Disclosure** 📰

**Risk:** Attacker reads task history, agent IPs, or error messages

**Mitigations:**
- Error messages don't expose internals ("Task failed" not "Connection timeout to 10.0.0.5:8000")
- Task history queryable only by owner (JWT sub claim)
- Agent IPs not exposed to frontend (only names/IDs)
- Logs don't contain secrets
- API docs disabled in production

**Check:**
```bash
# Error message is generic
curl http://localhost:9000/tasks/invalid_id \
  -H "Authorization: Bearer $TOKEN"
# Response: {"detail": "Task not found"}
# NOT: {"detail": "No record with id='invalid_id' in postgresql://..."}
```

---

### 6. **Denial of Service (DoS)** 💥

**Risk:** Attacker floods API with requests, crashing it

**Mitigations:**
- Rate limiting: 100 requests/min per IP
- Message size limit: 10KB (prevents memory exhaustion)
- Docker memory limit: 512MB (prevents agent runaway)
- Timeout on all operations (max 120s for shell commands)
- Connection pooling prevents socket exhaustion

**Test:**
```bash
# After 100 requests, returns 429
for i in {1..150}; do
  curl -s http://localhost:9000/health
done | grep -c "429"  # Should be ~50
```

---

### 7. **Man-in-the-Middle (MitM)** 🚨

**Risk:** Attacker intercepts traffic and steals credentials/tasks

**Mitigations:**
- HTTPS/TLS enforced in production
- WebSocket upgraded to WSS (secure WebSocket)
- Security headers: `Strict-Transport-Security` (HSTS)
- Certificate pinning (optional, for high-security deployments)

**Deployment requirement:** Use reverse proxy (nginx, CloudFlare) with valid SSL cert.

---

### 8. **Privilege Escalation** 🔑

**Risk:** Regular user gains admin access or reads other users' data

**Mitigations:**
- JWT tokens include `role` claim (user, admin)
- Task queries filtered by `user_id` in token
- Admin endpoints (e.g., `/agents/register`) restricted to admin role
- No way for user to modify their own role

---

### 9. **Supply Chain Attack** 📦

**Risk:** Compromised dependency (langchain, fastapi, etc.) contains malware

**Mitigations:**
- `requirements.txt` pinned to specific versions
- Dependency scanning: `pip-audit` checks for CVEs
- Dev-only dependencies separated from prod
- Minimal dependencies (no unnecessary packages)
- Docker image pinned to specific base (`python:3.11-slim`)

---

### 10. **Database Compromise** 🗄️

**Risk:** Attacker gains DB access and reads/modifies all data

**Mitigations:**
- PostgreSQL in production (not SQLite which is file-based)
- Credentials passed via env vars (not hardcoded)
- SQL injection impossible: Pydantic ORM prevents injection
- Database backups encrypted
- Connection string over TLS

---

## Vulnerability Disclosure

If you discover a security vulnerability, **please do not open a public issue**. Instead:

1. Email: **adwaitnaik27@gmail.com**
2. Include:
   - Vulnerability description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. Allow **7 days** for response
4. Vulnerability will be patched within **14 days**

---

## Security Updates

### Dependency Updates
```bash
# Check for vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt

# Test thoroughly before deploying
npm run test
```

### Patch Schedule
- Critical: 24 hours
- High: 7 days
- Medium: 14 days
- Low: Monthly

---

## Best Practices for Users

### API Key Management
```bash
# ✗ BAD
export ANTHROPIC_API_KEY="sk-ant-..."

# ✓ GOOD
# Store in .env (never commit)
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
# .env is in .gitignore

# ✓ BETTER (production)
# Use secret manager (1Password, Doppler, AWS Secrets Manager)
export ANTHROPIC_API_KEY=$(doppler secrets get ANTHROPIC_API_KEY)
```

### JWT Token Handling
```bash
# ✗ BAD
token="eyJhbGc..."
curl -H "Authorization: Bearer $token" http://localhost:9000/tasks
# (token visible in shell history)

# ✓ GOOD
# Get token from secure file or prompt
token=$(curl -X POST http://localhost:9000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass"}' \
  | jq -r '.access_token')

# Don't log tokens
curl -H "Authorization: Bearer $token" http://localhost:9000/tasks \
  2> /dev/null  # Redirect stderr to hide token from logs
```

### WebSocket Authentication
```javascript
// ✗ BAD
const ws = new WebSocket('ws://localhost:9000/ws/session-1');

// ✓ GOOD
const token = localStorage.getItem('jwt_token');  // from /auth/token
const ws = new WebSocket(
  `ws://localhost:9000/ws/session-1?token=${encodeURIComponent(token)}`
);

// ✓ BETTER (use WSS in production)
const ws = new WebSocket(
  `wss://yourdomain.com/ws/session-1?token=${encodeURIComponent(token)}`
);
```

---

## Testing Security

### Run Security Audit
```bash
# Check Python packages for CVEs
pip-audit

# Check Docker image for vulnerabilities
docker scan omi-platform:latest

# Run OWASP ZAP or similar to scan API
zaproxy -cmd -quickurl http://localhost:9000
```

### Pen Test Checklist
- [ ] SQL injection on all endpoints
- [ ] XSS on task message input
- [ ] CSRF on state-changing endpoints
- [ ] Authentication bypass (try JWT tampering)
- [ ] Authorization bypass (try accessing other users' tasks)
- [ ] Rate limit bypass (distributed requests)
- [ ] Path traversal in file operations
- [ ] Command injection in shell tasks
- [ ] Information disclosure (error messages, headers)
- [ ] Insecure cryptography (check JWT algorithm)

---

## Compliance

Omi doesn't collect personal data, but if you integrate with services that do:

- **GDPR:** Ensure data processing agreements with Anthropic, Google
- **SOC 2:** Follow the checklist above for audit trail
- **HIPAA:** Encrypt data at rest and in transit; audit all access
- **PCI DSS:** If handling payment info, isolate in separate service

---

## Conclusion

Omi's security model is **defense-in-depth**:

1. ✅ Secrets never exposed to frontend
2. ✅ All APIs require authentication
3. ✅ Code execution sandboxed in Docker
4. ✅ Rate limiting prevents DoS
5. ✅ Input validation at every boundary
6. ✅ Security headers for browser safety
7. ✅ Audit logging for forensics

**For production:** Run the pre-deployment checklist in [DEPLOYMENT.md](./DEPLOYMENT.md).

**For questions:** Open issue or email security contact.
