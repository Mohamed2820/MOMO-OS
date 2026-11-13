# Device Feasibility Gate — Samsung Galaxy A17

## Initial target
- Model reported: Samsung Galaxy A17, SM-A175F.
- CPU architecture reported: ARM64.
- Android version reported by maintainer: Android 16.

These are maintainer-provided starting details, not independently verified compatibility evidence.

## Required evidence before selecting a ROM base
1. Exact product name, codename, region/SKU, SoC, and current firmware build.
2. Whether the exact model/region permits bootloader unlocking.
3. Official kernel source matching the installed firmware and kernel configuration.
4. Device tree completeness and active maintainer/community support.
5. Vendor blobs and firmware requirements, including redistribution constraints.
6. Partition map, dynamic partitions, A/B behavior, recovery, and boot image format.
7. AVB/vbmeta and rollback protection behavior.
8. SELinux policy and hardware interface compatibility.
9. Verified stock firmware and tested restore path.
10. A safe test strategy that does not risk the user's daily-use device.

## Important distinction
A TWRP recovery tree, a kernel repository, or a device page is not by itself proof that a complete Android ROM can boot and operate on the device.

## Go/no-go rule
Do not build flashable release images or instruct installation until a maintainer has verified the full dependency chain and a recovery route. First target should be a cloud build and static analysis, then emulator/generic validation where useful, then device-specific validation.

## Evidence log
Record each finding in an ADR or a dated feasibility note with source URL, date checked, exact model/firmware, and confidence. Unknown means unknown; do not infer support.
