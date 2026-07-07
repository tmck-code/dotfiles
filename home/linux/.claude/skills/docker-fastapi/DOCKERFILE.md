# Multi-stage uv Dockerfile

One Dockerfile, many stages. The goal is **fast incremental builds**: the
expensive `uv sync` layer is isolated so it only re-runs when the lockfile
changes, and the shipped runtime image never carries the build toolchain.

## Stage layout

```
base-builder ─┬─ system-api-uv-builder ─┐
              ├─ web-api-uv-builder ─────┤   (each: uv sync --only-group X)
              └─ test-uv-builder ────────┘
                                          │  COPY --link .venv + /python
system-api-os-builder (debian-slim) ──── system-api   ← final runtime
                                         web-api       ← final runtime
                                         test
```

- **`base-builder`** — from the `uv` image. Installs the managed Python and any
  *build-time* system packages (compilers, `-dev` headers).
- **`*-uv-builder`** — one per dependency group. Runs `uv sync --locked
  --only-group <name>`. Purges compilers afterward where the group allows.
- **`*-os-builder`** — from clean `debian:trixie-slim`. Installs only *runtime*
  libs (`libpq5`, `ca-certificates`). This is the base for final stages.
- **final stages** — `COPY --link --from=<uv-builder>` the `.venv` and `/python`,
  add a non-root user, copy app code, set `PATH`.

## The base builder

Pin the `uv` image to a version tag — an unpinned base silently busts cache and
breaks reproducibility.

```dockerfile
FROM ghcr.io/astral-sh/uv:0.9-trixie-slim AS base-builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/python
ENV UV_PYTHON_PREFERENCE=only-managed
RUN uv python install 3.14
WORKDIR /app

# Required so the apt cache mounts below survive apt-get — docker-clean
# otherwise wipes /var/cache/apt after every install.
RUN rm -f /etc/apt/apt.conf.d/docker-clean
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt update && apt install -y --no-install-recommends gcc libc-dev \
    && rm -rf /tmp/* /var/tmp/*
```

## A dependency-group builder

The key layer. Bind-mount the lockfiles (don't `COPY` them — bind mounts don't
create layers), cache `~/.cache/uv`, and sync **only** this service's group.

```dockerfile
FROM base-builder AS web-api-uv-builder
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --only-group web-api
```

Because app code is **not** present in this stage, editing app code never
invalidates the `uv sync` layer.

## A runtime base

```dockerfile
FROM debian:trixie-slim AS system-api-os-builder
RUN rm -f /etc/apt/apt.conf.d/docker-clean
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        libpq5 ca-certificates \
    && rm -rf /tmp/* /var/tmp/*
```

## A final service stage

```dockerfile
FROM system-api-os-builder AS web-api
WORKDIR /app
RUN groupadd --system --gid 999 appuser \
    && useradd --system --gid 999 --uid 999 --create-home appuser

# --link makes COPY content-addressed → faster, cache-friendly across rebuilds.
COPY --link --from=web-api-uv-builder --chown=999:999 /app/.venv /app/.venv
COPY --link --from=web-api-uv-builder --chown=999:999 /python /python
COPY --chown=appuser:appuser ./pkg /app/pkg

ENV PATH="/app/.venv/bin:$PATH"
USER 999          # ← REQUIRED. Without it the chowns are theatre; the
                  #   container runs as root despite all the appuser setup.
```

> **Run as non-root.** Creating `appuser` and `--chown`-ing files does nothing on
> its own — Docker still runs the entrypoint as root until a `USER` directive
> switches it. Every web-facing/internal final stage must end with `USER 999`.
> Only keep root where a runtime genuinely needs it (e.g. system `cron`), and
> prefer an unprivileged scheduler (`supercronic`) so even that stage drops root.

## Why each trick matters

| Trick | Payoff |
|---|---|
| Bind-mount `uv.lock`/`pyproject.toml` | dep layer keyed on lockfile only, not code |
| `--mount=type=cache` for `~/.cache/uv` | wheels reused across builds |
| `--only-group X` per service | each image ships only its own deps |
| Separate uv-builder vs os-builder | compilers/headers never in runtime image |
| `COPY --link` | content-addressed copy, parallel & cache-stable |
| `rm docker-clean` before apt cache mounts | apt cache actually persists |
| Non-root `appuser` (uid/gid 999) | runtime least-privilege |

## Test stage

Mirror the system-api runtime base but sync **all** groups so the full toolchain
and test deps are present:

```dockerfile
FROM base-builder AS test-uv-builder
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --all-groups
```

## `.dockerignore` — guard the build context

The build context is tarred and sent to the daemon on **every** build. Anything
not ignored is shipped — slow, and a leak risk (DB dumps, `.git`, secrets). The
two most-missed entries:

```gitignore
.git
__pycache__/
.venv/
node_modules/

dbs/db-data/          # DB volume — never belongs in an image context
dbs/test-db-data/
.docker-cache/        # ← LOCAL BUILDKIT CACHE. Easy to miss: `.cache/` does
                      #   NOT match `.docker-cache/`. Can be gigabytes.
ops/security/         # certs / keys — keep them out of the context entirely
*.log
*.sql.gz
```

Verify after writing it:

```bash
# Heavy dirs that are NOT excluded will show up here:
du -sh .git .docker-cache dbs/db-data node_modules 2>/dev/null
```
