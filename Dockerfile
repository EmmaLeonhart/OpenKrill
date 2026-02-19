# krill — OpenClaw pod base image
# Ubuntu 24.04 + Node.js 22 + OpenClaw + Python 3 (for claw.py context archives)

FROM ubuntu:24.04

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    python3 \
    python3-pip \
    ca-certificates \
    gnupg \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 (via NodeSource)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install OpenClaw globally
RUN npm install -g openclaw@latest

# Create openclaw config directory
RUN mkdir -p /root/.openclaw/workspace

# Copy claw.py context archive utility into the image
COPY claw.py /usr/local/bin/claw.py
RUN chmod +x /usr/local/bin/claw.py

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy openclaw.json template — filled at runtime by entrypoint from env vars
COPY config/openclaw.json.tpl /etc/krill/openclaw.json.tpl

# Workspace and context archive volumes
VOLUME ["/root/.openclaw/workspace", "/krill/context"]

# OpenClaw gateway WebSocket port
EXPOSE 18789

ENTRYPOINT ["/entrypoint.sh"]
