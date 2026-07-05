# syntax=docker/dockerfile:1.7
#
# omp browser-container: resident, single-user browser automation container.
# Bundles Chrome + Xvfb + openbox + dual x11vnc (viewonly/interactive) + noVNC
# + the indexed automation engine exposing REST (9222 CDP internal, 8080 REST)
# and MCP (9223).
#
#   docker build -f docker/browser-container/Dockerfile \
#     -t omp-browser-container:local docker/browser-container

FROM ubuntu:24.04

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

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
        xvfb x11vnc openbox dbus-x11 \
        novnc websockify \
        python3 python3-venv python3-pip \
        fonts-liberation fonts-noto-cjk \
        supervisor procps net-tools \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome stable (apt chromium on 24.04 is a snap shim; avoid it).
RUN curl -fsSL https://dl.google.com/linux/linux_signing_key.pub \
        | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] \
        http://dl.google.com/linux/chrome/deb/ stable main" \
        > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Application: engine + REST + MCP (installed as the `app` package).
COPY pyproject.toml /opt/omp-browser/pkg/pyproject.toml
COPY app /opt/omp-browser/pkg/app
RUN python3 -m venv /opt/omp-browser/venv \
    && /opt/omp-browser/venv/bin/pip install --no-cache-dir /opt/omp-browser/pkg

COPY supervisord.conf /etc/supervisor/conf.d/omp-browser.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# REST 8080, MCP 9223, noVNC viewonly 6080, noVNC interactive 6081.
EXPOSE 8080 9223 6080 6081

ENTRYPOINT ["/entrypoint.sh"]
