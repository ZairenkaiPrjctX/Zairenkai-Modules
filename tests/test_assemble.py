# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""Tests for scripts/assemble.py with stand-in components (no Android build needed)."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import assemble  # noqa: E402

CORE = "a" * 40
FAS = "b" * 40
TUNING = "d" * 40
SRC = f"source/zairenkai-tuning-{TUNING}-src.tar.gz"


def lock(tmp):
    data = {
        "format": 1,
        "module": {"id": "zairenkai", "name": "Zairenkai", "version": "0.1.0"},
        "components": [
            {"name": "zairenkai-core", "repository": "ZairenkaiPrjctX/Zairenkai-Core",
             "commit": CORE, "binary": "bin/zcored", "summary": "zcored, the control plane"},
            {"name": "zairenkai-fas", "repository": "ZairenkaiPrjctX/Zairenkai-FAS",
             "commit": FAS, "binary": "bin/zfasd", "summary": "zfasd, frame-aware floors"},
            {"name": "zairenkai-tuning", "repository": "ZairenkaiPrjctX/Zairenkai-Tuning",
             "commit": TUNING, "binary": "bin/ztune", "license": "GPL-3.0-only",
             "summary": "ztune, telemetry and tuning (GPL-3.0)"},
        ],
    }
    p = Path(tmp) / "components.lock.json"
    p.write_text(json.dumps(data))
    return p


def component(tmp, name, commit, binary, version="0.1.0", target="aarch64-linux-android",
              extra=None, fields=None):
    d = Path(tmp) / name
    (d / "bin").mkdir(parents=True)
    contents = {binary: f"\x7fELF {name}".encode(), "LICENSE": b"Apache-2.0",
                "NOTICE": f"{name} notice".encode(), "THIRD_PARTY.md": b"crates"}
    contents.update(extra or {})
    for rel, data in contents.items():
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(data)
    (d / "component.json").write_text(json.dumps({
        "format": 1, "component": name, "repository": "x", "version": version,
        "commit": commit, "target": target, "min_api": 29, **(fields or {}),
        "files": {rel: hashlib.sha256(data).hexdigest() for rel, data in contents.items()},
    }))
    return d


def tuning(tmp, license="GPL-3.0-only", with_source=True):
    extra = {"LICENSE": b"GNU GENERAL PUBLIC LICENSE Version 3", "SOURCE.md": b"rebuild"}
    fields = {"license": license}
    if with_source:
        extra[SRC] = b"\x1f\x8b source archive"
        fields["source"] = SRC
    return component(tmp, "zairenkai-tuning", TUNING, "bin/ztune", extra=extra, fields=fields)


class AssembleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.lock = lock(self.dir)
        self.core = component(self.dir, "zairenkai-core", CORE, "bin/zcored")
        self.fas = component(self.dir, "zairenkai-fas", FAS, "bin/zfasd")
        self.tuning = tuning(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, out="out", components=None):
        return assemble.assemble(
            self.lock, components or [self.core, self.fas, self.tuning], self.dir / out
        )

    def test_one_module_with_every_component(self):
        path, digest = self.build()
        self.assertEqual(path.name, "zairenkai-v0.1.0.zip")
        self.assertEqual(Path(str(path) + ".sha256").read_text(), f"{digest}  {path.name}\n")
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            prop = z.read("module.prop").decode()
            comps = json.loads(z.read("components.json"))
            mode = {i.filename: (i.external_attr >> 16) & 0o777 for i in z.infolist()}
        for f in ["module.prop", "customize.sh", "service.sh", "action.sh", "uninstall.sh",
                  "META-INF/com/google/android/update-binary", "webroot/index.html",
                  "bin/zcored", "bin/zfasd", "LICENSE", "NOTICE", "components.json",
                  "licenses/zairenkai-core/LICENSE", "licenses/zairenkai-fas/NOTICE"]:
            self.assertIn(f, names)
        self.assertNotIn("module.prop.in", names)
        self.assertIn("id=zairenkai\n", prop)
        self.assertIn("versionCode=100\n", prop)
        self.assertNotIn("@", prop)
        self.assertEqual(comps["components"]["zairenkai-fas"]["commit"], FAS)
        self.assertEqual(mode["bin/zfasd"], 0o755)
        self.assertEqual(mode["service.sh"], 0o755)
        self.assertEqual(mode["LICENSE"], 0o644)

    def test_fas_starts_switched_off_on_first_install(self):
        path, _ = self.build()
        with zipfile.ZipFile(path) as z:
            cfg = z.read("defaults/fas-config.toml").decode()
            script = z.read("customize.sh").decode()
        self.assertIn("[general]\nenabled = false\n", cfg)
        self.assertIn("schema_version = 1\n", cfg)
        # Copied only when no configuration exists, so the user's choice survives updates.
        self.assertIn('[ ! -f "$DATA/fas/config.toml" ]', script)
        self.assertIn('cp "$MODPATH/defaults/fas-config.toml" "$DATA/fas/config.toml"', script)

    def test_customize_sh_can_read_components_json(self):
        path, _ = self.build()
        with zipfile.ZipFile(path) as z:
            text = z.read("components.json").decode()
        # customize.sh prints one line per component with a sed over this layout.
        self.assertRegex(text, r'\n    "zairenkai-core": \{"version": "0\.1\.0", ')
        self.assertRegex(text, r'\n    "zairenkai-fas": \{"version": "0\.1\.0", ')

    def test_reproducible(self):
        a, _ = self.build("a")
        b, _ = self.build("b")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_rejects_a_tampered_binary(self):
        (self.fas / "bin/zfasd").write_bytes(b"something else")
        with self.assertRaisesRegex(assemble.AssemblyError, "bin/zfasd does not match"):
            self.build()

    def test_rejects_a_commit_the_lock_does_not_pin(self):
        other = component(self.dir / "other", "zairenkai-core", "c" * 40, "bin/zcored")
        with self.assertRaisesRegex(assemble.AssemblyError, "pins " + CORE):
            self.build(components=[other, self.fas, self.tuning])

    def test_rejects_a_missing_component(self):
        with self.assertRaisesRegex(assemble.AssemblyError, "missing components.*zairenkai-fas"):
            self.build(components=[self.core, self.tuning])

    def test_rejects_an_undeclared_file(self):
        (self.core / "bin/extra").write_bytes(b"x")
        with self.assertRaisesRegex(assemble.AssemblyError, "undeclared files"):
            self.build()

    def test_rejects_another_target(self):
        other = component(self.dir / "x86", "zairenkai-fas", FAS, "bin/zfasd", target="x86_64-linux-android")
        with self.assertRaisesRegex(assemble.AssemblyError, "target"):
            self.build(components=[self.core, other, self.tuning])

    def test_rejects_a_symlinked_file(self):
        (self.core / "LICENSE").unlink()
        (self.core / "LICENSE").symlink_to("/etc/hostname")
        with self.assertRaisesRegex(assemble.AssemblyError, "LICENSE is missing or not a regular file"):
            self.build()

    def test_rejects_a_component_given_twice(self):
        with self.assertRaisesRegex(assemble.AssemblyError, "given twice"):
            self.build(components=[self.core, self.core, self.fas, self.tuning])

    def test_real_lock_pins_full_commits(self):
        real = assemble.load_lock(assemble.ROOT / "components.lock.json")
        self.assertEqual(
            [c["name"] for c in real["components"]],
            ["zairenkai-core", "zairenkai-fas", "zairenkai-tuning"],
        )
        tuning_entry = real["components"][2]
        self.assertEqual(tuning_entry["license"], "GPL-3.0-only")
        self.assertEqual(real["module"]["id"], "zairenkai")


    def test_gpl_component_ships_its_source_and_licence(self):
        path, _ = self.build()
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            comps = json.loads(z.read("components.json"))
            mode = {i.filename: (i.external_attr >> 16) & 0o777 for i in z.infolist()}
            licence = z.read("licenses/zairenkai-tuning/LICENSE")
        archive = f"source/zairenkai-tuning/zairenkai-tuning-{TUNING}-src.tar.gz"
        for f in ["bin/ztune", archive, "licenses/zairenkai-tuning/SOURCE.md",
                  "licenses/zairenkai-tuning/NOTICE"]:
            self.assertIn(f, names)
        self.assertIn(b"GNU GENERAL PUBLIC LICENSE", licence)
        self.assertEqual(mode["bin/ztune"], 0o755)
        entry = comps["components"]["zairenkai-tuning"]
        self.assertEqual(entry["license"], "GPL-3.0-only")
        self.assertEqual(entry["source"], archive)
        # Apache-2.0 components carry no source archive or licence field.
        self.assertNotIn("license", comps["components"]["zairenkai-core"])

    def test_rejects_a_gpl_component_without_source(self):
        bare = tuning(self.dir / "bare", with_source=False)
        with self.assertRaisesRegex(assemble.AssemblyError, "without a source archive"):
            self.build(components=[self.core, self.fas, bare])

    def test_rejects_a_gpl_component_with_another_licence(self):
        other = tuning(self.dir / "relicensed", license="Apache-2.0")
        with self.assertRaisesRegex(assemble.AssemblyError, "licence 'Apache-2.0'"):
            self.build(components=[self.core, self.fas, other])

    def test_rejects_a_source_archive_for_another_commit(self):
        wrong = "source/zairenkai-tuning-" + "e" * 40 + "-src.tar.gz"
        other = component(self.dir / "wrongsrc", "zairenkai-tuning", TUNING, "bin/ztune",
                          extra={"SOURCE.md": b"x", wrong: b"x"},
                          fields={"license": "GPL-3.0-only", "source": wrong})
        with self.assertRaisesRegex(assemble.AssemblyError, "not named for commit"):
            self.build(components=[self.core, self.fas, other])

    def test_nothing_runs_ztune_at_install_or_boot(self):
        path, _ = self.build()
        with zipfile.ZipFile(path) as z:
            customize = z.read("customize.sh").decode()
            service = z.read("service.sh").decode()
            uninstall = z.read("uninstall.sh").decode()
        executable = [l for l in customize.splitlines() + service.splitlines()
                      if "bin/ztune" in l and not l.lstrip().startswith("#")]
        self.assertTrue(all(l.strip().startswith("if [ -x") for l in executable), executable)
        self.assertIn('"$MODDIR/bin/ztune" --state-dir "$DATA/tuning" restore', uninstall)


if __name__ == "__main__":
    unittest.main()
