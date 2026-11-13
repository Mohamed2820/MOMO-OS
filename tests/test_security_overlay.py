import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intelligence/security"
TARGET = ROOT / "board/momo/rootfs-overlay/usr/lib/momo/intelligence/security"


class SecurityOverlayParityTests(unittest.TestCase):
    def test_security_modules_match_the_source_of_truth(self):
        for name in ("__init__.py", "linux_peercred.py", "ipc_protocol.py"):
            with self.subTest(module=name):
                self.assertEqual(
                    (SOURCE / name).read_text(encoding="utf-8"),
                    (TARGET / name).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
