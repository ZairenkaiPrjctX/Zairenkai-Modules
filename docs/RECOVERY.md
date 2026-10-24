# Disable, uninstall and recovery

| Goal | How | Effect |
|---|---|---|
| Stop everything until re-enabled | Disable `zairenkai` in the root manager, reboot | `service.sh` starts nothing while `disable` exists. FAS frequency floors are not persistent, so a reboot clears them. |
| Remove | Remove `zairenkai` in the root manager, reboot | `uninstall.sh` stops zfasd and runs `zfasd restore`, stops zcored (it restores temporary overrides on SIGTERM), then deletes `/data/adb/zairenkai`. If the FAS restore fails, `/data/adb/zairenkai/fas` is kept and the failure is logged to `/data/adb/zairenkai-uninstall.log`. |
| The manager shows "Blocked: files changed since install" | Read `/data/adb/zairenkai/integrity.log`, then reinstall the module from the Zairenkai app | A file of the module no longer matches `SHA256SUMS` (a damaged update, a replaced binary or script), so no daemon was started ([SECURITY.md](SECURITY.md)). `su -c /data/adb/modules/zairenkai/verify.sh` lists the problems. |
| A daemon keeps crashing | Read `/data/adb/zairenkai/<core\|fas>/<daemon>.log` | After 5 starts in 10 minutes the supervisor stops and writes `<data>/failed`; the next boot tries again. |
| Restore FAS settings by hand | `su -c /data/adb/modules/zairenkai/bin/zfasd restore --dir /data/adb/zairenkai/fas` | Writes back the values zfasd recorded before changing them. |
| Device does not boot | Boot into the root manager's safe mode (Magisk) or recovery and delete `/data/adb/modules/zairenkai` | The module changes no partition, boot image or persistent kernel setting, so removing its directory removes it. |

The earlier separate modules `zairenkai_core` and `zairenkai_fas` are superseded. Remove them
in the root manager; the installer warns while they are present, and Core reports them as
superseded.
