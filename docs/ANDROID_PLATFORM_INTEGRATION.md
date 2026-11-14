# MOMO OS — Android Platform Integration Engineering Design

**Status:** Architecture baseline only. No AOSP-derived image, Android adapter, phone boot or device certification is currently evidenced by this repository.

## 1. Purpose and platform boundary

The Android-compatible track integrates MOMO services and experience with an upstream Android platform. It does not replace the Android kernel, boot chain or hardware abstraction stack with the Buildroot Linux prototype.

The Android track shares MOMO-owned contracts, task semantics, policy vocabulary, user data formats and experience concepts with the mainline-Linux track. It does not share Linux AF_UNIX service code or assume identical native permissions.

## 2. Upstream strategy

Candidate bases must be evaluated independently:
- AOSP: canonical framework/platform baseline and build manifests.
- LineageOS: candidate integration base only where the exact device and maintenance branch are viable.
- Android Common Kernel/GKI: kernel maintenance and vendor-module compatibility must be checked for the exact target.

No base is final until an ADR records:
- API level and security patch maintenance policy.
- Source manifest and immutable revisions.
- Kernel/GKI strategy and vendor module dependencies.
- Bootloader, AVB, partition and recovery constraints.
- License and firmware provenance.
- Reproducible clean baseline build.
- Update and rollback path.

Build an unmodified upstream baseline before introducing MOMO changes.

## 3. Android integration layers

### 3.1 MOMO applications and shell

The initial experience should prefer ordinary platform applications, launcher integration and documented system extension points. Framework modifications are justified only when an API or privilege boundary cannot be implemented safely as an app/service.

The shell must provide:
- Navigation, app switching, notifications and quick settings integration.
- Permission dashboard and user-visible approval prompts.
- Task progress, cancellation and history.
- Accessibility services, Arabic RTL and English LTR.
- Clear indication of unsupported device capabilities.

### 3.2 MOMO system services

Each privileged service must have:
- A dedicated Android process/service identity where practical.
- A stable AIDL interface with versioned operations and structured errors.
- Explicit Binder caller identity checks.
- Signature-level permissions for MOMO-owned privileged APIs.
- SELinux domain and service-manager policy.
- AppOps/runtime permission mapping for user data and sensors.
- Audit and cancellation behavior.

No Binder method may accept arbitrary shell commands, arbitrary file paths or caller-selected privilege identities.

### 3.3 Hardware abstraction

Hardware access remains through Android framework APIs and supported HAL interfaces. MOMO adapters must not bypass vendor/HAL ownership through private sysfs/ioctl assumptions.

Adapter domains include:
- Display, input and windowing.
- Audio and media.
- Camera and sensors.
- Battery, charging, thermal and power.
- Wi-Fi, Bluetooth, modem and telephony.
- Biometrics and secure hardware.
- Storage, encryption and backup.
- Package/application lifecycle.
- Notifications and accessibility.

Each adapter declares API level, required permission, SELinux context, capability state, risk and exact-device test evidence.

## 4. Security mapping

| MOMO concept | Android enforcement |
|---|---|
| Authenticated service principal | Binder caller UID/PID plus package/signature verification |
| Service-to-service authorization | Signature permission and explicit Binder allowlist |
| User data access | Runtime permissions, AppOps, scoped storage and platform APIs |
| Service isolation | SELinux enforcing domain, process UID and framework sandbox |
| Secret storage | Android Keystore; hardware-backed protection where supported |
| Approval | MOMO approval UX plus policy check inside receiving service |
| Audit | Structured redacted audit events with stable request/task IDs |
| Update integrity | Verified Boot/AVB, signed packages and supported OTA mechanism |

The app must not trust identity fields supplied in AIDL arguments. Caller identity is derived from Binder and verified against installed package/signature state.

## 5. Device feasibility and boot requirements

Before selecting a phone:
1. Confirm exact marketed model, SKU, codename, region and SoC.
2. Verify official unlock status and a recoverable stock restore package.
3. Inspect bootloader, AVB/vbmeta, slots, dynamic partitions and rollback indexes.
4. Pin kernel source, branch, config, device tree, vendor modules and firmware provenance.
5. Confirm required HALs and vendor services are compatible with the selected Android base.
6. Build and boot the unmodified baseline in cloud CI where possible.
7. Only then integrate MOMO overlays and services.
8. Validate encryption, radio, emergency calling constraints, thermal, power, suspend/resume, camera, audio, sensors and biometrics.
9. Test OTA, rollback, data preservation and restore.

A kernel source repository, recovery image or generic GSI is not proof of support for the exact SKU.

## 6. Build and validation pipeline

Required stages:
- Immutable Repo manifest and remote provenance.
- License and firmware inventory.
- Clean baseline AOSP build.
- MOMO app/service build and static validation.
- AIDL API compatibility checks.
- SELinux policy compilation and neverallow checks.
- Unit and Binder integration tests.
- Emulator boot and service smoke tests.
- Exact-device boot and hardware test matrix.
- Signed test artifacts, checksums, SBOM and build provenance.

A full AOSP build requires a provisioned cloud worker sized for current upstream requirements. Standard hosted GitHub runners must not be assumed to have enough disk/RAM. Do not start a full source sync without pinned manifest and approved worker budget.

## 7. Android adapter contract

Every adapter implementation must:
- Implement the platform-neutral MOMO operation contract.
- Derive caller identity from Binder.
- Check current capability state and permissions at the receiving service.
- Bind approvals to exact operation, arguments, target and expiry.
- Enforce timeout/cancellation where the underlying API supports it.
- Return structured result and audit ID.
- Report unsupported/unknown features honestly.
- Avoid root and shell fallbacks.

## 8. Required tests

- Binder caller spoofing and cross-UID access denial.
- Package signature mismatch and permission revocation.
- AppOps denial and runtime permission denial.
- SELinux enforcing policy and unauthorized service-manager access.
- Scoped-storage traversal and document-provider boundary tests.
- Keystore key access and invalidation behavior.
- Adapter compatibility across supported API levels.
- OTA rollback and Verified Boot failure behavior.
- Exact-SKU hardware and recovery tests.

## 9. Current gaps

- No final Android base or API baseline selected.
- No Android Repo manifest pinned.
- No AOSP baseline build.
- No Binder/AIDL service implementation.
- No MOMO SELinux domains or AppOps integration.
- No Android hardware adapters.
- No physical device port or certification.
- No signing/OTA/recovery release process.

These gaps remain explicit roadmap gates. The x86_64 or AArch64 Buildroot QEMU targets do not provide Android compatibility evidence.
