# ============================================
# Stage 1: Base with dependencies
# ============================================
FROM node:22-alpine AS base

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm install

# ============================================
# Stage 2: Development (Vite dev server)
# ============================================
FROM base AS development

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ============================================
# Stage 3: Build
# ============================================
FROM base AS build

COPY . .

RUN npm run build

# ============================================
# Stage 4: Production (serve static via nginx)
# ============================================
FROM nginx:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
