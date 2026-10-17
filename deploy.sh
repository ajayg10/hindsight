#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "   Hindsight Production Deployment       "
echo "========================================="

# 1. Determine public domain
if [ -z "${DOMAIN:-}" ]; then
  echo "Detecting public IP for automatic TLS via sslip.io..."
  PUBLIC_IP=$(curl -s https://api.ipify.org || curl -s https://ifconfig.me || echo "127.0.0.1")
  if [ "$PUBLIC_IP" != "127.0.0.1" ]; then
    export DOMAIN="${PUBLIC_IP}.sslip.io"
  else
    export DOMAIN="localhost"
  fi
fi

echo "Deploying Hindsight with TLS domain: ${DOMAIN}"
echo "Stack: FalkorDB (internal) + Web (FastAPI) + Caddy (TLS 80/443)"

# 2. Build and launch production compose
docker compose -f docker-compose.prod.yml down --remove-orphans || true
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "Waiting for services to become healthy..."
sleep 5

echo ""
echo "========================================="
echo "  Hindsight Production Stack Launched!   "
echo "  Domain: https://${DOMAIN}              "
echo "  Verify: curl -k https://${DOMAIN}/health"
echo "========================================="
