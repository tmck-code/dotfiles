# Multi-stage Dockerfile for a Vite/TypeScript web UI

One Dockerfile, three stages. The goal is **fast incremental builds**: the
`npm ci` layer is keyed on the lockfile only, so editing source never re-runs it.
The shipped prod image contains only compiled artefacts + nginx — no Node.js, no
source code, no build toolchain.

## Stage layout

```
node-deps (node:22-bookworm-slim)
  └── builder → COPY dist → prod (nginx-unprivileged)
```

The `node-deps` stage doubles as the dev runtime (bind-mounted source, Vite dev server).

## The base dep stage

Pin both the node and slim variant tags. `--ignore-scripts` prevents arbitrary
install scripts from running in the dep layer (run `npm rebuild` separately if a
package needs native compilation).

```dockerfile
FROM node:22-bookworm-slim AS node-deps

WORKDIR /app

# Cache mount: npm's content-addressable store persists across builds.
# Bind mounts: lockfiles are not COPYed — no layer, keyed on file content only.
# Result: this RUN only re-executes when package-lock.json changes.
RUN --mount=type=cache,target=/root/.npm \
    --mount=type=bind,source=package.json,target=package.json \
    --mount=type=bind,source=package-lock.json,target=package-lock.json \
    npm ci --ignore-scripts
```

## The builder stage

Copies source on top of the installed deps and builds. Editing any source file
only invalidates layers from `COPY . .` onward — the expensive `npm ci` is
untouched.

```dockerfile
FROM node-deps AS builder

# Accept build-time VITE_* vars here (they are baked into the JS bundle).
# WARNING: these are NOT runtime vars — they are inlined by Vite at build time.
# See the "Runtime env-var injection" section below for config that must vary.
ARG VITE_APP_VERSION=dev

COPY . .
RUN npm run build
```

## The prod stage

Static artefacts only. `nginx-unprivileged` listens on 8080 as uid 101 — no
`USER` directive needed, no `CAP_NET_BIND_SERVICE`, no privilege tricks.

```dockerfile
FROM nginxinc/nginx-unprivileged:1.27-bookworm-slim AS prod

# --link: content-addressed copy; parallel and cache-stable across rebuilds.
COPY --link --from=builder /app/dist /usr/share/nginx/html
COPY --link ops/nginx.conf /etc/nginx/conf.d/default.conf

# If using runtime config injection (see below), add:
# COPY --link ops/config.template.js /etc/nginx/config.template.js
# COPY --link ops/entrypoint.sh /docker-entrypoint.d/40-inject-config.sh

EXPOSE 8080
```

## Runtime env-var injection (for config that varies by environment)

`VITE_*` variables are **baked in** at `npm run build` — they cannot change at
container startup. If you need, say, the backend API URL to vary between dev and
prod without rebuilding the image, use this pattern instead:

**`ops/config.template.js`** (committed, placeholder values):
```js
// Populated at container start by entrypoint; do not edit manually.
window.__CONFIG__ = {
  apiUrl: '${API_URL}',
  featureFlags: '${FEATURE_FLAGS}',
};
```

**`index.html`** — load it before your app bundle:
```html
<script src="/config.js"></script>
```

**`ops/entrypoint.sh`** — runs before nginx via `/docker-entrypoint.d/`:
```sh
#!/bin/sh
set -e
# Substitute env vars into the config template and serve the result.
envsubst < /etc/nginx/config.template.js > /usr/share/nginx/html/config.js
```

**In the app** — read from `window.__CONFIG__`:
```ts
const config = (window as any).__CONFIG__ ?? {};
export const API_URL: string = config.apiUrl ?? '';
```

**Updated prod stage:**
```dockerfile
FROM nginxinc/nginx-unprivileged:1.27-bookworm-slim AS prod
COPY --link --from=builder /app/dist /usr/share/nginx/html
COPY --link ops/nginx.conf /etc/nginx/conf.d/default.conf
COPY --link ops/config.template.js /etc/nginx/config.template.js
COPY --link ops/entrypoint.sh /docker-entrypoint.d/40-inject-config.sh
RUN chmod +x /docker-entrypoint.d/40-inject-config.sh
EXPOSE 8080
```

## ARG-selected nginx config (dev vs prod without runtime mounts)

Instead of bind-mounting different nginx configs per environment at runtime, bake
the right config into the image at build time via `ARG`. The prod image ships with
prod nginx config built in — no volume mounts, no config drift between hosts.

```dockerfile
FROM nginx:stable AS prod

ARG NGINX_CONFIG_DIR=nginx-dev   # default to dev; override in CI/bake
ADD $NGINX_CONFIG_DIR /etc/nginx/conf.d

COPY --link --from=builder /app/dist /usr/share/nginx/html
```

Layout your config dirs alongside the Dockerfile:

```
ops/
├── Dockerfile
├── nginx-dev/
│   └── default.conf   # HTTP, loose CORS, no SSL
└── nginx/
    └── default.conf   # HTTPS, strict headers, SSL cert paths
```

Pass the arg in compose or bake:

```yaml
# docker-compose.yml
services:
  ui:
    build:
      args:
        NGINX_CONFIG_DIR: ${NGINX_CONFIG_DIR:-nginx-dev}
```

```hcl
# docker-bake.hcl
variable "NGINX_CONFIG_DIR" { default = "nginx-dev" }
target "ui" {
  args = { NGINX_CONFIG_DIR = NGINX_CONFIG_DIR }
}
```

The tradeoff: prod and dev configs bake into separate image layers, so you cannot
swap config without rebuilding. That is intentional — a single image tag always
has a known config baked in, no mount required.

## Why each trick matters

| Trick | Payoff |
|---|---|
| Bind-mount `package-lock.json` | dep layer keyed on lockfile only, not code |
| `--mount=type=cache` for `/root/.npm` | tarballs reused across builds |
| `--ignore-scripts` on `npm ci` | no arbitrary install scripts in the build |
| `node-deps` as the dev runtime | dev and prod share the same dep install path |
| `COPY --link` | content-addressed, parallel, cache-stable |
| `nginx-unprivileged` | non-root + unprivileged port out of the box |
| Builder stage separate from node-deps | source code never in the dep layer |

## `.dockerignore` — guard the build context

The build context is tarred and sent to the daemon on every build. Missing entries
cause gigabytes of noise:

```gitignore
.git
node_modules/       # ← most important: often hundreds of MB
dist/
.vite/
.vite-cache/
coverage/
*.log
.env.local
.env.*.local
ops/secrets/        # keep keys/certs out of the context entirely
```

Verify after writing it:

```bash
# Dirs that are NOT excluded will bloat every build:
du -sh node_modules dist .vite 2>/dev/null
```
