// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZairenkaiPrjctX contributors
// Behaviour of the WebUI's command builders and parsers, run by tests/test_webui.py with Node.
// The daemon replies are real captured output (tests/fixtures/captured/SOURCES.md).
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ui = require("../module/webroot/app.js");

const fixture = (name) => fs.readFileSync(path.join(__dirname, "fixtures", "captured", name), "utf8");
const ok = (name) => ({ errno: 0, stdout: fixture(name), stderr: "" });
const CORE = "/data/adb/modules/zairenkai/bin/zcored ctl --dir /data/adb/zairenkai/core";
const FAS = "/data/adb/modules/zairenkai/bin/zfasd ctl --dir /data/adb/zairenkai/fas";

// Fixed read-only commands.
assert.equal(ui.CMD.health, `${CORE} health`);
assert.equal(ui.CMD.fasStatus, `${FAS} status`);
assert.equal(ui.CMD.verify, "/data/adb/modules/zairenkai/verify.sh");
for (const cmd of [ui.CMD.health, ui.CMD.leases, ui.CMD.fasStatus, ui.CMD.verify, ui.CMD.components, ui.CMD.version, ui.CMD.log.core, ui.CMD.log.fas]) {
  assert.doesNotMatch(cmd, /[;&|`$<>]/, cmd);
}

// Changes go through Core: a dry run first, the change only with the user's confirmation.
const op = ui.operation("profile", "performance");
assert.deepEqual(op, { op: "fas_set_profile", profile: "performance" });
assert.equal(
  ui.submitCommand(op, false),
  `${CORE} submit '{"operation":{"op":"fas_set_profile","profile":"performance"},"reason":"KernelSU WebUI","dry_run":true}'`,
);
assert.equal(
  ui.submitCommand(ui.operation("enabled", false), true),
  `${CORE} submit '{"operation":{"op":"fas_set_enabled","enabled":false},"reason":"KernelSU WebUI","confirmed":true}'`,
);
// Anything outside the allowlists builds no command.
for (const bad of ["turbo", "balanced; reboot", "'$(id)'", "", null]) {
  assert.equal(ui.operation("profile", bad), null);
  assert.throws(() => ui.fasDirectCommand("profile", bad));
}
assert.equal(ui.operation("enabled", "true"), null);
assert.equal(ui.operation("governor", "performance"), null);
assert.throws(() => ui.submitCommand(null, false));
assert.throws(() => ui.fasDirectCommand("rm -rf /"));
assert.equal(ui.fasDirectCommand("reset"), `${FAS} reset`);
assert.equal(ui.fasDirectCommand("profile", "balanced"), `${FAS} profile balanced`);
// Lease ids come from Core's output, so only a plain integer passes.
assert.equal(ui.releaseCommand(7), `${CORE} release '{"lease_id":7}'`);
for (const bad of ["7", 1.5, -1, NaN, "1'; reboot; '", { id: 1 }]) assert.throws(() => ui.releaseCommand(bad));
assert.match('{"a":"b c","d":true}', ui.SAFE_ARG);
for (const s of ["'", "$", "`", "\\", ";", "\n", "&", "|"]) assert.doesNotMatch(`x${s}`, ui.SAFE_ARG);

// Core replies.
const health = ui.parseCore(ok("core-health.json"));
assert.equal(health.ok, true);
const h = ui.summarizeHealth(health);
assert.equal(h.tone, "warn");
assert.equal(h.value, "Degraded");
assert.match(h.caption, /^3 reason\(s\) · up 0 s$/);
const down = ui.parseCore({ errno: 2, stdout: "", stderr: "ctl: cannot reach zcored" });
assert.equal(down.unreachable, true);
assert.equal(ui.summarizeHealth(down).value, "Not answering");
const refused = ui.parseCore({ errno: 1, stdout: '{"v":1,"id":"x","ok":false,"error":{"code":"busy","message":"try later"}}', stderr: "" });
assert.deepEqual(refused, { ok: false, error: "busy: try later" });
assert.equal(ui.parseCore({ errno: 1, stdout: "garbage", stderr: "" }).ok, false);

const plan = ui.parseCore(ok("core-submit-dry-run.json"));
assert.equal(plan.result.outcome, "rejected");
assert.equal(plan.result.decision.rules.filter((r) => r.verdict === "deny").length, 2);
assert.deepEqual(ui.parseCore(ok("core-leases.json")), { ok: true, result: [] });

// zfasd status.
const status = JSON.parse(fixture("fas-status.json"));
const fas = ui.summarizeFas({ status });
assert.equal(fas.value, "On");
assert.match(fas.caption, /^Balanced · observe only$/);
const facts = Object.fromEntries(ui.liveFacts(status));
assert.equal(facts.State, "telemetry_unavailable");
assert.equal(facts.Mode, "observe only (no writes)");
assert.equal(facts.Measured, null);
assert.equal(ui.summarizeFas({ error: "no socket" }).value, "Not answering");

// components.json as assemble.py writes it.
const comps = ui.parseComponents(JSON.stringify({
  format: 1, module: "zairenkai", version: "0.3.0",
  components: {
    "zairenkai-core": { version: "0.1.0", repository: "r", commit: "a".repeat(40), binary: "bin/zcored", sha256: "0" },
    "zairenkai-tuning": { version: "0.1.0", repository: "r", commit: "d".repeat(40), binary: "bin/ztune", sha256: "0", license: "GPL-3.0-only", source: "source/zairenkai-tuning/x.tar.gz" },
  },
}));
assert.equal(comps.items.length, 2);
assert.equal(comps.items[0].license, "Apache-2.0");
assert.equal(comps.items[0].commit, "aaaaaaaaaaaa");
assert.equal(comps.items[1].source, "source/zairenkai-tuning/x.tar.gz");
assert.equal(ui.parseComponents("not json"), null);

assert.equal(ui.duration(3_700_000), "1 h 1 min");
assert.equal(ui.duration(undefined), "–");
console.log("webui ok");
