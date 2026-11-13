import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from intelligence.runtime.device_inventory import (
    CapabilityStatus, DeviceInventory, DeviceProfileError,
)


class DeviceInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.proc = self.root / "proc"
        self.sys = self.root / "sys"
        self.etc = self.root / "etc"
        self.proc.mkdir()
        self.sys.mkdir()
        self.etc.mkdir()
        (self.etc / "os-release").write_text(
            'NAME="MOMO Test OS"\nVERSION_ID="0.1"\n', encoding="utf-8"
        )
        (self.etc / "momo-release").write_text(
            "NAME=MOMO OS\nTRACK=linux-x86_64\n", encoding="utf-8"
        )
        self.profile = self.root / "device-profile.json"

    def tearDown(self):
        self.temp.cleanup()

    def inventory(self, verified=False):
        return DeviceInventory(
            self.profile, proc_root=self.proc, sys_root=self.sys,
            etc_root=self.etc, profile_identity_verified=verified,
        )

    def test_runtime_facts_are_reported_without_claiming_capabilities(self):
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"), \
             patch("intelligence.runtime.device_inventory.platform.release", return_value="6.18.7"), \
             patch("intelligence.runtime.device_inventory.platform.node", return_value="momo-qemu"), \
             patch("intelligence.runtime.device_inventory.platform.system", return_value="Linux"):
            snapshot = self.inventory().snapshot()
        self.assertEqual(snapshot.identity.architecture, "x86_64")
        self.assertEqual(snapshot.identity.platform_track, "mainline-linux")
        self.assertEqual(snapshot.identity.kernel_release, "6.18.7")
        self.assertEqual(snapshot.identity.operating_system, "MOMO Test OS")
        self.assertEqual(snapshot.profile_status, "not_found")
        self.assertTrue(all(
            capability.status is CapabilityStatus.UNKNOWN
            for capability in snapshot.capabilities.values()
        ))

    def test_device_tree_model_is_detected(self):
        (self.proc / "device-tree").mkdir()
        (self.proc / "device-tree/model").write_bytes(b"QEMU Virtual Machine\x00")
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"):
            snapshot = self.inventory().snapshot()
        self.assertEqual(snapshot.identity.device_model, "QEMU Virtual Machine")

    def test_unverified_profile_never_grants_feature_support(self):
        self.profile.write_text(json.dumps({
            "profile_version": 1,
            "identity": {"manufacturer": "Example", "model": "Board", "codename": "board", "soc": "SoC"},
            "architecture": "x86_64",
            "features": {"wifi": "regression_tested"},
        }), encoding="utf-8")
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"):
            snapshot = self.inventory(verified=False).snapshot()
        self.assertEqual(snapshot.profile_status, "identity_unverified")
        self.assertEqual(snapshot.capabilities["wifi"].status, CapabilityStatus.UNKNOWN)

    def test_verified_profile_maps_only_evidence_backed_states(self):
        self.profile.write_text(json.dumps({
            "profile_version": 1,
            "identity": {"manufacturer": "Example", "model": "Board", "codename": "board", "soc": "SoC"},
            "architecture": "x86_64",
            "features": {"wifi": "regression_tested", "camera": "not_supported", "touch": "boot_tested"},
        }), encoding="utf-8")
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"):
            snapshot = self.inventory(verified=True).snapshot()
        self.assertEqual(snapshot.profile_status, "identity_verified")
        self.assertEqual(snapshot.capabilities["wifi"].status, CapabilityStatus.SUPPORTED)
        self.assertEqual(snapshot.capabilities["camera"].status, CapabilityStatus.UNSUPPORTED)
        self.assertEqual(snapshot.capabilities["touch"].status, CapabilityStatus.UNKNOWN)

    def test_profile_architecture_mismatch_is_rejected(self):
        self.profile.write_text(json.dumps({
            "profile_version": 1,
            "identity": {"manufacturer": "Example", "model": "Board", "codename": "board", "soc": "SoC"},
            "architecture": "arm64",
            "features": {},
        }), encoding="utf-8")
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"):
            with self.assertRaises(DeviceProfileError):
                self.inventory(verified=True).snapshot()

    def test_malformed_profile_is_rejected(self):
        self.profile.write_text("{broken", encoding="utf-8")
        with self.assertRaises(DeviceProfileError):
            self.inventory().snapshot()

    def test_snapshot_serializes_to_json_compatible_values(self):
        with patch("intelligence.runtime.device_inventory.platform.machine", return_value="x86_64"):
            payload = self.inventory().snapshot().to_dict()
        self.assertEqual(payload["capabilities"]["camera"]["status"], "unknown")
        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()
