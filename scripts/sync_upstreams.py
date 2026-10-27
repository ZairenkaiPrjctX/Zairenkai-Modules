#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Refresh the Core/FAS/Tuning commit pins from their dev branches. Only writes a reviewable PR."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "components.lock.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
EXPECTED = {
    "zairenkai-core": "ZairenkaiPrjctX/Zairenkai-Core",
    "zairenkai-fas": "ZairenkaiPrjctX/Zairenkai-FAS",
    "zairenkai-tuning": "ZairenkaiPrjctX/Zairenkai-Tuning",
}


def api_json(url: str) -> dict:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Zairenkai-component-sync/1.0", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot resolve upstream {url}: {exc}") from exc


def fetch_dev_sha(repository: str) -> str:
    encoded = "/".join(urllib.parse.quote(part, safe="") for part in repository.split("/"))
    data = api_json(f"https://api.github.com/repos/{encoded}/commits/dev")
    sha = data.get("sha", "")
    if not SHA1.fullmatch(sha):
        raise SystemExit(f"{repository}: GitHub did not return a full commit SHA")
    actual = data.get("html_url", "")
    if f"github.com/{repository}/commit/{sha}" not in actual:
        raise SystemExit(f"{repository}: response commit URL did not match its repository and SHA")
    return sha


def bump_patch(version: str) -> str:
    match = SEMVER.fullmatch(version)
    if not match:
        raise SystemExit(f"module version is not strict semver: {version!r}")
    major, minor, patch = map(int, match.groups())
    return f"{major}.{minor}.{patch + 1}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit nonzero if the lock would change; do not write")
    args = parser.parse_args()
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("format") != 1 or not isinstance(lock.get("components"), list):
        raise SystemExit("unsupported or malformed components.lock.json")
    components = {component.get("name"): component for component in lock["components"]}
    if not set(EXPECTED).issubset(components):
        raise SystemExit(f"component lock missing {sorted(set(EXPECTED) - components.keys())}")
    for name, repository in EXPECTED.items():
        if components[name].get("repository") != repository:
            raise SystemExit(f"{name}: expected trusted repository {repository}")
        sha = fetch_dev_sha(repository)
        components[name].setdefault("branch", "dev")
        if components[name].get("commit") != sha:
            components[name]["commit"] = sha
    changed = any(
        components[name]["commit"] != next(c["commit"] for c in json.loads(LOCK_PATH.read_text(encoding="utf-8"))["components"] if c["name"] == name)
        for name in EXPECTED
    )
    if not changed:
        print("All Core/FAS/Tuning pins already match dev; no PR is needed.")
        return 0
    next_version = bump_patch(lock["module"]["version"])
    date = dt.datetime.now(dt.timezone.utc).date().isoformat()
    old_version = lock["module"]["version"]
    lock["module"]["version"] = next_version
    new_changelog = f"## [{next_version}] - unreleased\n\n### Changed\n- Refresh Core, FAS and Tuning pins from their reviewed `dev` branch heads; this module version is a new immutable build candidate.\n\n"
    changelog = CHANGELOG_PATH.read_text(encoding="utf-8")
    if args.check:
        print(f"Upstream pins would change module v{old_version} -> v{next_version} ({date}); run without --check to write.")
        return 1
    # Do not duplicate an already-prepared release entry when re-running the workflow.
    if not changelog.startswith(f"## [{next_version}]"):
        CHANGELOG_PATH.write_text(new_changelog + changelog, encoding="utf-8")
    LOCK_PATH.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Updated Core/FAS/Tuning pins and bumped module version to {next_version}.")
    for name in EXPECTED:
        print(f"  {name}: {components[name]['commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
