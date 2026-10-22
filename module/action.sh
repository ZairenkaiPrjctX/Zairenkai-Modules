#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Manager "Action" button: read-only health of each component.
MODDIR=${0%/*}
DATA=/data/adb/zairenkai
echo "zcored:"
"$MODDIR/bin/zcored" ctl --dir "$DATA/core" health 2>&1 | head -c 4000
echo
if [ -x "$MODDIR/bin/zfasd" ]; then
  echo "zfasd:"
  "$MODDIR/bin/zfasd" ctl --dir "$DATA/fas" status 2>&1 | head -c 4000
  echo
fi
