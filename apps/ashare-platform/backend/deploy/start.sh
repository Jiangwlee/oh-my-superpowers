#!/usr/bin/env bash
set -euo pipefail

touch /var/log/ashare-platform-cron.log
exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
