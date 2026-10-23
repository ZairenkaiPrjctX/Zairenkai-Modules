#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Restore what ztune changed this boot (I/O scheduler, GPU governor; only nodes that still hold
# the value it wrote), stop zfasd and restore the settings it changed, stop zcored (it ends
# temporary overrides and restores their baselines on SIGTERM), then remove the data. If zfasd
# cannot restore, its data is kept so a manual restore can retry; frequency floors do not
# survive a reboot anyway. Only processes running this module's binaries are signalled.
MODDIR=${0%/*}
umask 077
# shellcheck source=module/common.sh
. "$MODDIR/common.sh" || exit 1
DATA=$ZR_DATA
LOG=/data/adb/zairenkai-uninstall.log
note() { echo "$(date) zairenkai: $1" >>"$LOG" 2>/dev/null; }

# stop <name>: SIGTERM to this module's <name>, then wait up to 30 s for it to exit.
stop() {
  bin="$MODDIR/bin/$1"
  for pid in $(zr_own_pids "$1" "$bin"); do kill -TERM "$pid" 2>/dev/null; done
  i=0
  while [ -n "$(zr_own_pids "$1" "$bin")" ] && [ "$i" -lt 30 ]; do sleep 1; i=$((i + 1)); done
  [ -z "$(zr_own_pids "$1" "$bin")" ] || note "$1 did not exit within 30 s"
}

if [ -L "$DATA" ]; then
  # Never follow a link here: remove the link only and leave its target alone.
  note "$DATA was a symlink; removed the link only"
  rm -f "$DATA"
  exit 0
fi
keep_fas=""
if [ -x "$MODDIR/bin/ztune" ]; then
  if ! "$MODDIR/bin/ztune" --state-dir "$DATA/tuning" restore >/dev/null 2>&1; then
    note "ztune restore failed; the values reset at the next reboot"
  fi
fi
if [ -x "$MODDIR/bin/zfasd" ]; then
  stop zfasd
  if ! "$MODDIR/bin/zfasd" restore --dir "$DATA/fas"; then
    keep_fas=1
    note "zfasd restore failed; $DATA/fas kept"
  fi
fi
stop zcored
if [ -n "$keep_fas" ]; then
  rm -rf "$DATA/core" "$DATA/tuning"
else
  rm -rf "$DATA"
fi
