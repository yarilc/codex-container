# Image inputs are pinned. Update them only through the maintenance procedure in
# README.md ("Updating pinned image inputs") and record the result in docs/validation.md.
FROM docker.io/library/node:22-bookworm-slim@sha256:4b150b48b4116e2a22f2c39cc27025fbf4f153e2078fd3b14d159fdb5c7279da

ARG CODEX_VERSION=0.167.0
ARG OPENSPEC_VERSION=1.16.0

ENV DEBIAN_FRONTEND=noninteractive \
    CODEX_HOME=/codex-home/.codex \
    HOME=/codex-home

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
        bubblewrap \
        bzip2 \
        ca-certificates \
        coreutils \
        curl \
        diffutils \
        file \
        findutils \
        gawk \
        git \
        grep \
        jq \
        less \
        patch \
        podman \
        procps \
        python3 \
        ripgrep \
        sed \
        tar \
        unzip \
        util-linux \
        xz-utils \
        zip \
    && npm install --global --omit=dev \
        "@fission-ai/openspec@${OPENSPEC_VERSION}" \
        "@openai/codex@${CODEX_VERSION}" \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /codex-home \
    && chmod 1777 /codex-home

WORKDIR /workspace
ENTRYPOINT ["codex"]
