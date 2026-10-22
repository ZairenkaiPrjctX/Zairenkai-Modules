# Building the zairenkai module

## Inputs

`components.lock.json` pins every component by full commit. A component is a directory built
by its repository's `scripts/build-android.sh`:

```
bin/<binary>        Android arm64 executable (API 29, 16 KB-aligned LOAD segments)
LICENSE NOTICE THIRD_PARTY.md
component.json      format 1: component, repository, version, commit, target, SHA-256 per file
```

A component whose lock entry has `"license": "GPL-…"` (Zairenkai-Tuning) must also have, and
declare in `component.json`:

```
"license": "GPL-3.0-only"                       same as the lock
"source": "source/<name>-<commit>-src.tar.gz"   Corresponding Source, named for the locked commit
SOURCE.md                                        how to rebuild the binary from the archive
```

The archive goes into the zip as `source/<component>/…` and `SOURCE.md` as
`licenses/<component>/SOURCE.md`.

## Assemble

```sh
python3 scripts/assemble.py \
  --component ../Zairenkai-Core/dist/zairenkai-core \
  --component ../Zairenkai-FAS/dist/zairenkai-fas \
  --component ../Zairenkai-Tuning/dist/zairenkai-tuning
# -> dist/zairenkai-v<version>.zip and .sha256
```

The assembler refuses a component whose commit is not the locked one, whose target is not
`aarch64-linux-android`, whose files do not match `component.json`, that has undeclared or
symlinked files, or that is missing, and a GPL component without its licence or source archive. The zip has fixed timestamps, order and permissions, so the
same components give the same bytes.

To move a component, build it at the new commit, update its entry in `components.lock.json`,
and bump `module.version` there.

## CI

`.github/workflows/ci.yml`:

- `checks`: shellcheck on `module/`, assembler tests (`python3 -m unittest discover -s tests`).
- `module`: checks out Core, FAS and Tuning at their locked commits, builds them with Rust and the
  checksum-verified NDK r27d, assembles the module and uploads it as the artifact
  `zairenkai-module-unsigned-not-for-distribution`.

The component repositories are public (2026-10-22), so the `module` job checks them out at the
locked commits with the workflow's own read-only token: no CI GitHub App, variable or secret is
needed. The job fails if a locked commit cannot be fetched.

A component built by a `pull_request` run of Core or FAS records the PR's merge commit, which
the lock does not pin, so `assemble.py` refuses it. Use a component built at the locked commit
itself (a `workflow_dispatch` or push run on that commit), as the `module` job does.

## Tests

```sh
shellcheck -s sh module/*.sh module/META-INF/com/google/android/update-binary
python3 -m unittest discover -s tests -v
```
