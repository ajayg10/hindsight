# Production Deployment Guide: Hindsight

This guide walks through deploying **Hindsight** to a standalone Ubuntu VPS with automated Let's Encrypt TLS via Caddy, production container orchestration, and multi-tenant copy-on-write isolation.

---

## 1. VPS Provisioning & Prerequisites

Deploy on any standard cloud provider offering Ubuntu (22.04 LTS or 24.04 LTS) with at least **2 GB RAM** and 1 vCPU (~$6–$12/month):
- **DigitalOcean**: Basic Droplet (2 GB RAM, 1 vCPU, 50 GB SSD)
- **Hetzner Cloud**: CX22 (4 GB RAM, 2 vCPU, 40 GB SSD, ~$4/mo)
- **AWS Lightsail**: 2 GB RAM, 1 vCPU instance
- **Vultr / Linode**: Standard 2 GB compute instance

### Firewall / Security Group Settings
Ensure the following ports are open in your provider's firewall:
| Port | Protocol | Purpose | Visibility |
| :--- | :--- | :--- | :--- |
| **22** | TCP | SSH Administration | Public (or restricted to your IP) |
| **80** | TCP | HTTP (ACME challenge & HTTP->HTTPS redirect) | Public |
| **443** | TCP | HTTPS (Web UI, SSE Stream, Public MCP) | Public |
| **6379** | TCP | FalkorDB Graph Engine | **BLOCKED (Internal Only)** |

> [!CAUTION]
> **Port 6379 (FalkorDB) must NEVER be exposed publicly.** The production compose file binds FalkorDB exclusively to the private Docker bridge network (`expose: ["6379"]`, no host port mapping).

---

## 2. Server Setup & Docker Installation

SSH into your fresh Ubuntu VPS:

```bash
ssh root@<your-vps-ip>
```

Install Docker Engine and Docker Compose v2:

```bash
# Update package index and install certificates
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker packages
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker compose version
```

---

## 3. Clone Repository & Launch

Clone the repository and run the production deployment script:

```bash
# Clone Hindsight repository
git clone https://github.com/ajayg10/hindsight.git
cd hindsight

# Make deploy script executable
chmod +x deploy.sh

# Run deployment using sslip.io wildcard DNS (replaces with your VPS public IP)
./deploy.sh <your-vps-ip>.sslip.io
```

The script will:
1. Validate system prerequisites (`docker`, `docker compose`).
2. Generate production configuration with `Caddyfile` configured for your domain.
3. Build the backend image with production dependencies.
4. Launch `falkordb`, `web` (FastAPI backend), and `caddy` (reverse proxy + auto-TLS).
5. Seed `t:parcelo` to **2,846 nodes, 6,933 edges** with all four golden invariants intact.
6. Verify local container health checks.

---

## 4. TLS Certificate Fallback Options

If Let's Encrypt rate-limiting occurs on shared wildcard domains like `sslip.io`, use one of the following two tested fallback options:

### Option A: Free Subdomain via DuckDNS (Recommended)
1. Visit [DuckDNS.org](https://www.duckdns.org/) and log in.
2. Create a free subdomain pointing to your VPS public IP (e.g., `parcelo-ops.duckdns.org`).
3. Re-run deploy with your DuckDNS domain:
   ```bash
   ./deploy.sh parcelo-ops.duckdns.org
   ```
4. Caddy will issue a dedicated, trusted Let's Encrypt certificate in under 10 seconds.

### Option B: Cloudflare Quick Tunnel (Zero-Configuration Fallback)
If you do not have a custom domain and need instant, trusted HTTPS:
```bash
# 1. Download and install cloudflared
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb

# 2. Launch an instant tunnel pointing to Caddy port 80
cloudflared tunnel --url http://localhost:80
```
Cloudflare outputs a public URL: `https://<random-id>.trycloudflare.com`. This provides instant SSL/TLS termination with no DNS configuration required.

---

## 5. Post-Deploy Verification Checklist

Run these five checks before recording the submission video or sharing the URL:

- [ ] **1. Port 6379 Accessibility Audit**:
  From your **local laptop terminal**, verify FalkorDB cannot be reached across the internet:
  ```bash
  nc -zv -w 3 <your-vps-ip> 6379
  # Expected: Connection timed out or Connection refused
  ```
- [ ] **2. Mobile Device Verification**:
  Open `https://<your-domain>` on your mobile smartphone browser (iOS Safari or Android Chrome):
  - Confirm dark Cyberpunk layout renders cleanly.
  - Confirm graph viewport scales correctly.
  - Verify SSE streaming keeps connection open (keepalive ping every 15s).
- [ ] **3. Two-Window Incognito Isolation Test**:
  Open two separate incognito browser windows side-by-side:
  - **Window 1 (Session Alpha)**: Click **Trigger Alert Storm**. Confirm Sentinel, Investigator-A, and Investigator-B execute and await operator approval.
  - **Window 2 (Session Beta)**: Click **Reset Session** or run concurrency race.
  - **Assertion**: Confirm that Reset or Approve in Window 2 **does NOT** clear or affect Window 1's live storm state.
- [ ] **4. Automated Session Isolation Harness**:
  Run the automated headless test inside the VPS container:
  ```bash
  docker compose -f docker-compose.prod.yml exec web python scripts/test_two_session_isolation.py
  # Expected: ALL TWO-SESSION CONCURRENT ISOLATION ASSERTIONS PASSED!
  ```
- [ ] **5. Read-Only Public MCP Audit**:
  Confirm that the public MCP interface is strictly read-only:
  ```bash
  curl -s https://<your-domain>/mcp/tools | jq .
  # Expected: 10 read-only tools, "mode": "read-only", "persist_answer": false
  ```
  Attempting to persist an answer via `/mcp/answer` returns `HTTP 403 Forbidden: Public MCP endpoint is read-only`.
