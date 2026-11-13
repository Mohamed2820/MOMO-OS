import unittest

from intelligence.runtime.momo_runtime import Risk
from platform_adapters.contracts import (
    Capability, CapabilityState, OperationSpec, PlatformIdentity,
    PlatformTrack, missing_capabilities,
)


class PlatformContractTests(unittest.TestCase):
    def test_identity_is_platform_neutral(self):
        identity = PlatformIdentity(
            PlatformTrack.MAINLINE_LINUX, "arm64", "rolling", "6.x", "example-board"
        )
        self.assertEqual(identity.track, PlatformTrack.MAINLINE_LINUX)

    def test_missing_capabilities_detected(self):
        operation = OperationSpec(
            "camera.capture", Risk.R2,
            frozenset({"camera", "storage.write"}), True, "Capture a photo"
        )
        available = (
            Capability("camera", CapabilityState.SUPPORTED),
            Capability("storage.write", CapabilityState.PERMISSION_DENIED),
        )
        self.assertEqual(
            missing_capabilities(operation, available), ("storage.write",)
        )

    def test_unsupported_and_unknown_are_not_treated_as_available(self):
        operation = OperationSpec(
            "radio.status", Risk.R1, frozenset({"telephony.read"}),
            True, "Read radio status"
        )
        self.assertEqual(
            missing_capabilities(operation, ()), ("telephony.read",)
        )

    def test_no_missing_capabilities_when_all_supported(self):
        operation = OperationSpec(
            "display.brightness", Risk.R2, frozenset({"display.control"}),
            True, "Set brightness"
        )
        available = (
            Capability("display.control", CapabilityState.SUPPORTED),
        )
        self.assertEqual(missing_capabilities(operation, available), ())


if __name__ == "__main__":
    unittest.main()
