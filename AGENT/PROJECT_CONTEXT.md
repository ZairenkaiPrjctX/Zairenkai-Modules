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
| Module scripts, installer stub, KernelSU WebUI | `module/` | Verified: shellcheck clean, 2026-10-22. **Unverified** on a device |
| Component lock | `components.lock.json` | Verified: Core `345fc7f` and FAS `1c453db` (merge commits on `dev`, trees identical to the tested PR heads), Tuning `0c226b2` (topic branch: Tuning has no default branch yet), module 0.2.0, 2026-10-23 |
| Assembler | `scripts/assemble.py` | Verified with stand-in components (17 tests, incl. the GPL source requirement), and on real arm64 components built locally with NDK r27d: zip of 26 entries, 2026-10-22 |
| CI | `.github/workflows/ci.yml` | Verified on GitHub. Evidence: run 39827725469 (`298311c`), `module` job and checks green, 2026-10-22; the public components are checked out without a token |
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
