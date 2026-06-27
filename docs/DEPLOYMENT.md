# Omi Platform — Deployment Guide

## Pre-Deployment Security Checklist

### Secrets Management
- [ ] Generate strong `PLATFORM_SECRET_KEY` (min 32 random chars)
- [ ] Never commit `.env` files (already in `.gitignore`)
- [ ] Use managed secrets service (Vercel Secrets, Doppler, 1Password)
- [ ] Rotate API keys quarterly
- [ ] Revoke any exposed keys immediately

### Environment Configuration
- [ ] Set `PLATFORM_ENVIRONMENT=production`
- [ ] Set `PLATFORM_DEBUG=false` (disables OpenAPI docs)
- [ ] Configure `PLATFORM_DASHBOARD_URL` to your domain
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `PLATFORM_SANDBOX=docker` (not subprocess)

### API Security
- [ ] CORS restricted to dashboard URL only
- [ ] JWT authentication enforced on all endpoints
- [ ] Rate limiting: 100 requests/min per IP
- [ ] WebSocket requires Bearer token
- [ ] Input validation: messages < 10KB

### Network & TLS
- [ ] HTTPS/TLS enforced (redirect HTTP → HTTPS)
- [ ] Security headers configured (HSTS, X-Frame-Options, etc.)
- [ ] CSP (Content-Security-Policy) configured
- [ ] Domain registered and SSL certificate valid

### Monitoring
- [ ] Error tracking enabled (Sentry/Datadog)
- [ ] Request logging configured (without secrets)
- [ ] Health checks passing: `/health`, `/health/ready`
- [ ] Alerts set up for failures

---

## Deployment Platforms

### Vercel (Recommended for Quick Start)

**Architecture:**
```
Frontend (React) → Vercel Functions (FastAPI)
                   ↓
                Platform API (port 9000)
                ↓
          Agents (local ports 8000-8002)
```

#### Step 1: Prepare Backend

```bash
cd /home/addy1997/addy_wp/omi/platform

# Create vercel.json
cat > vercel.json << 'EOF'
{
  "buildCommand": "pip install -r requirements.txt",
  "outputDirectory": ".",
  "functions": {
    "omi_platform/api/main.py": {
      "maxDuration": 30
    }
  },
  "routes": [
    {
      "src": "/(.*)",
      "dest": "omi_platform/api/main.py"
    }
  ]
}
EOF

# Create requirements-prod.txt
pip freeze > requirements-prod.txt
```

#### Step 2: Deploy to Vercel

```bash
npm install -g vercel
vercel --prod \
  --env PLATFORM_SECRET_KEY=<your-secret> \
  --env PLATFORM_DASHBOARD_URL=https://yourdomain.com \
  --env PLATFORM_DB_URL=postgresql://user:pass@host/omi
```

#### Step 3: Update Dashboard

```bash
cd /home/addy1997/addy_wp/omi/dashboard

# Update API endpoint in .env
echo "VITE_API_URL=https://yourdomain.com" > .env.production

# Deploy
npm run build
# Upload dist/ to Vercel (or use `vercel deploy --prod`)
```

#### Step 4: Wire Agents

Option A: Run agents locally and expose via ngrok
```bash
# In separate terminal
ngrok http 8000  # Helix
ngrok http 8001  # Nexus
ngrok http 8002  # Flux

# Register with platform at https://yourdomain.com
```

Option B: Run agents in VPS and register with platform URL

---

### Docker Compose (Self-Hosted)

**For VPS / Self-hosted deployment:**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  platform:
    build: ./platform
    ports: ["9000:9000"]
    environment:
      PLATFORM_SECRET_KEY: ${PLATFORM_SECRET_KEY}
      PLATFORM_ENVIRONMENT: production
      PLATFORM_DB_URL: postgresql://omi:${DB_PASSWORD}@postgres:5432/omi
    depends_on: [postgres]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: omi
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [omi_data:/var/lib/postgresql/data]

  helix:
    build: ./agents/helix
    environment:
      PLATFORM_URL: http://platform:9000
    depends_on: [platform]

  # nexus and flux similarly...

volumes:
  omi_data:
