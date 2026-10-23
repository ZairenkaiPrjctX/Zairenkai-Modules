#!/system/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
# Shared helpers for the module scripts (sourced, never run on its own). POSIX sh: the root
# managers run module scripts with their busybox ash, the WebUI with the system shell.

ZR_DATA=/data/adb/zairenkai

# Files the root manager may change or add after install, so the runtime check skips them:
# module.prop (the status in its description), the installer (removed after install) and the
# manager's marker files.
ZR_RUNTIME_SKIP="module.prop customize.sh"

# zr_safe_dir DIR: create DIR owned by root with mode 0700. Fails, without touching anything,
# when DIR is a symlink (a link planted there would redirect logs, sockets or removal).
zr_safe_dir() {
  [ -L "$1" ] && return 1
  mkdir -p "$1" 2>/dev/null || return 1
  [ -L "$1" ] && return 1
  [ -d "$1" ] || return 1
  chown 0:0 "$1" 2>/dev/null
  chmod 0700 "$1"
}

# zr_data_dirs: the data directory and its component directories, or fail.
zr_data_dirs() {
  for zr_dd in "$ZR_DATA" "$ZR_DATA/core" "$ZR_DATA/fas" "$ZR_DATA/tuning"; do
    zr_safe_dir "$zr_dd" || return 1
  done
}

# zr_sha256 FILE: the lowercase hex SHA-256 of FILE.
zr_sha256() {
  sha256sum "$1" 2>/dev/null | cut -d ' ' -f 1
}

# zr_problems DIR MODE: print one line per integrity problem of DIR against DIR/SHA256SUMS.
# MODE "install" checks every listed file and refuses any file the list does not name;
# MODE "runtime" skips what the manager changes ($ZR_RUNTIME_SKIP) and refuses unlisted files
# only where code lives (bin/, webroot/, *.sh).
zr_problems() {
  zr_d=$1 zr_m=$2
  zr_s="$zr_d/SHA256SUMS"
  if ! command -v sha256sum >/dev/null 2>&1; then
    echo "sha256sum is not available"
    return
  fi
  if [ -L "$zr_s" ] || [ ! -f "$zr_s" ]; then
    echo "SHA256SUMS is missing"
    return
  fi
  while IFS= read -r zr_l || [ -n "$zr_l" ]; do
    zr_h=${zr_l%%  *}
    zr_p=${zr_l#*  }
    if [ "$zr_h" = "$zr_l" ] || [ ${#zr_h} -ne 64 ]; then
      echo "SHA256SUMS has a malformed line"
      continue
    fi
    case $zr_h in *[!0-9a-f]*) echo "SHA256SUMS has a malformed line"; continue ;; esac
    case $zr_p in
      '' | /* | .. | ../* | */.. | */../* | *\\*)
        echo "unsafe path in SHA256SUMS: $zr_p"
        continue
        ;;
    esac
    if [ "$zr_m" = runtime ]; then
      case " $ZR_RUNTIME_SKIP " in *" $zr_p "*) continue ;; esac
    fi
    zr_f="$zr_d/$zr_p"
    if [ -L "$zr_f" ] || [ ! -f "$zr_f" ]; then
      echo "missing: $zr_p"
    elif [ "$(zr_sha256 "$zr_f")" != "$zr_h" ]; then
      echo "modified: $zr_p"
    fi
  done <"$zr_s"
  # Files the list does not name. Paths are compared as fixed strings (cut -c 67- drops the hash
  # and its two spaces), so a name is never read as a pattern.
  (cd "$zr_d" && find . \( -type f -o -type l \) 2>/dev/null) | sed 's|^\./||' | while IFS= read -r zr_q; do
    case $zr_q in SHA256SUMS | META-INF/*) continue ;; esac
    if [ "$zr_m" = runtime ]; then
      case $zr_q in bin/* | webroot/* | *.sh) ;; *) continue ;; esac
    fi
    cut -c 67- "$zr_s" | grep -Fxq -- "$zr_q" || echo "unexpected file: $zr_q"
  done
}

# zr_verify DIR MODE: print the problems; succeed only when there are none.
zr_verify() {
  zr_o=$(zr_problems "$1" "$2")
  [ -z "$zr_o" ] && return 0
  printf '%s\n' "$zr_o"
  return 1
}

# zr_own_pids NAME BINARY: pids of NAME whose executable is BINARY. A process that only shares
# the name is never signalled.
zr_own_pids() {
  zr_w=$(readlink -f "$2" 2>/dev/null) || return 0
  for zr_pid in $(pidof "$1" 2>/dev/null); do
    case "$(readlink "/proc/$zr_pid/exe" 2>/dev/null)" in
      "$zr_w" | "$zr_w (deleted)") echo "$zr_pid" ;;
    esac
  done
}

# zr_status MODDIR TEXT: show TEXT in front of the module description in the root manager
# ("[TEXT] description"). Only module.prop's description line changes, written to a temporary
# file and renamed; id, version and versionCode stay as installed.
zr_status() {
  zr_prop="$1/module.prop"
  [ -f "$zr_prop" ] && [ ! -L "$zr_prop" ] || return 0
  zr_t="$zr_prop.tmp"
  rm -f "$zr_t"
  while IFS= read -r zr_l || [ -n "$zr_l" ]; do
    case $zr_l in
      description=*)
        zr_b=${zr_l#description=}
        case $zr_b in '['*'] '*) zr_b=${zr_b#*'] '} ;; esac
        printf 'description=[%s] %s\n' "$2" "$zr_b"
        ;;
      *) printf '%s\n' "$zr_l" ;;
    esac
  done <"$zr_prop" >"$zr_t" && chmod 0644 "$zr_t" && mv -f "$zr_t" "$zr_prop"
  rm -f "$zr_t"
}

# zr_rotate LOG: keep a log under 512 KiB, with one previous generation.
zr_rotate() {
  if [ -f "$1" ] && [ "$(stat -c %s "$1" 2>/dev/null || echo 0)" -gt 524288 ]; then
    mv -f "$1" "$1.1"
  fi
}
