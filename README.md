# Zairenkai-Modules

The single Zairenkai root module, **`zairenkai`**, for Magisk, KernelSU and APatch.

One install gives one module directory and one data directory:

| Path | Content |
|---|---|
| `/data/adb/modules/zairenkai/` | `bin/zcored`, `bin/zfasd`, module scripts, `components.json`, licences |
| `/data/adb/zairenkai/core/` | zcored: `zcored.sock`, `config.toml`, audit log, AFID catalog |
| `/data/adb/zairenkai/fas/` | zfasd: `zfasd.sock`, `config.toml`, restore file |

This repository owns the module: its scripts (`module/`), the lock that pins each component
(`components.lock.json`) and the assembler (`scripts/assemble.py`). The components are built in
their own repositories and only packaged here:

| Component | Repository | Built by | In the module |
|---|---|---|---|
| zcored | Zairenkai-Core | `scripts/build-android.sh` → `dist/zairenkai-core/` | `bin/zcored` |
| zfasd | Zairenkai-FAS | `scripts/build-android.sh` → `dist/zairenkai-fas/` | `bin/zfasd` |

The Zairenkai app (Zairenkai-App) installs the module through the root manager's own
installer; zart and zthermal are app libraries and are not part of the module.

## What the module does

- **Install** (`customize.sh`): refuses non-arm64 devices, API < 29 and a package without
  `bin/zcored`; creates `/data/adb/zairenkai/{core,fas}` (0700); keeps existing configuration;
  warns when the earlier separate `zairenkai_core` / `zairenkai_fas` modules are installed.
  Nothing is tuned at install time. On a first install FAS gets a configuration with
  `enabled = false` (`defaults/fas-config.toml`): zfasd runs but boosts nothing until the user
  enables it from the app or the WebUI, which saves the choice.
- **Boot** (`service.sh`): after `sys.boot_completed`, supervises zcored and zfasd, each with
  backoff (5 s to 300 s) and a start limit (5 starts in 10 minutes, then `<data>/failed`).
  After any zfasd exit it runs `zfasd restore`.
- **Action button** (`action.sh`): read-only health of each component.
- **KernelSU WebUI** (`webroot/`): FAS status and profile, through `zfasd ctl` only.
- **Uninstall** (`uninstall.sh`): stops zfasd and restores its settings, stops zcored, then
  removes `/data/adb/zairenkai` (FAS data is kept if its restore fails).

## Status

Nothing has run on a device. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md). Build and
test: [docs/BUILDING.md](docs/BUILDING.md). Disable, uninstall, recovery:
[docs/RECOVERY.md](docs/RECOVERY.md).

## Licence

Apache-2.0 ([LICENSE](LICENSE), [NOTICE](NOTICE)). The module zip carries each component's
own licence files under `licenses/<component>/`.
