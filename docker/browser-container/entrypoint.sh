#!/usr/bin/env bash
set -euo pipefail

# X runtime + dbus dirs.
mkdir -p /tmp/runtime-root && chmod 700 /tmp/runtime-root
mkdir -p /var/run/dbus /var/log/omp-browser

# A machine-id must exist before Chrome/dbus start. Base images may ship an EMPTY
# /etc/machine-id (0 bytes), and an empty machine-id makes dbus/Chrome refuse to
# launch ("UUID file should contain a hex string of length 32, not length 0").
# `dbus-uuidgen --ensure` only writes when the file is *missing*, so it never
# fixes the empty file — generate explicitly when the id is empty or absent.
if [ ! -s /etc/machine-id ]; then
  dbus-uuidgen > /etc/machine-id
fi
mkdir -p /var/lib/dbus
if [ ! -s /var/lib/dbus/machine-id ]; then
  cp /etc/machine-id /var/lib/dbus/machine-id
fi

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
