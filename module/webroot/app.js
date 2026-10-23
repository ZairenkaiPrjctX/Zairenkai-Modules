// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 ZairenkaiPrjctX contributors
//
// Zairenkai WebUI (KernelSU / APatch). Every command this page can run is built below from
// constants and allowlisted values; nothing typed or read from a daemon becomes part of a
// command, except a Core lease id after it parsed as a plain integer. Daemon output is shown with
// textContent only. Changes go through Core (zcored ctl submit: a dry run first, then the change
// once the user confirmed Core's decision). Only when Core does not answer can zfasd be driven
// directly, and then each change asks for confirmation.
"use strict";

const MOD = "/data/adb/modules/zairenkai";
const DATA = "/data/adb/zairenkai";
const ZCORED = `${MOD}/bin/zcored ctl --dir ${DATA}/core`;
const ZFASD = `${MOD}/bin/zfasd ctl --dir ${DATA}/fas`;
const PROFILES = Object.freeze([
  ["power_saver", "Power saver"],
  ["balanced", "Balanced"],
  ["performance", "Performance"],
  ["fast_response", "Fast response"],
  ["adaptive", "Adaptive"],
]);
const PROFILE_IDS = PROFILES.map((p) => p[0]);
const CMD = Object.freeze({
  health: `${ZCORED} health`,
  leases: `${ZCORED} leases`,
  fasStatus: `${ZFASD} status`,
  verify: `${MOD}/verify.sh`,
  components: `cat ${MOD}/components.json`,
  version: `sed -n s/^version=//p ${MOD}/module.prop`,
  log: Object.freeze({ core: `tail -n 80 ${DATA}/core/zcored.log`, fas: `tail -n 80 ${DATA}/fas/zfasd.log` }),
});
/** zcored ctl exits 2 when its socket does not answer. */
const CORE_UNREACHABLE = 2;
/** A command argument may only hold these characters: no quote, backslash, $, `, ; or newline. */
const SAFE_ARG = /^[A-Za-z0-9_{}":,. -]*$/;
const EXEC_TIMEOUT_MS = 20000;

// ---- Commands -----------------------------------------------------------------------------

/** The Core operation for a FAS change, or null when the value is not allowed. */
function operation(kind, value) {
  if (kind === "profile" && PROFILE_IDS.includes(value)) return { op: "fas_set_profile", profile: value };
  if (kind === "enabled" && typeof value === "boolean") return { op: "fas_set_enabled", enabled: value };
  return null;
}

function quoted(json) {
  if (!SAFE_ARG.test(json)) throw new Error("refused an unsafe argument");
  return `'${json}'`;
}

/** `zcored ctl submit` for an operation; a dry run unless the user confirmed. */
function submitCommand(op, confirmed) {
  if (!op) throw new Error("no operation");
  const params = { operation: op, reason: "KernelSU WebUI" };
  if (confirmed) params.confirmed = true;
  else params.dry_run = true;
  return `${ZCORED} submit ${quoted(JSON.stringify(params))}`;
}

/** `zcored ctl release` for a lease id read from Core (an integer, nothing else). */
function releaseCommand(leaseId) {
  if (!Number.isSafeInteger(leaseId) || leaseId < 0) throw new Error("invalid lease id");
  return `${ZCORED} release ${quoted(JSON.stringify({ lease_id: leaseId }))}`;
}

/** Direct `zfasd ctl` for when Core does not answer. */
function fasDirectCommand(action, profile) {
  if (action === "profile") {
    if (!PROFILE_IDS.includes(profile)) throw new Error("invalid profile");
    return `${ZFASD} profile ${profile}`;
  }
  if (["enable", "disable", "reset"].includes(action)) return `${ZFASD} ${action}`;
  throw new Error("invalid action");
}

// ---- Parsing ------------------------------------------------------------------------------

/** A zcored ctl reply: {ok, result} or {ok: false, error}. */
function parseCore(r) {
  if (r.errno === CORE_UNREACHABLE) return { ok: false, unreachable: true, error: "Core is not answering" };
  let v;
  try {
    v = JSON.parse(r.stdout);
  } catch (e) {
    return { ok: false, error: (r.stderr || r.stdout || "no reply").trim().slice(0, 300) };
  }
  if (v && v.ok === true) return { ok: true, result: v.result };
  const err = v && v.error ? `${v.error.code}: ${v.error.message}` : "unexpected reply";
  return { ok: false, error: err };
}

function parseJson(text) {
  try {
    return JSON.parse(text);
  } catch (e) {
    return null;
  }
}

function duration(ms) {
  if (typeof ms !== "number" || ms < 0) return "–";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return h < 48 ? `${h} h ${m % 60} min` : `${Math.floor(h / 24)} d ${h % 24} h`;
}

/** Tile and pill for Core's health. */
function summarizeHealth(core) {
  if (!core) return { tone: "neutral", glyph: "…", value: "Checking", caption: "" };
  if (core.unreachable) return { tone: "bad", glyph: "✕", value: "Not answering", caption: "zcored is not running" };
  if (!core.ok) return { tone: "bad", glyph: "✕", value: "Error", caption: core.error };
  const h = core.result || {};
  const reasons = Array.isArray(h.reasons) ? h.reasons.length : 0;
  if (h.state === "ready") {
    return { tone: "good", glyph: "✓", value: "Ready", caption: `up ${duration(h.uptime_ms)} · ${h.leases || 0} active change(s)` };
  }
  return {
    tone: "warn",
    glyph: "!",
    value: h.state === "degraded" ? "Degraded" : String(h.state || "Unknown"),
    caption: `${reasons} reason(s) · up ${duration(h.uptime_ms)}`,
  };
}

/** Tile for zfasd's status document. */
function summarizeFas(fas) {
  if (!fas) return { tone: "neutral", value: "–", caption: "" };
  if (fas.error) return { tone: "bad", value: "Not answering", caption: fas.error };
  const s = fas.status;
  const on = s.enabled === true;
  const fps = s.step && s.step.stats && typeof s.step.stats.fps === "number" ? `${s.step.stats.fps.toFixed(0)} fps` : "no frames";
  return {
    tone: on ? "good" : "neutral",
    value: on ? "On" : "Off",
    caption: on ? `${label(s.profile)} · ${s.observe_only ? "observe only" : fps}` : "switched off",
  };
}

function label(profile) {
  const p = PROFILES.find((x) => x[0] === profile);
  return p ? p[1] : String(profile || "–");
}

/** The rows of the Live card from zfasd's status. */
function liveFacts(s) {
  const st = s.step || {};
  const d = st.decision || {};
  const w = st.stats || {};
  const ms = (ns) => (typeof ns === "number" ? `${(ns / 1e6).toFixed(1)} ms` : null);
  return [
    ["Mode", s.observe_only ? "observe only (no writes)" : "control"],
    ["App", s.package],
    ["State", d.state],
    ["Reason", d.reason],
    ["Target", typeof st.target_fps === "number" ? `${st.target_fps} fps` : null],
    ["Measured", typeof w.fps === "number" ? `${w.fps.toFixed(1)} fps` : null],
    ["P95 frame", ms(w.p95_ns)],
    ["Missed", typeof w.miss_ratio === "number" ? `${(w.miss_ratio * 100).toFixed(1)} %` : null],
    ["Bottleneck (est.)", d.bottleneck],
    ["Thermal", st.thermal ? `${st.thermal.reason} (cap ${st.thermal.level_cap})` : null],
    ["Levels", (s.domains || []).map((x) => `${String(x.id).replace("cpufreq/", "")}=${x.level}`).join("  ") || null],
    ["Telemetry", s.telemetry_error || (s.layer ? `SurfaceFlinger: ${s.layer}` : null)],
  ];
}

/** components.json → [{name, version, commit, license, source}]. */
function parseComponents(text) {
  const v = parseJson(text);
  if (!v || typeof v.components !== "object" || v.components === null) return null;
  return {
    version: v.version,
    items: Object.entries(v.components).map(([name, c]) => ({
      name,
      version: c.version,
      commit: typeof c.commit === "string" ? c.commit.slice(0, 12) : "",
      binary: c.binary,
      license: c.license || "Apache-2.0",
      source: c.source || null,
    })),
  };
}

// ---- KernelSU bridge ------------------------------------------------------------------------

let seq = 0;
/** Runs one command through KernelSU's WebUI bridge; never rejects. */
function run(cmd) {
  return new Promise((resolve) => {
    const api = typeof ksu !== "undefined" ? ksu : null;
    if (!api || typeof api.exec !== "function") {
      resolve({ errno: -1, stdout: "", stderr: "Open this page from KernelSU or APatch" });
      return;
    }
    const cb = `zr_cb_${Date.now()}_${seq++}`;
    const timer = setTimeout(() => {
      delete window[cb];
      resolve({ errno: -2, stdout: "", stderr: "no answer within 20 s" });
    }, EXEC_TIMEOUT_MS);
    window[cb] = (errno, stdout, stderr) => {
      clearTimeout(timer);
      delete window[cb];
      resolve({ errno, stdout: String(stdout || ""), stderr: String(stderr || "") });
    };
    try {
      api.exec(cmd, "{}", cb);
    } catch (e) {
      clearTimeout(timer);
      delete window[cb];
      resolve({ errno: -1, stdout: "", stderr: String(e) });
    }
  });
}

// ---- Page ---------------------------------------------------------------------------------

const state = { core: null, fas: null, busy: false, log: "core", timer: null };

function $(id) {
  return document.getElementById(id);
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = String(text);
  return e;
}

function setPill(node, tone, glyph, text) {
  node.dataset.tone = tone;
  node.querySelector(".glyph").textContent = glyph;
  node.querySelector(".label").textContent = text;
}

function setTile(id, s) {
  const t = $(id);
  t.dataset.tone = s.tone;
  t.querySelector(".value").textContent = s.value;
  t.querySelector(".caption").textContent = s.caption || "";
}

let toastTimer = null;
function toast(text) {
  const t = $("toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 4000);
}

function setBusy(busy) {
  state.busy = busy;
  document.querySelectorAll("#profiles .seg, #fas-toggle, #fas-reset, #leases button").forEach((b) => {
    b.disabled = busy || !controlsAvailable();
  });
}

function controlsAvailable() {
  return Boolean(state.fas && state.fas.status) || Boolean(state.core && state.core.ok);
}

function coreDown() {
  return Boolean(state.core && state.core.unreachable);
}

function renderOverall() {
  const h = summarizeHealth(state.core);
  setTile("t-core", h);
  setPill($("overall"), h.tone, h.glyph, h.tone === "good" ? "Running" : h.value);
  $("core-down").hidden = !coreDown();
  $("direct-actions").hidden = !coreDown();
}

function renderFas() {
  setTile("t-fas", summarizeFas(state.fas));
  const s = state.fas && state.fas.status;
  const toggle = $("fas-toggle");
  toggle.setAttribute("aria-checked", s && s.enabled ? "true" : "false");
  $("fas-switch-caption").textContent = !s
    ? "zfasd is not answering."
    : s.enabled
      ? "On: raises CPU frequency floors when frames run late."
      : "Off: zfasd runs but boosts nothing.";
  document.querySelectorAll("#profiles .seg").forEach((b) => {
    b.setAttribute("aria-checked", s && b.dataset.profile === s.profile ? "true" : "false");
  });
  const live = $("live");
  live.replaceChildren();
  if (!s) {
    live.append(el("dt", null, "zfasd"), el("dd", null, state.fas ? state.fas.error : "loading…"));
  } else {
    for (const [k, v] of liveFacts(s)) {
      live.append(el("dt", null, k), el("dd", null, v === null || v === undefined || v === "" ? "–" : v));
    }
  }
  setBusy(state.busy);
}

function renderLeases(core) {
  const ul = $("leases");
  ul.replaceChildren();
  if (!core || !core.ok || !Array.isArray(core.result)) {
    ul.append(el("li", "empty", core && core.unreachable ? "Core is not answering." : "–"));
    return;
  }
  if (core.result.length === 0) {
    ul.append(el("li", "empty", "None: every resource holds its own value."));
    return;
  }
  for (const l of core.result) {
    const li = el("li");
    const row = el("div", "row");
    const text = el("div");
    text.append(el("p", "title", `${l.resource}: ${JSON.stringify(l.value)}`));
    const until = typeof l.expires_at_ms === "number" ? "until it expires" : "until released";
    text.append(el("p", "sub", `by ${l.owner} · ${l.tier} · ${until}`));
    const b = el("button", "tonal", "Release");
    b.addEventListener("click", () => release(l.id));
    row.append(text, b);
    li.append(row);
    ul.append(li);
  }
  setBusy(state.busy);
}

async function refresh() {
  const [h, f, l] = await Promise.all([run(CMD.health), run(CMD.fasStatus), run(CMD.leases)]);
  state.core = parseCore(h);
  const fs = parseJson(f.stdout);
  state.fas = f.errno === 0 && fs ? { status: fs } : { error: (f.stderr || f.stdout || "not answering").trim().slice(0, 200) };
  renderOverall();
  renderFas();
  renderLeases(parseCore(l));
}

// ---- Actions ------------------------------------------------------------------------------

function ask(title, body, rules, okText) {
  return new Promise((resolve) => {
    const d = $("confirm");
    $("confirm-title").textContent = title;
    $("confirm-body").textContent = body;
    const ul = $("confirm-rules");
    ul.replaceChildren();
    for (const r of rules) ul.append(el("li", null, r));
    $("confirm-ok").textContent = okText;
    // A refusal is information only: one button.
    $("confirm-cancel").hidden = okText === "OK";
    const done = (v) => {
      $("confirm-ok").onclick = null;
      $("confirm-cancel").onclick = null;
      d.close();
      resolve(v);
    };
    $("confirm-ok").onclick = () => done(true);
    $("confirm-cancel").onclick = () => done(false);
    d.oncancel = () => done(false);
    d.showModal();
  });
}

/** Dry run through Core, show its decision, then apply once the user agrees. */
async function change(op, what) {
  if (state.busy) return;
  setBusy(true);
  try {
    if (coreDown()) {
      const direct = op.op === "fas_set_profile" ? fasDirectCommand("profile", op.profile) : fasDirectCommand(op.enabled ? "enable" : "disable");
      const ok = await ask(what, "Core is not answering, so this goes to zfasd directly, without Core's policy checks.", [], "Apply directly");
      if (!ok) return;
      const r = await run(direct);
      toast(r.errno === 0 ? "Done (zfasd)." : `zfasd refused: ${(r.stdout || r.stderr).trim().slice(0, 160)}`);
      return;
    }
    const plan = parseCore(await run(submitCommand(op, false)));
    if (!plan.ok) {
      toast(`Core: ${plan.error}`);
      return;
    }
    const p = plan.result || {};
    const rules = ((p.decision && p.decision.rules) || []).map((r) => `${r.verdict === "allow" ? "✓" : r.verdict === "deny" ? "✕" : "!"} ${r.explanation}`);
    if (p.outcome !== "dry_run") {
      await ask(what, `Core would not do this (${p.outcome}): ${p.message}`, rules, "OK");
      return;
    }
    const risk = p.plan && p.plan.risk ? ` Risk: ${p.plan.risk}.` : "";
    if (!(await ask(what, `Core's policy allows it.${risk}`, rules, "Apply"))) return;
    const done = parseCore(await run(submitCommand(op, true)));
    if (!done.ok) toast(`Core: ${done.error}`);
    else toast(`${done.result.outcome}: ${done.result.message}`);
  } catch (e) {
    toast(String(e.message || e));
  } finally {
    setBusy(false);
    refresh();
  }
}

async function release(leaseId) {
  if (state.busy) return;
  setBusy(true);
  try {
    const r = parseCore(await run(releaseCommand(leaseId)));
    toast(r.ok ? `${r.result.outcome}: ${r.result.message}` : `Core: ${r.error}`);
  } catch (e) {
    toast(String(e.message || e));
  } finally {
    setBusy(false);
    refresh();
  }
}

async function resetDirect() {
  if (state.busy || !coreDown()) return;
  if (!(await ask("Release FAS boosts?", "zfasd drops its frequency floors now. Core is not answering, so this goes to zfasd directly.", [], "Release"))) return;
  setBusy(true);
  const r = await run(fasDirectCommand("reset"));
  toast(r.errno === 0 ? "Boosts released." : `zfasd refused: ${(r.stdout || r.stderr).trim().slice(0, 160)}`);
  setBusy(false);
  refresh();
}

async function verify() {
  setPill($("integrity"), "neutral", "…", "Checking");
  const r = await run(CMD.verify);
  const ul = $("integrity-problems");
  ul.replaceChildren();
  const lines = (r.stdout || "").trim().split("\n").filter(Boolean);
  if (r.errno === 0) {
    setPill($("integrity"), "good", "✓", lines[0] || "verified");
    setTile("t-files", { tone: "good", value: "Verified", caption: "match SHA256SUMS" });
  } else {
    const n = lines.length;
    setPill($("integrity"), "bad", "✕", r.errno < 0 ? r.stderr : `${n} problem(s)`);
    setTile("t-files", { tone: "bad", value: "Changed", caption: `${n} problem(s)` });
    for (const line of lines.slice(0, 30)) ul.append(el("li", null, line));
  }
}

async function components() {
  const [r, v] = await Promise.all([run(CMD.components), run(CMD.version)]);
  const c = r.errno === 0 ? parseComponents(r.stdout) : null;
  const ul = $("components");
  ul.replaceChildren();
  $("version").textContent = v.errno === 0 && v.stdout.trim() ? `System module ${v.stdout.trim()}` : "System module";
  if (!c) {
    ul.append(el("li", "empty", "components.json is unreadable."));
    setTile("t-tuning", { tone: "neutral", value: "–", caption: "" });
    return;
  }
  for (const i of c.items) {
    const li = el("li");
    li.append(el("p", "title", `${i.name} ${i.version}`));
    li.append(el("p", "sub", `${i.binary} · ${i.license} · commit ${i.commit}`));
    if (i.source) li.append(el("p", "sub", `Source: ${i.source}`));
    ul.append(li);
  }
  const tuning = c.items.find((i) => i.name === "zairenkai-tuning");
  setTile("t-tuning", tuning
    ? { tone: "neutral", value: tuning.version, caption: "ztune · run by Core only" }
    : { tone: "neutral", value: "Not included", caption: "" });
}

async function showLog(which) {
  state.log = which;
  $("log-core").setAttribute("aria-selected", which === "core" ? "true" : "false");
  $("log-fas").setAttribute("aria-selected", which === "fas" ? "true" : "false");
  const r = await run(CMD.log[which]);
  $("log").textContent = r.errno === 0 ? r.stdout || "(empty)" : (r.stderr || "no log yet").trim();
}

function start() {
  const seg = $("profiles");
  for (const [id, name] of PROFILES) {
    const b = el("button", "seg", name);
    b.dataset.profile = id;
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", "false");
    b.addEventListener("click", () => change(operation("profile", id), `Switch FAS to ${name}?`));
    seg.append(b);
  }
  $("fas-toggle").addEventListener("click", () => {
    const on = $("fas-toggle").getAttribute("aria-checked") === "true";
    change(operation("enabled", !on), on ? "Switch FAS off?" : "Switch FAS on?");
  });
  $("fas-reset").addEventListener("click", resetDirect);
  $("verify").addEventListener("click", verify);
  $("log-core").addEventListener("click", () => showLog("core"));
  $("log-fas").addEventListener("click", () => showLog("fas"));
  refresh();
  verify();
  components();
  showLog("core");
  const poll = () => {
    clearInterval(state.timer);
    state.timer = document.hidden ? null : setInterval(refresh, 5000);
  };
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh();
    poll();
  });
  poll();
}

if (typeof module === "object" && module.exports) {
  module.exports = { CMD, PROFILES, SAFE_ARG, operation, submitCommand, releaseCommand, fasDirectCommand, parseCore, summarizeHealth, summarizeFas, liveFacts, parseComponents, duration };
}
if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", start);
