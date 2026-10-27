#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Download and verify an immutable, manifest-pinned Zairenkai release artifact."""
from __future__ import annotations
import argparse, hashlib, io, json, os, re, shutil, tarfile, tempfile, urllib.error, urllib.parse, urllib.request
from pathlib import Path, PurePosixPath

SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
USER_AGENT = "Zairenkai-Artifact-Consumer/1.0"
class ArtifactError(Exception): pass
class UnpinnedArtifact(ArtifactError): pass

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def safe_name(value: str) -> str:
    if not isinstance(value, str) or not value or "/" in value or "\\" in value or value in {".", ".."}:
        raise ArtifactError(f"unsafe release asset name: {value!r}")
    return value

def req(url: str) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    # Auth is only sent to api.github.com; never send the token to asset download hosts.
    if token and urllib.parse.urlsplit(url).hostname == "api.github.com": headers["Authorization"] = "Bearer " + token
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90) as response:
            data = response.read(1_000_000_000 + 1)
            if len(data) > 1_000_000_000: raise ArtifactError("response exceeded 1 GB safety limit")
            return data
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ArtifactError(f"download failed for {url}: {exc}") from exc

def parse_json(data: bytes, label: str) -> dict:
    try: value = json.loads(data)
    except (ValueError, UnicodeDecodeError) as exc: raise ArtifactError(f"invalid {label} JSON: {exc}") from exc
    if not isinstance(value, dict): raise ArtifactError(f"{label} must be a JSON object")
    return value

