# CLAUDE.md: Zairenkai-Modules

Instructions for Claude Code in `ZairenkaiPrjctX/Zairenkai-Modules`. Keep this file under 200 lines;
put detail in `AGENT/`.

@AGENTS.md
@AGENT/PROJECT_CONTEXT.md

## Current state (read first)

This repository packages the **single Zairenkai root module, `zairenkai`** (Magisk, KernelSU,
APatch): `module/` (scripts, installer stub, KernelSU WebUI), `components.lock.json` (Core and
FAS pinned by commit) and `scripts/assemble.py`. Components are built in their own
repositories and only assembled here. Architecture: `AGENT/ARCHITECTURE.md`. Nothing has run on
a device yet (`docs/COMPATIBILITY.md`).

Non-negotiables in this repo:
- One module (`zairenkai`), one data directory (`/data/adb/zairenkai/{core,fas}`). Do not add
  separately installed Zairenkai modules.
- Nothing is tuned at install time; daemons start at boot. FAS starts switched off on a first
  install (`module/defaults/fas-config.toml`) until the user enables it. No boot-image,
  partition or persistent kernel change, ever, from these scripts.
- A component enters the zip only through `assemble.py`, at the commit the lock pins, with
  every file matching its `component.json`. Never commit binaries.
- Uninstall restores what FAS changed before deleting its data.

## Commands

| Purpose | Command | Status |
|---|---|---|
| Assemble | `python3 scripts/assemble.py --component <core dist> --component <fas dist>` | Verified. Evidence: stand-in components (`tests/test_assemble.py`) and the real arm64 components of Core CI run 39701977860 / FAS CI run 39701982927, 2026-10-22. The CI `module` job has not run yet (CI GitHub App not configured here) |
| Test | `python3 -m unittest discover -s tests -v` | Verified. Evidence: 12 passed, 2026-10-22 |
| Shell lint | `shellcheck -s sh module/*.sh module/META-INF/com/google/android/update-binary` | Verified. Evidence: clean, 2026-10-22 |
| Workflow lint | `actionlint .github/workflows/ci.yml` | Verified. Evidence: clean (1.7.7), 2026-10-22 |
| Validate agent foundation | `python3 <path-to-.github>/agent-foundation/scripts/validate_agent_setup.py .` | Configured |

Only list commands that exist in this repository. Never invent one.

## Working rules

- Inspect the relevant code before editing it. Preserve unrelated and uncommitted changes.
- Generated files are edited at their source, then regenerated. Managed foundation files
  (listed in `AGENT/.foundation-manifest.json`) are edited in `ZairenkaiPrjctX/.github`, not here.
- Destructive or outward-facing actions (deleting data, force-push, history rewrites,
  publishing releases, deploying, flashing devices) need explicit human approval each time.
- Do not claim a build, test, or signature succeeded without showing the output.

## Git

- Work on a topic branch; open **draft** pull requests; never merge or approve.
- Commits must be cryptographically signed. If signing fails, stop and report the error.
  Trailer format and verification: `AGENT/policies/git-and-commit-signing.md`.

## Where things are

- `AGENT/README.md`: index of the agent library (prompts, policies, playbooks, templates).
- `.claude/skills/`: run `/repo-audit`, `/implement-feature`, `/bug-fix`, `/test-and-verify`,
  `/security-review`, `/release-readiness`.
- `.claude/rules/`: path-scoped rules, loaded automatically.
