#!/usr/bin/env bash
# Runs both scenarios back to back and prints the three proof points:
# whether the pivot reached the attacker target, whether it carried the
# real credential, and what the gateway's own access log recorded.
set -euo pipefail
cd "$(dirname "$0")"

stats() {
  docker compose -f "$1" exec -T "$2" python3 -c \
    "import urllib.request; print(urllib.request.urlopen('http://localhost:$3/stats').read().decode())"
}

echo "=== VULNERABLE: flat network, ambient credential, no gateway ==="
docker compose -f docker-compose.vulnerable.yml up -d registry-api attacker-target
sleep 1
docker compose -f docker-compose.vulnerable.yml run --rm agent
echo "--- attacker-target stats ---"
stats docker-compose.vulnerable.yml attacker-target 8092
docker compose -f docker-compose.vulnerable.yml down -v

echo
echo "=== ISOLATED: sandboxed network, no ambient credential, agentgateway in front ==="
docker compose -f docker-compose.isolated.yml up -d registry-api attacker-target agentgateway
sleep 2
docker compose -f docker-compose.isolated.yml run --rm agent
echo "--- attacker-target stats (should be untouched by the agent) ---"
stats docker-compose.isolated.yml attacker-target 8092
echo "--- agentgateway access log (the audit trail) ---"
docker compose -f docker-compose.isolated.yml logs agentgateway | grep -E "path=\"/package\"|path=\"/exfil\""
docker compose -f docker-compose.isolated.yml down -v
