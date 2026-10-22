#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Install-time checks for the single Zairenkai module (sourced by the Magisk/KernelSU/APatch
# installer, which provides $MODPATH, $ARCH, $API, ui_print, abort and set_perm). Nothing on the
# device is tuned here: the daemons start at boot from service.sh.
[ "$ARCH" = "arm64" ] || abort "! Zairenkai supports arm64 only (found $ARCH)"
[ "$API" -ge 29 ] || abort "! Android 10 (API 29) or newer is required (found API $API)"
[ -x "$MODPATH/bin/zcored" ] || abort "! The package has no bin/zcored; it is incomplete"

for old in zairenkai_core zairenkai_fas; do
  if [ -d "/data/adb/modules/$old" ]; then
    ui_print "! The separate $old module is installed. Zairenkai replaces it:"
    ui_print "!   remove $old in the root manager before rebooting."
  fi
done

DATA=/data/adb/zairenkai
mkdir -p "$DATA/core" "$DATA/fas"
chmod 0700 "$DATA" "$DATA/core" "$DATA/fas"
for c in core fas; do
  [ -f "$DATA/$c/config.toml" ] && ui_print "- Keeping existing $DATA/$c/config.toml"
done
# ztune (Zairenkai-Tuning, GPL-3.0) keeps its restore journal here; it never runs at install
# or boot, only when Core or a person asks for a tuning operation.
if [ -x "$MODPATH/bin/ztune" ]; then
  mkdir -p "$DATA/tuning"
  chmod 0700 "$DATA/tuning"
fi
# FAS writes cpufreq floors once enabled, so a first install leaves it switched off; the user
# turns it on from the app or the WebUI (zfasd ctl enable), which saves the choice here.
if [ -x "$MODPATH/bin/zfasd" ] && [ ! -f "$DATA/fas/config.toml" ]; then
  cp "$MODPATH/defaults/fas-config.toml" "$DATA/fas/config.toml"
  chmod 0600 "$DATA/fas/config.toml"
  ui_print "- FAS is installed switched off: enable it in the Zairenkai app when you want it"
fi

set_perm_recursive "$MODPATH" 0 0 0755 0644
for f in "$MODPATH"/bin/*; do set_perm "$f" 0 0 0755; done
for f in service.sh uninstall.sh action.sh; do set_perm "$MODPATH/$f" 0 0 0755; done

ui_print "- Components (components.json):"
sed -n 's/^ *"\(zairenkai-[a-z]*\)": *{ *"version": *"\([^"]*\)".*/    \1 \2/p' "$MODPATH/components.json" | while read -r line; do
  ui_print "  $line"
done
if [ -x "$MODPATH/bin/ztune" ]; then
  ui_print "- ztune is GPL-3.0: licence in licenses/zairenkai-tuning/, source in source/zairenkai-tuning/"
fi
ui_print "- Data: $DATA (core/, fas/, tuning/)"
ui_print "- Read-only report: $MODPATH/bin/zcored discover"
