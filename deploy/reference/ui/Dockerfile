# ---- Build stage ----
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm install

# Copy rest of source
COPY . .

# Build the Next.js app (standalone output)
RUN npm run build


# ---- Runtime stage ----
FROM node:20-slim AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy only the standalone output
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

# Start standalone server
CMD ["node", "server.js"]