import tempfile
import unittest
from pathlib import Path

from tools.validate_kernel_security_config import validate_config


REQUIRED = """CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_CGROUPS=y
CONFIG_CGROUP_PIDS=y
CONFIG_CGROUP_CPUACCT=y
CONFIG_CGROUP_SCHED=y
CONFIG_FAIR_GROUP_SCHED=y
CONFIG_CFS_BANDWIDTH=y
CONFIG_MEMCG=y
CONFIG_CGROUP_FREEZER=y
CONFIG_CGROUP_DEVICE=y
CONFIG_SECCOMP=y
CONFIG_SECCOMP_FILTER=y
CONFIG_SECURITY=y
CONFIG_SECURITYFS=y
CONFIG_SECURITY_LANDLOCK=y
CONFIG_LSM="landlock,lockdown,yama,integrity,bpf"
"""


class KernelSecurityConfigTests(unittest.TestCase):
    def _config(self, content):
        temp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        self.addCleanup(Path(temp.name).unlink, missing_ok=True)
        temp.write(content)
        temp.close()
        return Path(temp.name)

    def test_accepts_complete_security_configuration(self):
        validate_config(self._config(REQUIRED))

    def test_rejects_missing_namespace_or_cgroup_option(self):
        content = REQUIRED.replace("CONFIG_USER_NS=y\n", "")
        with self.assertRaisesRegex(ValueError, "CONFIG_USER_NS"):
            validate_config(self._config(content))

    def test_rejects_landlock_not_active_in_lsm_list(self):
        content = REQUIRED.replace(
            'CONFIG_LSM="landlock,lockdown,yama,integrity,bpf"',
            'CONFIG_LSM="lockdown,yama,integrity,bpf"',
        )
        with self.assertRaisesRegex(ValueError, "activate Landlock"):
            validate_config(self._config(content))

    def test_source_fragment_can_be_validated_without_final_lsm_value(self):
        content = REQUIRED.replace(
            'CONFIG_LSM="landlock,lockdown,yama,integrity,bpf"\n', ""
        )
        validate_config(self._config(content), check_lsm=False)


if __name__ == "__main__":
    unittest.main()
