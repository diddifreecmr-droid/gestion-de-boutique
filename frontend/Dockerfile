# syntax=docker/dockerfile:1
# Image « caddy » de production (T25, specs § 4.7) : build Vite du frontend servi par Caddy,
# qui proxifie aussi /api vers le conteneur `api`. Contexte de build : RACINE du dépôt
# (il faut frontend/ et infra/Caddyfile ; voir /.dockerignore).
#
# Le même build que sur Vercel : VITE_API_BASE=/api (même origine des deux côtés).

FROM node:24.22.3-alpine3.24 AS build
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Version affichée dans l'application (config/version.ts) ; vide :
# <version de package.json>+<date du build>.
ARG APP_VERSION=""
ENV VITE_API_BASE=/api \
    APP_VERSION=${APP_VERSION}
RUN npm run build && test -f dist/index.html && test -f dist/sw.js

FROM caddy:2.11.9-alpine AS runtime
COPY infra/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /build/dist /srv
# Refuse une configuration invalide dès le build (les variables sont factices ici).
RUN API_PUBLIC_HOST=build.invalid ACME_EMAIL=build@example.invalid \
    caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
