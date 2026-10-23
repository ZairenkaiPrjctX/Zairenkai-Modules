#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Late-start service: check the module's files, then supervise zcored and, when the package
# carries it, zfasd. Each daemon has its own loop with exponential backoff (5 s up to 300 s) and
# a start limit (5 starts in 10 minutes), after which its loop gives up and leaves
# <data>/failed instead of restart-looping. The root manager shows the state in the module's
# description.
MODDIR=${0%/*}
umask 077
# shellcheck source=module/common.sh
. "$MODDIR/common.sh" || exit 1
DATA=$ZR_DATA

if ! zr_data_dirs; then
  zr_status "$MODDIR" "Stopped: $DATA is a symlink or cannot be created"
  exit 1
fi
# Nothing runs as root from a module whose files changed since install (a damaged update, a
# replaced binary or script). The problems are listed in integrity.log; reinstalling the
# module from the Zairenkai app clears it.
if ! problems=$(zr_verify "$MODDIR" runtime); then
  { date; printf '%s\n' "$problems"; } >"$DATA/integrity.log"
  zr_status "$MODDIR" "Blocked: files changed since install, see $DATA/integrity.log"
  exit 1
fi
rm -f "$DATA/integrity.log"
zr_status "$MODDIR" "Starting"
# ztune is not a daemon and is not started here: nothing is tuned at boot. Its journal from an
# earlier boot is discarded by ztune itself, never replayed.

until [ "$(getprop sys.boot_completed)" = "1" ]; do sleep 5; done
sleep 5

# supervise <name> <data dir> <command...>
supervise() {
  name=$1 dir=$2
  shift 2
  log="$dir/$name.log"
  rm -f "$dir/failed"
  starts=""
  delay=5
  while [ ! -f "$MODDIR/disable" ] && [ ! -f "$MODDIR/remove" ]; do
    zr_rotate "$log"
    now=$(date +%s)
    recent=""
    count=0
    for t in $starts; do
      if [ $((now - t)) -lt 600 ]; then recent="$recent $t"; count=$((count + 1)); fi
    done
    if [ "$count" -ge 5 ]; then
      echo "service.sh: $name started 5 times within 10 minutes; giving up" >>"$log"
      echo "start limit hit at $now" >"$dir/failed"
      return 1
    fi
    starts="$recent $now"
    "$@" >>"$log" 2>&1
    code=$?
    echo "service.sh: $name exited with $code" >>"$log"
    if [ "$name" = zfasd ]; then
      # Whatever happened, leave nothing boosted.
      "$MODDIR/bin/zfasd" restore --dir "$dir" >>"$log" 2>&1
    fi
    [ "$code" -eq 0 ] && return 0
    [ "$code" -eq 3 ] && return 0 # another instance is running
    sleep "$delay"
    delay=$((delay * 2))
    [ "$delay" -gt 300 ] && delay=300
  done
}

# report: keep the description current ("Running: zcored, zfasd"), rewriting module.prop only
# when the text changes.
report() {
  shown=""
  while [ ! -f "$MODDIR/remove" ]; do
    up="" down=""
    for d in zcored:core zfasd:fas; do
      n=${d%%:*} c=${d#*:}
      [ -x "$MODDIR/bin/$n" ] || continue
      if [ -n "$(zr_own_pids "$n" "$MODDIR/bin/$n")" ]; then
        up="$up${up:+, }$n"
      elif [ -f "$DATA/$c/failed" ]; then
        down="$down${down:+, }$n stopped after repeated crashes ($c/$n.log)"
      else
        down="$down${down:+, }$n restarting"
      fi
    done
    if [ -z "$down" ]; then text="Running: $up | files verified"
    elif [ -z "$up" ]; then text="Not running: $down"
    else text="Running: $up | $down"
    fi
    if [ "$text" != "$shown" ]; then
      zr_status "$MODDIR" "$text"
      shown=$text
    fi
    sleep 30
  done
}

supervise zcored "$DATA/core" "$MODDIR/bin/zcored" run --dir "$DATA/core" &
if [ -x "$MODDIR/bin/zfasd" ]; then
  supervise zfasd "$DATA/fas" "$MODDIR/bin/zfasd" run --dir "$DATA/fas" &
fi
sleep 5
report &
wait
