---
name: docker-web-ui
description: Scaffold and structure a Dockerized frontend web UI — multi-stage builds optimised for build speed, npm cache mounts, non-root nginx serving the production build, live-reload dev mode via Vite dev server with bind-mounts, runtime env-var injection for SPAs, and nginx security headers. Use when setting up Docker for a TypeScript/Vite/React/Vue project, writing a multi-stage node→nginx Dockerfile, wiring a Vite dev container with HMR, configuring nginx for SPA routing and CSP headers, or injecting runtime config into a static build. Partners with the docker-fastapi skill.
---

# Docker + Web UI (node→nginx multi-stage)

A blueprint for packaging a Vite/TypeScript frontend as a Docker service. Optimised
for fast incremental builds in prod and a smooth hot-module-reload dev loop.

## The shape

One Dockerfile, three named stages:

| Stage        | Purpose                                        | Used by       |
|--------------|------------------------------------------------|---------------|
| `node-deps`  | `npm ci` with a cache mount — deps only        | dev container |
| `builder`    | copies source → `npm run build`                | prod image    |
| `prod`       | `nginx-unprivileged` serving `/app/dist`       | prod image    |

Dev uses the `node-deps` stage directly (bind-mounted source, Vite dev server).
Prod builds through `builder` and ships only the compiled artefacts via nginx.

## Core decisions (the load-bearing ones)

1. **Cache-mounted `npm ci`, not `npm install`.** Bind-mount `package.json` and
   `package-lock.json`; cache `/root/.npm`. The dep layer only re-runs when the
   lockfile changes — editing app source never busts it. See **[DOCKERFILE.md](DOCKERFILE.md)**.

2. **`nginx-unprivileged` for prod.** Runs as uid 101, listens on 8080 — no `CAP_NET_BIND_SERVICE`,
   no `USER` tricks needed. Every security default ships out of the box.
   See **[NGINX.md](NGINX.md)**.

3. **Live reload via Vite dev server, not nginx.** In dev, the `node-deps` stage
   is the running image. Source is bind-mounted; `node_modules` is isolated with a
   named volume so the host's `node_modules` can't shadow the container's.
   See **[COMPOSE.md](COMPOSE.md)**.

4. **`VITE_*` vars are baked at build time.** Any value that varies by environment
   cannot be a `VITE_` var unless you build once per env. For config that must vary
   at runtime (API URLs, feature flags), use the **runtime injection pattern**: an
   entrypoint script runs `envsubst` over a `/config.template.js` → `/config.js`
   before nginx starts. See **[DOCKERFILE.md](DOCKERFILE.md)**.

5. **Security headers in nginx, not the app.** CSP, `X-Frame-Options`,
   `X-Content-Type-Options`, `Referrer-Policy` all live in the nginx config.
   A tight CSP avoids inline script/style exceptions: use Vite's `build.modulePreload`
   to control preload injection. See **[NGINX.md](NGINX.md)**.

6. **Dev source mounts in `docker-compose.override.yml` only.** The base compose
   file stays clean so prod never accidentally runs host code. See **[COMPOSE.md](COMPOSE.md)**.

## Don't ship these gaps (the easy-to-miss ones)

- **Anonymous / named volume for `node_modules`** — without it, the host's
  `node_modules` dir (or absence of one) shadows the container's at runtime. (COMPOSE.md)
- **`--host 0.0.0.0` on the Vite dev server** — without it the port is bound to
  the container's loopback and is unreachable from the host. (COMPOSE.md)
- **Vite HMR websocket in nginx** — if you add nginx in front of Vite in dev, you
  *must* proxy the `/_vite/` websocket path too; a missing WS proxy silently breaks HMR. (NGINX.md)
- **`COPY --link`** — makes the `/app/dist` copy content-addressed and parallel;
  a plain `COPY` creates an extra layer and can't share cache across rebuilds. (DOCKERFILE.md)
- **Pin every image tag** — `node:22-bookworm-slim`, `nginxinc/nginx-unprivileged:1.27-bookworm-slim`.
  `:latest` silently busts cache. (DOCKERFILE.md)
- **`.dockerignore` must exclude `node_modules/`, `dist/`, and `.vite/`** — or
  gigabytes ride into the build context every build. (DOCKERFILE.md)
- **Sub-path `base` in Vite** — if nginx serves the app under `/app-path/`, set
  `base: '/app-path/'` in `vite.config.ts` or all asset paths 404. (NGINX.md)
- **ARG-selected nginx config** — bake dev vs prod nginx config into the image at
  build time via `ARG NGINX_CONFIG_DIR`; avoids runtime bind-mount config drift. (DOCKERFILE.md)

## Quick start

1. Copy the Dockerfile pattern → **[DOCKERFILE.md](DOCKERFILE.md)**.
2. Copy the nginx config → **[NGINX.md](NGINX.md)**.
3. Add the compose service + override → **[COMPOSE.md](COMPOSE.md)**.
4. If you need runtime env vars, add the entrypoint + template → **[DOCKERFILE.md](DOCKERFILE.md)** (runtime injection section).
