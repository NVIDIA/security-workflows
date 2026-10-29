# Support

## Support level

- **Status:** Pre-release / pilot
- **Audience:** NVIDIA-internal repositories onboarding to the GitHub-First initiative

## How to get help

| Need | Channel |
|---|---|
| Bug or unexpected behavior in a workflow | GitHub issue on this repository |
| Onboarding question (which workflow, which inputs, which runner) | GitHub issue on this repository |
| GuardWords hook setup, skip notices or findings | NVIDIA employees: the internal [`#github-first-security-scanning`](http://nv/ghf-scan-help) Slack channel — see [GuardWords help](hooks/guardwords/README.md#help). Don't post flagged terms, internal host names or client output in a public issue. |
| Security vulnerability | See [`SECURITY.md`](SECURITY.md) — **do not** file a public issue |
| NVIDIA-internal escalation | See [`MAINTAINERS.md`](MAINTAINERS.md) |

## Response expectations

Response times during the pre-release / pilot phase are best-effort. Formal SLAs will be published when the project moves out of pilot.

## What is not supported

- Forks of these workflows that have diverged from `main`.
- Workflows referenced by mutable Git tag rather than commit SHA — see the pinning policy in [`README.md`](README.md#versioning).
