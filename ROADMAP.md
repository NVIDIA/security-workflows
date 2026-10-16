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
| Vulnerability scanning | Design — [`.github/workflows/vuln-scan-pulse-oss.yml`](.github/workflows/vuln-scan-pulse-oss.yml) (Pulse OSS → nSpect) | Out of scope (>10s DX budget) | CI workflow only. Post-merge and scheduled today — PR gating is blocked on the Charon ref allowlist (see [Cross-cutting work](#cross-cutting-work)). SARIF publication is a follow-up. |
| Malware scanning | Planned | Out of scope (off-runner verdict service) | CI workflow only |
| Static Application Security Testing (SAST) | Design — [`.github/workflows/sast-scan-codeql.yml`](.github/workflows/sast-scan-codeql.yml) (CodeQL candidate; **selection pending ProdSec**) | Out of scope (>10s DX budget) | CI workflow only. Customization-tier lever; fleet baseline is GitHub Default setup via org Security Configurations. Candidates: CodeQL/SonarQube/Coverity. |
| GuardWords scanning | Planned | Planned | — |

## Cross-cutting work

| Item | Status | Notes |
|---|---|---|
| SHA-pinning policy and tooling | Planned | Enforce 40-char SHA pins on all `uses:` references in published workflows |
| Charon ref allowlist for `pull-request/*` | Blocked (platform) | Charon allowlists per ref and no tenant lists the mirror refs, so no Charon-backed scan can gate a pull request until they are added |
| SARIF publication for the vulnerability scan | Planned | Bring Pulse OSS findings into the Security tab, as the secret scan already does |
| Scanner image integrity for the Pulse scans | Planned | Both resolve `<image>:<tag>` from Actions variables, which resolve against the *caller*, and a tag is mutable. `vuln-scan-pulse-oss.yml` constrains the reference to the `nvcr.io` host; `secret-scan-pulse.yml` runs whatever its variables name. Digest pinning would fix both but needs a digest-roll process, since the variable has to change on every scanner release |
| Audit-log schema (v1) | Planned | Common shape for the structured run record emitted by every scan workflow |
| Pilot consumer onboarding guide | Planned | Will land alongside the first published workflow |

Roadmap ownership is handled by NVIDIA maintainers. External contribution
requests are not accepted for this repository at this time; see
[`CONTRIBUTING.md`](CONTRIBUTING.md).
