#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Assemble the single Zairenkai root module from its component builds.

Each component repository (Zairenkai-Core, Zairenkai-FAS, Zairenkai-Tuning) builds a directory
with its binary, its licence files and a component.json (format 1) naming the commit and the
SHA-256 of every file. This script accepts a component only when it is exactly what components.lock.json pins:
same name, same commit, Android arm64 target, every file present with the declared hash, and
no undeclared file. It then packages module/ plus the components into one zip with fixed
timestamps and order, so the same inputs give the same bytes.

The zip carries SHA256SUMS (sha256sum format) for every file the root manager extracts, that is
every entry except META-INF/. customize.sh refuses to install when a file does not match or an
unlisted file is present, and service.sh starts nothing when a file changed after install
(module/common.sh, docs/SECURITY.md).

A component whose lock entry names a GPL licence (Zairenkai-Tuning, GPL-3.0-only) must declare
the same licence in its component.json and ship its Corresponding Source: a source archive
under source/ and a SOURCE.md saying how to rebuild. Both go into the module (source/<name>/,
licenses/<name>/SOURCE.md) next to the binary; without them assembly fails. The zip is an
aggregate of separate programs; each keeps its own licence.

Releases: module.prop carries `updateJson`, the URL of update.json in the repository's latest
GitHub release, so Magisk, KernelSU and APatch offer a published release as an update. Next to
the zip the assembler writes update.json (version, versionCode, the release's zip and changelog
URLs) and changelog.md (this version's CHANGELOG.md entry; a version without an entry fails).
The zip also carries docs/README.md and docs/CHANGELOG.md.

Usage: assemble.py [--lock components.lock.json] --component DIR [--component DIR ...]
                   [--out dist]
Output: <out>/zairenkai-v<version>.zip, .zip.sha256, update.json and changelog.md
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = "aarch64-linux-android"
LICENCE_FILES = ("LICENSE", "NOTICE", "THIRD_PARTY.md")
SOURCE_INFO = "SOURCE.md"
ZIP_DATE = (2000, 1, 1, 0, 0, 0)
DEFAULT_REPOSITORY = "ZairenkaiPrjctX/Zairenkai-Modules"
SUMS = "SHA256SUMS"
MAX_COMPONENT_FILE = 64 * 1024 * 1024


class AssemblyError(Exception):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def load_lock(path):
    lock = json.loads(Path(path).read_text())
    if lock.get("format") != 1:
        raise AssemblyError(f"{path}: unsupported lock format {lock.get('format')!r}")
    module = lock["module"]
    if not re.fullmatch(r"\d+\.\d+\.\d+", module["version"]):
        raise AssemblyError(f"{path}: module version {module['version']!r} is not MAJOR.MINOR.PATCH")
    names = [c["name"] for c in lock["components"]]
    if len(names) != len(set(names)) or not names:
        raise AssemblyError(f"{path}: component names must be unique and non-empty")
    for c in lock["components"]:
        if not re.fullmatch(r"[0-9a-f]{40}", c["commit"]):
            raise AssemblyError(f"{path}: {c['name']}: commit must be a full SHA-1")
        if not re.fullmatch(r"bin/[a-z0-9_]+", c["binary"]):
            raise AssemblyError(f"{path}: {c['name']}: binary must be bin/<name>")
        if "license" in c and not re.fullmatch(r"[A-Za-z0-9.+-]+", c["license"]):
            raise AssemblyError(f"{path}: {c['name']}: license must be an SPDX identifier")
    return lock


def copyleft(pinned):
    """Components whose licence requires shipping source with the binary."""
    return pinned.get("license", "").startswith(("GPL-", "AGPL-", "LGPL-"))


def check_component(directory, pinned):
    """Validate one component directory against its lock entry; return its manifest."""
    d = Path(directory)
    manifest_path = d / "component.json"
    if not manifest_path.is_file():
        raise AssemblyError(f"{d}: no component.json")
    m = json.loads(manifest_path.read_text())
    name = m.get("component")
    if m.get("format") != 1:
        raise AssemblyError(f"{d}: unsupported component.json format {m.get('format')!r}")
    if name != pinned["name"]:
        raise AssemblyError(f"{d}: component {name!r}, expected {pinned['name']!r}")
    if m.get("commit") != pinned["commit"]:
        raise AssemblyError(
            f"{name}: built from {m.get('commit')}, but components.lock.json pins {pinned['commit']}"
        )
    if m.get("target") != TARGET:
        raise AssemblyError(f"{name}: target {m.get('target')!r}, expected {TARGET}")
    if not isinstance(m.get("version"), str) or not m["version"]:
        raise AssemblyError(f"{name}: no version")
    files = m.get("files")
    if not isinstance(files, dict):
        raise AssemblyError(f"{name}: no file list")
    required = {pinned["binary"], *LICENCE_FILES}
    if copyleft(pinned):
        if m.get("license") != pinned["license"]:
            raise AssemblyError(
                f"{name}: licence {m.get('license')!r}, but components.lock.json says {pinned['license']!r}"
            )
        source = m.get("source")
        if not isinstance(source, str) or not re.fullmatch(r"source/[A-Za-z0-9._-]+\.tar\.gz", source):
            raise AssemblyError(f"{name}: {pinned['license']} component without a source archive")
        if pinned["commit"] not in source:
            raise AssemblyError(f"{name}: source archive {source} is not named for commit {pinned['commit']}")
        required |= {source, SOURCE_INFO}
    if missing := required - files.keys():
        raise AssemblyError(f"{name}: component.json does not declare {sorted(missing)}")
    present = {
        p.relative_to(d).as_posix()
        for p in d.rglob("*")
        if p.is_file() or p.is_symlink()
    } - {"component.json"}
    if extra := present - files.keys():
        raise AssemblyError(f"{name}: undeclared files {sorted(extra)}")
    for rel, digest in files.items():
        p = d / rel
        if p.is_symlink() or not p.is_file():
            raise AssemblyError(f"{name}: {rel} is missing or not a regular file")
        if p.stat().st_size > MAX_COMPONENT_FILE:
            raise AssemblyError(f"{name}: {rel} is larger than {MAX_COMPONENT_FILE} bytes")
        if sha256(p) != digest:
            raise AssemblyError(f"{name}: {rel} does not match its SHA-256 in component.json")
    return m


def version_code(version):
    major, minor, patch = (int(x) for x in version.split("."))
    return major * 10000 + minor * 100 + patch


def repository(lock):
    repo = lock["module"].get("repository", DEFAULT_REPOSITORY)
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", repo):
        raise AssemblyError(f"module repository {repo!r} is not owner/name")
    return repo


def update_json_url(lock):
    """Stable URL root managers poll: update.json of the latest published (non-pre-) release."""
    return f"https://github.com/{repository(lock)}/releases/latest/download/update.json"


def changelog_entry(text, version):
    """The body of `## [version] ...` in CHANGELOG.md, without its heading."""
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = re.match(r"^## \[?v?" + re.escape(version) + r"\]?(\s|$)", line) is not None
            continue
        if inside:
            out.append(line)
    body = "\n".join(out).strip()
    if not body:
        raise AssemblyError(f"CHANGELOG.md has no entry for {version}")
    return body + "\n"


def update_json(lock):
    """Magisk's (and KernelSU's, APatch's) update.json for this version's GitHub release."""
    m = lock["module"]
    base = f"https://github.com/{repository(lock)}/releases/download/v{m['version']}"
    doc = {
        "version": f"v{m['version']}",
        "versionCode": version_code(m["version"]),
        "zipUrl": f"{base}/{m['id']}-v{m['version']}.zip",
        "changelog": f"{base}/changelog.md",
    }
    return json.dumps(doc, indent=2) + "\n"


def module_prop(lock, manifests):
    module = lock["module"]
    parts = ", ".join(
        f"{c['summary']} ({manifests[c['name']]['version']})" for c in lock["components"]
    )
    description = f"One module for the Zairenkai system: {parts}. Data in /data/adb/zairenkai."
    template = (ROOT / "module" / "module.prop.in").read_text()
    out = (
        template.replace("@VERSION@", module["version"])
        .replace("@VERSION_CODE@", str(version_code(module["version"])))
        .replace("@DESCRIPTION@", description)
        .replace("@UPDATE_JSON@", update_json_url(lock))
    )
    if "@" in out or f"id={module['id']}\n" not in out:
        raise AssemblyError("module.prop.in and components.lock.json disagree")
    return out


def components_json(lock, manifests):
    """components.json inside the module: one line per component (customize.sh reads it)."""
    lines = []
    for c in lock["components"]:
        m = manifests[c["name"]]
        entry = {
            "version": m["version"],
            "repository": c["repository"],
            "commit": m["commit"],
            "binary": c["binary"],
            "sha256": m["files"][c["binary"]],
        }
        if copyleft(c):
            entry["license"] = c["license"]
            entry["source"] = f"source/{c['name']}/{Path(m['source']).name}"
        lines.append(f'    "{c["name"]}": {json.dumps(entry, separators=(", ", ": "))}')
    body = ",\n".join(lines)
    return (
        "{\n"
        '  "format": 1,\n'
        f'  "module": "{lock["module"]["id"]}",\n'
        f'  "version": "{lock["module"]["version"]}",\n'
        '  "components": {\n'
        f"{body}\n"
        "  }\n"
        "}\n"
    )


def entries(lock, components, manifests):
    """Every (path in zip, bytes, executable) of the module, before sorting."""
    out = []
    for p in sorted((ROOT / "module").rglob("*")):
        rel = p.relative_to(ROOT / "module").as_posix()
        if p.is_file() and rel not in ("module.prop.in", "README.md"):
            executable = rel.endswith(".sh") or rel.endswith("update-binary")
            out.append((rel, p.read_bytes(), executable))
    out.append(("module.prop", module_prop(lock, manifests).encode(), False))
    out.append(("components.json", components_json(lock, manifests).encode(), False))
    out.append(("docs/README.md", (ROOT / "module" / "README.md").read_bytes(), False))
    out.append(("docs/CHANGELOG.md", (ROOT / "CHANGELOG.md").read_bytes(), False))
    out.append(("LICENSE", (ROOT / "LICENSE").read_bytes(), False))
    out.append(("NOTICE", (ROOT / "NOTICE").read_bytes(), False))
    for c in lock["components"]:
        d = Path(components[c["name"]])
        out.append((c["binary"], (d / c["binary"]).read_bytes(), True))
        for f in LICENCE_FILES:
            out.append((f"licenses/{c['name']}/{f}", (d / f).read_bytes(), False))
        if copyleft(c):
            m = manifests[c["name"]]
            src = m["source"]
            out.append((f"licenses/{c['name']}/{SOURCE_INFO}", (d / SOURCE_INFO).read_bytes(), False))
            out.append((f"source/{c['name']}/{Path(src).name}", (d / src).read_bytes(), False))
    names = [e[0] for e in out]
    if len(names) != len(set(names)):
        raise AssemblyError("two inputs map to the same path in the module")
    out.append((SUMS, sha256sums(out), False))
    return out


def sha256sums(files):
    """SHA256SUMS for the extracted module: every entry but META-INF/ (Magisk, KernelSU and APatch
    do not extract it), sorted, in the format sha256sum -c reads."""
    lines = []
    for name, data, _ in sorted(files):
        if name.startswith("META-INF/") or name == SUMS:
            continue
        if not re.fullmatch(r"[A-Za-z0-9._+/-]+", name) or ".." in name.split("/"):
            raise AssemblyError(f"{name}: not a safe path for SHA256SUMS")
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
    return "".join(lines).encode()


def write_zip(path, files):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data, executable in sorted(files):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3  # Unix, so the permission bits below are honoured
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            z.writestr(info, data)


def assemble(lock_path, component_dirs, out_dir):
    lock = load_lock(lock_path)
    by_name = {}
    for d in component_dirs:
        manifest = Path(d) / "component.json"
        if not manifest.is_file():
            raise AssemblyError(f"{d}: no component.json")
        name = json.loads(manifest.read_text()).get("component")
        if name in by_name:
            raise AssemblyError(f"component {name} given twice")
        by_name[name] = d
    pinned = {c["name"]: c for c in lock["components"]}
    if unknown := set(by_name) - set(pinned):
        raise AssemblyError(f"components not in components.lock.json: {sorted(map(str, unknown))}")
    if missing := set(pinned) - set(by_name):
        raise AssemblyError(f"missing components: {sorted(missing)}")
    manifests = {n: check_component(by_name[n], pinned[n]) for n in pinned}
    notes = changelog_entry((ROOT / "CHANGELOG.md").read_text(), lock["module"]["version"])
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / f"{lock['module']['id']}-v{lock['module']['version']}.zip"
    write_zip(zip_path, entries(lock, by_name, manifests))
    digest = sha256(zip_path)
    (out / (zip_path.name + ".sha256")).write_text(f"{digest}  {zip_path.name}\n")
    (out / "update.json").write_text(update_json(lock))
    (out / "changelog.md").write_text(notes)
    return zip_path, digest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Assemble the single Zairenkai root module.")
    ap.add_argument("--lock", default=str(ROOT / "components.lock.json"))
    ap.add_argument("--component", action="append", required=True, help="component directory")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    a = ap.parse_args(argv)
    try:
        zip_path, digest = assemble(a.lock, a.component, a.out)
    except (AssemblyError, KeyError, ValueError, OSError) as e:
        print(f"assemble: {e}", file=sys.stderr)
        return 1
    print(f"{digest}  {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
