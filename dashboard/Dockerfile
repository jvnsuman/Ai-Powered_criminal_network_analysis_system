# Builds the dashboard as a static bundle and serves it via nginx,
# which also reverse-proxies /api to the backend `api` service (see
# nginx.conf) so the production build never needs Vite's dev-only proxy.
FROM node:20-slim AS build

WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 4173
