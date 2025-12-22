# Stage 1: Build
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Add custom nginx config if we need SPA routing support (Create nginx.conf if needed)
# For now, default might fail on refresh without try_files.
# Let's create a dynamic config logic or just simple default for MVP.
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
