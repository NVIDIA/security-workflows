# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [0.4.0] - 2026-08-19

Additive release. Callers passing `languages: '["actions","python"]'` need no change; the declared `permissions:` are unchanged, and the `analyze` job keeps the name `CodeQL (<language>)` so required status checks continue to match.

### Added

- SAST (CodeQL) — build mode is resolved per language instead of one value applied to every matrix leg, so sets with conflicting requirements work in a single call. `'["go","rust"]'` could not previously be expressed (`go` needs `autobuild`, `rust` supports only `none`). Substitutions are reported as job-log notices and the resolved matrix is written to the job summary.
- SAST (CodeQL) — `languages` entries may be objects carrying a per-language `build-mode` or `runs-on`: `'[{"language":"swift","runs-on":"macos-14"},"rust"]'`. Per-entry `runs-on` makes `swift` usable, as it requires a macOS runner.
- SAST (CodeQL) — a `resolve` job validates the language set before any analysis starts, rejecting unknown languages, `manual` mode, unsupported explicit modes, duplicate languages, malformed JSON, and empty lists. New `resolve-runs-on` input (default `ubuntu-latest`); the suite passes `suite-runs-on` through to it.
- Documentation — the [workflow catalogue](.github/workflows/README.md#accepted-languages-values) now lists the accepted `languages` values with per-language buildless support, plus the two coverage gaps: no shell analyzer (use `shellcheck`) and no CUDA analyzer (`c-cpp` skips `.cu` / `.cuh`).

### Changed

- SAST (CodeQL) — `build-mode` is now a preference applied where the language supports it; an explicit per-language mode is exact and errors if CodeQL rejects it. No existing caller changes behaviour.
- SAST (CodeQL) — the `analyze` job keeps the name `CodeQL (<language>)`, so required status checks still match. A new non-required check, `Resolve language matrix`, appears alongside it.

### Fixed

- Documentation — `build-mode` was described as working "for every language": `go` and `swift` reject `none`, Kotlin requires `autobuild`, and `rust` supports only `none`.
- Documentation — the CodeQL prerequisite said Default setup must be off entirely. The conflict is per language: both publish `/language:<lang>`, so only an overlap collides. Default setup on other languages can coexist, as it already does on this repository.
- Documentation — the catalogue gave CodeQL's `runs-on` default as `linux-amd64-cpu4` (actual: `ubuntu-latest`) and required an `nv-gha-runners` label for every workflow, which does not apply to CodeQL.

## [0.3.0] - 2026-08-11

### Added

- Security suite reusable workflow — [`.github/workflows/security-suite.yml`](.github/workflows/security-suite.yml) runs the scans a caller enables (`enable-secret-scan`, `enable-sast-scan`) in parallel behind one pinned reference. Every scan is opt-in, including scans added in future releases, so onboarding a repository to the suite never turns on a scan it did not ask for; category-prefixed inputs preserve the child workflows' runner and policy configuration. A suite call that enables nothing warns instead of failing.
- SAST (CodeQL) reusable workflow — [`.github/workflows/sast-scan-codeql.yml`](.github/workflows/sast-scan-codeql.yml). Generic, matrix-driven CodeQL analysis (`languages`, `build-mode`, `queries`, `packs`, `config-file`, `runs-on` inputs) with the `github/codeql-action` steps pinned by SHA. Positioned as the **customization-tier** lever — the fleet baseline for CodeQL is GitHub Default setup via org/enterprise Security Configurations. See [`.github/workflows/README.md`](.github/workflows/README.md#sast-codeql) for prerequisites (GHAS/code scanning, Default-setup conflict) and usage.

### Changed

- Secret-scan (Pulse) — the reusable workflow no longer uploads SARIF on CI self-test runs (`ci_test_setup: true`), so the disposable RSA fixture no longer publishes a code-scanning alert to the default-branch Security tab. Real consumer scans are unaffected.
- Secret-scan (pre-commit) — `secret-scan-trufflehog` now installs the SHA-256-pinned TruffleHog release in pre-commit's isolated Python environment rather than the per-user cache.

### Fixed

- Secret-scan (pre-commit) — `secret-scan-trufflehog` no longer fails on pytest function names. A Lob API key is `test_` followed by 35 characters, so TruffleHog's Lob detector matched names such as `test_gpu_conf_compute_attestation_report` and its verifier reported them as **verified**, the one result class the hook blocks on. Lob is now excluded from the hook's detector set.

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

[Unreleased]: https://github.com/NVIDIA/security-workflows/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.4.0
[0.3.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.3.0
[0.2.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.2.0
[0.1.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.1.0
