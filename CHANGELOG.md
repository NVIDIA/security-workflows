# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [Unreleased]

### Added

- Repository scaffolding — `README`, `GOVERNANCE`, `CONTRIBUTING`, `SUPPORT`, `MAINTAINERS`, `SECURITY`, `CODE_OF_CONDUCT`, `LICENSE`.

- Secret-scan (Pulse) reusable workflow — [`.github/workflows/secret-scan-pulse.yml`](.github/workflows/secret-scan-pulse.yml). NVIDIA's enterprise secret scanner (Pulse Secret Scanner) is the CI enforcement lane, with a fail-closed default. Each run converts findings to redacted SARIF and publishes them to the repository Security tab (maintainers only); raw scanner output is kept off the job log. Default `--results=verified,unknown`. Runs on NVIDIA's self-hosted runners. Internal registry/Vault details are sourced from repository/org variables, not hardcoded.

- Secret-scan (OSS) pre-commit hook — [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) + [`hooks/trufflehog.sh`](hooks/trufflehog.sh), composing upstream [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog), fail-closed with NVIDIA default `--results=verified`. This is the local-advisory lane; the CI enforcement lane is the Pulse workflow above.

- Continuous integration — [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Validates the repository's own workflow and hooks, and runs positive/negative integration tests for the Pulse scan (clean input passes; a planted secret must be detected) on every change. Adds [`.github/actionlint.yaml`](.github/actionlint.yaml) declaring self-hosted runner labels.

- Documentation — top-level [`README.md`](README.md) covers the two-surface model (reusable workflow + pre-commit hook) with consumption examples and the pin-policy table; [`.github/workflows/README.md`](.github/workflows/README.md) is the workflow catalogue.

- OSRB compliance artifacts — [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md), no-contributions [`CONTRIBUTING.md`](CONTRIBUTING.md) per OSRB template (maintainer PR workflow lives in [`GOVERNANCE.md`](GOVERNANCE.md#maintainer-workflow)), and source/config SPDX copyright headers.

- Contribution posture — clarified the OSS Type 2 model: public source code with
  NVIDIA-internal development and no external contribution intake.

- Pin policy ([`README.md` → Pin policy per surface](README.md#pin-policy-per-surface)) — 40-character commit SHA for GHA `uses:`; release tag for pre-commit `rev:`; branch references not acceptable. Release tags cut on consumer-visible behaviour or contract changes.

### Changed

- Secret-scan (Pulse) — always publish redacted SARIF to code scanning; remove `upload-sarif` and `upload-artifact` caller inputs; redirect scanner stderr off the job log; use `pulse-secret-scan-*` temp artifact names and `pulse-secret-scan` SARIF category.

- `THIRD_PARTY_NOTICES.md` — add direct workflow dependencies (`vault-action`, `docker/login-action`, `setup-python`, `codeql-action/upload-sarif`) with SHA pins.
