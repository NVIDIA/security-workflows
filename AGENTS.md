# Agent Instructions

Guidelines for agents (and humans) working in the NVIDIA Security Workflows repository.

---

## Overview

This repository publishes the security-compliance machinery that downstream NVIDIA repositories consume across six scan categories — Secret, License, Vulnerability, Malware, SAST, GuardWords. It exposes **two surfaces**:

- **Reusable GitHub Actions workflows** under `.github/workflows/` — job-level server-side enforcement via [`workflow_call`](https://docs.github.com/en/actions/using-workflows/reusing-workflows). Each workflow declares its own `permissions:` block and runs in an isolated job. This is the CI enforcement surface for security gates per guardrail #4 (least-privilege).
- **Pre-commit hooks** declared in [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) — local-advisory checks consumed by downstream `.pre-commit-config.yaml` files. Hooks use `language: script` and delegate to thin wrapper scripts under [`hooks/`](hooks/) that encode NVIDIA-approved args and resolve the scanner binary from `$PATH`. Pre-commit runs on developer machines only; consumers need the underlying scanner binary installed locally (per-tool install steps live in each wrapper's header).

Consumer repositories reference the CI workflow by 40-character commit SHA and pre-commit hooks by release tag — see [`README.md` → Pin policy per surface](README.md#pin-policy-per-surface). Changes here have **org-wide reach**.

The repository is currently in early scaffold (`v0.1.0` pre-release). The first scan — Secret scanning — ships two lanes: the CI enforcement workflow [`.github/workflows/secret-scan-pulse.yml`](.github/workflows/secret-scan-pulse.yml) (NVIDIA-licensed Pulse Secret Scanner, run on `nv-gha-runners`), and the local-advisory pre-commit hook [`.pre-commit-hooks.yaml`](.pre-commit-hooks.yaml) → [`hooks/trufflehog.sh`](hooks/trufflehog.sh) (open-source `trufflesecurity/trufflehog`). Pulse is container-only, so it is CI-only; the pre-commit lane deliberately uses the OSS CLI to stay within the <10s DX budget on developer machines.

---

## Read First

Before any non-trivial change, read:

- [`README.md`](README.md) — repository scope, the `workflow_call` contract, versioning policy
- [`GOVERNANCE.md`](GOVERNANCE.md) — what changes require ProdSec sign-off vs routine maintainer review
- [`ROADMAP.md`](ROADMAP.md) — current status of each scan category
- [`CHANGELOG.md`](CHANGELOG.md) — record your change under `[Unreleased]`
- [`SECURITY.md`](SECURITY.md) — vulnerability reporting (never open public issues)
- Any `AGENTS.md` in subdirectories — nearest wins.

---

## Workflow Development Guardrails

Everything published from this repository — `workflow_call` workflows and `.pre-commit-hooks.yaml` hooks — has org-wide reach through pinned references in downstream repositories (SHA for the CI workflow, release tag for pre-commit). These constraints keep that blast radius contained.

1. **`workflow_call` interfaces and `.pre-commit-hooks.yaml` hook ids are public contracts.** Renaming or removing a workflow input, renaming or removing a hook id, changing hook arguments, or changing a default that affects security posture is a **major** version bump per [`README.md`](README.md#versioning).
2. **Default to fail-closed.** A scan finding blocks the consumer's merge (workflows) or commit (pre-commit hooks). Fail-open behavior must be an explicit, opt-in input — never the default.
3. **Pin every external reference per surface** — full table in [`README.md`](README.md#pin-policy-per-surface):
   - `uses:` in a workflow → **40-character commit SHA**
   - `rev:` in a consumer's `.pre-commit-config.yaml` → **release tag** (e.g. `v0.1.0`)

   Branch references (`@main`, `@latest`) are never acceptable.
4. **Least-privilege `permissions:`.** Default the workflow root to read-only; escalate per-job only where required (e.g. `security-events: write` for SARIF upload).
5. **No secrets in this repository.** Workflows may *consume* caller-supplied secrets via `secrets:` inputs, but no tokens, certificates, or `.env` files are ever committed here. If a change appears to require a committed secret, stop and ask.
6. **Audit-log output is part of the contract.** Each workflow is expected to emit a structured run record; changing its shape is at least a minor version bump. The shared schema is tracked in [`ROADMAP.md`](ROADMAP.md).
7. **Pre-commit hooks must respect the <10s DX budget.** Scans that cannot fit (malware verdict service, full SCA, full SAST) ship as workflows only — they are explicitly out of scope for the pre-commit surface.

Changes that fall outside these guardrails require ProdSec acknowledgment per [`GOVERNANCE.md`](GOVERNANCE.md).

---

## Validating Changes

This repository contains no application code; validation is YAML- and Actions-focused.

```bash
# Syntactic YAML check across all tracked YAML files
python3 -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" \
  $(git ls-files '*.yml' '*.yaml')

# GitHub Actions semantics — strongly recommended for any .github/workflows/ change.
# https://github.com/rhysd/actionlint
actionlint
```

Run `pre-commit run --all-files` before committing.

---

## Out of Scope

- Application source code or libraries — this is a workflow-only repository.
- Per-repository configuration for downstream consumers — lives in each consumer repo, not here.

---

## General Guidelines

- Prefer focused pull requests — one workflow change per PR.
- Update [`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` for every change that affects consumers.
- When in doubt about whether a change is a patch, minor, or major version bump, raise it in the PR for maintainer review.
