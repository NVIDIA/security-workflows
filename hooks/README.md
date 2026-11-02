# Pre-commit Hooks

Local-advisory surface. Hooks are declared in [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) and consumed by a repository's `.pre-commit-config.yaml` through the [pre-commit](https://pre-commit.com/) framework. They give developers fast feedback before a commit leaves their machine; enforcement is the CI surface in [`.github/workflows/`](../.github/workflows/README.md).
Arguments and defaults are documented inline in [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml); per-scan release status is in [`ROADMAP.md`](../ROADMAP.md).

## Catalogue

| Hook id | Scan | Needs on the developer's machine | Stages |
|---|---|---|---|
| [`secret-scan-trufflehog`](#secret-scan--secret-scan-trufflehog) | Secret | Nothing; pre-commit installs a pinned TruffleHog release | `pre-commit`, `pre-push` |
| [`guardwords-scan-code-scanning`](#guardwords--guardwords-scan-code-scanning) | GuardWords | NVIDIA employees: ProdSec's code-scanning client and the NVIDIA network. Everyone else: nothing; the hook skips | `pre-commit` |

## Using a hook

These rules apply to **every** hook in this directory. Hook-specific details are under [Hooks](#hooks).

**1. Pin by commit SHA.** Set `rev:` to a 40-character commit SHA with the release tag as a `# frozen:` comment, the form `pre-commit autoupdate --freeze` writes, per the [pin policy](../README.md#pin-policy-per-surface).
Branch references (`main`) are not acceptable.

**2. Run `pre-commit install` in every clone.** Until then no hook runs, and commits succeed unscanned.

**3. Pair every hook with CI.** A hook is advisory: `git commit --no-verify` bypasses it, and a contributor may never install it. Require the matching CI workflow, where one exists, in branch protection.

### Configuration skeleton

```yaml
# In a consumer's `.pre-commit-config.yaml`:
repos:
  - repo: https://github.com/NVIDIA/security-workflows
    rev: <commit SHA>  # frozen: <release tag>
    hooks:
      - id: secret-scan-trufflehog
      # NVIDIA-internal service; see its setup before adding it:
      # - id: guardwords-scan-code-scanning
```

## Hooks

### Secret scan — `secret-scan-trufflehog`

Scans the files being committed or pushed with the open-source [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog) CLI and fails only on **verified** secrets. The hook uses `language: python`: on first installation pre-commit downloads the platform's pinned, SHA-256-verified TruffleHog release into the hook's isolated environment, so consumers need no system scanner or shell installer.

The Lob detector is excluded because it matches ordinary pytest function names and reports them as verified. The CI enforcement lane is [`secret-scan-pulse.yml`](../.github/workflows/README.md#secret-scan--secret-scan-pulseyml).

### GuardWords — `guardwords-scan-code-scanning`

Sends the staged diff to NVIDIA's internal code-scanning service, which runs the GuardWords and secret scanners, and blocks the commit on blocking findings. It is for NVIDIA employees only: where the client or service is unavailable it skips with a notice, so the same configuration works for external contributors. There is no GuardWords CI workflow yet.

Setup, troubleshooting and help are in [`guardwords/README.md`](guardwords/README.md), where the hook's notices link.

## Adding a hook

1. Declare it in [`.pre-commit-hooks.yaml`](../.pre-commit-hooks.yaml) and put its package under `hooks/<name>/`.
2. Add a row to the [Catalogue](#catalogue).
3. Add a section under [Hooks](#hooks) with **only** what is specific to that hook. Do not restate the rules in [Using a hook](#using-a-hook).
4. Give the hook its own `hooks/<name>/README.md` only if users must follow setup or troubleshooting steps, or the hook prints a link to its documentation. Link there from the hook's section.
5. Add a regression step to [`ci.yml`](../.github/workflows/ci.yml), update [`ROADMAP.md`](../ROADMAP.md), and add a bullet under `[Unreleased]` in [`CHANGELOG.md`](../CHANGELOG.md).
6. Update the top-level [`README.md`](../README.md) only if the canonical usage pattern changes.
