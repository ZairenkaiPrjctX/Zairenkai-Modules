# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 ZairenkaiPrjctX contributors
"""The KernelSU WebUI: a strict Content-Security-Policy, no inline code, no HTML built from daemon
output, and only fixed or allowlisted commands (tests/webui_check.js runs the builders)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "module" / "webroot"
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "connect-src 'none'; font-src 'none'; object-src 'none'; frame-src 'none'; "
       "base-uri 'none'; form-action 'none'")


class WebUiTest(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text()
        self.js = (WEB / "app.js").read_text()

    def test_strict_content_security_policy(self):
        m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', self.html)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), CSP)
        # The policy must come before anything it governs.
        self.assertLess(m.start(), self.html.index("<link"))
        self.assertLess(m.start(), self.html.index("<script"))

    def test_no_inline_code_or_style(self):
        scripts = re.findall(r"<script\b([^>]*)>(.*?)</script>", self.html, re.S)
        self.assertEqual(scripts, [(' src="app.js" defer', "")])
        self.assertNotRegex(self.html, r"\son[a-z]+\s*=", "inline event handler")
        self.assertNotRegex(self.html, r"\sstyle\s*=", "inline style attribute")
        self.assertNotIn("<style", self.html)
        self.assertNotIn("javascript:", self.html + self.js)

    def test_hidden_wins_over_display_rules(self):
        # The Core-down banner and direct actions are toggled with the hidden attribute; a class
        # with display: flex would otherwise show them while Core answers.
        css = (WEB / "style.css").read_text()
        self.assertIn("[hidden] { display: none !important; }", css)

    def test_nothing_is_fetched_from_the_network(self):
        for f in WEB.iterdir():
            text = f.read_text()
            urls = set(re.findall(r"https?://[^\s\"')]+", text)) - {"http://www.w3.org/2000/svg"}
            self.assertEqual(urls, set(), f.name)
        self.assertNotRegex(self.js, r"\b(fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon)\b")

    def test_daemon_output_never_becomes_html_or_code(self):
        for api in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                    "new Function", "setTimeout(\"", "setInterval(\""):
            self.assertNotIn(api, self.js, api)

    def test_commands_come_only_from_constants_and_builders(self):
        calls = re.findall(r"(?<!function )\brun\(([^)]*\)?)\)", self.js)
        self.assertTrue(calls)
        allowed = re.compile(
            r"(CMD\.[a-zA-Z]+(\[which\])?|CMD\.log\[which\]|direct|submitCommand\(op, (true|false)\)"
            r"|releaseCommand\(leaseId\)|fasDirectCommand\(\"reset\"\))$")
        for c in calls:
            self.assertRegex(c, allowed, c)
        # ksu.exec is reached only through run().
        self.assertEqual(len(re.findall(r"\.exec\(", self.js)), 1)

    def test_changes_go_through_core_first(self):
        # The direct zfasd path exists only for when Core does not answer, and asks first.
        body = self.js[self.js.index("async function change"):self.js.index("async function release")]
        self.assertLess(body.index("if (coreDown())"), body.index("submitCommand(op, false)"))
        self.assertLess(body.index("submitCommand(op, false)"), body.index("submitCommand(op, true)"))
        self.assertLess(body.index("await ask("), body.index("await run(direct)"))

    def test_builders_and_parsers_with_captured_output(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is not installed")
        r = subprocess.run([node, str(ROOT / "tests" / "webui_check.js")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("webui ok", r.stdout)


if __name__ == "__main__":
    unittest.main()
