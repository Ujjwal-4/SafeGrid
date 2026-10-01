#!/bin/bash
cd "$(dirname "$0")"
echo "========================================"
echo " Building & Starting SafeGrid in Docker "
echo "========================================"
docker compose down 2>/dev/null
docker compose up --build -d

echo ""
echo "Checking container status..."
sleep 3
docker compose ps

echo ""
echo "Recent logs:"
docker compose logs --tail=10

echo ""
echo "Opening browser at http://localhost:8080 ..."
xdg-open http://localhost:8080 2>/dev/null || sensible-browser http://localhost:8080 2>/dev/null || google-chrome http://localhost:8080 2>/dev/null || true

echo ""
echo "========================================"
echo " SafeGrid is running at http://localhost:8080"
echo "========================================"
echo "Leave this window open during your demo."
echo "Press [Enter] to exit."
read
