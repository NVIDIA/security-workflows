| [Contributing](CONTRIBUTING.md) | [Security](SECURITY.md) | [Support](SUPPORT.md) | [Governance](GOVERNANCE.md) | [Maintainers](MAINTAINERS.md) | [Changelog](CHANGELOG.md) | [Third-Party Notices](THIRD_PARTY_NOTICES.md) |
|-|-|-|-|-|-|-|

# NVIDIA Security Workflows

Centrally maintained, reusable GitHub Actions workflows for the security-compliance scans rolled out by the NVIDIA GitHub-First initiative.

This repository is the single source of truth for the security-compliance machinery that powers pre-merge and pre-release security scanning across NVIDIA's GitHub repositories. It is built around two artifact types: **reusable GitHub Actions workflows** (`workflow_call`) under `.github/workflows/` for job-level server-side enforcement, and **pre-commit hooks** for local-advisory checks on the developer's machine. Pre-commit hooks delegate to thin wrapper scripts under `hooks/` that encode the NVIDIA-approved args and resolve the scanner binary from `$PATH`; consumers need the underlying scanner binaries installed locally (per-tool install steps live in each wrapper's header). Both surfaces are pinned per the [surface-specific policy below](#pin-policy-per-surface). No scan surface is published yet — see [`ROADMAP.md`](ROADMAP.md) for per-scan status.

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

- **One contract per scan type.** Each scan category is exposed as a single reusable workflow with a stable `workflow_call` interface. Callers depend on the interface, not the implementation underneath.
- **Self-hosted-runner first.** Workflows target NVIDIA's self-hosted runner platform (`nv-gha-runners`) by default, with a fallback path for GitHub-hosted runners where appropriate.
- **Fail-closed by default.** A finding blocks the merge unless an explicit, documented exception applies.
- **Audit-ready output.** Each run emits a structured audit record for downstream compliance roll-up.
- **Compose, don't reimplement.** Workflows here orchestrate lower-level building blocks — upstream scanner actions (pinned by SHA inside each workflow) and, where appropriate, vetted internal actions — rather than re-implementing scanner integrations. The version, default args, and fail policy of each scan are owned in this repository so that every consumer inherits one audited contract.

The six scan categories below are the in-scope surface for this repository. Specific tool selections are made per scan in coordination with ProdSec and may evolve; the `workflow_call` interface is the stable contract for consumers.

### Secret scanning

Detects credentials, API keys, tokens, and other sensitive material introduced in a pull request before they merge. Runs on the diff for performance and on full-repo for periodic baseline sweeps.

Planned. The CI enforcement lane will run NVIDIA's licensed TruffleHog Enterprise (Pulse Secret Scanner) on `nv-gha-runners`; a local-advisory pre-commit lane will use the open-source [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog) CLI. See [`ROADMAP.md`](ROADMAP.md) for status.

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

No workflows or pre-commit hooks are published yet. Consumption examples for each surface — a job-level `uses:` reference for reusable workflows and a `.pre-commit-config.yaml` entry for hooks — will land here alongside the first published scan. The recommended pin in each context is defined in [Pin policy per surface](#pin-policy-per-surface) (40-character commit SHA for workflows, release tag for pre-commit hooks).

## Getting Started

### Consumers (downstream NVIDIA repositories)

Reusable workflows are consumed via GitHub Actions' [`workflow_call`](https://docs.github.com/en/actions/using-workflows/reusing-workflows) mechanism — a job-level `uses:` reference in the consumer's workflow, pinned by 40-character commit SHA. Pre-commit hooks are consumed via the [pre-commit](https://pre-commit.com/) framework, which references this repository by URL and `rev:` (release tag) in the consumer's `.pre-commit-config.yaml`; hooks use `language: script` and delegate to wrapper scripts under `hooks/` that encode NVIDIA's chosen args and fail-policy. Pre-commit runs on developer machines only — consumers need the underlying scanner binaries installed locally, and per-tool install steps live in each wrapper's header. The full per-surface pin policy is documented in [Pin policy per surface](#pin-policy-per-surface) below.

Per-surface onboarding instructions — runner labels, trigger model, hook arguments, required developer-side tooling, security trade-offs — are documented inline in each workflow file's `workflow_call` definition and the published `.pre-commit-hooks.yaml` manifest, as each surface is published. Higher-level guidance lands in [`SUPPORT.md`](SUPPORT.md) as each surface stabilizes.

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

Workflows in this repository target NVIDIA's self-hosted runner platform (`nv-gha-runners`) as the default. CPU-only runner pools are sufficient for every scan category currently in scope.

A fallback path for GitHub-hosted runners (`ubuntu-latest`) is supported for repositories that have not yet onboarded to `nv-gha-runners`. Specific runner labels are accepted as inputs to each workflow so that consumers can choose the right pool for their repository.

The runner platform itself is documented at [`docs.gha-runners.nvidia.com`](https://docs.gha-runners.nvidia.com/).

### GitHub repository requirements

Consumer repositories are expected to:

- Have GitHub Actions enabled.
- Use branch protection to require the relevant scan checks before merge.
- For downstream consumer repositories that accept external-contributor pull requests on `nv-gha-runners`: have the `copy-pr-bot` GitHub App installed and configured per the runner platform's onboarding guidance. This does not change this repository's no-external-contributions policy.

Specific per-workflow requirements are documented inline in each workflow file's `workflow_call` definition.

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

- [`pre-commit`](https://pre-commit.com/) — Upstream framework that will consume the `.pre-commit-hooks.yaml` manifest published by this repository. The [Installation](https://pre-commit.com/#install) and [Usage](https://pre-commit.com/#usage) sections cover `pre-commit install`, `pre-commit run`, and `pre-commit autoupdate` — the commands consumers will use to install and refresh the hooks defined here.
- [`NVIDIA-GitHub-Management/PLC-OSS-Template`](https://github.com/NVIDIA-GitHub-Management/PLC-OSS-Template) — NVIDIA OSS repository template.

## Repositories Using These Workflows

This list will be populated by NVIDIA maintainers as pilot consumers onboard.

- NVIDIA/cccl

## Security

For vulnerability reporting, see [`SECURITY.md`](SECURITY.md). **Do not file public GitHub issues for security reports.**

## License

This project is licensed under the Apache License 2.0 — see [`LICENSE`](LICENSE) for details. The project-level NVIDIA notice is in [`NOTICE`](NOTICE), and third-party license notices are in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

This project is distributed as source code only. It does not distribute binary
versions of this project or any copyleft-licensed components.
