FROM node:20-alpine AS build
WORKDIR /repo
COPY package.json package-lock.json tsconfig.base.json ./
COPY apps/extension/package.json apps/extension/package.json
COPY apps/dashboard/package.json apps/dashboard/package.json
RUN npm ci
COPY apps/dashboard apps/dashboard
ARG VITE_API_URL=http://127.0.0.1:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm --workspace @fantasy-hud/dashboard run build

FROM nginx:1.27-alpine
COPY --from=build /repo/apps/dashboard/dist /usr/share/nginx/html
EXPOSE 80
