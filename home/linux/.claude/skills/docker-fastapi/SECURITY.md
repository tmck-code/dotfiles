# Security: secrets, non-root, fail-closed

Three things the happy-path scaffold gets wrong by default. Implement all three.

## 1. File-based secrets, never env vars

**The problem with `environment:`.** Anything in the env table leaks: it shows in
`docker inspect`, in `/proc/<pid>/environ` (readable by anything that can see the
process), and is inherited by every child process. The worst form is a service
that materialises the whole env to disk — e.g. a cron container doing
`printenv > /etc/environment` so jobs inherit vars: that writes every secret to a
plaintext file. Don't.

**The fix — Compose file-based secrets.** Declared at the top level, mounted into
the container as read-only files under `/run/secrets/<name>` (tmpfs, not in
`inspect`, not in the env table):

```yaml
secrets:
  postgres_password: { file: ./ops/deployments/secrets/postgres_password }
  app_secret_key:    { file: ./ops/deployments/secrets/app_secret_key }

services:
  web-api:
    secrets: [ postgres_password, app_secret_key ]
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password   # path, not value
      SECRET_KEY_FILE:        /run/secrets/app_secret_key
```

**App-side `*_FILE` reader.** Accept either an inline var (dev convenience) or a
`_FILE` path (the secret), preferring the file. One helper, used everywhere:

```python
import os

def secret(name: str) -> str:
    '''Read NAME, or NAME_FILE's contents if set. File wins.'''
    if path := os.getenv(f'{name}_FILE'):
        with open(path) as fh:
            return fh.read().strip()
    if val := os.getenv(name):
        return val
    raise RuntimeError(f'{name} (or {name}_FILE) is required')

DB_PASSWORD = secret('POSTGRES_PASSWORD')
SECRET_KEY  = secret('SECRET_KEY')
```

**Generate + gitignore the secret files** (never commit real values):

```bash
mkdir -p ops/deployments/secrets
python -c "import secrets; print(secrets.token_urlsafe(32))" \
  > ops/deployments/secrets/app_secret_key
echo 'ops/deployments/secrets/' >> .gitignore
```

Committed `*.env` files hold **non-secret** config and *placeholder* dev values
only. If a real key ever needs to live in env (CI, a platform that injects env),
inject it at runtime from a secret store — don't commit it.

### cron without leaking

If a scheduler container needs secrets, don't dump the env. Either read
`/run/secrets/*` at job start, or use an unprivileged scheduler that inherits the
process env without writing it to disk (e.g. `supercronic`, which also lets the
stage drop root — see below).

## 2. Run as a non-root user

Creating `appuser` and `--chown`-ing files is inert without a `USER` directive —
Docker runs the entrypoint as **root** until one appears. Every final stage that
doesn't strictly need root must end with:

```dockerfile
USER 999
```

`docker inspect --format '{{.Config.User}}' <image>` must print `999`, not empty.
The only legitimate root stages are ones needing privileged runtime (classic
`cron`); prefer an unprivileged scheduler so even those drop root.

## 3. Fail closed in prod

A dev default that boots is a prod default that boots insecurely. Forbidden:

```yaml
SECRET_KEY: ${SECRET_KEY:-DEV_SECRET_KEY}     # ← silently insecure if unset
```

Instead, make absence fatal at three layers:

- **Compose:** `ENV: ${ENV:?set ENV explicitly}` and pass secrets as files (a
  missing file = no mount = the `*_FILE` reader raises).
- **Makefile:** a `check-secrets` preflight that asserts every required prod
  secret is set before bringing the stack up (see MAKEFILE.md).
- **App:** `secret()` raises on a missing required value; the http/https switch
  never falls back to http when `ENV=prod` and certs are absent — let it crash.

## Defence-in-depth (worth adding)

- **Scan images for CVEs**, not just source. Bandit/first-principles checks the
  code; add a `trivy image <tag>` (or grype) step for the built layers.
- **Resource limits** (`deploy.resources.limits`) so a runaway request/scrape
  can't starve the host.
- **Bind admin tools to localhost** and pin them — never expose pgadmin/dozzle on
  a public interface with default creds.
- **Don't bind-mount source in prod** (COMPOSE.md) — it's a tamper surface and
  defeats the immutable image.

## Checklist

- [ ] No secret appears under any `environment:` key (only `*_FILE` paths do)
- [ ] No `printenv > …` / env-to-disk anywhere
- [ ] `secrets/` dir gitignored; committed env files hold placeholders only
- [ ] Every non-cron final stage ends `USER 999`; `inspect` confirms it
- [ ] No `:-DEV_SECRET` style fallbacks; `ENV` has no silent default
- [ ] `check-secrets` guards prod container targets
- [ ] `.dockerignore` excludes `ops/security/`, the build cache, and DB volumes
- [ ] Image CVE scan wired in; prod services have resource limits
