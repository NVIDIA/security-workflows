# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [Unreleased]

### Changed

- Secret-scan (pre-commit) — retained the `secret-scan-trufflehog` public hook and moved its TruffleHog `v3.95.9` installation from an external user cache to pre-commit's isolated Python environment. The pinned `setuptools-download` build helper downloads the official platform release, verifies its SHA-256, and installs `trufflehog` in that environment's `bin` / `Scripts` directory. This works natively on Windows without Go, Git Bash, curl, tar, or a system-installed scanner; `pre-commit clean` removes the environment and binary.

## [0.2.0] - 2026-07-24

### Changed

- Secret-scan (pre-commit) — the `secret-scan-trufflehog` hook is now **self-installing**: on first use it downloads a pinned, checksum-verified TruffleHog release (`3.95.9`) into a per-user cache and reuses it thereafter, so contributors no longer install `trufflehog` manually. The archive is fetched over HTTPS and verified against a per-platform SHA-256 pinned from the release's cosign-signed `checksums.txt`; the hook fails closed on any mismatch. Supports Linux/macOS/Windows (amd64/arm64).

## [0.1.0] - 2026-07-22

First pilot release. Ships the secret-scan surface (Pulse reusable workflow + TruffleHog pre-commit hook). Pre-1.0: interfaces may change in a minor release while surfaces stabilize with ProdSec.

### Added

- Repository scaffolding — `README`, `ROADMAP`, `GOVERNANCE`, `CONTRIBUTING`, `SUPPORT`, `MAINTAINERS`, `SECURITY`, `CODE_OF_CONDUCT`, `LICENSE`.

- Documentation — top-level [`README.md`](README.md) covers the two-surface model (reusable workflow + pre-commit hook) with consumption examples and the pin-policy table; [`.github/workflows/README.md`](.github/workflows/README.md) is the workflow catalogue; [`ROADMAP.md`](ROADMAP.md) tracks per-scan status.

- OSRB compliance artifacts — [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), no-contributions [`CONTRIBUTING.md`](CONTRIBUTING.md) per OSRB template (maintainer PR workflow lives in [`GOVERNANCE.md`](GOVERNANCE.md#maintainer-workflow)), and source/config SPDX copyright headers.

- Contribution posture — clarified the OSS Type 2 model: public source code with
  NVIDIA-internal development and no external contribution intake.

- Pin policy ([`README.md` → Pin policy per surface](README.md#pin-policy-per-surface)) — 40-character commit SHA for GHA `uses:`; release tag for pre-commit `rev:`; branch references not acceptable. Release tags cut on consumer-visible behaviour or contract changes.

- Repository tooling — pre-commit hygiene configuration ([`.pre-commit-config.yaml`](.pre-commit-config.yaml)) running `pre-commit-hooks`, `yamllint`, `shellcheck`, `actionlint`, and `codespell`; agent guidance ([`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md)).

- copy-pr-bot — [`.github/copy-pr-bot.yaml`](.github/copy-pr-bot.yaml) to gate external-contributor pull-request CI on self-hosted runners.

- Secret-scan (OSS) pre-commit hook — [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) + [`hooks/trufflehog.sh`](hooks/trufflehog.sh), composing upstream [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog). The `secret-scan-trufflehog` hook scans changed files (`pass_filenames: true`) at the `pre-commit` and `pre-push` stages, fail-closed with NVIDIA default `--results=verified` and `--no-update` to keep the local scan fast. The wrapper resolves the `trufflehog` binary from `$PATH` and prints install guidance if it is missing. This is the local-advisory lane.

- Dogfooding — [`.pre-commit-config.yaml`](.pre-commit-config.yaml) runs the `secret-scan-trufflehog` hook from `repo: local` so edits to the wrapper are self-tested; skipped on `pre-commit.ci` (no `trufflehog` binary in that sandbox).

- Secret-scan (Pulse) reusable workflow — [`.github/workflows/secret-scan-pulse.yml`](.github/workflows/secret-scan-pulse.yml). Runs the Pulse Secret Scanner as the CI enforcement lane and publishes redacted SARIF (verified/unknown/unverified) to the repository Security tab. Enforcement via the `failure_policy` input (`unverified` | `strict` | `all`, default `unverified`; names match the GitLab secret-scan component). Fails closed on scanner/infra errors.

- Continuous integration — [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Lints all workflow/hook files and runs positive/negative Pulse integration tests across all three `failure_policy` values.

- Third-party notices — TruffleHog (AGPL-3.0, developer-installed CLI) and the direct workflow actions (`actions/checkout`, `hashicorp/vault-action`, `docker/login-action`, `actions/setup-python`, `github/codeql-action/upload-sarif`) recorded in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) with SHA pins where applicable.

[Unreleased]: https://github.com/NVIDIA/security-workflows/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.1.0
