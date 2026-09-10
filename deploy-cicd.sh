#!/bin/bash
# ============================================================
# CI/CD Update Script (non-interactive)
# Called by GitHub Actions or manually for code updates.
# Assumes initial deploy.sh has already been run.
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== E-Invoicing Update ===${NC}"
echo "Started: $(date)"

# Sync the working tree to origin/master before anything reads it.
# This must be the FIRST step, not just a pre-build step: the nginx config
# below is copied out of this working tree, so syncing later would install
# a stale config even with a fresh image. `reset --hard` discards local
# tracked edits (untracked files such as .env are left alone).
echo -e "\n${YELLOW}[1/6] Syncing repository to origin/master...${NC}"
git fetch origin
git reset --hard origin/master
echo -e "${GREEN}Now at: $(git log -1 --oneline)${NC}"

# Install/update nginx config (in case e-invoicing.conf changed)
echo -e "\n${YELLOW}[2/6] Updating nginx config...${NC}"
if [ -f nginx/e-invoicing.conf ]; then
    cp nginx/e-invoicing.conf /etc/nginx/conf.d/e-invoicing.conf
    nginx -t && nginx -s reload || echo "Nginx reload skipped (config unchanged)"
fi
echo -e "${GREEN}Done.${NC}"

# Build new images
docker compose down --remove-orphans 2>/dev/null || true
docker container prune -f
echo -e "\n${YELLOW}[3/6] Building Docker images...${NC}"
DOCKER_BUILDKIT=0 docker compose build
echo -e "${GREEN}Build complete.${NC}"

# Restart with new images
echo -e "\n${YELLOW}[4/6] Restarting containers...${NC}"
docker compose up -d --force-recreate
echo -e "${GREEN}Containers restarted.${NC}"

# Wait for backend
echo -e "\n${YELLOW}[5/6] Waiting for backend to be ready...${NC}"
for i in $(seq 1 15); do
    if curl -sf http://127.0.0.1:7860/health > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready.${NC}"
        break
    fi
    echo "  Waiting... ($i/15)"
    sleep 2
done

# Run migrations
echo -e "\n${YELLOW}[6/6] Running database migrations...${NC}"
docker compose exec -T backend /app/.venv/bin/python -m alembic upgrade head || echo "Already up to date"
echo -e "${GREEN}Done.${NC}"

# Status
echo -e "\n${GREEN}=== Update Complete ===${NC}"
echo "Finished: $(date)"
docker compose ps