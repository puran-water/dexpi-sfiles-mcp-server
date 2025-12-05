# Proteus Viewer - Server-side Rendering Service
# Uses Paper.js with node-canvas for SVG generation

# =====================
# Build Stage
# =====================
FROM node:20-slim AS builder

# Install canvas build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    python3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package files and install ALL dependencies (including devDependencies for tsc)
COPY package.json package-lock.json* ./
RUN npm install

# Copy all source files (including proteusXmlDrawing folder)
COPY tsconfig.json ./
COPY src/ ./src/

# Build TypeScript
RUN npm run build

# =====================
# Production Stage
# =====================
FROM node:20-slim

# Install canvas runtime dependencies only
RUN apt-get update && apt-get install -y \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libjpeg62-turbo \
    libgif7 \
    librsvg2-2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package.json and install production dependencies only
COPY package.json package-lock.json* ./
RUN npm install --omit=dev

# Copy compiled JavaScript from builder
COPY --from=builder /app/dist ./dist

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Run service
ENV PROTEUS_VIEWER_PORT=8081
CMD ["node", "dist/server.js"]