def validate_manifest(manifest: dict, *, repository: str, component: str, commit: str, asset_name: str, archive: bytes) -> None:
    if manifest.get("schema_version") != 1: raise ArtifactError("unsupported artifact manifest schema")
    if manifest.get("repository") != repository: raise ArtifactError("manifest repository does not match the lock")
    if manifest.get("component") != component: raise ArtifactError("manifest component id does not match the lock")
    if manifest.get("source_commit") != commit or not SHA1.fullmatch(commit): raise ArtifactError("manifest source commit does not match the pinned source commit")
    if manifest.get("archive_format") != "tar.gz": raise ArtifactError("artifact must use tar.gz format")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or len(assets) != 1: raise ArtifactError("manifest must declare exactly one archive asset")
    a = assets[0]
    if not isinstance(a, dict) or a.get("name") != asset_name: raise ArtifactError("manifest asset name does not match the lock")
    if not isinstance(a.get("size_bytes"), int) or a["size_bytes"] != len(archive): raise ArtifactError("archive size does not match the manifest")
    if not SHA256.fullmatch(str(a.get("sha256", ""))) or a["sha256"] != sha(archive): raise ArtifactError("archive SHA-256 does not match the manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or not files: raise ArtifactError("manifest has no packaged files")
    seen=set()
    for item in files:
        if not isinstance(item, dict): raise ArtifactError("manifest file entry is not an object")
        name=item.get("path")
        pure=PurePosixPath(name) if isinstance(name,str) else None
        if pure is None or pure.is_absolute() or ".." in pure.parts or "\\" in name or not name or name in seen:
            raise ArtifactError(f"unsafe or duplicate manifest path: {name!r}")
        seen.add(name)
        if not isinstance(item.get("size_bytes"), int) or item["size_bytes"] < 0 or not SHA256.fullmatch(str(item.get("sha256", ""))):
            raise ArtifactError(f"invalid size/hash in manifest entry {name}")

def release_for(repo: str, tag: str) -> dict:
    if not REPO.fullmatch(repo): raise ArtifactError("invalid repository in lock")
    url=f"https://api.github.com/repos/{repo}/releases/tags/{urllib.parse.quote(tag, safe='')}"
    r=parse_json(req(url), "GitHub release")
    if r.get("tag_name") != tag or r.get("draft") is True or r.get("prerelease") is True:
        raise ArtifactError("release tag mismatch, draft, or prerelease cannot be consumed")
    if not isinstance(r.get("assets"), list): raise ArtifactError("release has no asset list")
    return r

def download_release_asset(release: dict, name: str) -> bytes:
    safe_name(name)
    assets=release.get("assets", [])
    matches=[a for a in assets if isinstance(a,dict) and a.get("name")==name]
    if len(matches)!=1: raise ArtifactError(f"release must contain exactly one asset named {name}")
    u=matches[0].get("browser_download_url")
    if not isinstance(u,str) or urllib.parse.urlsplit(u).hostname not in {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}:
        raise ArtifactError("release asset URL is not an allowed GitHub download URL")
    return req(u)

def verify_and_extract(archive: bytes, manifest: dict, destination: Path) -> int:
    expected={x["path"]:x for x in manifest["files"]}
    staged=Path(tempfile.mkdtemp(prefix="zairenkai-artifact-"))
    try:
        try: tar=tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz")
        except tarfile.TarError as exc: raise ArtifactError(f"archive is not valid tar.gz: {exc}") from exc
        with tar:
            members=tar.getmembers()
            actual_names=set()
            for member in members:
                p=PurePosixPath(member.name)
                if p.is_absolute() or ".." in p.parts or "\\" in member.name or member.name not in expected:
                    raise ArtifactError(f"archive contains a path not permitted by manifest: {member.name!r}")
                if not member.isfile() or member.issym() or member.islnk() or member.isdev():
                    raise ArtifactError(f"non-regular archive entry is forbidden: {member.name}")
                if member.name in actual_names: raise ArtifactError(f"duplicate archive entry: {member.name}")
                actual_names.add(member.name)
                f=tar.extractfile(member)
                if f is None: raise ArtifactError(f"cannot read archive entry: {member.name}")
                data=f.read()
                e=expected[member.name]
                if len(data)!=e["size_bytes"] or sha(data)!=e["sha256"]:
                    raise ArtifactError(f"file hash or size mismatch: {member.name}")
                out=staged.joinpath(*p.parts); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
                out.chmod(0o755 if e.get("executable") is True else 0o644)
            if actual_names != set(expected): raise ArtifactError("archive contents differ from manifest file list")
        destination.parent.mkdir(parents=True,exist_ok=True)
        # Atomic replacement with backup: never delete the old good artifact until validation succeeds.
        backup=None
        if destination.exists():
            backup=destination.with_name(destination.name+".old-verified")
            if backup.exists(): shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
            destination.rename(backup)
        try: staged.rename(destination)
        except Exception:
            if backup and backup.exists(): backup.rename(destination)
            raise
        if backup and backup.exists(): shutil.rmtree(backup) if backup.is_dir() else backup.unlink()
        return len(expected)
    finally:
        if staged.exists(): shutil.rmtree(staged,ignore_errors=True)

def fetch(lock_path: Path, component_key: str, destination: Path, *, collection: str, name_key: str="name") -> int:
    lock=parse_json(lock_path.read_bytes(), "component lock")
    rows=lock.get(collection, [])
    if not isinstance(rows,list): raise ArtifactError(f"lock field {collection} must be an array")
    row=next((x for x in rows if isinstance(x,dict) and x.get(name_key if collection=="components" else "id")==component_key),None)
    if row is None: raise ArtifactError(f"component {component_key} missing from lock")
    pin=row.get("release_artifact")
    if not isinstance(pin,dict): raise UnpinnedArtifact(f"{component_key}: no immutable release artifact is pinned; source build fallback is required")
    repo=pin.get("repository", row.get("repository")); commit=pin.get("source_commit", row.get("commit")); tag=pin.get("release_tag")
    component=pin.get("component", component_key); asset_name=safe_name(pin.get("asset_name")); manifest_name=safe_name(pin.get("manifest_name", "artifact-manifest.json"))
    if not isinstance(tag,str) or tag != f"artifact-{commit}": raise ArtifactError("release tag must be artifact-<exact-source-commit>")
    if not SHA256.fullmatch(str(pin.get("manifest_sha256",""))) or not SHA256.fullmatch(str(pin.get("asset_sha256",""))): raise ArtifactError("artifact lock is missing valid SHA-256 digests")
    release=release_for(repo,tag)
    manifest_bytes=download_release_asset(release,manifest_name)
    if sha(manifest_bytes)!=pin["manifest_sha256"]: raise ArtifactError("published artifact manifest SHA-256 does not match the lock")
    archive=download_release_asset(release,asset_name)
    if len(archive)!=pin.get("asset_size_bytes") or sha(archive)!=pin["asset_sha256"]: raise ArtifactError("published archive size/SHA-256 does not match the lock")
    manifest=parse_json(manifest_bytes,"artifact manifest")
    validate_manifest(manifest,repository=repo,component=component,commit=commit,asset_name=asset_name,archive=archive)
    count=verify_and_extract(archive,manifest,destination)
    print(f"verified {repo}@{commit} release {tag}: {asset_name} ({count} files)")
    return count

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock",required=True,type=Path); ap.add_argument("--component",required=True); ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--collection",default="components",choices=("components","components"))
    ap.add_argument("--key",default="name")
    ns=ap.parse_args()
    try: fetch(ns.lock,ns.component,ns.out,collection=ns.collection,name_key=ns.key)
    except UnpinnedArtifact as exc: print(str(exc)); return 3
    except ArtifactError as exc: print(f"artifact verification failed: {exc}"); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
