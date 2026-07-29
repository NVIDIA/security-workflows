#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Self-installing, dependency-free TruffleHog pre-commit wrapper."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


TRUFFLEHOG_VERSION = "3.95.9"
CHECKSUMS = {
    "darwin_amd64": "4306a58d25b85aad7b5fb6f5732df77c50a9161db2746b56e196649072218691",
    "darwin_arm64": "944c6ea3a2993a9f808d08107b40e03ba92bc75972876a1ee47d567bfd6fa1b5",
    "linux_amd64": "f6d1106b85107d79527ed7a5b98b592beadd8b770dc3c9e8c1ad99e1b2cf127e",
    "linux_arm64": "9d9c2ec4ea36a089a9c5aaafe1969d176013ddf9f44d68e8cd75291aed8c83ed",
    "windows_amd64": "25cc731f678922c870edba49f19c324aa6c8e7190b551c4fbe49d0c4e1c5446a",
    "windows_arm64": "df982afbf72d1c1a125e4871b624b7f959b2f62caa40e4d14bf861fb93c237bb",
}


class HookError(Exception):
    """An expected setup error that must block the commit."""


def platform_name() -> tuple[str, str]:
    operating_system = {"Darwin": "darwin", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    architecture = {"x86_64": "amd64", "AMD64": "amd64", "arm64": "arm64", "aarch64": "arm64"}.get(
        platform.machine()
    )
    if operating_system is None:
        raise HookError(f"unsupported OS {platform.system()!r}.")
    if architecture is None:
        raise HookError(f"unsupported architecture {platform.machine()!r}.")
    return operating_system, architecture


def cache_root(operating_system: str) -> Path:
    if operating_system == "windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base is None:
            raise HookError("LOCALAPPDATA or APPDATA must be set on Windows.")
        return Path(base)
    if operating_system == "darwin":
        return Path.home() / "Library" / "Caches"
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


def release_url(platform_id: str) -> str:
    return (
        "https://github.com/trufflesecurity/trufflehog/releases/download/"
        f"v{TRUFFLEHOG_VERSION}/trufflehog_{TRUFFLEHOG_VERSION}_{platform_id}.tar.gz"
    )


def download_archive(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "nvidia-security-workflows"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as archive:
            shutil.copyfileobj(response, archive)
    except urllib.error.HTTPError as error:
        raise HookError(f"download failed ({error.code}) from {url}") from error
    except urllib.error.URLError as error:
        raise HookError(f"download failed from {url}: {error.reason}") from error


def verify_archive(archive: Path, expected_checksum: str, url: str) -> None:
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    if checksum != expected_checksum:
        raise HookError(
            f"checksum mismatch for {url}\n"
            f"  expected: {expected_checksum}\n"
            f"  actual:   {checksum}\n"
            "This may indicate a corrupted download or a tampered artifact. Aborting."
        )


def extract_binary(archive: Path, binary_name: str, destination: Path) -> None:
    try:
        with tarfile.open(archive, "r:gz") as tar:
            member = tar.getmember(binary_name)
            if not member.isfile() or Path(member.name).name != binary_name:
                raise HookError(f"archive contains an unsafe {binary_name!r} member.")
            extracted = tar.extractfile(member)
            if extracted is None:
                raise HookError(f"failed to extract {binary_name} from archive.")
            with extracted, destination.open("wb") as binary:
                shutil.copyfileobj(extracted, binary)
    except (tarfile.TarError, KeyError) as error:
        raise HookError(f"failed to extract {binary_name} from archive.") from error


def install_binary(platform_id: str, binary_name: str, cache_dir: Path) -> Path:
    binary = cache_dir / binary_name
    if binary.is_file():
        return binary

    expected_checksum = CHECKSUMS[platform_id]
    url = release_url(platform_id)
    print(
        f"secret-scan-trufflehog: fetching pinned TruffleHog v{TRUFFLEHOG_VERSION} ({platform_id}) on first use...",
        file=sys.stderr,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nv-trufflehog-") as temporary_directory:
        temporary_path = Path(temporary_directory)
        archive = temporary_path / "trufflehog.tar.gz"
        extracted_binary = temporary_path / binary_name
        download_archive(url, archive)
        verify_archive(archive, expected_checksum, url)
        extract_binary(archive, binary_name, extracted_binary)
        if os.name != "nt":
            extracted_binary.chmod(extracted_binary.stat().st_mode | stat.S_IXUSR)
        with tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as published:
            published_binary = Path(published.name)
        try:
            shutil.copyfile(extracted_binary, published_binary)
            if os.name != "nt":
                published_binary.chmod(published_binary.stat().st_mode | stat.S_IXUSR)
            os.replace(published_binary, binary)
        finally:
            published_binary.unlink(missing_ok=True)
    return binary


def main(arguments: list[str]) -> int:
    # Do not let TruffleHog interpret an empty list as a request to scan the whole tree.
    if not arguments:
        return 0
    operating_system, architecture = platform_name()
    platform_id = f"{operating_system}_{architecture}"
    binary_name = "trufflehog.exe" if operating_system == "windows" else "trufflehog"
    binary = install_binary(
        platform_id,
        binary_name,
        cache_root(operating_system) / "nvidia-security-workflows" / "trufflehog" / TRUFFLEHOG_VERSION,
    )
    return subprocess.run(
        [str(binary), "filesystem", *arguments, "--results=verified", "--fail", "--no-update"], check=False
    ).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except HookError as error:
        print(f"::error::secret-scan-trufflehog: {error}", file=sys.stderr)
        raise SystemExit(1) from error
