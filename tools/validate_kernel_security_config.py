"""Validate MOMO's required Linux kernel security configuration."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

REQUIRED_Y = frozenset({
    "CONFIG_NAMESPACES",
    "CONFIG_UTS_NS",
    "CONFIG_IPC_NS",
    "CONFIG_USER_NS",
    "CONFIG_PID_NS",
    "CONFIG_NET_NS",
    "CONFIG_CGROUPS",
    "CONFIG_CGROUP_PIDS",
    "CONFIG_CGROUP_CPUACCT",
    "CONFIG_CGROUP_SCHED",
    "CONFIG_FAIR_GROUP_SCHED",
    "CONFIG_CFS_BANDWIDTH",
    "CONFIG_MEMCG",
    "CONFIG_CGROUP_FREEZER",
    "CONFIG_CGROUP_DEVICE",
    "CONFIG_SECCOMP",
    "CONFIG_SECCOMP_FILTER",
    "CONFIG_SECURITY",
    "CONFIG_SECURITYFS",
    "CONFIG_SECURITY_LANDLOCK",
})
LSM_REQUIRED = "landlock"


def parse_config(path: Path) -> tuple[set[str], str | None]:
    enabled: set[str] = set()
    lsm: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.endswith("=y") and line.startswith("CONFIG_"):
            enabled.add(line.split("=", 1)[0])
        elif line.startswith("CONFIG_LSM="):
            match = re.fullmatch(r'CONFIG_LSM="([^"]*)"', line)
            if match:
                lsm = match.group(1)
    return enabled, lsm


def validate_config(path: Path, *, check_lsm: bool = True) -> None:
    enabled, lsm = parse_config(path)
    missing = sorted(REQUIRED_Y - enabled)
    if missing:
        raise ValueError("Missing required kernel options: " + ", ".join(missing))
    if check_lsm and (lsm is None or LSM_REQUIRED not in lsm.split(",")):
        raise ValueError("CONFIG_LSM must activate Landlock")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    parser.add_argument(
        "--fragment",
        action="store_true",
        help="Validate a source fragment (does not require the final CONFIG_LSM line)",
    )
    args = parser.parse_args()
    validate_config(args.config, check_lsm=not args.fragment)
    print(f"Kernel security configuration verified: {args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
