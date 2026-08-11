| [Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Support](SUPPORT.md) | [Governance](GOVERNANCE.md) | [Maintainers](MAINTAINERS.md) | [Changelog](CHANGELOG.md) | [Third-Party Notices](THIRD_PARTY_NOTICES.md) |
|-|-|-|-|-|-|-|

# NVIDIA Security Workflows

Centrally maintained, reusable GitHub Actions workflows for the security-compliance scans rolled out by the NVIDIA GitHub-First initiative.

This repository is the single source of truth for the security-compliance machinery that powers pre-merge and pre-release security scanning across NVIDIA's GitHub repositories. It publishes two artifact types: **reusable GitHub Actions workflows** (`workflow_call`) under [`.github/workflows/`](.github/workflows/README.md) for job-level server-side enforcement, and **pre-commit hooks** declared in [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) for local-advisory checks on the developer's machine. `secret-scan-trufflehog` downloads a pinned, SHA-256-verified TruffleHog release into pre-commit's isolated environment during hook installation, so consumers need no system scanner or shell installer. Both surfaces are pinned per the [surface-specific policy below](#pin-policy-per-surface).

Pre-commit and CI are complementary, not alternatives: pre-commit is local-advisory (best-effort, optimized for developer experience) and CI is server-side enforcement (authoritative, fail-closed). The CI surface is a reusable workflow (declared `permissions:`, isolated job) — the preferred shape for security gates. A scan category may ship the CI workflow, the pre-commit hook, or both, depending on whether it fits the <10s local-execution budget.

The repository covers six scan categories:

