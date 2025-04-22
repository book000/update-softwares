FROM mcr.microsoft.com/devcontainers/base:noble

COPY .devcontainer/apt-packages.txt /tmp/apt-packages.txt

# hadolint ignore=DL3018
RUN apt-get update \
    && xargs -a /tmp/apt-packages.txt apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
