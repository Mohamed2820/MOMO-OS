# Device Compatibility and Porting Contract

## Why device profiles exist

The same MOMO product must adapt to different hardware without pretending that phone firmware is interchangeable. A device profile is a reviewed record of exact hardware and software facts, not a generic model-name label.

## Required identity

Every profile must identify:
- Manufacturer and exact marketed model.
- Board/device codename and regional variant where applicable.
- SoC family and CPU architecture.
- Bootloader and unlock status, including evidence.
- Current and target firmware/build identifiers.
- Kernel source, branch/version, configuration and patch provenance.
- Device tree and vendor component provenance.
- Partition and verified-boot information.
- Display, touch, storage, battery/power, radio, Wi-Fi, Bluetooth, audio, camera, sensors and biometrics status.
- Recovery/restore procedure and evidence.
- Support tier, maintainer and last validation date.

Do not merge a profile based only on a product page or a similarly named model.

## Porting workflow

1. Identify exact SKU, codename, SoC and region.
2. Establish whether bootloader unlocking is officially possible and whether a recoverable stock image exists.
3. Collect source and license provenance for kernel, device tree, HAL and firmware dependencies.
4. Map boot chain, partition layout, AVB/vbmeta, dynamic partitions, slots and rollback behavior.
5. Build an unmodified upstream/base image in cloud CI.
6. Boot only through a documented, reversible test procedure.
7. Validate display, touch, storage, charging, thermal, suspend/resume and logs.
8. Validate radio, emergency calling constraints, Wi-Fi, Bluetooth, audio, camera, sensors, biometrics and encryption.
9. Integrate MOMO adapters and services incrementally.
10. Test OTA, rollback, recovery and data preservation.
11. Assign a support tier based on evidence; publish a device feature matrix.

## Hard stops

Stop porting or do not flash when:
- Bootloader unlock status is unknown or prohibited.
- No matching stock restore package or reliable recovery path exists.
- Kernel/vendor binary compatibility is unverified.
- Partition/AVB layout is uncertain.
- Required proprietary components have unclear legal provenance.
- A test would risk the only available device or user data.

No exploit-based unlock, security downgrade, SELinux disabling, or blind partition writes are acceptable default strategies.

## Evidence levels

- Documented: supported by an official source or source repository.
- Inspected: verified against the exact device/firmware artifacts.
- Built: reproducible artifact generated from pinned sources.
- Boot-tested: observed on the exact device with logs.
- Function-tested: each listed feature passed a repeatable test.
- Maintained: release and security update process is active.

A lower evidence level must never be described as a higher one.
