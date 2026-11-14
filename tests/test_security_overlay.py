import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intelligence/security"
TARGET = ROOT / "board/momo/rootfs-overlay/usr/lib/momo/intelligence/security"
SANDBOX = ROOT / "board/momo/rootfs-overlay/usr/bin/momo-ipc-sandbox"
INIT = ROOT / "board/momo/rootfs-overlay/etc/init.d/S98momo-ipc"


class SecurityOverlayParityTests(unittest.TestCase):
    def test_ipc_launcher_enters_private_namespaces_and_drops_privileges(self):
        source = SANDBOX.read_text(encoding="utf-8")
        for required in (
            "CLONE_NEWNS", "CLONE_NEWIPC", "CLONE_NEWUTS", "CLONE_NEWNET",
            "MOMO_NAMESPACE_INODES", "os.stat(f\"/proc/self/ns/{name}\").st_ino",
            "MS_PRIVATE", "os.setgroups([])", 'os.setgid(account.pw_gid)',
            'os.setuid(account.pw_uid)', "PR_SET_NO_NEW_PRIVS",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_ipc_daemon_verifies_launch_time_namespace_inodes(self):
        source = (ROOT / "board/momo/rootfs-overlay/usr/lib/momo/momo_ipcd.py").read_text(encoding="utf-8")
        self.assertIn("MOMO_NAMESPACE_INODES", source)
        self.assertIn("expected_inode", source)
        self.assertNotIn('/proc/1/ns/{name}', source)

    def test_ipc_init_assigns_cgroup_resource_limits(self):
        source = INIT.read_text(encoding="utf-8")
        for required in (
            "cgroup.subtree_control", "memory.max", "pids.max", "cpu.max",
            "MOMO_IPC_CGROUP", "/usr/bin/momo-ipc-sandbox",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_security_modules_match_the_source_of_truth(self):
        for name in ("__init__.py", "linux_peercred.py", "ipc_protocol.py"):
            with self.subTest(module=name):
                self.assertEqual(
                    (SOURCE / name).read_text(encoding="utf-8"),
                    (TARGET / name).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()
