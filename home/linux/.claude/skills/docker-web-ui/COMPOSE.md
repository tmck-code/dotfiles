# docker-compose: dev HMR vs prod nginx

One compose file for every environment. Dev uses the `node-deps` stage with a
bind-mounted source tree (Vite dev server, HMR). Prod uses the `prod` stage (nginx,
immutable built artefacts). The source bind-mount **only** lives in
`docker-compose.override.yml` — it must never appear in the base file.

## The prod UI service

Serves the pre-built static bundle. `nginx-unprivileged` listens on 8080.

```yaml
services:
  ui:
    image: ghcr.io/you/proj-ui:${TAG:-dev}
    build:
      context: .
      dockerfile: ops/Dockerfile
      target: prod
    ports:
      - "${UI_PORT:-3000}:8080"
    environment:
      # Pass runtime config here if using the envsubst injection pattern.
      # These are NOT baked into the JS bundle — they populate /config.js at start.
      API_URL: ${API_URL:-http://localhost:8000}
    healthcheck:
      test: [ "CMD-SHELL", "wget -qO- http://localhost:8080/health || exit 1" ]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits: { memory: 128M }
    profiles: [ dev, prod ]
```

> Add a `/health` location in your nginx config (see NGINX.md) so the healthcheck
> can fire without returning a 404.

## Dev override — source mount + Vite dev server

This file is applied automatically by `docker compose` when present on the
developer's machine. It must not be committed to the prod host.

```yaml
# docker-compose.override.yml  (developer machines only — do not deploy)
services:
  ui:
    # Override the prod stage with the dev stage — no nginx, just node.
    build:
      target: node-deps    # stop before builder/prod; use installed deps only
    command: npm run dev -- --host 0.0.0.0 --port 5173
    ports:
      - "5173:5173"        # Vite dev server (overrides the prod 3000→8080 mapping)
    volumes:
      - .:/app                    # bind-mount source for hot reload
      - node_modules:/app/node_modules   # named volume shadows host node_modules
    environment:
      # Vite uses these at dev-server runtime (not baked)
      VITE_API_URL: ${API_URL:-http://localhost:8000}

volumes:
  node_modules:   # declared here so compose manages the named volume lifecycle
```

### Why the `node_modules` named volume?

Without it, `.:/app` mounts the host directory — which may have no `node_modules`,
or one built for a different OS. The named volume `node_modules:/app/node_modules`
shadows the mounted path at that exact subdirectory, so the container's npm-installed
modules are used, not the host's. Always declare it explicitly; anonymous volumes
(`- /app/node_modules`) work but aren't visible in `docker volume ls` and are harder
to manage.

### HMR websocket — no nginx in dev

Run Vite directly (no nginx service in dev). Vite's HMR transport uses a WebSocket
on the same port as the dev server, so there's nothing to proxy. If you later add
an nginx layer in dev (e.g. for SSL), see NGINX.md for the required `/_vite/` proxy.

## Containerised npm — never run on the host

If the team doesn't require Node installed locally (or you want to enforce a single
Node version), ban `npm` on the host entirely and wrap all npm operations in a
`docker run` against the `node-deps` dev image.

**Build a named dev image from the dep stage:**

```makefile
build/ui-dev:
	docker build \
	    --target node-deps \
	    --tag myapp-ui-dev:latest \
	    --file ops/Dockerfile .
```

**Run any npm command via Makefile wrapper:**

```makefile
# Usage: make npm CMD="install lodash"
npm: build/ui-dev
	docker run --rm \
	    -v "$(PWD)/src:/app/src" \
	    -v /app/node_modules \
	    -w /app/src \
	    myapp-ui-dev:latest \
	    npm $(CMD)
```

The `-v /app/node_modules` anonymous volume shadows the bind-mounted path so the
container's installed modules are used, not whatever (or nothing) is on the host.

**Run tests the same way:**

```makefile
test/ui: build/ui-dev
	docker run --rm \
	    -v "$(PWD)/src:/app/src" \
	    -v /app/node_modules \
	    -w /app/src \
	    myapp-ui-dev:latest \
	    npm test
```

`build/ui-dev` is a prerequisite on every target — it's a near-instant cache hit
when `package-lock.json` hasn't changed, so the overhead is negligible.

## Profiles

Tag services the same way as the fastapi skill:
- `dev`, `prod` — the running stack.
- `test` — CI runner, throwaway mock backends.

```bash
# start dev stack (api + ui + db)
docker compose --env-file ops/deployments/dev.env --profile dev up -d

# check what's actually running before touching it
docker compose --env-file ops/deployments/dev.env --profile dev ps
```

## Pinning image tags

Never use `:latest` on base images — it silently busts cache and breaks reproducibility.
In compose: `nginx-unprivileged:1.27-bookworm-slim`, `node:22-bookworm-slim`.
Pin the full variant, not just the major version.

## Env files

`ops/deployments/{dev,prod,test}.env` supply all `$VAR` references. Keep secrets
out of committed env files. For the UI, the secrets surface is small (usually just
`API_URL`), but if you add auth tokens or signing keys consumed by the entrypoint
script, treat them the same as the fastapi skill: secret files at
`/run/secrets/<name>`, not in the env table.
