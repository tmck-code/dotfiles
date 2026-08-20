# Makefile: arch + env passthrough, bake, env-file discipline

The Makefile is the single front door. It (a) detects host architecture and pins
builds to it, (b) always passes the right env file, and (c) drives image builds
through `docker buildx bake` so cache layout is consistent.

## Architecture passthrough

Detect the host arch once; let it be overridden for cross-arch publish.

```makefile
# Detect host arch (amd64/arm64) so build/* pin to the native platform.
# Override with PLATFORM=linux/amd64 (or a comma list for publish).
HOST_ARCH    := $(shell docker version --format '{{.Server.Arch}}')
PLATFORM     ?= linux/$(HOST_ARCH)
PLATFORM_ARG := --set "*.platform=$(PLATFORM)"

PLATFORMS    ?= linux/amd64,linux/arm64   # publish targets fan out to both
```

## Env-file discipline

Every container target threads the chosen env file and profile. `ENV` defaults
to dev; flip with `ENV=prod make <target>`.

```makefile
ENV ?= dev
COMPOSE = docker compose --profile $(ENV) --env-file ops/deployments/$(ENV).env

serve: build/ui
	$(COMPOSE) up -d --remove-orphans app db web-api
	$(COMPOSE) logs -f
	$(COMPOSE) down
```

## Builds via bake

A `docker-bake.hcl` defines one target per image; each gets its **own** local
cache dir (parallel bake exporters race on a shared cache dir).

```makefile
BAKE := docker buildx bake --file docker-bake.hcl
NO_CACHE  ?= ""
CACHE_ARG  = $(if $(filter 1,$(NO_CACHE)),--no-cache,)

build/app:
	IMAGE='$(IMAGE)' TAG='$(TAG)' $(BAKE) $(CACHE_ARG) $(PLATFORM_ARG) app
build/web-api:
	IMAGE='$(IMAGE)' TAG='$(TAG)' $(BAKE) $(CACHE_ARG) $(PLATFORM_ARG) web-api
```

```hcl
# docker-bake.hcl
target "common" { context = "." dockerfile = "ops/Dockerfile" }
target "app" {
  inherits   = ["common"]
  target     = "system-api"
  tags       = ["${IMAGE}:${TAG}"]
  cache-to   = ["type=local,dest=.docker-cache/app,mode=max"]
  cache-from = ["type=local,src=.docker-cache/app"]
  output     = ["type=docker"]
}
target "web-api" {
  inherits   = ["common"]
  target     = "web-api"
  tags       = ["${IMAGE}-web-api:${TAG}"]
  cache-to   = ["type=local,dest=.docker-cache/web-api,mode=max"]
  cache-from = ["type=local,src=.docker-cache/web-api"]
  output     = ["type=docker"]
}
```

> Per-target cache dirs are deliberate: multiple bake targets can't safely share
> one `cache-to=type=local,dest=…` in parallel — the exporters race on
> `ingest/<hash>/` tempfiles and fail.

## Multi-arch publish (two-pass)

Build all arches into cache (no push), confirm, then re-bake with push — the
second pass is a cache hit and only uploads manifests + new layers. Build targets
**sequentially** to avoid parallel-exporter contention on the shared cache dirs.

```makefile
publish/all:
	for tgt in app web-api test; do \
	  $(BAKE) $(CACHE_ARG) --set "$$tgt.platform=$(PLATFORMS)" \
	    --set "$$tgt.output=type=image,push=false" $$tgt || exit 1; \
	done
	@read -r -p "Type 'yes' to push: " c; [ "$$c" = yes ] || exit 1
	for tgt in app web-api test; do \
	  $(BAKE) --set "$$tgt.platform=$(PLATFORMS)" \
	    --set "$$tgt.output=type=registry" $$tgt || exit 1; \
	done
```

## Lockfile maintenance through the image

Keep `uv` off the host — run it in the built image against bind-mounted lockfiles:

```makefile
uv/update:
	docker run --rm \
	  -v $(PWD)/pyproject.toml:/app/pyproject.toml \
	  -v $(PWD)/uv.lock:/app/uv.lock \
	  $(IMAGE):uv bash -c "cd /app && uv sync --all-groups"
```

## Fail-closed preflight for prod secrets

Make container targets depend on a `check-secrets` guard that asserts every
required secret is present **before** prod boots — so a missing secret stops the
deploy instead of silently falling back to a dev default. Check *all* of them,
not just one:

```makefile
REQUIRED_PROD_SECRETS := JWT_SECRET_KEY APP_SECRET_KEY UNSUBSCRIBE_SECRET

check-secrets:
	@if [ "$(ENV)" = "prod" ]; then \
	  for v in $(REQUIRED_PROD_SECRETS); do \
	    test -n "$${!v}" || { echo "$$v must be set for prod (did you source ~/.secrets?)"; exit 1; }; \
	  done; \
	fi

serve: check-secrets build/ui
	$(COMPOSE) up -d --remove-orphans app db web-api
```

Pair this with `ENV: ${ENV:?set ENV explicitly}` in compose and **no**
`:-DEV_SECRET` fallbacks: the only way to run prod is with real secrets supplied.

## Self-documenting help

A `## comment` after each target name + an `awk` `help` target gives `make` with
no args a printed target list — cheap and keeps the Makefile its own docs.
