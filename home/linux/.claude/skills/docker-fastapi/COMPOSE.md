# docker-compose: profiles, env, the app↔web-api split

One compose file for every environment. **Profiles** select which services run;
an **env file** supplies all values. Never invoke naked `docker compose` —
always `--env-file ops/deployments/<env>.env --profile <dev|prod|test>`.

> **Note on the examples below.** Non-secret config travels as `environment:`;
> anything sensitive travels as `secrets:` (file-mounted at `/run/secrets/…`),
> never in the env table. See [SECURITY.md](SECURITY.md) for the full rationale
> and the `*_FILE` reader. Build `platforms:` is intentionally absent — the
> Makefile owns architecture; hardcoding it here forces emulation.

## The internal "system" API (`app`)

Backend/worker traffic only. Runs uvicorn directly, published on an internal port.

```yaml
  app:
    image: ghcr.io/you/proj:dev
    restart: always
    build:
      context: .
      dockerfile: ops/Dockerfile
      target: system-api
    command: [ "uvicorn", "pkg.api.system:app", "--host", "0.0.0.0", "--port", "8000" ]
    ports:
      - $SYSTEM_API_PORT:8000
    environment:                    # non-secret config only
      POSTGRES_DB:   $POSTGRES_DB
      POSTGRES_HOST: $POSTGRES_HOST
      POSTGRES_USER: $POSTGRES_USER
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      TZ: 'Australia/Melbourne'
    secrets: [ postgres_password ]
    depends_on:
      db: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 512M }
    profiles: [ dev, prod ]
```

> The source bind-mount (`$PWD/pkg:/app/pkg`) is **not** here — it lives in a
> dev-only override (see below) so prod runs the baked image, not host code.

## The outward-facing "web" API (`web-api`)

Separate service so frontend volume / rate-limiting doesn't contend with internal
load. Its `__main__` chooses http vs https on `ENV`. TLS material comes in as
secrets, not a bind-mounted dir.

```yaml
  web-api:
    image: ghcr.io/you/proj-web-api:dev
    restart: always
    build:
      context: .
      dockerfile: ops/Dockerfile
      target: web-api
    command: [ "python", "-m", "pkg.api.web" ]   # module path, no sys.path hack
    ports:
      - $WEB_API_PORT:8000
    environment:
      POSTGRES_DB:   $POSTGRES_DB
      POSTGRES_HOST: $POSTGRES_HOST
      POSTGRES_USER: $POSTGRES_USER
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      SECRET_KEY_FILE:        /run/secrets/app_secret_key
      ENV: ${ENV:?set ENV explicitly}    # no silent default; dev→http, prod→https
      TZ:  'Australia/Melbourne'
    secrets: [ postgres_password, app_secret_key, tls_cert, tls_key ]
    depends_on:
      db: { condition: service_healthy }
    deploy:
      resources:
        limits: { memory: 512M }
    profiles: [ dev, prod ]
```

The `ENV` var is the http/https switch: the `web.py` `__main__` block reads it
and passes `ssl_keyfile`/`ssl_certfile` only when `prod`. **No `:-DEV_SECRET_KEY`
fallback** — a missing secret in prod must crash, not boot insecurely. See
SKILL.md and [SECURITY.md](SECURITY.md).

## Profiles

Tag every service with the environments it belongs to:

- `dev`, `prod` — the running stack (`app`, `web-api`, `db`, `ui`, …).
- `test` — the test runner, a throwaway `test-db`, any mock servers.

`--profile dev up` starts only dev-tagged services. The `test` profile is run
ad-hoc via `docker compose --profile test run … test`, not `up`.

## Healthchecks, not just `depends_on`

Plain `depends_on: [db]` waits for the *container to exist*, not for Postgres to
accept connections — so `app` races the DB on cold start. Give `db` a healthcheck
and gate dependents on `condition: service_healthy` (as shown above):

```yaml
  db:
    image: postgres:18-trixie        # pin the tag — never :latest
    restart: always
    healthcheck:
      test: [ "CMD-SHELL", "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB" ]
      interval: 5s
      timeout: 3s
      retries: 10
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets: [ postgres_password ]
    profiles: [ dev, prod ]
```

> **Pin every image** — `postgres:18-trixie`, `nginx:1.27`, `dozzle:v8.x`,
> `pgadmin4:8.x`. A `:latest` tag silently busts cache and breaks reproducibility,
> and admin tools (pgadmin) must never ship default creds into a `prod` profile.

## DRY services with `extends`

Derive near-identical services instead of duplicating:

```yaml
  test-db:
    extends:
      service: db
    volumes:
      - ${DB_DIR:-./dbs/test-db-data}:/var/lib/postgresql/
    profiles: [ test ]
```

## Dev-only source mounts via override

Bind-mounting source for hot reload belongs in `docker-compose.override.yml`,
which Compose auto-applies **only when present** (keep it out of prod hosts). The
base file stays clean so `prod` runs the immutable baked image:

```yaml
# docker-compose.override.yml  (developer machines only)
services:
  app:
    volumes: [ "$PWD/pkg:/app/pkg" ]
  web-api:
    volumes: [ "$PWD/pkg:/app/pkg" ]
```

Putting these mounts in the base file is a real footgun: in prod the container
ignores its baked image and runs whatever happens to be on the host disk.

## Declaring the secrets

File-based secrets are declared once at the top level and referenced per service:

```yaml
secrets:
  postgres_password: { file: ./ops/deployments/secrets/postgres_password }
  app_secret_key:    { file: ./ops/deployments/secrets/app_secret_key }
  tls_cert:          { file: ./ops/security/certs/fullchain.pem }
  tls_key:           { file: ./ops/security/certs/privkey.pem }
```

The `secrets/` dir is gitignored; see [SECURITY.md](SECURITY.md) for generation
and the app-side `*_FILE` reader.

## Env files

`ops/deployments/{dev,prod,test}.env` — each defines ports, DB creds, secrets,
and `ENV`. Compose interpolates `$VAR` / `${VAR:-default}`. Keep real secrets out
of the committed env files (source them from a separate `~/.secrets`, default to
placeholders for dev).

## Safety check before touching containers

Many `make`/compose targets stop and recreate containers. Before running one,
list what's up so you don't clobber a running stack:

```bash
docker compose --env-file ops/deployments/dev.env --profile dev ps
```
