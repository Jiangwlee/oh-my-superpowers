#!/usr/bin/env bash
set -euo pipefail

# X runtime + dbus dirs.
mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root
mkdir -p /var/run/dbus /var/log/omp-browser

# Login state lives on the mounted volume (Chrome profile).
mkdir -p /data/profile

# The copied config is a complete supervisord config, not a conf.d snippet.
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/omp-browser.conf
