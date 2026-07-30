# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Run TruffleHog with the hook's fail-closed policy."""

import subprocess
import sys


def main() -> int:
    # Append these after consumer args so they cannot weaken the public policy.
    return subprocess.call(
        [
            "trufflehog",
            "filesystem",
            *sys.argv[1:],
            "--results=verified",
            "--fail",
            "--no-update",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
