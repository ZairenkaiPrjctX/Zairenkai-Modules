# Building the zairenkai module

## Inputs

`components.lock.json` pins every component by full commit. A component is a directory built
by its repository's `scripts/build-android.sh`:

```
bin/<binary>        Android arm64 executable (API 29, 16 KB-aligned LOAD segments)
LICENSE NOTICE THIRD_PARTY.md
component.json      format 1: component, repository, version, commit, target, SHA-256 per file
```

## Assemble

```sh
python3 scripts/assemble.py \
  --component ../Zairenkai-Core/dist/zairenkai-core \
  --component ../Zairenkai-FAS/dist/zairenkai-fas
# -> dist/zairenkai-v<version>.zip and .sha256
```

The assembler refuses a component whose commit is not the locked one, whose target is not
`aarch64-linux-android`, whose files do not match `component.json`, that has undeclared or
symlinked files, or that is missing. The zip has fixed timestamps, order and permissions, so the
same components give the same bytes.

To move a component, build it at the new commit, update its entry in `components.lock.json`,
and bump `module.version` there.

## CI

`.github/workflows/ci.yml`:

- `checks`: shellcheck on `module/`, assembler tests (`python3 -m unittest discover -s tests`).
- `module`: checks out Core and FAS at their locked commits, builds them with Rust and the
  checksum-verified NDK r27d, assembles the module and uploads it as the artifact
  `zairenkai-module-unsigned-not-for-distribution`.

The `module` job reads the private component repositories through the organization's CI GitHub
App: the repository variable `ZAIRENKAI_CI_APP_ID` and the secret
`ZAIRENKAI_CI_APP_PRIVATE_KEY` must be set in this repository, and the App must be installed
on Zairenkai-Core and Zairenkai-FAS. Without them the job fails and says so.

## Tests

```sh
shellcheck -s sh module/*.sh module/META-INF/com/google/android/update-binary
python3 -m unittest discover -s tests -v
```
