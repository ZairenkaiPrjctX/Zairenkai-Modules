## [0.3.3] - unreleased

### Changed
- Refresh Core, FAS and Tuning pins from their reviewed `dev` branch heads; this module version is a new immutable build candidate.

# Changelog

## [0.3.2] - unreleased

### Fixed
- Update the bundled Core to `377ba450` so its component-path validator accepts Android's
  platform-managed `/data` ownership policy while still requiring the protected `/data/adb`
  tree and executed component binaries to be root-owned and not group/other-writable. This fixes
  a false `PermissionRestricted` result caused by the old Core build on affected Android builds.

### Safety
- Tuning remains fail-closed: I/O scheduler and GPU governor writes still require an exact-device,
  hardware-validated authorization profile. This release does not add an allowlist or bypass SELinux.

Every version of the zairenkai module, newest first. The release workflow publishes the entry of
the version it builds as the release notes (and as `changelog.md`, which root managers show).
The zip carries this file as `docs/CHANGELOG.md`.

## [0.3.1] - 2026-10-27 (published)

### Fixed
- The installer no longer stops with "The package has no bin/zcored; it is incomplete" on
  KernelSU-Next (reported on a device, arm64, API 37). The manager extracts the zip without file
  modes, and the installer tested the exec bit before setting it; it now checks that the file is
  present, then sets the modes. The same test kept FAS's default configuration (switched off)
  from being copied on a first install.

## [0.3.0] - unreleased

### Added
- Root managers offer updates: `module.prop` has `updateJson`, pointing at the latest GitHub
  release (`update.json`, `changelog.md` and the zip are release assets).
- `SHA256SUMS` for every file. The installer refuses a package that does not match it or carries
  an extra file; at boot nothing starts if a binary, script or WebUI file changed
  (`/data/adb/zairenkai/integrity.log`, "Blocked" in the root manager). `verify.sh` checks by hand.
- The module description shows the live state ("Running: zcored, zfasd | files verified").
- A redesigned WebUI (KernelSU, APatch): Core, FAS, files and components at a glance, live FAS
  telemetry, Core's active changes, logs; FAS changes go through Core with a dry run first.
- `docs/README.md` and `docs/CHANGELOG.md` in the zip.

### Changed
- The installer prints five numbered steps.
- Core `345fc7f` and FAS `1c453db` (the `dev` merge commits; same code as 0.2.0's components).

### Security
- Data directories are root-only and never followed through a symlink; uninstall signals only
  this module's processes and logs to `/data/adb` (there is no `/cache` on A/B devices).
- The WebUI has a strict Content-Security-Policy, runs only fixed or allowlisted commands and
  never builds HTML from daemon output.

## [0.2.0] - 2026-10-22

### Added
- ztune (Zairenkai-Tuning, GPL-3.0) with its Corresponding Source.
- One module, `zairenkai`, replacing the separate `zairenkai_core` and `zairenkai_fas` modules.

## [0.1.0] - 2026-10-22

### Added
- First module: zcored and zfasd, FAS installed switched off.
