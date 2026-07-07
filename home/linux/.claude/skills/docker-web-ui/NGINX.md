# nginx config: non-root, SPA routing, security headers, API proxy

`nginxinc/nginx-unprivileged` already runs as uid 101 on port 8080 — no `USER`
directive, no `CAP_NET_BIND_SERVICE`. The config below adds the pieces that
aren't automatic: SPA routing, security headers, API reverse proxy, and a tight CSP.

## Full `ops/nginx.conf`

```nginx
server {
    listen       8080;
    server_name  _;

    root  /usr/share/nginx/html;
    index index.html;

    # ── Health endpoint (used by compose healthcheck) ─────────────────────────
    location /health {
        access_log off;
        return 200 'ok';
        add_header Content-Type text/plain;
    }

    # ── Static assets (immutable Vite build artefacts) ────────────────────────
    # Vite hashes asset filenames on build → aggressive caching is safe.
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        try_files $uri =404;
    }

    # ── Runtime config (re-generated at start; short TTL) ─────────────────────
    location /config.js {
        expires -1;
        add_header Cache-Control "no-store";
        try_files $uri =404;
    }

    # ── API proxy (forward /api/* to the backend) ─────────────────────────────
    location /api/ {
        proxy_pass         http://api:8000/;      # "api" = compose service name
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # WebSocket support (if the backend uses WS at /api/)
        proxy_set_header   Upgrade    $http_upgrade;
        proxy_set_header   Connection "upgrade";
    }

    # ── SPA fallback (client-side routing) ────────────────────────────────────
    # Try the exact file, then the exact dir, then fall back to index.html.
    location / {
        try_files $uri $uri/ /index.html;
    }

    # ── Security headers ──────────────────────────────────────────────────────
    # Applied to every response (including the SPA fallback).
    add_header X-Frame-Options          "DENY"                            always;
    add_header X-Content-Type-Options   "nosniff"                         always;
    add_header Referrer-Policy          "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy       "camera=(), microphone=(), geolocation=()" always;

    # Content-Security-Policy — tighten after confirming no violations.
    # 'self' only; no inline scripts or styles. Vite builds clean JS modules.
    # If you use Google Fonts, add https://fonts.googleapis.com to font-src.
    add_header Content-Security-Policy
        "default-src 'self'; \
         script-src  'self'; \
         style-src   'self'; \
         img-src     'self' data:; \
         font-src    'self'; \
         connect-src 'self'; \
         frame-ancestors 'none';"
        always;

    # ── Compression ───────────────────────────────────────────────────────────
    gzip              on;
    gzip_types        text/plain text/css application/javascript application/json
                      image/svg+xml application/wasm;
    gzip_min_length   1024;
    gzip_comp_level   5;
}
```

## CSP and Vite — avoiding inline script exceptions

Vite's default build injects module-preload link tags but does **not** require
`'unsafe-inline'` for scripts. However, watch out for:

- **CSS-in-JS libraries** (e.g. styled-components, Emotion without SSR) inject
  `<style>` tags at runtime → need `'unsafe-inline'` in `style-src` or a nonce.
  Prefer static CSS imports to avoid this.
- **Vite `modulePreload`** injects `<link rel="modulepreload">` — these are not
  scripts, so no CSP exemption needed.
- **React Fast Refresh** (dev only) injects inline scripts — only applies in the
  Vite dev server, not to the nginx prod stage.

To check your CSP before locking it down, set `Content-Security-Policy-Report-Only`
with a `report-uri` endpoint, observe violations, then flip to enforcement.

## Sub-path SPA mounting

When nginx hosts multiple services and your app lives at `/app-path/` instead of
`/`, you need changes in **both** nginx and Vite — missing either one breaks routing.

**nginx** — redirect bare path, serve under prefix, fall back to prefix index:

```nginx
# Redirect /app-path → /app-path/ (browsers need the trailing slash)
location = /app-path {
    return 302 /app-path/;
}

location /app-path/ {
    root  /usr/share/nginx/html;
    index index.html;
    try_files $uri $uri/ /app-path/index.html;
    error_page 404 = /app-path/index.html;
}
```

**`vite.config.ts`** — set `base` to match:

```ts
export default defineConfig({
  base: '/app-path/',   // must match the nginx location prefix, trailing slash required
  // ...
})
```

Without `base`, Vite emits asset paths relative to `/` and the browser fetches
`/assets/index-xxx.js` instead of `/app-path/assets/index-xxx.js` — a silent 404.

**Static assets under the sub-path** — add a separate aggressive-cache location:

```nginx
location /app-path/assets/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
    try_files $uri =404;
}
```

## Vite HMR WebSocket through nginx (dev only, opt-in)

Skip this if your dev setup exposes Vite directly (the recommended approach in
COMPOSE.md). If you add nginx in front of Vite dev for SSL or routing reasons:

```nginx
# Proxy the Vite dev server including its HMR WebSocket.
location / {
    proxy_pass         http://ui:5173;
    proxy_http_version 1.1;
    proxy_set_header   Upgrade    $http_upgrade;
    proxy_set_header   Connection "upgrade";
    proxy_set_header   Host       $host;
}
```

Without the `Upgrade`/`Connection` headers, the WS handshake fails silently and
HMR stops working (the browser falls back to full-page reload).

## Non-root confirmation

```bash
docker inspect --format '{{.Config.User}}' <image>
```

For `nginx-unprivileged` this returns `101`. For a custom nginx image it must
not return empty (which means root). If you see empty, add `USER 101` to the
final stage.

## Security checklist

- [ ] `X-Frame-Options: DENY` present
- [ ] `X-Content-Type-Options: nosniff` present
- [ ] CSP defined (start with `Report-Only`, tighten, then enforce)
- [ ] No `'unsafe-inline'` or `'unsafe-eval'` without a documented reason
- [ ] Proxy headers set correctly (`X-Forwarded-For`, `X-Real-IP`)
- [ ] Container runs as uid 101, not root (`docker inspect` confirms)
- [ ] `/assets/` has long-lived cache only (Vite asset filenames are hashed)
- [ ] `/config.js` has `no-store` (generated at start, must not be CDN-cached)
