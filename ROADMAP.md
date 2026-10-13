# Roadmap

## Status legend

| Status | Meaning |
|---|---|
| Planned | In scope, not yet started |
| Design | Interface and policy under design with ProdSec |
| Pilot | Published; consumed by a small set of pilot repositories |
| GA | Generally available for any NVIDIA repository to consume |
| Deprecated | Scheduled for removal in a future major release |

## Scan categories

| Scan | Reusable workflow status | Pre-commit hook status | Notes |
|---|---|---|---|
| Secret scanning | Pilot (v0.1.0) — [`.github/workflows/secret-scan-pulse.yml`](.github/workflows/secret-scan-pulse.yml) | Pilot (v0.1.0) — `secret-scan-trufflehog` published in [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) | Pulse is the CI enforcement lane (runs the Pulse image on `nv-gha-runners`); OSS TruffleHog is the local pre-commit advisory lane. |
| License scanning | Planned | Planned | — |
| Vulnerability scanning | Design — [`.github/workflows/vuln-scan-pulse-oss.yml`](.github/workflows/vuln-scan-pulse-oss.yml) (Pulse OSS → nSpect) | Out of scope (>10s DX budget) | CI workflow only. A repository needs a Charon tenant granting the Pulse backends, and each gating ref on its allowlist. SARIF publication is a follow-up. |
| Malware scanning | Design — [`.github/workflows/malware-scan-pulse.yml`](.github/workflows/malware-scan-pulse.yml) (Pulse Malware Service, server-side fetch) | Out of scope (off-runner verdict service) | CI workflow only. Nothing is checked out — the service fetches the commit itself. Each consuming tenant needs Charon route approval, and the mirror refs to gate merges. Detection is not yet proven end-to-end. |
| Static Application Security Testing (SAST) | Design — [`.github/workflows/sast-scan-codeql.yml`](.github/workflows/sast-scan-codeql.yml) (CodeQL candidate; **selection pending ProdSec**) | Out of scope (>10s DX budget) | CI workflow only. Customization-tier lever; fleet baseline is GitHub Default setup via org Security Configurations. Candidates: CodeQL/SonarQube/Coverity. |
| GuardWords scanning | Planned | Planned | — |

## Cross-cutting work

| Item | Status | Notes |
|---|---|---|
| SHA-pinning policy and tooling | Planned | Enforce 40-char SHA pins on all `uses:` references in published workflows |
| Audit-log schema (v1) | Planned | Common shape for the structured run record emitted by every scan workflow |
| Pilot consumer onboarding guide | Planned | Will land alongside the first published workflow |

Roadmap ownership is handled by NVIDIA maintainers. External contribution
requests are not accepted for this repository at this time; see
[`CONTRIBUTING.md`](CONTRIBUTING.md).
