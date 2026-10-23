# Architecture: Zairenkai-Modules

> Owned by this repository. Document only what inspected code supports, citing file paths.

## Overview

Assembles one Magisk/KernelSU/APatch module, `zairenkai`, from component builds of
Zairenkai-Core (zcored), Zairenkai-FAS (zfasd) and Zairenkai-Tuning (ztune, GPL-3.0).

## Components

| Path | Responsibility |
|---|---|
| `module/module.prop.in` | Module identity; version and description are filled in by the assembler |
| `module/common.sh` | Shared helpers: integrity check against `SHA256SUMS`, safe data directories, own-process lookup, status line, log rotation |
| `module/customize.sh` | Install-time checks (arm64, API 29, package integrity), data directories, permissions |
| `module/service.sh` | Boot: integrity check, then supervisor for zcored and zfasd (backoff, start limit, FAS restore after exit), status line |
| `module/action.sh` | Read-only file check and health of each component |
| `module/verify.sh` | Read-only file check (WebUI, Action button, root shell) |
| `module/uninstall.sh` | Restore ztune and FAS, stop this module's processes, remove data |
| `module/webroot/` | KernelSU/APatch WebUI: `index.html`, `app.js`, `style.css`, `logo.svg`; changes through Core |
| `module/META-INF/` | Magisk installer stub (`install_module`) |
| `components.lock.json` | Module version; each component's repository, commit and binary |
| `scripts/assemble.py` | Validates components against the lock and writes a reproducible zip |
| `tests/test_assemble.py` | Assembler tests with stand-in components |
| `tests/test_scripts.py` | `common.sh` under the host's POSIX sh, on an assembled module |
| `tests/test_webui.py`, `tests/webui_check.js` | WebUI policy and command checks; builders and parsers on captured output (`tests/fixtures/captured/`) |

## Data flow

Core, FAS and Tuning `scripts/build-android.sh` → `dist/<component>/` (binary, licences,
`component.json`, source for Tuning) → `scripts/assemble.py` → `dist/zairenkai-v<version>.zip`
(with `SHA256SUMS`) and `.sha256`.

## Trust boundaries

- The scripts run as root during install, boot and uninstall. They execute only the packaged
  binaries, with fixed arguments, and only after the files matched `SHA256SUMS`.
- The WebUI runs only constant commands or commands built from allowlists (profiles, on/off, an
  integer lease id); changes go through `zcored ctl submit`. See `docs/SECURITY.md`.
- CI checks out the public component repositories without a token; no secret enters the module.

## Generated artifacts

`dist/` from `scripts/assemble.py`; `module.prop` and `components.json` are generated inside
the zip. Edit `module/module.prop.in` and `components.lock.json` instead.
