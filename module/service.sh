#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Late-start service: supervise zcored and, when the package carries it, zfasd. Each daemon has
# its own loop with exponential backoff (5 s up to 300 s) and a start limit (5 starts in 10
# minutes), after which its loop gives up and leaves <data>/failed instead of restart-looping.
MODDIR=${0%/*}
DATA=/data/adb/zairenkai
mkdir -p "$DATA/core" "$DATA/fas" && chmod 0700 "$DATA" "$DATA/core" "$DATA/fas"
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
    if [ -f "$log" ] && [ "$(stat -c %s "$log" 2>/dev/null || echo 0)" -gt 524288 ]; then
      mv -f "$log" "$log.1"
    fi
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

supervise zcored "$DATA/core" "$MODDIR/bin/zcored" run --dir "$DATA/core" &
if [ -x "$MODDIR/bin/zfasd" ]; then
  supervise zfasd "$DATA/fas" "$MODDIR/bin/zfasd" run --dir "$DATA/fas" &
fi
wait
