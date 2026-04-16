FROM node:20-bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 make g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY package.json ./
RUN npm install --production

FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# node:20 already has user 'node' (uid 1000, gid 1000).
# Mount host SSH keys at /home/node/.ssh to match uid.

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY server.js ./
RUN chown -R node:node /app

USER node
EXPOSE 3100
CMD ["node", "server.js"]