- [Secret scanning](#secret-scanning)
- [License scanning](#license-scanning)
- [Vulnerability scanning](#vulnerability-scanning)
- [Malware scanning](#malware-scanning)
- [Static Application Security Testing (SAST)](#static-application-security-testing-sast)
- [GuardWords scanning](#guardwords-scanning)

This repository focuses on the reusable security workflow surface for NVIDIA repositories. Project support, governance, and release rules are documented in the linked repository policy files above.

## Overview

The goal of this repository is to give every NVIDIA repository a consistent, audit-ready security-scan surface without forcing each team to reinvent it. By consuming reusable workflows from one central location, downstream repositories inherit the policy, telemetry, and runner-isolation choices that are made once at the org level and reviewed by NVIDIA Product Security (ProdSec).

Workflows in this repository are designed around a few shared principles:

- **One contract per scan type.** Each scan category is exposed as a single reusable workflow with a stable `workflow_call` interface. Callers depend on the interface, not the implementation underneath. Repositories that want several scans behind one pinned reference can use the `security-suite.yml` aggregate, which fans out in parallel to the scans the caller explicitly enables; its full contract is in the [workflow catalogue](.github/workflows/README.md).
- **Self-hosted runners required for internal-service scans.** Workflows that use NVIDIA-internal services — Vault (OIDC) and `nvcr.io` scanner images, e.g. the Pulse secret scan — run **only** on `nv-gha-runners`; those services are unreachable from GitHub-hosted runners. Workflows with no such dependency (e.g. CodeQL SAST) may run on GitHub-hosted runners.
- **Fail-closed by default.** A finding blocks the merge unless an explicit, documented exception applies.
- **Audit-ready output.** Each run emits a structured audit record for downstream compliance roll-up.
- **Compose, don't reimplement.** Workflows here orchestrate lower-level building blocks — upstream scanner actions (pinned by SHA inside each workflow) and, where appropriate, vetted internal actions — rather than re-implementing scanner integrations. The version, default args, and fail policy of each scan are owned in this repository so that every consumer inherits one audited contract.

The six scan categories below are the in-scope surface for this repository. Specific tool selections are made per scan in coordination with ProdSec and may evolve; the `workflow_call` interface is the stable contract for consumers.

### Secret scanning

Detects credentials, API keys, tokens, and other sensitive material introduced in a pull request before they merge. Runs on the diff for performance and on full-repo for periodic baseline sweeps.

The CI surface is `secret-scan-pulse`, which runs NVIDIA's licensed TruffleHog Enterprise (Pulse Secret Scanner) on `nv-gha-runners`. Each run publishes redacted findings to the repository Security tab (maintainers only); raw scanner output is not written to the job log. Local pre-commit checks use `secret-scan-trufflehog`, built on the open-source [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog) CLI. See the [workflow catalogue](.github/workflows/README.md) for the CI interface and [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) for the hook.

### License scanning

Verifies that source files carry approved license headers and that direct and transitive dependencies use licenses compatible with NVIDIA's open-source distribution policy.

### Vulnerability scanning

Identifies known vulnerabilities (CVEs) and risky packages in third-party dependencies pulled in by the repository, across supported language ecosystems. Sometimes referred to as Software Composition Analysis (SCA).

### Malware scanning

Inspects committed and incoming files for malicious binaries, packers, droppers, and known indicators of compromise. Targeted at repositories that ingest binaries, models, or other non-source artifacts.

### Static Application Security Testing (SAST)

Performs static code analysis to surface security defects in first-party source code (e.g. injection, unsafe deserialization, weak cryptographic primitives).

### GuardWords scanning

Flags terminology and content that conflicts with NVIDIA brand, legal, or inclusivity guidance.

## Example

The expected consumption pattern for each surface is shown below. See [Pin policy per surface](#pin-policy-per-surface) for the recommended pin in each context (40-character commit SHA for workflows, release tag for pre-commit hooks).

**Reusable workflow** — drop into a new isolated job (the CI security gate):

```yaml
on: [pull_request]

permissions:
  contents: read
  id-token: write          # OIDC → Vault → nvcr.io image pull
  security-events: write   # publish redacted SARIF to code scanning
  actions: read            # required by upload-sarif action

jobs:
  secret-scan:
    uses: NVIDIA/security-workflows/.github/workflows/secret-scan-pulse.yml@<COMMIT-SHA>
    # Optional overrides — see the workflow file for the full interface:
    # with:
    #   runs-on: linux-amd64-cpu4   # nv-gha-runners label
    #   failure_policy: strict      # fail on any finding (default: unverified — fail verified, warn unverified)
```

The full catalogue lives in [`.github/workflows/`](.github/workflows/README.md). Each workflow's inputs, required permissions, and security trade-offs are documented in the workflow catalogue README and inline in each workflow's `workflow_call` block.

**Pre-commit hook** (in a consumer's `.pre-commit-config.yaml`):

```yaml
# `secret-scan-trufflehog` installs its pinned scanner in pre-commit's
# isolated environment; no system TruffleHog installation is needed.
- repo: https://github.com/NVIDIA/security-workflows
  rev: v0.3.0                              # release tag — see Pin policy per surface below
  hooks:
    - id: secret-scan-trufflehog
```

## Getting Started

### Consumers (downstream NVIDIA repositories)

Reusable workflows are consumed via GitHub Actions' [`workflow_call`](https://docs.github.com/en/actions/using-workflows/reusing-workflows) mechanism — a job-level `uses:` reference in the consumer's workflow, pinned by 40-character commit SHA. Pre-commit hooks are consumed via the [pre-commit](https://pre-commit.com/) framework, which references this repository by URL and `rev:` (release tag) in the consumer's `.pre-commit-config.yaml`. `secret-scan-trufflehog` uses `language: python` and installs its pinned, SHA-256-verified TruffleHog release in pre-commit's isolated environment; consumers need no system scanner or shell installer. The full per-surface pin policy is documented in [Pin policy per surface](#pin-policy-per-surface) below.

Per-surface onboarding instructions — runner labels, trigger model, hook arguments, required developer-side tooling, security trade-offs — are documented inline: each workflow file's `workflow_call` definition and [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml). Higher-level guidance lands in [`SUPPORT.md`](SUPPORT.md) as each surface stabilizes.

The current release status of each scan category lives in [`ROADMAP.md`](ROADMAP.md).

### Contributors

This is an NVIDIA OSS Type 2 repository: the source code is public, but development and contribution intake are handled inside NVIDIA.
This project is currently not accepting contributions (see [`CONTRIBUTING.md`](CONTRIBUTING.md)).

NVIDIA maintainers should follow [`GOVERNANCE.md`](GOVERNANCE.md#maintainer-workflow)
for the pull request process and the NVIDIA IP review requirement.
Maintainer escalation paths are in [`MAINTAINERS.md`](MAINTAINERS.md).

## Platform Support

**Objective:** This section describes where workflows in this repository are expected to run successfully.

### Runners

The Vault- and `nvcr.io`-backed CI workflows (e.g. the Pulse secret scan) run **only on NVIDIA's self-hosted runners (`nv-gha-runners`)**. They mint short-lived credentials to pull the scanner image and are reachable only from self-hosted runners. On GitHub-hosted runners (`ubuntu-latest`) the Vault step fails and the scan cannot run. Workflows without those dependencies (e.g. CodeQL SAST) may use GitHub-hosted runners.

Pass an actual runner **label** to `runs-on` (e.g. `linux-amd64-cpu4`). CPU-only pools are sufficient for every scan category in scope. See the [runner label catalog](https://nv/gha-runner-labels) for the label↔group mapping and the [runner platform documentation](https://nv/gha-runners-docs) for the platform itself.

> `nv/…` links in this document are NVIDIA-internal and resolve only from the NVIDIA network. NVIDIA maintainers of consumer repositories are the audience for the runner onboarding steps.

### GitHub repository requirements

Consumer repositories are expected to:

- Have GitHub Actions enabled.
- Use branch protection to require the relevant scan checks before merge.
- For downstream consumer repositories that accept external-contributor pull requests on `nv-gha-runners`: have the `copy-pr-bot` GitHub App installed and configured per the runner platform's onboarding guidance. This does not change this repository's no-external-contributions policy.

Specific per-workflow requirements are documented inline in each workflow file's `workflow_call` definition.

### Onboarding a repository

To run the CI security workflows in your repository:

1. **Get self-hosted runner access.** Your org must have the [`nvidia-runner-mgmt`](https://nv/gha-runner-app) app installed, and your repo must be granted a runner group (e.g. `nv-cpu-general`) via a PR to the [runner configuration repository](https://nv/gha-runner-config) — see [Requesting access](https://nv/gha-runner-access).
2. **Confirm the Vault / Pulse Actions variables exist** (secret-scan only). The Pulse workflow reads repo/org variables `NV_VAULT_URL`, `NVCR_VAULT_*`, `SECRET_SCAN_PULSE_IMAGE`, and `SECRET_SCAN_PULSE_IMAGE_TAG`. If unset, the Vault step fails with `Input required and not supplied: url` — ask the GitHub-First platform team to provision them.
3. **Add the caller workflow** — reference the reusable workflow pinned by commit SHA, grant the permissions it declares, and set `runs-on` to a real label (see the [Example](#example)).
4. **Add the pre-commit hook** (optional, local-advisory) — see the [Example](#example).
5. **Require the check** in branch protection once it is green.

Reference onboarding PRs: [`NVIDIA/cccl#10010`](https://github.com/NVIDIA/cccl/pull/10010) and [`NVIDIA/cuda-python#2405`](https://github.com/NVIDIA/cuda-python/pull/2405).

## Versioning

**Objective:** This section describes how workflows in this repository are versioned and how consumers should reference them.

- Releases follow [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH` — published as Git tags on this repository. The same release tag covers both surfaces (reusable workflows and pre-commit hooks).
- A breaking change to a workflow's `workflow_call` interface, or a pre-commit hook's id, arguments, or default policy bumps the **major** version.
- New optional inputs, additional scan categories, or additional hooks bump the **minor** version.
- Bug fixes and tightening of internal implementation bump the **patch** version.
- Tags are immutable — see [`GOVERNANCE.md`](GOVERNANCE.md#release-tagging) for the release-tag policy.

### Pin policy per surface

Consumers must pin every reference. The recommended pin differs by surface because the underlying tooling differs.

| Where the reference appears | Recommended pin | Rationale |
|---|---|---|
| Job-level `uses:` in a consumer workflow (reusable workflow) | 40-character commit SHA | GitHub Actions has no autoupdate mechanism; a force-pushed tag is exploited on the next CI run. |
| `rev:` in a consumer `.pre-commit-config.yaml` | Release tag (e.g. `v0.1.0`) | `pre-commit autoupdate` is the gated refresh mechanism; tags from this repository are immutable per release policy. |

Branch references (`@main`, `@latest`) are not acceptable on any surface — they defeat reproducibility and supply-chain controls.

A changelog of each release lives in [`CHANGELOG.md`](CHANGELOG.md).

## Deprecation Policy

Breaking changes to a published workflow will be announced at least one minor version in advance, when feasible. Deprecation notices appear in:

- The workflow's `workflow_call` description.
- Release notes in [`CHANGELOG.md`](CHANGELOG.md).
- The maintainers' communication channels (see [`SUPPORT.md`](SUPPORT.md)).

The deprecation window will depend on the impact of the change but will usually last at least one minor version release.

## Related Projects

- [`pre-commit`](https://pre-commit.com/) — Upstream framework that consumes the `.pre-commit-hooks.yaml` manifest in this repository. The [Installation](https://pre-commit.com/#install) and [Usage](https://pre-commit.com/#usage) sections cover `pre-commit install`, `pre-commit run`, and `pre-commit autoupdate` — the commands consumers will use to install and refresh the hooks defined here.
- [NVIDIA OSS repository template](https://nv/oss-repo-template) — Template NVIDIA maintainers start new OSS repositories from.

## Repositories Using These Workflows

This list will be populated by NVIDIA maintainers as pilot consumers onboard.

- NVIDIA/cccl

## Security

For vulnerability reporting, see [`SECURITY.md`](SECURITY.md). **Do not file public GitHub issues for security reports.**

## License

This project is licensed under the Apache License 2.0 — see [`LICENSE`](LICENSE) for details. The project-level NVIDIA notice is in [`NOTICE`](NOTICE), and third-party license notices are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

This project is distributed as source code only. It does not distribute binary
versions of this project or any copyleft-licensed components.
