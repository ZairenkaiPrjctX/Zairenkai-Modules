# Zairenkai system module

One root module for Magisk, KernelSU and APatch that carries the Zairenkai system services:

| Program | What it does | Licence |
|---|---|---|
| `bin/zcored` | Zairenkai-Core: the control plane. Every change goes through its policy, is read back, and is recorded in an audit log | Apache-2.0 |
| `bin/zfasd` | Zairenkai-FAS: frame-aware CPU frequency floors. Installed **switched off**; enable it in the Zairenkai app | Apache-2.0 |
| `bin/ztune` | Zairenkai-Tuning: telemetry; tuning only with a hardware-validated profile (none ships). Run only by Core | GPL-3.0-only, source in `source/zairenkai-tuning/` |

- **Data:** `/data/adb/zairenkai/{core,fas,tuning}` (root only).
- **Nothing is tuned at install.** The daemons start at boot; the root manager shows their state
  in the module description.
- **Integrity:** every file is listed in `SHA256SUMS`. The installer refuses a package that does
  not match, and nothing starts at boot if a binary, script or WebUI file changed. Check by hand:
  `su -c /data/adb/modules/zairenkai/verify.sh`.
- **Updates:** `updateJson` in `module.prop` points at the latest published GitHub release of
  ZairenkaiPrjctX/Zairenkai-Modules, so your root manager offers new versions. The Zairenkai app
  also tells you when a newer module is released.
- **Action button / WebUI:** read-only status; FAS changes go through Core (KernelSU, APatch).
- **Remove:** in the root manager. Uninstall restores what FAS and ztune changed, then deletes
  the data.

Recovery, security and building: https://github.com/ZairenkaiPrjctX/Zairenkai-Modules
