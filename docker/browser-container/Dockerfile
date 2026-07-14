# omp browser-container: resident, single-user browser automation container.
# Bundles Chromium + Xvfb + openbox + dual x11vnc (viewonly/interactive) + noVNC
# + the indexed automation engine exposing REST (9222 CDP internal, 8080 REST)
# and MCP (9223).
#
# Multi-arch by design: debian's chromium ships native amd64 AND arm64 debs, so
# the same Dockerfile builds natively on Linux/amd64 (docker) and on Apple
# Silicon via apple/container — no Rosetta, no google-chrome (amd64-only, and
# dl.google.com is unreliable from CN networks).
#
#   docker build -f docker/browser-container/Dockerfile \
#     -t omp-browser-container:local docker/browser-container

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Shanghai \
    DISPLAY=:1 \
    HOME=/root \
    XDG_RUNTIME_DIR=/tmp/runtime-root \
    PYTHONUNBUFFERED=1 \
    CDP_HOST=127.0.0.1 \
    CDP_PORT=9222

RUN sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
        xvfb x11vnc openbox dbus dbus-x11 \
        novnc websockify \
        python3 python3-venv python3-pip \
        fonts-liberation fonts-noto-cjk \
        supervisor procps net-tools \
        chromium \
    && rm -rf /var/lib/apt/lists/*

# Application: engine + REST + MCP (installed as the `app` package).
COPY pyproject.toml /opt/omp-browser/pkg/pyproject.toml
COPY app /opt/omp-browser/pkg/app
RUN python3 -m venv /opt/omp-browser/venv \
    && /opt/omp-browser/venv/bin/pip install --no-cache-dir \
        -i https://pypi.tuna.tsinghua.edu.cn/simple /opt/omp-browser/pkg

COPY supervisord.conf /etc/supervisor/conf.d/omp-browser.conf
COPY entrypoint.sh /entrypoint.sh
COPY chrome-launch.sh /usr/local/bin/chrome-launch.sh
RUN chmod +x /entrypoint.sh /usr/local/bin/chrome-launch.sh

# REST 8080, MCP 9223, noVNC viewonly 6080, noVNC interactive 6081.
EXPOSE 8080 9223 6080 6081

ENTRYPOINT ["/entrypoint.sh"]
