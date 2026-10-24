#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Manager "Action" button: read-only health of each component and of the module's files.
MODDIR=${0%/*}
# shellcheck source=module/common.sh
. "$MODDIR/common.sh" || exit 1
DATA=$ZR_DATA
echo "== Zairenkai $(sed -n 's/^version=//p' "$MODDIR/module.prop")"
echo
echo "== Files"
"$MODDIR/verify.sh" 2>&1 | head -n 20
echo
echo "== zcored"
"$MODDIR/bin/zcored" ctl --dir "$DATA/core" health 2>&1 | head -c 4000
echo
if [ -x "$MODDIR/bin/zfasd" ]; then
  echo "== zfasd"
  "$MODDIR/bin/zfasd" ctl --dir "$DATA/fas" status 2>&1 | head -c 4000
  echo
fi
if [ -x "$MODDIR/bin/ztune" ]; then
  echo "== ztune (read only)"
  "$MODDIR/bin/ztune" --state-dir "$DATA/tuning" capabilities 2>&1 | head -c 4000
  echo
fi
