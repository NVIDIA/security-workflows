# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [Unreleased]

### Changed

- Secret scan — the job is renamed from `pulse` to `pulse-secret`, matching `pulse-oss` and `pulse-malware`. Its status check becomes `… / pulse-secret`, so repositories that require the old `… / pulse` check must update branch protection when they repin.

## [0.5.0] - 2026-11-03

Additive release: two reusable workflows (vulnerability, malware) and one pre-commit hook (GuardWords). Existing suite callers need no change — `enable-vuln-scan` and `enable-malware-scan` default to false, and the scans' permissions (`contents: read` + `id-token: write` for the vulnerability scan, `id-token: write` alone for the malware scan) are already inside the suite's permission union.

### Added

- Vulnerability scan (SCA) reusable workflow — [`.github/workflows/vuln-scan-pulse-oss.yml`](.github/workflows/vuln-scan-pulse-oss.yml). Runs NVIDIA's Pulse OSS scanner against a disposable copy of the checkout and reports to the nSpect backend over a Charon loopback tunnel. Consumers supply no credentials: GitHub OIDC is the only identity the scan presents, and the `nvcr.io` pull login comes from Vault. The scanner image and the tunnel settings are owned by the workflow, so a caller can substitute neither. `pull_request` / `pull_request_target` are rejected. Inputs and prerequisites are in the [workflow catalogue](.github/workflows/README.md#vulnerability-scan-sca--vuln-scan-pulse-ossyml); build-environment setup is in the [scan guide](docs/vuln-scan/README.md).
- Vulnerability scan — scan targeting. `nspect_id` is optional: left empty the scan runs unregistered, which is the only lane open to a repository with no nSpect registration and is rapid-only. `sbom_name` selects the registration when the registered branch carries more than one SBOM entry, and `inventory_writeback` requires it. `copy-pr-bot` mirrors (`refs/heads/pull-request/*`) are rapid-only.
- Vulnerability scan — findings never decide the scanner's exit code. The CLI always runs with `--no-fail` and `failure_policy` is applied to the validated report, so a non-zero exit is always a failed scan rather than a finding.
- Vulnerability scan — optional build controls, off by default and forwarded by the suite: prepared Python wheels, typed Detect properties, and redacted console/debug logging. Snippet scanning and snippet-match export are deferred to a follow-up release.
- Malware scan reusable workflow — [`.github/workflows/malware-scan-pulse.yml`](.github/workflows/malware-scan-pulse.yml). Asks the Pulse Malware Service to scan the calling run's own commit with ReversingLabs over the production Charon loopback tunnel. The service fetches the commit itself, so nothing is checked out and the scan cannot be pointed at another repository or commit. `failure_policy` is `strict` (default — SUSPICIOUS blocks too) or `malicious-only`; a MALICIOUS verdict, and any scan that ends without one, block under both. `pull_request` / `pull_request_target` are rejected. Prerequisites are in the [workflow catalogue](.github/workflows/README.md#malware-scan--malware-scan-pulseyml).
- Security suite — `enable-vuln-scan` and `enable-malware-scan`, each with its own `vuln-*` / `malware-*` inputs, plus an unprefixed `nspect-id`: an nSpect ID identifies the repository rather than one scan, so every scan reporting to nSpect reads the same one. The malware scan requires it — enabling that scan without it fails the preflight.
- GuardWords (pre-commit) — `guardwords-scan-code-scanning` sends the staged diff to NVIDIA's internal code-scanning service and blocks the commit on blocking findings. It is for NVIDIA employees only: where the client or service is unavailable it skips with a notice, so external contributors are never blocked. [`hooks/guardwords/install_client.py`](hooks/guardwords/install_client.py) sets up the client in one command. See the [GuardWords hook guide](hooks/guardwords/README.md).
- Pre-commit hook catalogue — [`hooks/README.md`](hooks/README.md), the hook-side counterpart to the [workflow catalogue](.github/workflows/README.md).
- CI — contract tests covering every gate in both new workflows, plus live integration runs. The vulnerability scan's integration is ungated, so its Vault and Charon prerequisites stay hard requirements.
- Third-party notices — `teleport-actions/setup` and `actions/upload-artifact`, both pinned by SHA.

### Changed

- Security suite — the preflight reports *every* missing companion input in one run rather than exiting on the first.
- Pin policy — the recommended pre-commit `rev:` pin is now the 40-character commit SHA with the release tag as a `# frozen:` comment, the form `pre-commit autoupdate --freeze` writes, matching the SHA pin already required for reusable workflows. Existing release-tag pins keep working; switch with `pre-commit autoupdate --freeze` at the next refresh. See [Pin policy per surface](README.md#pin-policy-per-surface).

### Fixed

- Secret scan (Pulse): use a shallow checkout for the filesystem scan instead of downloading every branch and tag's history, avoiding large unrelated branches such as `gh-pages`.

### Known limitations

- **Charon is a prerequisite for both scans.** The tunnel authorizes per repository *and* per ref, so a consuming tenant must grant the Pulse backends and list every ref it scans from. Gating pull requests needs the `pull-request/*` mirrors listed; without them both scans are post-merge and scheduled gates. The malware scan-submission route is not granted by default and needs platform approval.
- **Scanner upgrades ship as workflow releases.** Both scanners are pinned by digest — Pulse OSS `0.5.3-charon.11`, Pulse malware `1.3.0` — so a new scanner reaches callers only through a new release of this repository.
- Vulnerability scan — **SARIF publication is a follow-up.** Findings land in the job summary and an optional artifact, not the Security tab.
- Vulnerability scan — **`build: true` runs the repository's build inside the scanner.** Maven and Go graphs resolve only through a build. Prefer it on post-merge and scheduled runs; see the [workflow catalogue](.github/workflows/README.md#vulnerability-scan-sca--vuln-scan-pulse-ossyml) before enabling it on pull-request mirrors.
- Vulnerability scan — **Persistent and write-back scans are pilot-only.** Inventory write-back with `sbom_name` against a branch with several SBOM entries has not been validated end-to-end.
- Malware scan — **Detection is not yet proven end-to-end.** CI asserts transport and a CLEAN verdict; proving a blocking verdict needs a ProdSec-approved detection sample, and the contract tests cover how one is handled.
- GuardWords — **No CI counterpart.** The hook is the only surface and it skips wherever the client or service is unavailable, so a commit that skipped is not re-scanned before merge.

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

[Unreleased]: https://github.com/NVIDIA/security-workflows/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.5.0
[0.4.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.4.0
[0.3.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.3.0
[0.2.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.2.0
[0.1.0]: https://github.com/NVIDIA/security-workflows/releases/tag/v0.1.0
