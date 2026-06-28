# Stage 1: Build the Vue application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for better layer caching
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# Stage 2: Serve the application with Nginx (drastically reduces image size)
FROM nginx:alpine

# Copy the custom Nginx configuration for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static files from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
