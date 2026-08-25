FROM node:22-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends librsvg2-bin fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work

COPY scripts/package.json scripts/package-lock.json ./
RUN npm ci --omit=dev

COPY scripts/export_image.mjs ./
COPY fonts/*.ttf /work/fonts/

WORKDIR /data
ENTRYPOINT ["node", "/work/export_image.mjs"]
