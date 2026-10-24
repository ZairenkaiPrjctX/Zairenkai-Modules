# Captured daemon output

Real output of `zcored ctl` and `zfasd ctl`, captured on a Linux host (no Android services, so
device inputs report unavailable) by Zairenkai-App's `integration/scripts/capture-contracts.sh`
and copied unchanged from Zairenkai-App `integration-core/src/test/resources/contracts/` at
`e1ca387`. Never edit these files; re-copy them after a new capture.

| File | Source | Binary commit | SHA-256 |
|---|---|---|---|
| `core-health.json` | `zcored ctl health` (`contracts/core/health.json`) | zcored `8931cbb` | `080f9041963ad37b421a61117e778986ffa7d1467783a5eb9af63ed7f49e6431` |
| `core-submit-dry-run.json` | `zcored ctl submit` (dry run) (`contracts/core/submit-dry-run.json`) | zcored `8931cbb` | `d15e4df2c3694a52caf9556366cd609a1efcd163d2bdc93b2f64f4adccc7ae5f` |
| `core-leases.json` | `zcored ctl leases` (`contracts/core/leases.json`) | zcored `8931cbb` | `f95e6e4e7bdd25c519c645da9211b78ad308da9a103332c65e397e6733ffb4b0` |
| `fas-status.json` | `zfasd ctl status` (`contracts/fas/status.json`) | zfasd `99cfb18` | `85442cccd9ce982b79b1ac07e17a3a00b611229d0703c0d10e5dc8580ae2caa7` |
