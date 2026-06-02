# Build stage
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

# Runtime stage
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./

RUN npm ci --only=production

COPY --from=builder /app/dist ./dist
COPY public ./public

EXPOSE 4173

ENV NODE_ENV=production

CMD ["npm", "run", "preview"]
