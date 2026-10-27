# Artifact release and upstream synchronization

`components.lock.json` is the source of truth for the Core, FAS and Tuning commits in the one root
module. The `sync-upstreams.yml` workflow resolves the `dev` heads from the three allowlisted
organization repositories and proposes a PR with the new immutable commit SHAs and a patch-version
bump. It never pushes the proposal directly to `dev`. The real module CI is dispatched against the
candidate branch and the synchronization job fails when it fails.

After the pin PR is reviewed and merged, `release.yml` builds every locked component, assembles the
root module, verifies its internal hashes and metadata, and writes `artifact-manifest.json`. The
manifest includes the source commit, module version and version code, exact Core/FAS/Tuning commits,
ZIP size and SHA-256. The workflow creates a **draft** GitHub release. A maintainer should inspect the
run summary, changelog, artifact manifest and ZIP checksum before publishing it.

The App sync workflow consumes only a published release carrying the manifest. Once published, the
App workflow can lock the immutable artifact automatically, but only through a PR and full-integration
CI. It verifies that source lock and package agree before creating an APK. The old source-build path
remains as a compatibility fallback until the first manifest-bearing release is published.

This automation must not override per-device tuning restrictions. `PermissionRestricted` reports a
real access limitation unless the Core ownership false-positive is corrected by the matching version;
no generic sysfs permission or SELinux bypass is permitted. Device validation is still required.
