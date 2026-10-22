# Compatibility

| Item | Requirement | Status |
|---|---|---|
| ABI | arm64-v8a only | Enforced by `customize.sh`. |
| Android | API 29 (Android 10) or newer | Enforced by `customize.sh`; the binaries link against API 29. |
| Page size | 4 KB and 16 KB | Each component's build checks for 16 KB-aligned LOAD segments. |
| Magisk | v20.4 or newer (`update-binary` uses `install_module`) | **Unverified** on a device. |
| KernelSU / KernelSU-Next | Module format and WebUI | **Unverified** on a device. |
| APatch | Module format | **Unverified** on a device. |
| Devices | Any; features depend on the kernel interfaces each daemon probes | **Unverified**: no device has run this module. |

Verified so far, without a device: the scripts pass shellcheck, and the assembler is tested with
stand-in components (`tests/test_assemble.py`). A module built from the real components exists
only once the CI `module` job has run.
