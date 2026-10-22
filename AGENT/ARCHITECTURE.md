# Architecture: Zairenkai-Modules

> Owned by this repository. Document only what inspected code supports, citing file paths.

## Overview

Assembles one Magisk/KernelSU/APatch module, `zairenkai`, from component builds of
Zairenkai-Core (zcored) and Zairenkai-FAS (zfasd).

## Components

| Path | Responsibility |
|---|---|
| `module/module.prop.in` | Module identity; version and description are filled in by the assembler |
| `module/customize.sh` | Install-time checks (arm64, API 29, zcored present), data directories, permissions |
| `module/service.sh` | Boot supervisor for zcored and zfasd (backoff, start limit, FAS restore after exit) |
| `module/action.sh` | Read-only health of each component |
| `module/uninstall.sh` | Stop, restore FAS, remove data |
| `module/webroot/index.html` | KernelSU WebUI for FAS (fixed `zfasd ctl` commands only) |
| `module/META-INF/` | Magisk installer stub (`install_module`) |
| `components.lock.json` | Module version; each component's repository, commit and binary |
| `scripts/assemble.py` | Validates components against the lock and writes a reproducible zip |
| `tests/test_assemble.py` | Assembler tests with stand-in components |

## Data flow

Core and FAS `scripts/build-android.sh` → `dist/<component>/` (binary, licences,
`component.json`) → `scripts/assemble.py` → `dist/zairenkai-v<version>.zip` and `.sha256`.

## Trust boundaries

- The scripts run as root during install, boot and uninstall. They execute only the packaged
  binaries, with fixed arguments.
- The WebUI passes only fixed commands and a profile from a fixed list to `zfasd ctl`.
- CI reads Core and FAS through a read-only GitHub App token; no secret enters the module.

## Generated artifacts

`dist/` from `scripts/assemble.py`; `module.prop` and `components.json` are generated inside
the zip. Edit `module/module.prop.in` and `components.lock.json` instead.