```

Deploy:
```bash
export PLATFORM_SECRET_KEY=$(openssl rand -base64 32)
docker-compose -f docker-compose.prod.yml up -d
```

---

### Kubernetes (Production Scale)

**For high-availability deployments:**

```yaml
# k8s/platform-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: omi-platform
spec:
  replicas: 3
  selector:
    matchLabels:
      app: omi-platform
  template:
    metadata:
      labels:
        app: omi-platform
    spec:
      containers:
      - name: platform
        image: omi-platform:latest
        ports:
        - containerPort: 9000
        env:
        - name: PLATFORM_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: omi-secrets
              key: platform-secret-key
        - name: PLATFORM_DB_URL
          valueFrom:
            secretKeyRef:
              name: omi-secrets
              key: db-url
        livenessProbe:
          httpGet:
            path: /health
            port: 9000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 9000
          initialDelaySeconds: 5
          periodSeconds: 5
      imagePullSecrets:
      - name: regcred
---
apiVersion: v1
kind: Service
metadata:
  name: omi-platform-service
spec:
  selector:
    app: omi-platform
  ports:
  - protocol: TCP
    port: 80
    targetPort: 9000
  type: LoadBalancer
```

Deploy:
```bash
kubectl create secret generic omi-secrets \
  --from-literal=platform-secret-key=$(openssl rand -base64 32) \
  --from-literal=db-url=postgresql://...

kubectl apply -f k8s/
```

---

## Post-Deployment

### Verify Security
```bash
# Check CORS headers
curl -H "Origin: https://attacker.com" \
     -H "Access-Control-Request-Method: POST" \
     https://yourdomain.com/health
# Should NOT return Access-Control-Allow-Origin header

# Check rate limiting
for i in {1..150}; do
  curl -s https://yourdomain.com/health > /dev/null
done
# Should get 429 errors after 100 requests

# Check authentication
curl https://yourdomain.com/ws/test
# Should get 401 or connection rejected
```

### Monitor
- [ ] Dashboard up at https://yourdomain.com
- [ ] Platform API responding on port 9000
- [ ] Agents registered and healthy
- [ ] Logs flowing to observability backend
- [ ] Alerts configured and tested

### Backup Strategy
- [ ] Daily PostgreSQL backups (S3 / Cloud Storage)
- [ ] Code repository backed up (GitHub)
- [ ] Secrets backed up securely (encrypted vault)
- [ ] Disaster recovery plan tested quarterly

---

## Troubleshooting

### "CORS error in browser"
→ Check `PLATFORM_DASHBOARD_URL` matches your frontend domain
→ Verify `Allow-Origin` headers in response

### "Authentication failed"
→ Verify `PLATFORM_SECRET_KEY` is set and consistent
→ Check JWT tokens are being issued from `/auth/token`
→ Ensure WebSocket includes `?token=...` query param

### "Agents not registering"
→ Check `PLATFORM_URL` env var points to correct API
→ Verify network connectivity between agent and platform
→ Check agent logs for registration errors

### "Rate limit too strict"
→ Adjust `rate_limit_middleware` in `api/middleware.py`
→ Whitelist internal IPs (agent-to-platform calls)

### "WebSocket connection refused"
→ Ensure deployment supports WebSocket upgrades
→ Vercel: requires Functions v2 or higher
→ Check reverse proxy (nginx, CloudFlare) allows WS

---

## Security Hardening Checklist

- [ ] Secret key rotated monthly
- [ ] Database password changed quarterly
- [ ] API keys for LLM services rotated every 90 days
- [ ] Security patches applied within 24 hours
- [ ] Dependency updates reviewed for CVEs
- [ ] Log retention policies configured (30 days min)
- [ ] Access logs reviewed weekly for anomalies
- [ ] Rate limits tuned based on actual traffic
- [ ] Backup integrity tested monthly
- [ ] Disaster recovery runbook updated quarterly

---

## Support

For issues during deployment, check:
1. [Omi README.md](./README.md) — architecture overview
2. [AGENTS.md](./AGENTS.md) — agent capabilities
3. GitHub Issues: https://github.com/addy1997/omi/issues

For security concerns, email: adwaitnaik27@gmail.com
