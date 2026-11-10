# Build : compile le bundle statique (TypeScript + Vite).
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Vite inline les variables VITE_* dans le bundle à la compilation (pas au
# runtime) : doit donc passer par un build arg, pas une env docker-compose
# classique.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Serve : nginx sert les fichiers statiques, pas de serveur Node en prod.
FROM nginx:1.27-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
