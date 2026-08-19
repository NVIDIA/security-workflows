# Reusable Workflows

Job-level surface (`workflow_call`). Each workflow declares its own `permissions:` and runs in an isolated job — this is the surface for CI security gates.
Inputs and defaults are documented inline in each workflow's `workflow_call` block; per-scan release status is in [`ROADMAP.md`](../../ROADMAP.md).

## Catalogue

| Workflow | Scan | Scanner |
|---|---|---|
| [`security-suite.yml`](security-suite.yml) | Opt-in set of the scans below | Fans out in parallel to the scans the caller enables |
| [`secret-scan-pulse.yml`](secret-scan-pulse.yml) | Secret | Pulse Secret Scanner — TruffleHog Enterprise, NVIDIA-licensed, Self-hosted runners only |
| [`sast-scan-codeql.yml`](sast-scan-codeql.yml) | SAST | CodeQL (`github/codeql-action`, pinned inside the workflow) |

## Using a workflow

These rules apply to **every** workflow in this directory. Scan-specific details are under [Scans](#scans).

**1. Pin by commit SHA.** Reference each workflow by a 40-character commit SHA, per the [pin policy](../../README.md#pin-policy-per-surface).
Branch or tag references (`@main`, `@latest`) are not acceptable.

**2. Grant every permission the workflow declares.** A caller must grant *at least* what the reusable workflow declares, or the run fails at load time with `requesting '<scope>', but is only allowed '<scope>: none'`.
Copy the `permissions:` block from the scan's section — do not trim it to what looks necessary.

**3. Set `runs-on` to a real label.** Scans that reach NVIDIA-internal services (OIDC → Vault, `nvcr.io`) run **only** on self-hosted runners and need an `nv-gha-runners` label (e.g. `linux-amd64-cpu4`) — see the [runner label catalog](https://nv/gha-runner-labels) (NVIDIA-internal).
Scans with no internal dependency (CodeQL SAST) default to a GitHub-hosted runner and need no label. Each scan's section below states which applies.

**4. Onboard the repository first.** Runner access and repository-level expectations (Actions enabled, branch protection, `copy-pr-bot` for fork PRs) are in [Onboarding a repository](../../README.md#onboarding-a-repository).

### Caller skeleton

```yaml
# In a consumer's `.github/workflows/<your-name>.yml`:
on: [pull_request]

permissions:
  # copy from the scan's section below

jobs:
  scan:
    uses: NVIDIA/security-workflows/.github/workflows/<workflow>.yml@<COMMIT-SHA>
    with:
      # scan-specific inputs — see the workflow's `workflow_call` block
```

## Scans

### Security suite — [`security-suite.yml`](security-suite.yml)

One pinned reference that runs the scans you enable, each in its own job so they
run in parallel. Use it instead of one caller block per scan.

**Every scan is opt-in.** A suite call with no `enable-*` input runs nothing and
emits a warning — it does not fail, but it also does not mean anything, so set at
least one. Scans added to the suite in future releases will also default to off;
turning a default on is treated as a breaking change (see [Versioning](../../README.md#versioning)).

| Input | Enables | Notes |
|---|---|---|
| `enable-secret-scan` | [`secret-scan-pulse.yml`](secret-scan-pulse.yml) | Self-hosted `nv-gha-runners` and the Vault / Pulse variables required. |
| `enable-sast-scan` | [`sast-scan-codeql.yml`](sast-scan-codeql.yml) | Requires `sast-languages` — accepted values are listed under [Accepted `languages` values](#accepted-languages-values) — and requires CodeQL Default setup to be **off**. Most repositories should stay on Default setup and leave this off. |

**Grant the union of every scan's permissions, not just the ones you enable.** GitHub
validates a caller against what the called workflow *declares*, before any `if:` is
evaluated, so a suite call that grants less fails at startup with
`The nested job '<scan>' is requesting '<scope>'` even when that scan is disabled:

```yaml
permissions:
  actions: read
  contents: read
  id-token: write
  security-events: write

jobs:
  security-scans:
    uses: NVIDIA/security-workflows/.github/workflows/security-suite.yml@<COMMIT-SHA>
    with:
      enable-secret-scan: true
      # Advanced-setup repositories only — leave off if you use CodeQL Default setup:
      # enable-sast-scan: true
      # sast-languages: '["actions"]'
      #
      # Optional category-prefixed overrides:
      # secret-failure-policy: strict
      # secret-runs-on: linux-amd64-cpu4
      # sast-runs-on: ubuntu-latest
      # sast-build-mode: autobuild
      # sast-queries: +security-and-quality
      # sast-config-file: .github/codeql/codeql.yml
      #
      # Runner for the preflight job, which is scheduled only to report an empty or
      # invalid selection. Set this if you cannot use GitHub-hosted runners:
      # suite-runs-on: linux-amd64-cpu4
```

Enabling SAST without `sast-languages` fails the suite with an explicit error rather
than starting a scan that cannot work.

### Secret scan — [`secret-scan-pulse.yml`](secret-scan-pulse.yml)

CI enforcement lane. Runs the Pulse Secret Scanner container and publishes redacted SARIF to the repository Security tab.
The companion local-advisory lane is the `secret-scan-trufflehog`.
**pre-commit hook** (open-source [`trufflesecurity/trufflehog`](https://github.com/trufflesecurity/trufflehog)) declared in [`.pre-commit-hooks.yaml`](../../.pre-commit-hooks.yaml).

Scan-specific prerequisites:

- **Self-hosted runners only.** The job authenticates via OIDC → Vault and pulls the scanner image from `nvcr.io`; neither is reachable from GitHub-hosted runners.
- **Vault / Pulse Actions variables** must be visible to the repository (`NV_VAULT_URL`, `NVCR_VAULT_*`, `SECRET_SCAN_PULSE_IMAGE`, `SECRET_SCAN_PULSE_IMAGE_TAG`).

Key inputs: `runs-on` (default `linux-amd64-cpu4`), `failure_policy` (`unverified` default — fail on verified secrets, warn on unverified; `strict` — fail on any finding; `all` — warn only).

```yaml
permissions:
  contents: read
  id-token: write          # OIDC → Vault → nvcr.io image pull
  security-events: write   # publish redacted SARIF to code scanning
  actions: read

jobs:
  secret-scan:
    uses: NVIDIA/security-workflows/.github/workflows/secret-scan-pulse.yml@<COMMIT-SHA>
    # Optional overrides — see the workflow file for the full interface:
    # with:
    #   runs-on: linux-amd64-cpu4   # nv-gha-runners label
    #   failure_policy: strict      # fail on any finding (default: unverified — fail verified, warn unverified)
```

### SAST — [`sast-scan-codeql.yml`](sast-scan-codeql.yml)

**Choose the right delivery model first.** CodeQL is native to GitHub, so the baseline for most repositories is **Default setup applied via an org/enterprise Security Configuration** — zero YAML in the repo, GitHub-managed CodeQL upgrades, auto-applied to current and future repos.

| Model | Use for | How |
|---|---|---|
| **Default setup** (Security Configuration) | The vast majority of repos | Org/enterprise owner enables it centrally; no file in the repo |
| **This reusable workflow** | Repos needing custom query packs, path filters, a shared build step, or a centrally-pinned action | Add a caller (below) |
| **Standalone advanced** | Rare repos with a bespoke, non-generalizable build | Repo-local `codeql.yml` |

Use `sast-scan-codeql.yml` only when you actually need the customization. If you don't, use Default setup.

Scan-specific prerequisites:

- **Licensing.** Public repos get code scanning free. Private/internal repos require GitHub Advanced Security (Code Security).
- **Default setup must be off.** Default setup and an advanced/reusable CodeQL workflow are mutually exclusive; if Default setup is on, this workflow's upload fails.
- **Runner toolchain.** `build-mode: none` needs no toolchain. `build-mode: autobuild` needs the language's build tools.
- **Rollout alerts-first.** Enable without a merge gate, triage the backlog, then enforce via branch protection — turning enforcement on fleet-wide on day one lights every repo red.

Key inputs: `languages` (required, JSON array — one matrix leg per entry), `runs-on` (default `ubuntu-latest`), `build-mode` (default `none`), `resolve-runs-on` (default `ubuntu-latest`), `queries` (default `security-extended`), `packs`, `config-file`.

#### Accepted `languages` values

`languages` takes CodeQL's supported languages. Anything else fails validation before any scan starts.

| Value | Covers | Buildless (`none`) | Resolved mode by default |
|---|---|---|---|
| `actions` | GitHub Actions workflows | yes | `none` |
| `c-cpp` | C, C++ | yes | `none` |
| `csharp` | C# | yes | `none` |
| `go` | Go | **no** | `autobuild` |
| `java-kotlin` | Java, Kotlin | Java only — **Kotlin needs a build** | `none` |
| `javascript-typescript` | JavaScript, TypeScript | yes | `none` |
| `python` | Python | yes | `none` |
| `ruby` | Ruby | yes | `none` |
| `rust` | Rust | yes — **only** `none` | `none` |
| `swift` | Swift | **no** (and macOS runners only) | `autobuild` |

**You do not have to work this table out yourself.** The workflow resolves a build mode per language, mirroring what GitHub Default setup picks,
so languages with incompatible requirements can be combined in one call: `'["go","rust"]'` is valid even though Go rejects `none` and Rust accepts
nothing else. Each substitution is reported as a notice in the job log, and the resolved matrix is written to the job summary.

`build-mode` sets your *preference*, applied wherever the language supports it. For exact control, use the object form of an entry:

```yaml
sast-languages: '[{"language":"c-cpp","build-mode":"autobuild"},{"language":"swift","runs-on":"macos-14"},"rust"]'
```

An explicit per-language `build-mode` that CodeQL does not support is an error, not a silent substitution — the run fails in the resolver with the offending
pair named, before any analysis starts. `manual` is rejected everywhere: a reusable workflow cannot carry repo-specific build steps.

Two coverage gaps to plan around:

- **No shell analyzer.** CodeQL cannot analyze Bash or other shell. Cover shell with a linter such as [`shellcheck`](https://www.shellcheck.net/), typically at pre-commit.
- **No CUDA analyzer.** The `c-cpp` extractor does not understand CUDA, so `.cu` / `.cuh` device code is not analyzed. A CUDA-heavy repository pays full C/C++ extraction cost for coverage of its host-side translation units only — measure that trade before enabling `c-cpp`.

Every entry is its own matrix leg, so scan cost scales with the list. Start with the languages carrying the most risk, then widen once you have a runtime and alert-volume baseline.

```yaml
permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  codeql:
    uses: NVIDIA/security-workflows/.github/workflows/sast-scan-codeql.yml@<COMMIT-SHA>
    with:
      languages: '["actions"]'
```

## Adding a workflow

1. Land the file as `<scan>-<tool>.yml` in this directory.
2. Add a row to the [Catalogue](#catalogue).
3. Add a section under [Scans](#scans) with **only** what is specific to that scan — prerequisites, key inputs, permissions block, and a minimal caller snippet. Do not restate the rules in [Using a workflow](#using-a-workflow).
4. Update [`ROADMAP.md`](../../ROADMAP.md) and add a bullet under `[Unreleased]` in [`CHANGELOG.md`](../../CHANGELOG.md).
5. Update the top-level [`README.md`](../../README.md) only if the canonical usage pattern changes.
