---
name: docker-fastapi
description: Scaffold and structure a Dockerized FastAPI backend with uv-managed dependencies — multi-stage builds optimised for build speed, split internal/external API services, an env-file + profile driven docker-compose, and a Makefile that passes through host architecture and env vars. Use when setting up Docker for a Python/FastAPI project, writing a multi-stage uv Dockerfile, splitting a backend-only service from an outward-facing (http/https) API, designing docker-compose profiles, or wiring a Makefile around docker buildx bake. Also use when optimising an existing setup: shrinking a Python/FastAPI Docker image, reducing image size, speeding up slow Docker builds, improving layer caching, or trimming heavy ML/native dependencies out of the shipped runtime image. Modeled on the TenderAI repo's ops setup.
---

# Docker + FastAPI (uv multi-stage)

A blueprint for packaging a FastAPI backend as a multi-container Docker app using
`uv` for dependency management. Optimised for fast incremental builds and a clean
split between an internal "system" API and an outward-facing "web" API.

## The shape

Two FastAPI services from **one Dockerfile, different stages**:

| Service  | Audience              | How it runs                                              | Exposure |
|----------|-----------------------|---------------------------------------------------------|----------|
| `app`    | backend / workers only | `uvicorn pkg.api.system:app --host 0.0.0.0 --port 8000` | internal port only |
| `web-api`| browsers / frontend    | runs the module directly; picks http (dev) or https (prod) | published + 443 |

Split them so frontend request volume and rate-limiting don't compete with
internal worker load on the same process/DB pool. Both share the same image
base but are **separate compose services and separate build stages** with only
the dependency group each needs.

## Core decisions (the load-bearing ones)

1. **Per-service dependency groups.** Define `[dependency-groups]` in
   `pyproject.toml` (`system-api`, `web-api`, `scraper`, …). Each builder stage
   runs `uv sync --locked --only-group <name>` so an image carries only its deps.
   A `test` stage uses `--all-groups`.

2. **Builder vs runtime base, always separate.** The `*-uv-builder` stages start
   from the heavy `uv` image (compilers, headers). The final runtime stages start
   from clean `debian:trixie-slim` with only runtime libs (e.g. `libpq5`), then
   `COPY --link --from=<builder> /app/.venv` and the managed Python. The toolchain
   never reaches the shipped image.

3. **Cache mounts + bind mounts for the dependency layer.** Mount `uv.lock` and
   `pyproject.toml` as bind mounts and `/root/.cache/uv` as a cache mount, so the
   expensive `uv sync` layer only re-runs when the lockfile changes — not when app
   code changes.

4. **Env-file + profiles drive compose.** Never run naked `docker compose`. Always
   `--env-file <env>.env --profile <dev|prod|test>`. The same compose file serves
   all environments; profiles select which services start.

5. **Native-arch by default, overridable.** The Makefile detects the host arch via
   `docker version` and pins builds to it; publish targets fan out to multi-arch.
   Do **not** also hardcode `build.platforms` in compose — it fights the Makefile
   and forces emulation on the other arch.

6. **Ship least-privilege, fail closed.** Final stages end with `USER 999` — a
   created non-root user is wasted unless `USER` activates it. Secrets are
   file-mounted (`secrets:` → `/run/secrets/…`), never in the `environment:`
   table. Prod has no working dev defaults: a missing secret must crash, not boot
   insecurely. See **[SECURITY.md](SECURITY.md)**.

## Don't ship these gaps (the easy-to-miss ones)

These are the practices people omit; the reference files implement them:

- **`USER 999` in every final stage** — without it, `chown appuser` is theatre and
  containers run as root. (DOCKERFILE.md)
- **File-based secrets, not env vars** — env leaks via `docker inspect` and
  `/proc/<pid>/environ`; never `printenv > /etc/environment`. (SECURITY.md)
- **Bind-mount source in a dev-only `docker-compose.override.yml`** — never in the
  base file, or prod runs host code over the baked image. (COMPOSE.md)
- **`.dockerignore` excludes the local build-cache dir** (e.g. `.docker-cache/`)
  and the DB volume — or gigabytes ride into the context every build. (DOCKERFILE.md)
- **Healthchecks + `depends_on: { condition: service_healthy }`** — plain
  `depends_on` waits for the container, not for Postgres to accept. (COMPOSE.md)
- **Pin every image tag** (no `:latest`, pin the `uv` image too) and set prod
  resource limits. (COMPOSE.md)

## Execution model (coordinate, don't write)

This skill produces several files at once — Dockerfile, `docker-compose.yml`, an
override, a Makefile, `.dockerignore`, and `ops/deployments/*.env`. **The thread
that invokes this skill is a coordinator: it must not write those files itself.**

- After any research/discovery, **delegate the writing to subagents** — one
  `general-purpose` subagent per artifact group is the default split:
  1. **Dockerfile + `.dockerignore`** (DOCKERFILE.md)
  2. **`docker-compose.yml` + override + `ops/deployments/*.env`** (COMPOSE.md)
  3. **Makefile + `docker-bake.hcl`** (MAKEFILE.md)
- Hand each subagent the relevant reference file and the project's concrete facts
  (package name, module paths, dependency groups, ports). The subagents write and
  self-verify; the main thread holds the plan and reviews the returned diffs.
- These groups are independent — spawn them **in parallel** (one message, multiple
  Agent calls), then reconcile.
- The coordinator does NOT do the file writing even though it "already has the
  context." Reviewing diffs and resolving cross-file conflicts is the main thread's
  job; producing the files is the subagents'.

## Quick start

1. Add `[dependency-groups]` to `pyproject.toml`, one per service.
2. Copy the Dockerfile pattern → **[DOCKERFILE.md](DOCKERFILE.md)**.
3. Copy the compose pattern (profiles, env, http/https, the app↔web-api split)
   → **[COMPOSE.md](COMPOSE.md)**.
4. Copy the Makefile pattern (arch/env passthrough, bake, env-file rule)
   → **[MAKEFILE.md](MAKEFILE.md)**.
5. Create `ops/deployments/{dev,prod,test}.env`; reference vars as `$VAR` in compose.

## http vs https in the outward-facing API

The `web-api` entrypoint branches on an `ENV` var instead of needing two images.
Use the fully-qualified module path so there's no `sys.path` hack or CWD coupling:

```python
if __name__ == '__main__':
    common = dict(host='0.0.0.0', port=8000)
    if os.getenv('ENV') == 'prod':
        uvicorn.run('pkg.api.web:app', **common,
                    ssl_keyfile='/run/secrets/tls_key',
                    ssl_certfile='/run/secrets/tls_cert')
    else:  # dev — plain http, hot reload
        uvicorn.run('pkg.api.web:app', **common, reload=True)
```

Certs are bind-mounted (or supplied as secrets) into the container; the prod env
file sets `ENV=prod`. Dev serves plain http behind nginx. **Fail closed:** if
`ENV=prod` but the cert files are missing, let uvicorn raise — never silently fall
back to http. See **[SECURITY.md](SECURITY.md)** for the secrets wiring.
