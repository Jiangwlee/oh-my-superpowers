#!/usr/bin/env bash
set -euo pipefail

# X runtime + dbus dirs.
mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root
mkdir -p /var/run/dbus /var/log/omp-browser

# A machine-id must exist before Chrome/dbus start. The image ships none, and an
# empty /etc/machine-id makes Chrome read the profile lock as "from another
# machine" and refuse to launch. Generate a stable id for both the system and
# dbus locations (idempotent: --ensure only writes when the file is missing).
dbus-uuidgen --ensure=/etc/machine-id
dbus-uuidgen --ensure  # /var/lib/dbus/machine-id

# Login state lives on the mounted volume (Chrome profile).
mkdir -p /data/profile

# The profile is a persistent named volume, so Chrome's Singleton* lock files
# survive `docker compose down`. They bind to the previous container's hostname;
# on recreate the new hostname no longer matches and Chrome deadlocks on startup.
# These are pure single-instance locks (not login state — cookies/storage are
# separate files), so clearing stale ones at boot is safe: no Chrome is running
# yet (supervisord starts it after this entrypoint).
rm -f /data/profile/Singleton*

# Downloads land here (tmpfs, transient). mindora fetches by range then DELETEs;
# nothing here is a durable SoT (ADR 0056). Chrome is pointed at it via
# Browser.setDownloadBehavior on startup, not a launch flag.
mkdir -p /data/downloads

# The copied config is a complete supervisord config, not a conf.d snippet.
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/omp-browser.conf
