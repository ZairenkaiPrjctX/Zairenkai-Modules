#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Read-only integrity check of the installed module against its SHA256SUMS (used by the WebUI,
# the Action button and anyone in a root shell). Exit 0 and one summary line when every file
# matches; otherwise exit 1 and one line per problem.
MODDIR=${0%/*}
# shellcheck source=module/common.sh
. "$MODDIR/common.sh" || exit 2
if zr_verify "$MODDIR" runtime; then
  echo "verified: $(grep -c '' "$MODDIR/SHA256SUMS") files match SHA256SUMS"
else
  exit 1
fi
