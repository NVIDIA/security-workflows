# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [Unreleased]

### Added

- Repository scaffolding — `README`, `ROADMAP`, `GOVERNANCE`, `CONTRIBUTING`, `SUPPORT`, `MAINTAINERS`, `SECURITY`, `CODE_OF_CONDUCT`, `LICENSE`.

- Documentation — top-level [`README.md`](README.md) covers the two-surface model (reusable workflow + pre-commit hook) with consumption guidance and the pin-policy table; [`ROADMAP.md`](ROADMAP.md) tracks per-scan status.

- OSRB compliance artifacts — [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), no-contributions [`CONTRIBUTING.md`](CONTRIBUTING.md) per OSRB template (maintainer PR workflow lives in [`GOVERNANCE.md`](GOVERNANCE.md#maintainer-workflow)), and source/config SPDX copyright headers.

- Contribution posture — clarified the OSS Type 2 model: public source code with
  NVIDIA-internal development and no external contribution intake.

- Pin policy ([`README.md` → Pin policy per surface](README.md#pin-policy-per-surface)) — 40-character commit SHA for GHA `uses:`; release tag for pre-commit `rev:`; branch references not acceptable. Release tags cut on consumer-visible behaviour or contract changes.

- Repository tooling — pre-commit hygiene configuration ([`.pre-commit-config.yaml`](.pre-commit-config.yaml)) running `pre-commit-hooks`, `yamllint`, `shellcheck`, `actionlint`, and `codespell`; agent guidance ([`AGENTS.md`](AGENTS.md), [`CLAUDE.md`](CLAUDE.md)).

- copy-pr-bot — [`.github/copy-pr-bot.yaml`](.github/copy-pr-bot.yaml) to gate external-contributor pull-request CI on self-hosted runners.

- Secret-scan (OSS) pre-commit hook — [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) + [`hooks/trufflehog.sh`](hooks/trufflehog.sh), composing upstream [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog). The `secret-scan-trufflehog` hook scans changed files (`pass_filenames: true`) at the `pre-commit` and `pre-push` stages, fail-closed with NVIDIA default `--results=verified` and `--no-update` to keep the local scan fast. The wrapper resolves the `trufflehog` binary from `$PATH` and prints install guidance if it is missing. This is the local-advisory lane; a CI enforcement lane (Pulse Secret Scanner) is planned.

- Dogfooding — [`.pre-commit-config.yaml`](.pre-commit-config.yaml) runs the `secret-scan-trufflehog` hook from `repo: local` so edits to the wrapper are self-tested; skipped on `pre-commit.ci` (no `trufflehog` binary in that sandbox).

- Third-party notices — TruffleHog (AGPL-3.0, developer-installed CLI) recorded in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
