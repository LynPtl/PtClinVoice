# Stage 1: Build the React Application
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency graphs first
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy the rest of the frontend source code
COPY . .

# Build the Vite application for production
RUN npm run build

# Stage 2: Serve the application using Nginx
FROM nginx:alpine

# Copy the custom Nginx configuration which handles SPA routing and API proxying
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the generated static files from the build stage into Nginx's web root
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 for incoming HTTP traffic
EXPOSE 80

# Start Nginx daemon
CMD ["nginx", "-g", "daemon off;"]
