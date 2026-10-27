# Project context: Zairenkai-Modules

> Owned by this repository. Update it whenever verified facts change. Label every statement
> **Verified** (with `Evidence:`), **Unverified**, or **Unknown / Not Configured**.

## Identity

| Field | Value | Status |
|---|---|---|
| Repository | `ZairenkaiPrjctX/Zairenkai-Modules` | Verified. Evidence: GitHub API |
| Visibility | public | Verified. Evidence: `list_repos`, 2026-10-22 |
| Default branch | `dev` | Verified. Evidence: `gh repo list`, 2026-10-22 |
| Purpose | Packages the single `zairenkai` root module from the Core, FAS and Tuning builds | Verified. Evidence: maintainer decision 2026-10-22; `module/`, `scripts/assemble.py` |
| Licence | Apache-2.0 (`LICENSE`, `NOTICE`). The zip is an aggregate: it also carries ztune under GPL-3.0-only with its source | Verified. Evidence: repository tree; `assemble.py`; maintainer decision 2026-10-22 (separate GPL component) |

## Contents

| Area | Location | Status |
|---|---|---|
| Module scripts, installer stub, KernelSU/APatch WebUI | `module/` | Verified on the host: shellcheck clean; `common.sh` (integrity check, status line, own-process lookup, data-directory guard) run under POSIX sh; WebUI builders and parsers run under Node on captured output; WebUI rendered in Chromium with a stand-in `ksu.exec`, 2026-10-23. **Unverified** on a device |
| Component lock | `components.lock.json` | **Proposed, not yet released:** Core `377ba45` (Android component-path validation fix), FAS `1c453db`, Tuning `0c226b2`, module 0.3.2. Requires the Modules CI/release workflow and a post-install device check. |
| Assembler | `scripts/assemble.py` | Verified with stand-in components (18 tests, incl. the GPL source requirement and `SHA256SUMS`), and on real arm64 components built locally with NDK r27d: zip of 26 entries, 2026-10-22. With 0.3.0, a zip from the earlier real arm64 builds (Core `8931cbb`, FAS `99cfb18`, Tuning `0c226b2`, assembled against a scratch lock naming those commits) has 32 entries and `sha256sum -c SHA256SUMS` and `verify.sh` pass on its extracted files, 2026-10-23 |
| CI | `.github/workflows/ci.yml` | The published v0.3.1 Release workflow run 40483942101 succeeded at Modules `a3efff6` (2026-10-27). The proposed v0.3.2 component-lock change must run CI and Release again before publication. |
| Docs | `README.md`, `docs/` | Verified: files present |

## Key facts

- Module id `zairenkai`; data `/data/adb/zairenkai/core` (zcored) and `/data/adb/zairenkai/fas`
  (zfasd). Verified. Evidence: `module/*.sh`; Core `daemon.rs`/`fas.rs` and FAS `daemon.rs`
  defaults at the locked commits.
- The earlier separate modules `zairenkai_core` and `zairenkai_fas` are superseded; the
  installer warns about them and Core reports them. Verified. Evidence: `module/customize.sh`;
  Core `engine.rs` end-to-end test.
- FAS is packaged in the distributed module by the maintainer's decision of 2026-10-22. Its
  hardware validation is still pending (Zairenkai-App `docs/integration/fas-provenance.md`).
- Security (0.3.0): the zip carries `SHA256SUMS`; `customize.sh` aborts on a mismatch or an
  unlisted file, `service.sh` starts nothing when a file changed (`integrity.log`, "Blocked" in the
  manager), uninstall signals only this module's processes and never follows a symlinked data
  directory, and the WebUI has a strict Content-Security-Policy and routes changes through Core.
  `SHA256SUMS` proves integrity, not authenticity (the app's signed catalog does that). Verified
  on the host. Evidence: `tests/test_scripts.py`, `tests/test_webui.py`, `docs/SECURITY.md`,
  2026-10-23. **Unverified** on a device, including whether KernelSU's WebView delivers
  `ksu.exec` results under the page's policy.

- First device evidence (2026-10-23, user screenshot): KernelSU-Next with "Hybrid Mount
  metainstall", arm64, API 37, installing 0.3.0. Steps 1 (device) and 2 (`SHA256SUMS`, busybox
  `sha256sum`) passed; the install then aborted with "The package has no bin/zcored" because
  KernelSU-Next extracts without file modes and `customize.sh` tested `-x` before `set_perm`.
  0.3.1 tests presence instead. Verified on the host: reproduced with files extracted at 0644,
  passing after the fix (`tests/test_scripts.py`). **Unverified** on the device until reinstalled.

- Releases: `module.prop` has `updateJson` and the public v0.3.1 release is published. The
  Release workflow run 40483942101 succeeded on 2026-10-27, building and checking the v0.3.1
  artifact. The v0.3.2 change in this patch is not published or device-tested yet.

## Tuning path diagnosis (2026-10-27)

The user's KernelSU 3.4.1 screenshot shows module v0.3.1 with Core 0.1.0 reporting
`PermissionRestricted` for `tuning.io_scheduler` and `tuning.gpu_governor`. Core's current `dev`
commit `377ba4508321557f378d0188f05ff5c643ee62b4` contains a correction for Android's
platform-managed `/data` ownership validation. The published v0.3.1 module still pins Core
`345fc7f8c9e192c6a5b7d4e4f923f3b2b3cf33fb`; this patch advances that pin and the module to
0.3.2. Tuning writes are still intentionally denied unless an exact-device hardware-validation
profile authorizes them. A successful build does not substitute for a device retest.

## Authoritative sources

| Topic | Source |
|---|---|
| Repository facts | this file |
| Architecture | `AGENT/ARCHITECTURE.md` |
| Build | `docs/BUILDING.md` |
| Recovery | `docs/RECOVERY.md` |
| Compatibility | `docs/COMPATIBILITY.md` |
| Organization standards | `ZairenkaiPrjctX/.github` → `agent-foundation/standards/` |

## Related repositories

- Zairenkai-Core, Zairenkai-FAS and Zairenkai-Tuning (GPL-3.0): components, pinned in
  `components.lock.json`.
- Zairenkai-App: installs this module through the root manager. Verified. Evidence: App
  `integration/system-modules.json`.

## Open questions

- Which device will run the first install?
- Should the module zip be signed here, or only through the app's signed catalog?
