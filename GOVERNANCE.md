# Governance

## Project model

NVIDIA Security Workflows is a maintainer-driven project owned by the NVIDIA GitHub-First initiative. Day-to-day decisions about workflow design, scan-tool selection, and policy defaults are made by the maintainers in coordination with NVIDIA Product Security (ProdSec).

## Decision making

- Routine changes (bug fixes, additive inputs, documentation) are made via standard GitHub pull request review by a maintainer.
- Changes that alter a workflow's `workflow_call` interface, change a default policy, or change runner contracts require sign-off from a maintainer **and** an explicit ProdSec acknowledgment recorded in the PR.
- Adding a new scan category, deprecating an existing one, or changing the SHA-pinning contract requires consensus among the maintainers.

## Release tagging

Release tags are the consumption surface for downstream repositories and are immutable.

- **Cut a tag** for any change consumers should adopt: workflow `workflow_call` interface changes, pre-commit hook id / argument / default-policy changes, new hooks or workflows, and behaviour-changing bug or security fixes.
- **Don't cut a tag** for changes that don't affect consumers — repository scaffolding, documentation, governance updates, refactors.
- **Tags are immutable.** Never force-push a tag. If a release was bad, cut a new one.
- **SemVer.** Major / minor / patch semantics are defined in [`README.md`](README.md#versioning).
- **Sign-off.** A release tag requires maintainer sign-off; tags that touch a contract additionally require ProdSec acknowledgment per the decision-making rules above.

## Roles

| Role | Responsibility |
|---|---|
| Maintainer | Reviews and merges pull requests, owns release process, on-call for consumer escalations |
| NVIDIA contributor | NVIDIA personnel opening maintainer-reviewed pull requests under the internal development process |
| ProdSec reviewer | Sign-off authority for security-policy-relevant changes |

The current list of maintainers is in [`MAINTAINERS.md`](MAINTAINERS.md).

## Maintainer workflow

External contributions are not accepted (see [`CONTRIBUTING.md`](CONTRIBUTING.md)). The pull request process below applies to NVIDIA maintainers landing changes against this repository.

1. Branch from `main`.
2. Make focused changes — one workflow change per PR.
3. Verify the YAML is well-formed and (where applicable) passes [`actionlint`](https://github.com/rhysd/actionlint).
4. Update [`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` with a one-line entry.
5. Open a PR against `main`. Review and merge follow the rules in [Decision making](#decision-making) above; escalation contacts are in [`MAINTAINERS.md`](MAINTAINERS.md).

### NVIDIA IP review

NVIDIA maintainers are responsible for following NVIDIA's internal IP review process for ongoing project modifications before release.

## Changes to this document

Changes to governance go through the same pull request process and require maintainer consensus.
