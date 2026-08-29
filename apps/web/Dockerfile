# DocuLens web image.
#
# Build context is `apps/web` itself; the frontend has no dependency on the
# repository root. Multi-stage build keeps the runtime image to the Next.js
# standalone server output plus static assets, not the full node_modules tree.

FROM node:22-bookworm-slim AS build

WORKDIR /code

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /code

COPY --from=build /code/public ./public
COPY --from=build /code/.next/standalone ./
COPY --from=build /code/.next/static ./.next/static

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /code
USER appuser

EXPOSE 3000

CMD ["node", "server.js"]
