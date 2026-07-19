FROM docker.io/library/node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    CODEX_HOME=/codex-home/.codex \
    HOME=/codex-home

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        bash \
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
        ripgrep \
        sed \
        tar \
        unzip \
        util-linux \
        xz-utils \
        zip \
    && npm install --global --omit=dev @openai/codex \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /root/.npm \
    && mkdir -p /codex-home \
    && chmod 1777 /codex-home

WORKDIR /workspace
ENTRYPOINT ["codex"]
