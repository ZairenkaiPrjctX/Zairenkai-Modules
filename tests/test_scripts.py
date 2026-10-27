# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""The module's shell helpers (module/common.sh), run with the host's POSIX sh against a module
assembled from stand-in components: the integrity check, the status line, the process check and
the data directory guard. The paths under /data/adb are never touched."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_assemble as t  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COMMON = ROOT / "module" / "common.sh"


def sh(script, *args, cwd=None):
    return subprocess.run(["sh", "-c", f'. "{COMMON}"; {script}', "sh", *args],
                          capture_output=True, text=True, cwd=cwd, timeout=60)


class IntegrityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        lock = t.lock(base)
        comps = [t.component(base, "zairenkai-core", t.CORE, "bin/zcored"),
                 t.component(base, "zairenkai-fas", t.FAS, "bin/zfasd"),
                 t.tuning(base)]
        zip_path, _ = t.assemble.assemble(lock, comps, base / "out")
        self.mod = base / "zairenkai"
        with zipfile.ZipFile(zip_path) as z:
            # Like the root managers: META-INF is not extracted.
            z.extractall(self.mod, [n for n in z.namelist() if not n.startswith("META-INF/")])

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, mode):
        return sh('zr_verify "$1" "$2"', str(self.mod), mode)

    def test_a_clean_install_passes_both_checks(self):
        for mode in ("install", "runtime"):
            r = self.verify(mode)
            self.assertEqual((r.returncode, r.stdout), (0, ""), mode)
        r = subprocess.run(["sh", str(self.mod / "verify.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertRegex(r.stdout, r"^verified: \d+ files match SHA256SUMS\n$")

    def run_installer(self, until):
        """customize.sh as a root manager sources it, stopped when it prints `until`. The stubs
        stand in for the installer's functions; nothing outside the module directory is read
        for writing before step 3, so the run ends there."""
        stub = (
            'ui_print() { echo "$1"; case "$1" in "' + until + '"*) exit 0;; esac; }\n'
            'abort() { echo "$1"; exit 1; }\n'
            "set_perm() { :; }\nset_perm_recursive() { :; }\n"
            f'MODPATH="{self.mod}"; ARCH=arm64; API=37\n'
            '. "$MODPATH/customize.sh"\n'
        )
        return subprocess.run(["sh", "-c", stub], capture_output=True, text=True, timeout=60)

    def test_the_installer_accepts_files_extracted_without_the_exec_bit(self):
        # KernelSU-Next extracts the zip without file modes; customize.sh sets them in step 4.
        # A device install failed on "has no bin/zcored" when step 2 tested -x (2026-10-23).
        for f in (self.mod / "bin").iterdir():
            f.chmod(0o644)
        r = self.run_installer("[3/5]")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("files match SHA256SUMS", r.stdout)
        self.assertNotIn("incomplete", r.stdout)

    def test_the_installer_refuses_a_package_without_zcored(self):
        (self.mod / "bin/zcored").unlink()
        r = self.run_installer("[3/5]")
        self.assertEqual(r.returncode, 1)
        self.assertIn("nothing was installed", r.stdout)

    def test_no_exec_bit_is_tested_before_the_permissions_step(self):
        customize = (ROOT / "module/customize.sh").read_text()
        before = customize[:customize.index('ui_print "[4/5] Permissions"')]
        self.assertNotIn('-x "$MODPATH', before)

    def test_a_modified_binary_is_refused(self):
        (self.mod / "bin/zfasd").write_bytes(b"\x7fELF replaced")
        for mode in ("install", "runtime"):
            r = self.verify(mode)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(r.stdout, "modified: bin/zfasd\n")

    def test_a_modified_script_is_refused(self):
        with open(self.mod / "service.sh", "a") as f:
            f.write("\nid\n")
        self.assertEqual(self.verify("runtime").stdout, "modified: service.sh\n")

    def test_an_added_executable_is_refused(self):
        (self.mod / "bin/helper").write_bytes(b"x")
        (self.mod / "webroot/extra.js").write_text("x")
        (self.mod / "post-fs-data.sh").write_text("x")
        for mode in ("install", "runtime"):
            r = self.verify(mode)
            self.assertEqual(r.returncode, 1)
            self.assertEqual(sorted(r.stdout.splitlines()), [
                "unexpected file: bin/helper", "unexpected file: post-fs-data.sh",
                "unexpected file: webroot/extra.js"])

    def test_a_symlink_is_never_followed(self):
        target = Path(self.tmp.name) / "copy"
        shutil.copy(self.mod / "bin/zcored", target)  # same bytes, but through a link
        (self.mod / "bin/zcored").unlink()
        (self.mod / "bin/zcored").symlink_to(target)
        self.assertEqual(self.verify("runtime").stdout, "missing: bin/zcored\n")

    def test_unsafe_or_malformed_lines_fail(self):
        sums = self.mod / "SHA256SUMS"
        original = sums.read_text()
        for line, message in [
            ("0" * 64 + "  ../../etc/passwd", "unsafe path in SHA256SUMS: ../../etc/passwd"),
            ("0" * 64 + "  /system/bin/sh", "unsafe path in SHA256SUMS: /system/bin/sh"),
            ("0" * 64 + "  bin/../../x", "unsafe path in SHA256SUMS: bin/../../x"),
            ("XYZ  bin/zcored", "SHA256SUMS has a malformed line"),
            ("0" * 64 + " bin/zcored", "SHA256SUMS has a malformed line"),
        ]:
            sums.write_text(original + line + "\n")
            r = self.verify("runtime")
            self.assertEqual(r.returncode, 1, line)
            self.assertIn(message, r.stdout.splitlines(), line)
        sums.unlink()
        self.assertEqual(self.verify("runtime").stdout, "SHA256SUMS is missing\n")

    def test_runtime_check_allows_what_the_manager_changes(self):
        # The status line in module.prop, the removed installer and the manager's markers.
        sh('zr_status "$1" "Running: zcored"', str(self.mod))
        (self.mod / "customize.sh").unlink()
        for marker in ("disable", "remove", "update", "skip_mount"):
            (self.mod / marker).write_text("")
        (self.mod / "README.md").write_text("added by a manager")
        self.assertEqual(self.verify("runtime").returncode, 0, self.verify("runtime").stdout)
        r = self.verify("install")
        self.assertEqual(r.returncode, 1)
        self.assertIn("modified: module.prop", r.stdout)
        self.assertIn("missing: customize.sh", r.stdout)
        self.assertIn("unexpected file: disable", r.stdout)


class HelpersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_status_replaces_only_the_description(self):
        prop = self.dir / "module.prop"
        prop.write_text("id=zairenkai\nname=Zairenkai\nversion=v0.3.0\nversionCode=300\n"
                        "description=One module for the Zairenkai system. Data in /data/adb/zairenkai.\n")
        for text in ("Starting", "Running: zcored, zfasd | files verified", "Blocked: a/b & c"):
            r = sh('zr_status "$1" "$2"', str(self.dir), text)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(prop.read_text(), (
            "id=zairenkai\nname=Zairenkai\nversion=v0.3.0\nversionCode=300\n"
            "description=[Blocked: a/b & c] One module for the Zairenkai system. Data in /data/adb/zairenkai.\n"))
        self.assertEqual(oct(prop.stat().st_mode & 0o777), "0o644")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["module.prop"])

    def test_status_leaves_a_symlinked_prop_alone(self):
        real = self.dir / "elsewhere"
        real.write_text("description=x\n")
        (self.dir / "module.prop").symlink_to(real)
        sh('zr_status "$1" "Running"', str(self.dir))
        self.assertEqual(real.read_text(), "description=x\n")

    def test_safe_dir_refuses_a_symlink(self):
        target = self.dir / "target"
        target.mkdir()
        (self.dir / "data").symlink_to(target)
        self.assertEqual(sh('zr_safe_dir "$1"', str(self.dir / "data")).returncode, 1)
        r = sh('zr_safe_dir "$1"', str(self.dir / "fresh/core"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(oct((self.dir / "fresh/core").stat().st_mode & 0o777), "0o700")

    def test_own_pids_ignores_other_processes_with_the_same_name(self):
        # Keep an executable alive at two distinct paths. Copying the host's `sleep` binary and
        # renaming it to zfasd is not portable: multicall coreutils resolves its applet from argv[0]
        # and exits with "unknown program zfasd" on some runners.
        executable = Path(sys.executable).resolve()
        mine, other = self.dir / "mod/bin/zfasd", self.dir / "other/bin/zfasd"
        for p in (mine, other):
            p.parent.mkdir(parents=True)
            shutil.copy(executable, p)
        sleeper = ["-c", "import time; time.sleep(30)"]
        a = subprocess.Popen([str(mine), *sleeper])
        b = subprocess.Popen([str(other), *sleeper])
        try:
            time.sleep(0.3)
            r = sh('zr_own_pids zfasd "$1"', str(mine))
            self.assertEqual(r.stdout.split(), [str(a.pid)])
        finally:
            for p in (a, b):
                p.kill()
                p.wait()

    def test_scripts_use_the_guards(self):
        service = (ROOT / "module/service.sh").read_text()
        uninstall = (ROOT / "module/uninstall.sh").read_text()
        customize = (ROOT / "module/customize.sh").read_text()
        # Boot: files are checked before any daemon starts.
        self.assertLess(service.index('zr_verify "$MODDIR" runtime'), service.index('supervise zcored "$DATA/core"'))
        self.assertIn("exit 1", service[:service.index("supervise() {")])
        # Install: the package is checked before anything is written outside the module.
        self.assertLess(customize.index('zr_verify "$MODPATH" install'), customize.index("zr_data_dirs"))
        # Uninstall: only this module's processes, and a symlinked data directory is not followed.
        self.assertNotIn("$(pidof", uninstall)
        self.assertIn('zr_own_pids "$1" "$bin"', uninstall)
        self.assertLess(uninstall.index('if [ -L "$DATA" ]'), uninstall.index('rm -rf "$DATA"'))
        for s in (service, uninstall, customize):
            self.assertIn("umask 077", s)


if __name__ == "__main__":
    unittest.main()
