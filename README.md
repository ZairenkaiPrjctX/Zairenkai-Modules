# Zairenkai-Modules

The single Zairenkai root module, **`zairenkai`**, for Magisk, KernelSU and APatch.

One install gives one module directory and one data directory:

| Path | Content |
|---|---|
| `/data/adb/modules/zairenkai/` | `bin/zcored`, `bin/zfasd`, `bin/ztune`, module scripts, `components.json`, licences, `source/zairenkai-tuning/` |
| `/data/adb/zairenkai/core/` | zcored: `zcored.sock`, `config.toml`, audit log, AFID catalog |
| `/data/adb/zairenkai/fas/` | zfasd: `zfasd.sock`, `config.toml`, restore file |
| `/data/adb/zairenkai/tuning/` | ztune: restore journal (boot-scoped) and lock |

This repository owns the module: its scripts (`module/`), the lock that pins each component
(`components.lock.json`) and the assembler (`scripts/assemble.py`). The components are built in
their own repositories and only packaged here:

| Component | Repository | Built by | In the module |
|---|---|---|---|
| zcored | Zairenkai-Core | `scripts/build-android.sh` → `dist/zairenkai-core/` | `bin/zcored` |
| zfasd | Zairenkai-FAS | `scripts/build-android.sh` → `dist/zairenkai-fas/` | `bin/zfasd` |
| ztune (GPL-3.0) | Zairenkai-Tuning | `scripts/build-android.sh` → `dist/zairenkai-tuning/` (binary + Corresponding Source) | `bin/ztune`, `source/zairenkai-tuning/*.tar.gz`, `licenses/zairenkai-tuning/` |

The Zairenkai app (Zairenkai-App) installs the module through the root manager's own
installer; zart and zthermal are app libraries and are not part of the module.

## What the module does

- **Install** (`customize.sh`): refuses non-arm64 devices, API < 29, and a package whose files
  do not match its `SHA256SUMS` or that carries an unlisted file; creates
  `/data/adb/zairenkai/{core,fas,tuning}` (root, 0700, never through a symlink); keeps existing
  configuration; warns when the earlier separate `zairenkai_core` / `zairenkai_fas` modules are
  installed. The installer prints five numbered steps.
  Nothing is tuned at install time. On a first install FAS gets a configuration with
  `enabled = false` (`defaults/fas-config.toml`): zfasd runs but boosts nothing until the user
  enables it from the app or the WebUI, which saves the choice.
- **Boot** (`service.sh`): checks the module's files against `SHA256SUMS` and starts nothing
  when one changed (`integrity.log`); after `sys.boot_completed`, supervises zcored and zfasd,
  each with backoff (5 s to 300 s) and a start limit (5 starts in 10 minutes, then
  `<data>/failed`). After any zfasd exit it runs `zfasd restore`. The root manager shows the
  live state in the module description ("Running: zcored, zfasd | files verified",
  "Blocked: …").
- **Action button** (`action.sh`): read-only file check and health of each component
  (`ztune capabilities` for Tuning). `verify.sh` runs the file check on its own.
- **ztune** is not a daemon: nothing runs it at install or boot. zcored runs it when a tuning
  request (I/O scheduler, GPU governor) is allowed by Core's policy, or a person runs it from a
  root shell. Its GPU table tool never flashes anything.
- **KernelSU / APatch WebUI** (`webroot/`): status of Core, FAS, the files and the components,
  live FAS telemetry, Core's active changes, logs; FAS on/off and profile **through Core** (dry
  run, Core's decision shown, then confirm), directly through `zfasd ctl` only when Core does not
  answer and after confirmation. Strict Content-Security-Policy, no network, fixed commands.
- **Uninstall** (`uninstall.sh`): runs `ztune restore` (only nodes that still hold the value
  ztune wrote this boot), stops zfasd and restores its settings, stops zcored, then removes
  `/data/adb/zairenkai` (FAS data is kept if its restore fails). Only this module's own
  processes are signalled, and a symlink in place of the data directory is never followed.

Security model and its limits: [docs/SECURITY.md](docs/SECURITY.md).

## Status

Nothing has run on a device. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md). Build and
test: [docs/BUILDING.md](docs/BUILDING.md). Disable, uninstall, recovery:
[docs/RECOVERY.md](docs/RECOVERY.md).

## Licence

This repository (scripts, assembler, docs) is Apache-2.0 ([LICENSE](LICENSE),
[NOTICE](NOTICE)). The module zip is an **aggregate of separate programs**, each under its own
licence, carried under `licenses/<component>/`:

| Program | Licence |
|---|---|
| zcored, zfasd, module scripts | Apache-2.0 |
| ztune | GPL-3.0-only; its Corresponding Source is in the zip (`source/zairenkai-tuning/`), with build steps in `licenses/zairenkai-tuning/SOURCE.md` |

ztune runs as a separate process; zcored only reads its JSON output (Zairenkai-Tuning
`docs/LICENSING.md`). `assemble.py` refuses a GPL component that does not ship its source.
