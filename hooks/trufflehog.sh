#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# NVIDIA Security Workflows — TruffleHog pre-commit wrapper.
#
# Scans the file list pre-commit passes in — staged files at pre-commit
# stage, push-range files at pre-push. NOT the whole working tree (the
# CI reusable workflow covers the merged tree; together = defense in
# depth).
#
# Flag overrides:
#   * `filesystem "$@"`    — pre-commit's file list via `pass_filenames:
#                            true`. Upstream `git --since-commit HEAD`
#                            mode is unusable in pre-commit context
#                            (the new commit doesn't exist yet → empty
#                            range).
#   * `--no-update`        — skip the startup version check (~1s + an
#                            outbound HTTPS call per commit).
#   * `--results=verified` — verified-active leaks only; matches CI
#                            re-scan policy and keeps local scans focused.

set -euo pipefail

# Resolve trufflehog from $PATH (Homebrew on macOS and the upstream
# install script on Linux both land the binary on $PATH).
if ! command -v trufflehog >/dev/null 2>&1; then
    cat >&2 <<'EOF'

ERROR: trufflehog binary not found on $PATH.

  Install on macOS (Homebrew):
    brew install trufflesecurity/trufflehog/trufflehog

  Install on macOS or Linux (no package manager required):
    curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh \
        | sh -s -- -b /usr/local/bin
    # /usr/local/bin write may need sudo on macOS without Homebrew;
    # alternatively pass `-b "$HOME/.local/bin"` if that dir is on $PATH.

  After install, open a new shell (or `hash -r`) so the new binary is
  visible on $PATH, then re-run the commit.

EOF
    exit 1
fi

# Empty arg list = nothing staged matched. Exit clean (calling
# `trufflehog filesystem` with no paths defaults to `.` — whole-tree).
if [[ $# -eq 0 ]]; then
    exit 0
fi

exec trufflehog filesystem "$@" \
    --results=verified \
    --fail \
    --no-update
