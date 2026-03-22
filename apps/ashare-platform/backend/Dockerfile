FROM python:3.12-slim

WORKDIR /app
ENV ASHARE_PLATFORM_HOME=/app/runtime

RUN sed -i 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g; s|http://deb.debian.org/debian-security|https://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends cron supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ashare-data /app/packages/ashare-data
COPY apps/ashare-platform/backend/pyproject.toml /app/pyproject.toml
COPY apps/ashare-platform/backend/app /app/app
COPY apps/ashare-platform/backend/deploy /app/deploy

RUN python -m pip install --upgrade pip \
    && python -m pip install /app/packages/ashare-data \
    && python -m pip install . \
    && chmod +x /app/deploy/run_scheduled_collect.sh /app/deploy/start.sh \
    && cp /app/deploy/ashare-platform.cron /etc/cron.d/ashare-platform \
    && chmod 0644 /etc/cron.d/ashare-platform \
    && mkdir -p /var/log/supervisor \
    && touch /var/log/ashare-platform-cron.log

EXPOSE 8000

CMD ["/app/deploy/start.sh"]
