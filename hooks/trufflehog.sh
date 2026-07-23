#!/usr/bin/env bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# NVIDIA Security Workflows — TruffleHog pre-commit wrapper (self-installing).
#
# Contributors install nothing: on first run this downloads a pinned, checksum-verified TruffleHog release into a per-user cache
# then scans the file list pre-commit passes in. Later runs reuse the cached binary (offline, no network).
#
# Scope of the scan:
#   staged files at the pre-commit stage, push-range files at pre-push — NOT the whole tree.
#
# Security model (why this is safe to auto-download):
#   * The exact version AND the per-platform SHA-256 of the official release archive are pinned below.
#     The pins are taken from TruffleHog's cosign-signed `checksums.txt` for the release.
#   * The archive is fetched over HTTPS and verified against the pinned SHA-256.
#     On ANY mismatch the hook fails closed and the binary is never executed.
#   * Bumping the tool = editing TRUFFLEHOG_VERSION + the checksum table in a
#     reviewed commit (same trust model as pinning a GitHub Action by SHA).
#
# Flags: `filesystem "$@"` (pre-commit file list), `--results=verified`
# (verified-active leaks only; matches CI policy), `--fail`, `--no-update`
# (skip the scanner's own startup version check).

set -euo pipefail

# Pinned upstream release. Update both the version and every checksum together.
readonly TRUFFLEHOG_VERSION="3.95.9"

# SHA-256 of trufflehog_<version>_<os>_<arch>.tar.gz (from the signed checksums.txt).
sha256_for_platform() {
  case "$1" in
    darwin_amd64)  printf '%s' "4306a58d25b85aad7b5fb6f5732df77c50a9161db2746b56e196649072218691" ;;
    darwin_arm64)  printf '%s' "944c6ea3a2993a9f808d08107b40e03ba92bc75972876a1ee47d567bfd6fa1b5" ;;
    linux_amd64)   printf '%s' "f6d1106b85107d79527ed7a5b98b592beadd8b770dc3c9e8c1ad99e1b2cf127e" ;;
    linux_arm64)   printf '%s' "9d9c2ec4ea36a089a9c5aaafe1969d176013ddf9f44d68e8cd75291aed8c83ed" ;;
    windows_amd64) printf '%s' "25cc731f678922c870edba49f19c324aa6c8e7190b551c4fbe49d0c4e1c5446a" ;;
    windows_arm64) printf '%s' "df982afbf72d1c1a125e4871b624b7f959b2f62caa40e4d14bf861fb93c237bb" ;;
    *) return 1 ;;
  esac
}

die() { printf '::error::secret-scan-trufflehog: %s\n' "$*" >&2; exit 1; }

# Nothing staged matched the hook's file types -> nothing to scan.
# (Exit before any download; `trufflehog filesystem` with no paths would default to scanning the whole tree.)
[[ $# -eq 0 ]] && exit 0

# --- Resolve platform ---------------------------------------------------------
case "$(uname -s)" in
  Darwin)                os="darwin" ;;
  Linux)                 os="linux" ;;
  # Windows under a bash environment (Git for Windows / MSYS2 / Cygwin).
  MINGW*|MSYS*|CYGWIN*)  os="windows" ;;
  *)                     die "unsupported OS '$(uname -s)' (supported: Linux, macOS, Windows via Git Bash/MSYS). Install trufflehog manually and open an issue." ;;
esac
case "$(uname -m)" in
  x86_64|amd64)  arch="amd64" ;;
  arm64|aarch64) arch="arm64" ;;
  *)             die "unsupported architecture '$(uname -m)'." ;;
esac
platform="${os}_${arch}"
expected_sha="$(sha256_for_platform "$platform")" || die "no pinned checksum for platform '${platform}'."

# Windows release archives ship trufflehog.exe.
binname="trufflehog"
[[ "${os}" == "windows" ]] && binname="trufflehog.exe"

# --- sha256 helper (portable across macOS/Linux) ------------------------------
sha256_of() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    die "need 'sha256sum' or 'shasum' to verify the download."
  fi
}

# --- Cache location (versioned; binary is immutable per version) --------------
cache_dir="${XDG_CACHE_HOME:-${HOME}/.cache}/nvidia-security-workflows/trufflehog/${TRUFFLEHOG_VERSION}"
bin="${cache_dir}/${binname}"

# --- Install on first use -----------------------------------------------------
install_trufflehog() {
  local url tmp tarball got
  url="https://github.com/trufflesecurity/trufflehog/releases/download/v${TRUFFLEHOG_VERSION}/trufflehog_${TRUFFLEHOG_VERSION}_${platform}.tar.gz"
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/nv-trufflehog.XXXXXX")"
  # shellcheck disable=SC2064
  trap "rm -rf '${tmp}'" RETURN
  tarball="${tmp}/trufflehog.tar.gz"

  printf 'secret-scan-trufflehog: fetching pinned TruffleHog v%s (%s) on first use...\n' \
    "${TRUFFLEHOG_VERSION}" "${platform}" >&2

  if command -v curl >/dev/null 2>&1; then
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
      --retry 3 --retry-delay 1 -o "${tarball}" "${url}" \
      || die "download failed (curl) from ${url}"
  elif command -v wget >/dev/null 2>&1; then
    wget --quiet --https-only -O "${tarball}" "${url}" \
      || die "download failed (wget) from ${url}"
  else
    die "need 'curl' or 'wget' to download TruffleHog."
  fi

  # Verify BEFORE extracting/executing anything. Fail closed on mismatch.
  got="$(sha256_of "${tarball}")"
  if [[ "${got}" != "${expected_sha}" ]]; then
    die "checksum mismatch for ${url}
  expected: ${expected_sha}
  actual:   ${got}
This may indicate a corrupted download or a tampered artifact. Aborting."
  fi

  tar -xzf "${tarball}" -C "${tmp}" "${binname}" || die "failed to extract ${binname} from archive."
  chmod +x "${tmp}/${binname}"

  # Atomic publish into the cache (survives concurrent hook invocations).
  mkdir -p "${cache_dir}"
  mv -f "${tmp}/${binname}" "${bin}"
}

[[ -x "${bin}" ]] || install_trufflehog

exec "${bin}" filesystem "$@" \
  --results=verified \
  --fail \
  --no-update
