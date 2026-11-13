# MOMO OS Platform Support Matrix

**Status date:** 2026-11-13  
**Policy:** A platform is supported only after its own build, boot, core-service and security tests pass. Source-level portability or a QEMU target definition is not device support.

| Platform target | Build path | Current evidence | Status |
|---|---|---|---|
| Linux x86_64 QEMU | Buildroot `qemu_x86_64_defconfig` | Workflow #43446234529 is still compiling; no artifact or QEMU serial evidence observed | Under validation |
| Linux AArch64 QEMU virt | Buildroot `qemu_aarch64_virt_defconfig` | Workflow definition in PR #42; no target build/boot result yet | Planned / CI pending |
| Android / AOSP | AOSP + Android Common Kernel + Binder/AIDL + SELinux/AppOps adapters | Architecture documented; no AOSP image or device boot evidence | Not implemented |
| Physical ARM phones | Per-device boot chain, kernel, DT, firmware, vendor modules and hardware validation | No physical-device qualification | Not supported |
| Physical x86_64 PCs/laptops | Per-platform boot, graphics, storage, networking, suspend and firmware validation | QEMU baseline only; no physical-hardware qualification | Not supported |
| Windows / macOS | No native porting implementation | No build or test evidence | Not supported |

## Minimum promotion gates

1. Reproducible pinned source/toolchain and successful image build.
2. Image integrity and provenance checks.
3. Successful boot on the declared target.
4. MOMO readiness checks, including task persistence, device inventory and permission service.
5. Authenticated IPC status test and security policy checks.
6. Reboot/recovery behavior and negative tests.
7. Hardware-specific tests before any physical device is listed as supported.

## Important interpretation

A successful x86_64 QEMU image does not imply AArch64 support. A successful AArch64 QEMU virt image does not imply support for an arbitrary ARM phone. Android is a distinct platform track and requires Binder/AIDL, SELinux, AppOps, HAL and vendor integration. No universal boot binary is promised.
