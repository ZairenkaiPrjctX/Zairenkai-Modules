# Security of the zairenkai module

The module runs as root at install, at boot, from the Action button, from the KernelSU/APatch
WebUI and at uninstall. This page says what each step trusts, what it checks, and what it does
not protect against.

## Trust chain

| Step | Who checks | What it proves |
|---|---|---|
| Build | `scripts/assemble.py` | Each component is the commit `components.lock.json` pins, every file matches its `component.json` SHA-256, nothing undeclared or symlinked is included, a GPL component ships its source. The zip is reproducible. |
| Distribution | Zairenkai-App | The app installs only a zip listed in its **signed** catalog (key in the app's `integration/module-trust.json`): size, whole-file SHA-256, the exact entry set, every entry's SHA-256 and the installer scripts. This is the authenticity check. |
| Install | `customize.sh` | Every extracted file matches `SHA256SUMS`, and no unlisted file is present. Otherwise the install aborts before anything outside the module directory is written. |
| Boot | `service.sh` | The binaries, scripts, WebUI and `components.json` still match `SHA256SUMS`, and no file was added to `bin/`, `webroot/` or as a script. Otherwise no daemon starts; the problems go to `/data/adb/zairenkai/integrity.log` and the root manager shows "Blocked". |
| Any time | `verify.sh`, Action button, WebUI | The same check as at boot, read only. |

`SHA256SUMS` sits inside the zip and the module directory, so it proves **integrity, not
authenticity**: it catches a damaged download, an interrupted update, a replaced binary or
script, and an added executable. Anyone with root can rewrite both a file and `SHA256SUMS`; root
malware is outside what a module can defend against. Authenticity comes from the app's signed
catalog (or, for a manual install, from comparing the zip with the `.sha256` published next to
it by a release the maintainer signed).

The runtime check skips what the root manager itself changes: `module.prop` (the status shown in
its description), `customize.sh` (removed after install) and the manager's marker files
(`disable`, `remove`, `update`, `skip_mount`).

## Hardening in the scripts

- `umask 077`: logs, sockets and state the daemons create are readable by root only.
- `/data/adb/zairenkai` and `core/`, `fas/`, `tuning/` are created root-owned with mode 0700.
  A symlink in their place is refused at install and at boot (it could redirect logs, sockets or
  removal); uninstall removes such a link and never follows it.
- Uninstall signals only processes whose executable is this module's binary
  (`/proc/<pid>/exe`), never every process that shares the name.
- The install changes nothing on the device: no tuning, no daemon start, no partition, boot image
  or persistent kernel setting. FAS is installed switched off. ztune never runs at install or
  boot.
- Daemons are supervised with backoff and a start limit, so a crashing daemon cannot
  restart-loop; zfasd's frequency floors are restored after every exit.
- The uninstall log is `/data/adb/zairenkai-uninstall.log` (root only; `/cache` does not exist
  on A/B devices).

## WebUI

The KernelSU/APatch WebUI can run any command as root through `ksu.exec`, so the page is kept
small and strict:

- A Content-Security-Policy allows only the module's own script, stylesheet and images, no
  inline script or style, no network (`connect-src 'none'`), no frames, forms or base URL.
- Every command is a constant or is built from an allowlist (the five FAS profiles, on/off, an
  integer lease id that Core returned). Arguments are single-quoted JSON that is checked against
  a character allowlist with no quote, `$`, backtick, backslash, `;` or newline.
- Daemon output is shown with `textContent` only; no HTML is built from it.
- Changes go through Core: a dry run first (`zcored ctl submit … dry_run`), Core's decision and
  rules shown to the user, then the change with `confirmed: true` only after the user agrees.
  Only when Core does not answer (`zcored ctl` exit 2) can zfasd be driven directly, and each
  such change asks for confirmation first.
- Polling stops while the page is hidden.

Tested: `tests/test_webui.py` (policy, no inline code, no HTML sinks, no network APIs, command
sources) and `tests/webui_check.js` (builders and parsers, on captured daemon output).

**Unverified on a device:** KernelSU delivers `ksu.exec` results through `loadUrl("javascript:…")`
(KernelSU `WebViewInterface.kt`). A browser-initiated `javascript:` URL is expected not to be
blocked by the page's policy, but no device has confirmed it. If the WebUI shows "no answer
within 20 s" on every command, that is the cause: report it rather than loosening the policy.

## Reporting

Report a vulnerability to the ZairenkaiPrjctX maintainers privately, not in a public issue.
