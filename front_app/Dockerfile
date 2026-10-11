# Compila front_app (Vite + React) y lo sirve con nginx.
FROM node:20-alpine AS build

WORKDIR /front_app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM nginx:alpine

COPY --from=build /front_app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
