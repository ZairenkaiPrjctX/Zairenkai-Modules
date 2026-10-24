# Releasing the zairenkai module

## What a release is

A GitHub release `v<version>` of this repository with four files:

| Asset | Used by |
|---|---|
| `zairenkai-v<version>.zip` | root managers (update) and people installing by hand |
| `zairenkai-v<version>.zip.sha256` | anyone checking the download |
| `update.json` | Magisk, KernelSU and APatch: `module.prop`'s `updateJson` points at `releases/latest/download/update.json`, so the managers offer the newest **published, non-pre-release** version |
| `changelog.md` | the managers' "changelog" link; the release notes |

The Zairenkai app reads the same release list and tells the user when a newer module is out. It
still installs only the module packaged in its own signed APK (Zairenkai-App
`docs/integration/system-module.md`): a release here reaches the app's installer through an app
update, and reaches root managers directly through `updateJson`.

## Steps (maintainer)

1. Raise `module.version` in `components.lock.json` (MAJOR.MINOR.PATCH; the versionCode is
   MAJOR·10000 + MINOR·100 + PATCH) and add its `CHANGELOG.md` entry. `assemble.py` refuses a
   version without an entry. Merge into `dev`.
2. Run the **Release** workflow on `dev` with **draft_release** checked. The `build` job builds
   Core, FAS and Tuning at the locked commits, assembles, checks every file against
   `SHA256SUMS` like the installer, and checks that `update.json` and `module.prop` agree. The
   `draft` job (the only one with `contents: write`) creates a **draft** release and refuses a
   version that already exists.
3. Review the draft and **publish** it. Until then neither root managers nor the app see it.

## Trust

`updateJson` makes the GitHub repository the source of updates for people who install through a
root manager: whoever can publish a release here can ship a module that runs as root. Keep
release publishing restricted to maintainers, and branch protection on `dev`. Inside the zip,
`SHA256SUMS` protects integrity on the device (`docs/SECURITY.md`); the app's installer
additionally requires its catalog signed by a trusted key.

**Unverified:** the workflow has not run on GitHub yet, and no release exists.
