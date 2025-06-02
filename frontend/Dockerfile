# FROM node:18-alpine

# WORKDIR /app

# COPY package*.json ./
# RUN npm i pnpm --global
# RUN pnpm install

# COPY . .

# EXPOSE 3000

# CMD ["pnpm", "dev"]

# -------------------------------- 

# FROM node:18-alpine AS builder

# WORKDIR /app

# COPY package*.json pnpm-lock.yaml ./
# RUN npm install -g pnpm
# RUN pnpm install --frozen-lockfile

# COPY . .

# RUN pnpm build

# FROM node:18-alpine AS runner

# WORKDIR /app

# COPY package*.json pnpm-lock.yaml ./
# RUN npm install -g pnpm
# RUN pnpm install --frozen-lockfile --prod

# COPY --from=builder /app/.next ./.next
# COPY --from=builder /app/public ./public
# COPY --from=builder /app/next.config.js ./

# EXPOSE 3000

# CMD ["pnpm", "start"]

FROM node:18-alpine

WORKDIR /app

RUN apk add --no-cache \
    libc6-compat \
    python3 \
    make \
    g++ \
    git


ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_TYPESCRIPT_IGNOREBUILDTYPES=true
ENV CI=true


RUN npm install -g pnpm

COPY package*.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile --silent

COPY . .

RUN pnpm build

EXPOSE 3000

CMD ["pnpm", "start"]