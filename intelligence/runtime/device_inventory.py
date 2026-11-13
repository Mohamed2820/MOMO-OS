"""Conservative runtime device inventory.

This module reports facts it can observe and keeps unverified hardware
capabilities unknown. A profile is not trusted for feature reporting until a
caller explicitly confirms exact-device identity.
"""
from __future__ import annotations

import json
import platform
import shlex
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class CapabilityStatus(str, Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class DeviceProfileError(ValueError):
    """Raised when a device profile is malformed or incompatible."""


@dataclass(frozen=True)
class RuntimeIdentity:
    platform_track: str
    architecture: str
    kernel_release: str
    operating_system: str
    os_version: str | None
    hostname: str
    device_model: str | None


@dataclass(frozen=True)
class Capability:
    status: CapabilityStatus
    source: str


@dataclass(frozen=True)
class InventorySnapshot:
    identity: RuntimeIdentity
    profile_status: str
    capabilities: dict[str, Capability]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": asdict(self.identity),
            "profile_status": self.profile_status,
            "capabilities": {
                name: {"status": item.status.value, "source": item.source}
                for name, item in sorted(self.capabilities.items())
            },
        }


_ARCHITECTURES = {
    "x86_64": "x86_64",
    "amd64": "x86_64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv7l": "arm32",
    "armv8l": "arm32",
    "riscv64": "riscv64",
}
_PROFILE_FEATURES = (
    "display", "touch", "storage", "charging", "wifi", "bluetooth",
    "telephony", "audio", "camera", "sensors", "biometrics",
    "encryption", "suspend_resume", "ota",
)


class DeviceInventory:
    """Collect OS facts and conservatively expose profile-backed capabilities."""

    def __init__(
        self,
        profile_path: str | Path = "/etc/momo/device-profile.json",
        *,
        proc_root: str | Path = "/proc",
        sys_root: str | Path = "/sys",
        etc_root: str | Path = "/etc",
        profile_identity_verified: bool = False,
    ) -> None:
        self.profile_path = Path(profile_path)
        self.proc_root = Path(proc_root)
        self.sys_root = Path(sys_root)
        self.etc_root = Path(etc_root)
        self.profile_identity_verified = profile_identity_verified

    @staticmethod
    def _read_text(path: Path) -> str | None:
        try:
            value = path.read_text(encoding="utf-8", errors="replace").strip("\x00\r\n ")
            return value or None
        except OSError:
            return None

    def _os_release(self) -> dict[str, str]:
        path = self.etc_root / "os-release"
        result: dict[str, str] = {}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return result
        for line in lines:
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, raw = line.split("=", 1)
            try:
                values = shlex.split(raw, posix=True)
                result[key] = values[0] if values else ""
            except ValueError:
                continue
        return result

    def _platform_track(self) -> str:
        release = self._read_text(self.etc_root / "momo-release")
        if release:
            for line in release.splitlines():
                if line.startswith("TRACK="):
                    value = line.partition("=")[2].strip().lower()
                    if value.startswith("android"):
                        return "android"
                    if value.startswith("linux"):
                        return "mainline-linux"
                    if value.startswith("virtual"):
                        return "virtual"
        return "unknown"

    def _device_model(self) -> str | None:
        candidates = (
            self.proc_root / "device-tree/model",
            self.sys_root / "class/dmi/id/product_name",
            self.sys_root / "firmware/devicetree/base/model",
        )
        for path in candidates:
            value = self._read_text(path)
            if value:
                return value
        return None

    def _identity(self) -> RuntimeIdentity:
        os_release = self._os_release()
        machine = platform.machine().lower()
        return RuntimeIdentity(
            platform_track=self._platform_track(),
            architecture=_ARCHITECTURES.get(machine, machine or "unknown"),
            kernel_release=platform.release(),
            operating_system=os_release.get("NAME") or platform.system(),
            os_version=os_release.get("VERSION_ID"),
            hostname=platform.node(),
            device_model=self._device_model(),
        )

    @staticmethod
    def _load_profile(path: Path) -> dict[str, Any]:
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as error:
            raise DeviceProfileError(f"Cannot read device profile: {error}") from error

        if not isinstance(profile, dict):
            raise DeviceProfileError("Device profile root must be an object")
        if profile.get("profile_version") != 1:
            raise DeviceProfileError("Unsupported device profile version")
        identity = profile.get("identity")
        if not isinstance(identity, dict):
            raise DeviceProfileError("Device profile identity is missing")
        for key in ("manufacturer", "model", "codename", "soc"):
            if not isinstance(identity.get(key), str) or not identity[key].strip():
                raise DeviceProfileError(f"Device profile identity.{key} is required")
        if profile.get("architecture") not in set(_ARCHITECTURES.values()):
            raise DeviceProfileError("Device profile architecture is invalid")
        features = profile.get("features", {})
        if not isinstance(features, dict):
            raise DeviceProfileError("Device profile features must be an object")
        return profile

    def snapshot(self) -> InventorySnapshot:
        identity = self._identity()
        profile = self._load_profile(self.profile_path)
        capabilities = {
            name: Capability(CapabilityStatus.UNKNOWN, "no_verified_device_profile")
            for name in _PROFILE_FEATURES
        }
        profile_status = "not_found" if not profile else "identity_unverified"

        if profile and self.profile_identity_verified:
            if profile["architecture"] != identity.architecture:
                raise DeviceProfileError(
                    "Device profile architecture does not match the running system"
                )
            profile_status = "identity_verified"
            for name in _PROFILE_FEATURES:
                value = profile.get("features", {}).get(name, "unknown")
                status = {
                    "functional": CapabilityStatus.SUPPORTED,
                    "regression_tested": CapabilityStatus.SUPPORTED,
                    "not_supported": CapabilityStatus.UNSUPPORTED,
                    "unknown": CapabilityStatus.UNKNOWN,
                    "build_only": CapabilityStatus.UNKNOWN,
                    "boot_tested": CapabilityStatus.UNKNOWN,
                }.get(value, CapabilityStatus.UNKNOWN)
                capabilities[name] = Capability(status, f"verified_profile:{value}")

        return InventorySnapshot(identity, profile_status, capabilities)
