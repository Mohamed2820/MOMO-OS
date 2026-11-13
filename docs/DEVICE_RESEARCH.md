# Device Research — Samsung Galaxy A17 SM-A175F

Status: preliminary research; not a porting approval.

## Confirmed model distinction
SM-A175F is the Galaxy A17 LTE/4G model. It must not be confused with SM-A176B (Galaxy A17 5G). Public product documentation distinguishes the LTE model's MediaTek Helio G99 platform from the 5G model's Exynos 1330 platform.

## Preliminary public evidence
- A public device information index identifies SM-A175F with product string a17xx, MediaTek MT6789 / Helio G99, ARM Mali-G57, and Android 16 kernel builds. This is third-party data and must be cross-checked against the exact phone's firmware.
- Public repositories exist for A17-specific kernel research and kernel offsets, but these are not a complete Android device tree, vendor implementation, or a verified ROM port.
- No official LineageOS support page or complete, verified device bring-up was established during this initial research pass.

## Missing evidence
- Exact installed build number and CSC/region.
- Bootloader unlock option and actual unlock eligibility on this unit.
- Official Samsung kernel source archive matching the installed firmware.
- Complete device tree and common tree dependencies.
- Vendor blobs, firmware requirements, extraction reproducibility, and redistribution rights.
- Partition map, dynamic partition layout, boot/recovery image formats, AVB and rollback behavior.
- Working recovery and tested stock restore path.
- Hardware validation for telephony, data, Wi-Fi, Bluetooth, NFC, camera, audio, biometrics, sensors, charging, suspend, and encryption.

## Decision
Do not select an A17 ROM base or produce flashable images yet. Treat this handset as a research target, not the first guaranteed release device. If its bootloader is not unlockable or the source/vendor chain is incomplete, use a supported reference device or emulator for platform development while keeping A17 work in a separate feasibility track.

## Safety
Do not use kernel exploit code, SELinux-disabling payloads, or untrusted rooted kernels as a substitute for a supported bootloader and reproducible device port. Preserve stock firmware and a verified restore route before any future hardware experiment.

## Reference links
- [LineageOS device support requirements](https://github.com/LineageOS/charter/blob/main/device-support-requirements.md) — upstream acceptance requirements; not proof that this model is supported.
- [LineageOS device support FAQ](https://lineageos.github.io/lineage_wiki/faq.html) — unsupported variants are not interchangeable.
- [Samsung Galaxy A17 model distinction (SM-A175F vs SM-A176B)](https://cdn.shoepping.at/medias/sys_master/cloud-misc-1710-21068400/h21/hde/17394089328670/272867/272867.pdf) — third-party-hosted product specification; verify against Samsung documentation and the actual device.
- [Public SM-A175F device information](https://specdeviceinfo.com/devices/samsung/sm-a175f-121073/) — third-party index, used only as a lead for further verification.

References are discovery leads. Before device decisions, record official Samsung source archives and exact firmware evidence for the actual handset.
