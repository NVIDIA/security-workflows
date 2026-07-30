# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Contract tests for the packaged TruffleHog pre-commit hook."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
PACKAGE_CONFIG = PACKAGE_ROOT / "pyproject.toml"
HOOK_MANIFEST = REPOSITORY_ROOT / ".pre-commit-hooks.yaml"

DOWNLOAD_SCRIPTS = re.compile(
    r'(?ms)^\[tool\.distutils\.setuptools_download\]\n'
    r'(?:#[^\n]*\n)*download_scripts = """\n(?P<entries>.*?)\n"""',
)

EXPECTED_ARCHIVES = {
    ("trufflehog", 'sys_platform == "darwin" and platform_machine == "x86_64"'): (
        "trufflehog_3.95.9_darwin_amd64.tar.gz",
        "4306a58d25b85aad7b5fb6f5732df77c50a9161db2746b56e196649072218691",
        "trufflehog",
    ),
    ("trufflehog", 'sys_platform == "darwin" and platform_machine == "arm64"'): (
        "trufflehog_3.95.9_darwin_arm64.tar.gz",
        "944c6ea3a2993a9f808d08107b40e03ba92bc75972876a1ee47d567bfd6fa1b5",
        "trufflehog",
    ),
    ("trufflehog", 'sys_platform == "linux" and platform_machine == "x86_64"'): (
        "trufflehog_3.95.9_linux_amd64.tar.gz",
        "f6d1106b85107d79527ed7a5b98b592beadd8b770dc3c9e8c1ad99e1b2cf127e",
        "trufflehog",
    ),
    ("trufflehog", 'sys_platform == "linux" and platform_machine == "aarch64"'): (
        "trufflehog_3.95.9_linux_arm64.tar.gz",
        "9d9c2ec4ea36a089a9c5aaafe1969d176013ddf9f44d68e8cd75291aed8c83ed",
        "trufflehog",
    ),
    ("trufflehog.exe", 'sys_platform == "win32" and platform_machine == "AMD64"'): (
        "trufflehog_3.95.9_windows_amd64.tar.gz",
        "25cc731f678922c870edba49f19c324aa6c8e7190b551c4fbe49d0c4e1c5446a",
        "trufflehog.exe",
    ),
    ("trufflehog.exe", 'sys_platform == "win32" and platform_machine == "ARM64"'): (
        "trufflehog_3.95.9_windows_arm64.tar.gz",
        "df982afbf72d1c1a125e4871b624b7f959b2f62caa40e4d14bf861fb93c237bb",
        "trufflehog.exe",
    ),
}


def download_entries() -> list[dict[str, str]]:
    match = DOWNLOAD_SCRIPTS.search(PACKAGE_CONFIG.read_text(encoding="utf-8"))
    assert match is not None

    entries: list[dict[str, str]] = []
    entry: dict[str, str] | None = None
    for line in match.group("entries").splitlines():
        assert line == line.lstrip()
        line = line.strip()
        assert line
        if line.startswith("[") and line.endswith("]"):
            if entry is not None:
                entries.append(entry)
            entry = {"name": line[1:-1]}
        else:
            assert entry is not None
            key, value = line.split(" = ", 1)
            entry[key] = value
    assert entry is not None
    entries.append(entry)
    return entries


class TruffleHogPackagingTests(unittest.TestCase):
    def test_every_supported_platform_has_a_pinned_archive(self) -> None:
        actual = {
            (entry["name"], entry["marker"]): (
                entry["url"].rsplit("/", 1)[1],
                entry["sha256"],
                entry["extract_path"],
            )
            for entry in download_entries()
        }
        self.assertEqual(actual, EXPECTED_ARCHIVES)
        for _, checksum, _ in actual.values():
            self.assertRegex(checksum, r"^[0-9a-f]{64}$")

    def test_archives_are_verified_and_executables_are_grouped(self) -> None:
        for entry in download_entries():
            self.assertEqual(entry["group"], "trufflehog-binary")
            self.assertEqual(entry["extract"], "tar")
            self.assertTrue(entry["url"].startswith("https://github.com/trufflesecurity/trufflehog/releases/"))

    def test_hook_uses_the_nested_package_and_nvidia_policy(self) -> None:
        manifest = HOOK_MANIFEST.read_text(encoding="utf-8")
        self.assertIn("id: secret-scan-trufflehog", manifest)
        self.assertIn("entry: trufflehog filesystem --results=verified --fail --no-update", manifest)
        self.assertIn("language: python", manifest)
        self.assertIn("additional_dependencies: [./hooks/trufflehog]", manifest)
        self.assertIn("pass_filenames: true", manifest)
        self.assertIn("require_serial: true", manifest)

    def test_trufflehog_build_requirement_is_isolated_from_the_root_bridge(self) -> None:
        package_config = PACKAGE_CONFIG.read_text(encoding="utf-8")
        root_build_config = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertRegex(package_config, r'"setuptools-download==1\.0\.1"')
        self.assertIn("[tool.distutils.setuptools_download]", package_config)
        self.assertFalse((PACKAGE_ROOT / "setup.cfg").exists())
        self.assertNotIn("setuptools-download", root_build_config)
        self.assertIn("packages = []", root_build_config)


if __name__ == "__main__":
    unittest.main()
