#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Restore what ztune changed this boot (I/O scheduler, GPU governor; only nodes that still hold
# the value it wrote), stop zfasd and restore the settings it changed, stop zcored (it ends temporary overrides and
# restores their baselines on SIGTERM), then remove the data. If zfasd cannot restore, its data
# is kept so a manual restore can retry; frequency floors do not survive a reboot anyway.
MODDIR=${0%/*}
DATA=/data/adb/zairenkai
keep_fas=""
if [ -x "$MODDIR/bin/ztune" ]; then
  if ! "$MODDIR/bin/ztune" --state-dir "$DATA/tuning" restore >/dev/null 2>&1; then
    echo "zairenkai: ztune restore failed; the values reset at the next reboot" >>/cache/zairenkai-uninstall.log 2>/dev/null
  fi
fi
if [ -x "$MODDIR/bin/zfasd" ]; then
  for pid in $(pidof zfasd); do kill -TERM "$pid" 2>/dev/null; done
  sleep 2
  if ! "$MODDIR/bin/zfasd" restore --dir "$DATA/fas"; then
    keep_fas=1
    echo "zairenkai: zfasd restore failed; $DATA/fas kept" >>/cache/zairenkai-uninstall.log 2>/dev/null
  fi
fi
for pid in $(pidof zcored); do kill -TERM "$pid" 2>/dev/null; done
i=0
while [ -n "$(pidof zcored)" ] && [ "$i" -lt 30 ]; do sleep 1; i=$((i + 1)); done
if [ -n "$keep_fas" ]; then
  rm -rf "$DATA/core"
else
  rm -rf "$DATA"
fi
