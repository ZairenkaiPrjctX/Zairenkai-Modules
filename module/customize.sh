#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Install-time checks for the single Zairenkai module (sourced by the Magisk/KernelSU/APatch
# installer, which provides $MODPATH, $ARCH, $API, ui_print, abort and set_perm). Nothing on the
# device is tuned here: the daemons start at boot from service.sh.
umask 077
# shellcheck source=module/common.sh
. "$MODPATH/common.sh" || abort "! The package has no common.sh; it is incomplete"

version=$(sed -n 's/^version=//p' "$MODPATH/module.prop")
ui_print " "
ui_print "  ===================================="
ui_print "    Z A I R E N K A I    $version"
ui_print "    Core  .  FAS  .  Tuning"
ui_print "  ===================================="
ui_print " "

ui_print "[1/5] Device"
[ "$ARCH" = "arm64" ] || abort "! Zairenkai supports arm64 only (found $ARCH)"
[ "$API" -ge 29 ] || abort "! Android 10 (API 29) or newer is required (found API $API)"
ui_print "      arm64, API $API"
for old in zairenkai_core zairenkai_fas; do
  if [ -d "/data/adb/modules/$old" ]; then
    ui_print "!     The separate $old module is installed. Zairenkai replaces it:"
    ui_print "!     remove $old in the root manager before rebooting."
  fi
done

# Every file of the package must match the SHA-256 the build recorded, and no other file may be
# present. A damaged download or a modified zip stops here, before anything is written outside
# the module directory.
ui_print "[2/5] Package integrity"
if ! problems=$(zr_verify "$MODPATH" install); then
  printf '%s\n' "$problems" | head -n 20 | while IFS= read -r p; do ui_print "!     $p"; done
  abort "! The package does not match its SHA256SUMS; nothing was installed"
fi
[ -x "$MODPATH/bin/zcored" ] || abort "! The package has no bin/zcored; it is incomplete"
ui_print "      $(grep -c '' "$MODPATH/SHA256SUMS") files match SHA256SUMS"

ui_print "[3/5] Data in $ZR_DATA"
zr_data_dirs || abort "! $ZR_DATA (or a directory in it) is a symlink or cannot be created"
for c in core fas; do
  [ -f "$ZR_DATA/$c/config.toml" ] && ui_print "      keeping $c/config.toml"
done
# FAS writes cpufreq floors once enabled, so a first install leaves it switched off; the user
# turns it on from the app or the WebUI, which saves the choice here.
if [ -x "$MODPATH/bin/zfasd" ] && [ ! -f "$ZR_DATA/fas/config.toml" ]; then
  cp "$MODPATH/defaults/fas-config.toml" "$ZR_DATA/fas/config.toml"
  chmod 0600 "$ZR_DATA/fas/config.toml"
  ui_print "      FAS installed switched off: enable it in the Zairenkai app"
fi
# ztune (Zairenkai-Tuning, GPL-3.0) keeps its restore journal in tuning/; it never runs at
# install or boot, only when Core or a person asks for a tuning operation.

ui_print "[4/5] Permissions"
set_perm_recursive "$MODPATH" 0 0 0755 0644
for f in "$MODPATH"/bin/*; do set_perm "$f" 0 0 0755; done
for f in service.sh uninstall.sh action.sh verify.sh; do set_perm "$MODPATH/$f" 0 0 0755; done
ui_print "      root-owned; binaries 0755, data 0700"

ui_print "[5/5] Components"
sed -n 's/^ *"\(zairenkai-[a-z]*\)": *{ *"version": *"\([^"]*\)".*/\1 \2/p' "$MODPATH/components.json" | while read -r name ver; do
  ui_print "      $name $ver"
done
if [ -x "$MODPATH/bin/ztune" ]; then
  ui_print "      ztune is GPL-3.0: licence in licenses/zairenkai-tuning/,"
  ui_print "      source in source/zairenkai-tuning/"
fi
ui_print " "
ui_print "- Reboot to start Zairenkai. Nothing was tuned during install."
ui_print "- Check the files at any time: $MODPATH/verify.sh"
