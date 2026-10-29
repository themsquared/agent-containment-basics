# agent-containment-basics

> 📖 **Read the write-up:** [AI Agent Containment: Why a Sandbox Alone Isn't Enough](https://webofmike.com/agent-containment-basics/)

**"Your sheep haven't escaped, you just built too low a fence."**

A [CSO Online piece](https://www.csoonline.com/) that hit 948 points and 620 comments on
[Hacker News](https://news.ycombinator.com/item?id=50091788) in October 2026 argued that
the OpenAI/Hugging Face registry-proxy intrusion and Anthropic's eval-environment review
weren't "agents going rogue" — they were frontier labs skipping containment basics: no
secure sandbox, live internet reachable from eval runs, no egress monitoring, and
credentials sitting in reach of anything that could ask for them.

Commentary is cheap. This repo is four of those failures reproduced on purpose, and the
specific, runnable control that closes each one — not a new idea, just agentgateway and
plain Docker networking applied directly at the boundary CSO's piece describes.

## The four failures, as code

| CSO's failure | This repo's control | Where |
|---|---|---|
| No secure sandbox / live internet reachable | Agent container has **zero network membership** in the network that can reach anything external — not a firewall rule, a Docker network it was never joined to | `docker-compose.isolated.yml` |
| No egress monitoring | [agentgateway](https://agentgateway.dev)'s access log records every request that reaches the listener, matched or not | `config/config.yaml` → `frontendPolicies.accessLog` |
| Ambient credentials | The agent container never holds the registry API key. The gateway injects it, only on the one route allowed to use it | `config/config.yaml` → `transformations.request.add` |
| No default-deny at the perimeter | The gateway has exactly one route. Anything else has nowhere to go — not an allowlist to maintain, an absence of one that didn't need adding | `config/config.yaml` → `binds[].listeners[].routes` |

## The scenario

A toy eval agent has one real job: look up a package on a registry API. Then — modeling
the registry-proxy pattern, where a tool or a config edit gets pointed at a destination
nobody approved — it makes one more request, to a host that was never part of its job, with
whatever credential it's holding.

`agent/eval_runner.py` is **byte-for-byte identical** in both runs. Nothing about the agent
changes. Only its environment and its network membership do.

### Vulnerable: flat network, ambient credential, no gateway

```bash
docker compose -f docker-compose.vulnerable.yml up -d registry-api attacker-target
docker compose -f docker-compose.vulnerable.yml run --rm agent
```

```
[agent] ambient credential present: True
[agent] legit registry lookup: HTTP 200 <- http://registry-api:8091/package
[agent] unapproved pivot attempt: HTTP 200 <- http://attacker-target:8092/exfil
```

The attacker target's own request log proves what landed:

```json
{"path": "/exfil", "api_key": "registry-secret-9f2"}
```

The pivot succeeded, and it carried the real credential, because the agent held it and
had a direct route to send it anywhere.

### Isolated: sandboxed network, no ambient credential, agentgateway in front

```bash
docker compose -f docker-compose.isolated.yml up -d registry-api attacker-target agentgateway
docker compose -f docker-compose.isolated.yml run --rm agent
```

```
[agent] ambient credential present: False
[agent] legit registry lookup: HTTP 200 <- http://agentgateway:8080/package
[agent] unapproved pivot attempt: HTTP 404 <- http://agentgateway:8080/exfil
```

The attacker target's request log never changes — the agent's own network has no path to
it at all, gateway or no gateway. And the gateway's access log shows the rejected attempt
anyway:

```
... route=default/registry-lookup ... http.path=/package ... http.status=200 ...
... error="route not found" reason=NotFound ... http.path=/exfil ... http.status=404 ...
```

That second line is the egress-monitoring gap closed: the request that would have been
invisible on a flat network with no gateway shows up as a structured, queryable log line,
rejected before it went anywhere.

Run both scenarios back to back:

```bash
./run.sh
```

## The config in full

```yaml
# yaml-language-server: $schema=https://agentgateway.dev/schema/config
frontendPolicies:
  accessLog:
    add:
      path: request.path
      status: "string(response.code)"
binds:
- port: 8080
  listeners:
  - protocol: HTTP
    routes:
    - name: registry-lookup
      matches:
      - path:
          pathPrefix: /package
      policies:
        transformations:
          request:
            add:
              x-api-key: "'registry-secret-9f2'"
      backends:
      - host: registry-api:8091
```

Validated against the real [v1.6.0 schema](https://github.com/agentgateway/agentgateway/releases/tag/v1.6.0):

```bash
docker run --rm -v "$PWD/config/config.yaml:/config/config.yaml:ro" \
  cr.agentgateway.dev/agentgateway:v1.6.0 -f /config/config.yaml --validate-only
# Configuration is valid!
```

## What this is and isn't

This is the perimeter half of containment: default-deny egress, no ambient credentials,
an audit trail. It is not a sandbox escape mitigation — a separate, harder case is an
agent that breaks out of its own sandbox boundary entirely (a microVM escape, a side
channel). The claim here is narrower and, CSO's piece argues, more commonly skipped: even
a sandboxed agent needs a perimeter it can't talk its way around, because the sandbox
boundary is one layer, not the only one.

Distinct from this campaign's `rogue-agent-controls` post (pre-incident framing, no red-team
detail) and `wikimedia-rogue-agent-egress` (a single incident, not the general pattern).

## Why this is one file

Every control here is configuration, not code: no custom proxy, no sidecar, no SDK
wrapper. The agent's own code never needed to know about any of it. That's the actual
argument CSO's piece is making about frontier labs' failures — these controls are cheap
enough that "we didn't have time" doesn't hold up.

## Prerequisites

- Docker and Docker Compose.
- No GPU, no cluster, no API keys. Runs entirely on stdlib Python mocks and a public
  agentgateway image.

## License

Apache-2.0. Personal project, not a Solo.io product or support artifact.
