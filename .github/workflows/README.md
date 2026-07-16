# Reusable Workflows

Job-level surface (`workflow_call`). Reusable workflows declare their own `permissions:` and run in an isolated job; this is the surface for CI security gates.

## Catalogue

| Workflow | Scan | Scanner |
|---|---|---|
| [`secret-scan-pulse.yml`](secret-scan-pulse.yml) | Secret | Pulse Secret Scanner — TruffleHog Enterprise, NVIDIA-licensed, from the `nvcr.io` image (pinned inside the workflow) |

The secret scan also ships a local-advisory **pre-commit hook** (`secret-scan-trufflehog`, built on open-source
[`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog)) declared in
[`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml): pre-commit is developer-machine advisory, this workflow
is CI enforcement. Inputs, defaults, and required permissions are documented inline in each workflow's
`workflow_call` block. Scan-category status is in [`ROADMAP.md`](../../ROADMAP.md).

## Consumer pattern

```yaml
# In a consumer's `.github/workflows/<your-name>.yml`:
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
    #   runs-on: linux-amd64-cpu4              # nv-gha-runners label
    #   extra-args: "--results=verified,unknown"   # workflow default
    #   fail-on-findings: false                # warn-only during initial rollout
```

Pin `<COMMIT-SHA>` to a 40-character commit SHA per the [pin policy](../../README.md#pin-policy-per-surface).
Branch references (`@main`, `@latest`) are not acceptable.

## Adding a workflow

1. Land the file as `<scan>-<tool>.yml` in this directory.
2. Add a row to the Catalogue table above.
3. Update [`ROADMAP.md`](../../ROADMAP.md) and add a bullet under `[Unreleased]` in [`CHANGELOG.md`](../../CHANGELOG.md).
4. Update the top-level [`README.md`](../../README.md) consumer example only if the new workflow changes the canonical usage pattern.
