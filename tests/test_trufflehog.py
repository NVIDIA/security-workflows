# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the dependency-free TruffleHog hook launcher."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HOOK_PATH = Path(__file__).parents[1] / "hooks" / "trufflehog.py"
SPEC = importlib.util.spec_from_file_location("trufflehog_hook", HOOK_PATH)
assert SPEC is not None and SPEC.loader is not None
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


class TruffleHogHookTests(unittest.TestCase):
    def test_empty_file_list_skips_download(self) -> None:
        with mock.patch.object(HOOK, "install_binary") as install_binary:
            self.assertEqual(HOOK.main([]), 0)
        install_binary.assert_not_called()

    def test_platform_name_supports_native_windows(self) -> None:
        with mock.patch.object(HOOK.platform, "system", return_value="Windows"), mock.patch.object(
            HOOK.platform, "machine", return_value="AMD64"
        ):
            self.assertEqual(HOOK.platform_name(), ("windows", "amd64"))

    def test_verify_archive_rejects_checksum_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(temporary_directory) / "archive.tar.gz"
            archive.write_bytes(b"not an archive")
            with self.assertRaises(HOOK.HookError):
                HOOK.verify_archive(archive, "0" * 64, "https://example.invalid/archive")

    def test_extract_binary_rejects_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(temporary_directory) / "archive.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("trufflehog")
                info.type = tarfile.SYMTYPE
                info.linkname = "/unexpected"
                tar.addfile(info)
            with self.assertRaises(HOOK.HookError):
                HOOK.extract_binary(archive, "trufflehog", Path(temporary_directory) / "trufflehog")

    def test_extract_binary_writes_only_the_requested_member(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(temporary_directory) / "archive.tar.gz"
            content = b"binary"
            with tarfile.open(archive, "w:gz") as tar:
                info = tarfile.TarInfo("trufflehog")
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
            binary = Path(temporary_directory) / "trufflehog"
            HOOK.extract_binary(archive, "trufflehog", binary)
            self.assertEqual(binary.read_bytes(), content)

    def test_verify_archive_accepts_pinned_content(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            archive = Path(temporary_directory) / "archive.tar.gz"
            content = b"verified archive"
            archive.write_bytes(content)
            HOOK.verify_archive(archive, hashlib.sha256(content).hexdigest(), "https://example.invalid/archive")


if __name__ == "__main__":
    unittest.main()
