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
| Secret scanning | Pilot (v0.1.0) — [`.github/workflows/secret-scan-pulse.yml`](.github/workflows/secret-scan-pulse.yml) | Pilot — [`secret-scan-trufflehog`](.pre-commit-hooks.yaml), TruffleHog `v3.95.9` | Pulse is the CI enforcement lane (runs the Pulse image on `nv-gha-runners`); the managed OSS hook is the optional local-advisory lane. It installs a pinned prebuilt binary in the isolated pre-commit environment. |
| License scanning | Planned | Planned | — |
| Vulnerability scanning | Planned | Out of scope (>10s DX budget) | CI workflow only |
| Malware scanning | Planned | Out of scope (off-runner verdict service) | CI workflow only |
| Static Application Security Testing (SAST) | Planned | Out of scope (>10s DX budget) | CI workflow only; CodeQL/SonarQube/Coverity |
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
