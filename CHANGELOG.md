# Changelog

All notable changes to the workflows in this repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html). See [`README.md`](README.md#versioning) for the SHA-pinning contract that consumers are expected to follow.

## [Unreleased]

Additive release. Existing suite callers need no change: `enable-vuln-scan` and `enable-malware-scan` default to false, and the scans' permissions — `contents: read` + `id-token: write` for the vulnerability scan, `id-token: write` alone for the malware scan — are already inside the suite's permission union.

### Added

- Vulnerability scan (SCA) reusable workflow — [`.github/workflows/vuln-scan-pulse-oss.yml`](.github/workflows/vuln-scan-pulse-oss.yml). Runs NVIDIA's Pulse OSS scanner and reports to the nSpect backend over a Charon loopback tunnel. GitHub OIDC is the only identity presented: the `nvcr.io` image is pulled with short-lived Vault credentials, so consumers supply none of their own. The scanner image is pinned by digest inside the workflow, so callers cannot substitute it, and each run records the digest it executed in the job summary and the `scanner_image_digest` output. The Charon tunnel settings are likewise owned by the workflow. The scanner runs with no capabilities, cannot acquire any, and never sees the caller's checkout — it scans a disposable copy that is discarded with the job. `pull_request` / `pull_request_target` are rejected. Prerequisites and constraints are in the [workflow catalogue](.github/workflows/README.md#vulnerability-scan-sca--vuln-scan-pulse-ossyml).
- Vulnerability scan — unregistered scans. `nspect_id` is optional; left empty the scan runs `--no-nspect`, reporting findings in the job without recording them against a registration. That is the only lane open to a repository with no nSpect registration, and it is rapid-only: a persistent scan has no registration to write back to.
- Vulnerability scan — `sbom_name`, passed to the CLI as `--sbom-name`, selects the nSpect registration when the registered branch carries more than one SBOM entry. It needs `nspect_id`, and `inventory_writeback` requires it, so a write lands only on a named registration.
- Vulnerability scan — `copy-pr-bot` pull-request mirrors (`refs/heads/pull-request/*`) are RAPID-only: `persistent` and `inventory_writeback` are refused there, `auto` resolves to `rapid`, and `registered_branch` cannot name a mirror.
- Vulnerability scan — findings never decide the scanner's exit code. The CLI always runs with `--no-fail` and `failure_policy` is applied to the validated report, so a non-zero exit is always a failed scan; log text can mark a zero exit as failed but never the reverse. A policy violation the report has no findings for is refused rather than passed.
- Security suite — `enable-vuln-scan` with `vuln-*` inputs (`vuln-registered-branch`, `vuln-sbom-name`, `vuln-runs-on`, `vuln-scan-path`, `vuln-scan-mode`, `vuln-build`, `vuln-failure-policy`, `vuln-inventory-writeback`, `vuln-upload-report`, `vuln-timeout-seconds`), plus an unprefixed `nspect-id`: an nSpect ID identifies the repository rather than one scan, so every scan reporting to nSpect reads the same one.
- CI — contract tests driving the five gates extracted from `vuln-scan-pulse-oss.yml` (input contract, `scan_path` containment, result classification, report validation, enforcement) and the suite preflight, located by step name so a rename fails extraction rather than silently testing nothing. They cover what a live scan cannot: every rejection path, and `fail-on-vulnerability`, whose correct outcome is a *failing* job — unmaskable in a reusable-workflow call.
- CI — live integration on every push, ungated, so the scan's prerequisites (the Vault variables, and the triggering ref on this repository's Charon tenant allowlist) are hard requirements rather than optional extras. One scan proves transport; a `ci_test_setup` fixture with a known-vulnerable pin proves detection, asserted non-zero — a clean result there would mean no components resolved, not that the dependency is safe.
- Malware scan reusable workflow — [`.github/workflows/malware-scan-pulse.yml`](.github/workflows/malware-scan-pulse.yml). Asks the Pulse Malware Service to scan the calling run's commit with ReversingLabs over the production Charon loopback tunnel. The service fetches the commit itself, so nothing is checked out and the target cannot be pointed at another repository or commit; GitHub OIDC is the only identity the scan presents, and the job's only other credential is the `nvcr.io` pull login it reads from Vault. The scanner image is pinned by digest inside the workflow, so callers cannot substitute it, and each run records the digest it executed in the job summary and the `scanner_image_digest` output. `timeout_minutes` (default 60) sets the job timeout, and the scanner's report polling is derived from it, so a slow scan fails as `timeout` rather than as a cancelled job. `failure_policy` is `strict` (default — SUSPICIOUS blocks too) or `malicious-only` (SUSPICIOUS warns); a MALICIOUS verdict, and any scan that ends without one, block under both. A verdict stands only where the scanner's exit code and its report agree — every other pairing fails closed with a named diagnostic category. `pull_request` / `pull_request_target` are rejected. The Charon tunnel settings are likewise owned by the workflow, so a caller cannot send the scan, or the job's OIDC token, through another proxy. The scanner container runs with no capabilities and cannot acquire any. Scanner output is redacted of tokens, auth headers, cookies, and signed-URL credentials before it is printed or kept, and withheld if anything credential-shaped survives. Prerequisites are in the [workflow catalogue](.github/workflows/README.md#malware-scan--malware-scan-pulseyml).
- Security suite — `enable-malware-scan` with `malware-*` inputs (`malware-runs-on`, `malware-failure-policy`, `malware-upload-report`, `malware-timeout-minutes`). The malware scan reads the shared `nspect-id` and requires it: enabling the scan without it fails the preflight.
- CI — contract tests driving the four gates extracted from `malware-scan-pulse.yml` (input contract, verdict classification, report validation, enforcement) and the suite preflight, located by step name so a rename fails extraction rather than silently testing nothing. CI also asserts that the workflow reads neither the scanner image nor the Charon settings from caller variables and accepts only digest references, and extraction fails unless the job timeout comes from `timeout_minutes`. They cover what a live scan cannot: every rejection path, every pairing of exit code and report status, redaction of credential-shaped scanner output, and the blocking verdicts, whose correct outcome is a *failing* job.
- CI — live integration asserting transport, a CLEAN verdict, and the recorded scanner digest through the workflow outputs, plus a suite self-test, gated on `ENABLE_PULSE_INTEGRATION` like the secret-scan live jobs.
- Third-party notices — `teleport-actions/setup` and `actions/upload-artifact`, both pinned by SHA, used by the vulnerability and malware scans.

### Changed

- Security suite — the preflight reports *every* missing companion input in one run rather than exiting on the first.
- Vulnerability scan — the scanner now works on a disposable copy of the checkout rather than a read-only mount of it. The consumer's working tree is still never writable by the container, but Detect's language detectors can generate the per-project metadata they need. A read-only tree made the `SETUPTOOLS` and `UV` detectors fail on any repository whose packages generate `.egg-info`, and Detect reports a failed detector as a non-zero status rather than as a partial scan, so the whole scan failed.

### Known limitations

- **SARIF publication is a follow-up.** Findings land in the job summary and an optional artifact, not the Security tab.
- **A Charon tenant is a prerequisite.** The scan reaches nSpect and Black Duck through a Charon tunnel, which authorizes per repository *and* per ref. A consuming repository needs a tenant granting the Pulse backends and listing every ref it scans from, including the `pull-request/*` mirrors if the scan gates pull requests.
- **`build: true` runs the repository's build inside the scanner.** Maven and Go graphs resolve only through a build, so build mode executes repository-controlled build logic in the container. Prefer it on post-merge and scheduled runs; see the [workflow catalogue](.github/workflows/README.md#vulnerability-scan-sca--vuln-scan-pulse-ossyml) before enabling it on pull-request mirrors.
- **`registered_branch` is the branch reported to nSpect** even when a rapid scan runs from another ref, because the registration lookup is keyed on it. Rapid scans record nothing, so this is request metadata, not a finding of record.
- **Release scans are not yet advertised.** Inventory write-back with `sbom_name` against a repository whose branch has several SBOM entries has not been validated end-to-end; treat persistent and write-back scans as pilot-only until it has.
- Malware scan — **Scanner upgrades ship as workflow releases.** The scanner is pinned to the `1.3.0` image by digest, so a new scanner release reaches callers only through a new release of this workflow.
- Malware scan — **Charon route approval.** The scan-submission route is not in the set tenants are granted by default, so each consuming tenant needs platform approval before the scan can run.
- Malware scan — **Mirror refs need a tenant entry.** The scan runs on `pull-request/*` mirrors only where the repository's Charon tenant lists `refs/heads/pull-request/*`; elsewhere it is a post-merge and scheduled gate.
- Malware scan — **Detection is not yet proven end-to-end.** CI asserts transport and a CLEAN verdict; proving a blocking verdict needs a ProdSec-approved detection sample. The contract tests cover how one is handled.

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
