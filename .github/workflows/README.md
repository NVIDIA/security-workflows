# Reusable Workflows

Job-level surface (`workflow_call`). Each workflow declares its own `permissions:` and runs in an isolated job — this is the surface for CI security gates.
Inputs and defaults are documented inline in each workflow's `workflow_call` block; per-scan release status is in [`ROADMAP.md`](../../ROADMAP.md).

## Catalogue

| Workflow | Scan | Scanner |
|---|---|---|
| [`security-suite.yml`](security-suite.yml) | Opt-in set of the scans below | Fans out in parallel to the scans the caller enables |
| [`secret-scan-pulse.yml`](secret-scan-pulse.yml) | Secret | Pulse Secret Scanner — TruffleHog Enterprise, NVIDIA-licensed, Self-hosted runners only |
| [`vuln-scan-pulse-oss.yml`](vuln-scan-pulse-oss.yml) | Vulnerability (SCA) | Pulse OSS CLI reporting to nSpect over a Charon tunnel, NVIDIA-internal, Self-hosted runners only |
| [`malware-scan-pulse.yml`](malware-scan-pulse.yml) | Malware | Pulse Malware Service (ReversingLabs), which fetches the commit itself over a Charon tunnel, NVIDIA-internal, Self-hosted runners only |
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
| `enable-vuln-scan` | [`vuln-scan-pulse-oss.yml`](vuln-scan-pulse-oss.yml) | Needs self-hosted `nv-gha-runners`, the Vault / Pulse variables, and a Charon tenant granting the Pulse backends with the calling ref allowlisted. `nspect-id` is optional: without it the scan runs unregistered. |
| `enable-malware-scan` | [`malware-scan-pulse.yml`](malware-scan-pulse.yml) | Requires `nspect-id` (the repository's nSpect ID), self-hosted `nv-gha-runners`, the Vault, scanner-image, and Charon variables, and the calling ref and the scan's routes on the repository's Charon tenant. |
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
      # Requires an nSpect registration — see the vulnerability and malware scan sections.
      # nspect-id carries no scan prefix: it identifies the repository, not one scan.
      # enable-vuln-scan: true
      # enable-malware-scan: true
      # nspect-id: ${{ vars.NSPECT_ID }}
      # Advanced-setup repositories only — leave off if you use CodeQL Default setup:
      # enable-sast-scan: true
      # sast-languages: '["actions"]'
      #
      # Optional category-prefixed overrides:
      # secret-failure-policy: strict
      # secret-runs-on: linux-amd64-cpu4
      # vuln-runs-on: linux-amd64-cpu4
      # vuln-scan-path: .
      # vuln-scan-mode: auto
      # vuln-build: true                          # Maven / Go
      # vuln-failure-policy: fail-on-vulnerability
      # vuln-registered-branch: main
      # vuln-sbom-name: <SBOM_NAME>               # several SBOM entries on that branch
      # vuln-inventory-writeback: true            # persistent scans only; needs vuln-sbom-name
      # vuln-upload-report: true
      # vuln-timeout-seconds: 1800
      # malware-runs-on: linux-amd64-cpu4
      # malware-failure-policy: malicious-only
      # malware-upload-report: true
      # malware-timeout-minutes: 90
      # sast-runs-on: ubuntu-latest
      # sast-build-mode: autobuild
      # sast-queries: +security-and-quality
      # sast-config-file: .github/codeql/codeql.yml
      #
      # Runner for the preflight job, which is scheduled only to report an empty or
      # invalid selection. Set this if you cannot use GitHub-hosted runners:
      # suite-runs-on: linux-amd64-cpu4
```

Enabling a scan without the input it needs fails the suite with an explicit error rather
than starting a scan that cannot work — `enable-sast-scan` without `sast-languages`, or
`enable-malware-scan` without `nspect-id`. Every missing companion input is reported in
one run.

The suite does not expose the vulnerability scan's `ci_test_setup` input; it exists only
for this repository's own self-tests.

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

### Vulnerability scan (SCA) — [`vuln-scan-pulse-oss.yml`](vuln-scan-pulse-oss.yml)

For dependency preparation and current setup limitations, see
[Build environments for vulnerability scans](../../docs/vuln-scan/README.md).

Runs NVIDIA's **Pulse OSS scanner** against the dependency graph under `scan_path` and reports findings to the **nSpect** vulnerability backend, so they become findings of record rather than only CI output.
The scanner is pulled from `nvcr.io` and reaches nSpect through a Charon application tunnel on loopback. **GitHub OIDC is the only identity presented** — no service account, registry credential, or backend token enters the job. The scanner image is **pinned by digest inside the workflow** (the approved `charon-stable` release), so a caller cannot substitute another image, and every run records the digest it executed in the job summary and the `scanner_image_digest` output. A scanner upgrade is a digest change in this repository. The container runs with no capabilities, cannot acquire any, and never sees your checkout: it is given a disposable copy, which is discarded when the job ends. The copy is writable, because Detect's language detectors generate metadata next to each project they find and a read-only tree turns those into scan failures.

Scan-specific prerequisites:

- **Self-hosted runners only.** OIDC → Vault, `nvcr.io`, and the Charon tunnel are all unreachable from GitHub-hosted runners.
- **nSpect registration, if you want findings of record.** Register the repository, set its ID as a repository variable `NSPECT_ID` (format `NSPECT-xxxx-xxxx`), and pass it as `nspect_id`; a malformed ID is refused. Leave it empty and the scan runs unregistered (`--no-nspect`): findings appear in the job but are not recorded against a registration, and the scan is rapid-only, because a persistent scan has no registration to write back to. The variable carries no scan prefix because an nSpect ID belongs to the repository, not to one scan — any future scan reporting to nSpect reads the same one.
- **Platform variables**, provisioned for the organization by the GitHub-First platform team: `NV_VAULT_URL`, `NVCR_VAULT_ROLE`, `NVCR_VAULT_JWT_PATH`, `NVCR_VAULT_NAMESPACE`, `NVCR_VAULT_SECRET_PATH`. A missing one is named by the preflight rather than surfacing as the Vault action's `Input required and not supplied: url`. The scanner image and the Charon tunnel settings belong to the workflow and are not caller-configurable.
- **Optional `VULN_SCAN_TUNNEL_CLIENT_VERSION`** pins the Teleport tunnel client to an approved bare semver. Leave it unset and the version is resolved from the Charon proxy; pinning is the supply-chain-safer choice. It is a variable rather than a secret because a client version is configuration — masking it would only remove it from the audit trail.
- **Trigger model**, identical to the secret scan: the workflow **rejects `pull_request` and `pull_request_target`**, so call it from `push`, `schedule`, or `workflow_dispatch`. Pull-request coverage comes from `copy-pr-bot`'s `pull-request/<n>` mirror branches, added to your `push` filter as the [pilot consumers already do](../../README.md#onboarding-a-repository).
- **Pull-request mirrors are RAPID-only.** On a `refs/heads/pull-request/*` ref, `scan_mode: auto` resolves to `rapid`, and `persistent` or `inventory_writeback: true` is refused; `registered_branch` can never name a mirror. A mirror carries pull-request content, so it must not create backend state, upload an SBOM, or write inventory. Persistent and write-back scans belong to the registered branch.
- **Charon tenant and ref allowlist.** Charon authorizes per tenant *and per ref*. Your repository needs a tenant granting the Pulse backends — `pulse-nspect`, `pulse-pms`, `pulse-pcsf`, `pulse-exception-tracker`, `pulse-blackduck`, `pulse-nvdataflow` — and every ref you scan from on its allowlist, including the `pull-request/*` mirrors if the scan is to gate pull requests. A missing backend or an unlisted ref surfaces as an opaque `HTTP 403` from inside the scanner, so get the tenant in place before debugging anything else.

Behaviours to know about before you point it at a path:

- **A symbolic link that points outside the checkout blocks the scan.** Anything under `scan_path` linking out of the scanned tree is refused, because it would smuggle unreviewed content into the container mount. A repository holding one cannot scan `.` until the link is removed or `scan_path` is narrowed around it.
- **`build: true` executes the repository's build logic.** Maven and Go resolve their dependency graphs only through a build, so the scanner runs that build inside its container, on a host network, with the job's OIDC request variables present. On a `pull-request/*` mirror that build logic comes from the pull request. `copy-pr-bot` mirrors only approved PRs with signed commits from org members or trustees, so this is reviewed rather than arbitrary content, and the container holds no capabilities and works on a disposable copy rather than your checkout — but an approving maintainer is the control, and under `build: true` that build may write anywhere inside the copy. **Prefer `build: true` on post-merge and scheduled runs**, and treat approving a PR that changes build files as approving code execution.
- **`registered_branch` is the branch reported to nSpect, whichever ref is scanned.** A `rapid` scan of a `pull-request/*` mirror still presents `registered_branch` to the backend, because the registration lookup is keyed on it and sending the mirror's name would not resolve. Rapid scans are stateless and record nothing, so this affects request metadata rather than findings of record — but do not read an nSpect branch as proof of which tree was scanned. A `persistent` scan is refused unless the checked-out ref really is `registered_branch`.
- **Local allowlisting in no-nSpect mode is TBD.** Local allowlisting is being explored and is not yet validated or supported by this reusable workflow. No-nSpect scans do not retrieve approved exceptions. The CLI may still apply rules found in repository allowlist files, which can affect filtered results and whether the job passes.

`failure_policy` decides only whether *findings* fail the job — the scan always produces the full report. `report-only` (default) warns; `fail-on-vulnerability` blocks on any finding. **Scanner, transport, and report-validation failures block under both**: a missing, malformed, or credential-bearing report is never a pass. The CLI always runs with `--no-fail` and the policy is applied to the validated report, so a non-zero scanner exit is always a failed scan — no finding message in the log can turn it into a pass. **Start on `report-only`** — turning on `fail-on-vulnerability` in an established repository blocks everything on day one over pre-existing findings. Triage first, then flip.

`scan_mode: auto` runs a `persistent` scan (which creates or updates project state in the backend) only on `registered_branch`, and a stateless `rapid` scan everywhere else. Pass `rapid` explicitly where backend state is not wanted at all. Set `build: true` for **Maven** and **Go**, whose dependency graphs resolve only through a build.

Results are the run's job summary plus, with `upload_report: true`, a 3-day artifact. **SARIF publication is a follow-up**, so unlike the secret scan these findings do not appear under code scanning yet.

Key inputs: `nspect_id` (optional — empty runs unregistered), `runs-on` (default `linux-amd64-cpu4`), `registered_branch` (default `main`), `sbom_name` (optional — selects the registration when `registered_branch` has more than one SBOM entry; needs `nspect_id`, required with `inventory_writeback`), `scan_path` (default `.`), `scan_mode` (default `auto`), `build` (default `false`), `failure_policy` (default `report-only`), `inventory_writeback` (default `false`, persistent scans only), `upload_report` (default `false`), `timeout_seconds` (default `1800`, range 60–3600).
Outputs: `resolved_mode`, `finding_count`, `scanner_exit_code`, `scanner_image_digest`.

```yaml
on:
  push:
    branches: [main]
  schedule:
    - cron: '17 4 * * 1'

permissions:
  contents: read
  id-token: write          # OIDC → Vault for the image pull, and → Charon for the scan

jobs:
  vulnerability-scan:
    uses: NVIDIA/security-workflows/.github/workflows/vuln-scan-pulse-oss.yml@<COMMIT-SHA>
    with:
      nspect_id: ${{ vars.NSPECT_ID }}
    # Optional overrides — see the workflow file for the full interface:
    #   runs-on: linux-amd64-cpu4       # nv-gha-runners label
    #   scan_path: services/api
    #   build: true                     # Maven / Go
    #   failure_policy: fail-on-vulnerability
    #   upload_report: true
```

### Malware scan — [`malware-scan-pulse.yml`](malware-scan-pulse.yml)

Asks NVIDIA's **Pulse Malware Service** to scan the calling run's commit with ReversingLabs. **Nothing is checked out**: the job sends only identifiers — the repository, commit SHA, nSpect ID, and tenant — through the production Charon application tunnel on loopback, and the service fetches that commit from GitHub itself. **GitHub OIDC is the only identity the scan presents**: Charon adds the service credential on its side, so no service account or backend token enters the job. Apart from tokens minted from OIDC, the job's only credential is the `nvcr.io` pull login, which it reads from Vault with its OIDC token. The scanner container runs with no capabilities and cannot acquire any.
The scan target is always `github.repository` at `github.sha`; no input can point the service at another repository, or at a commit already known to be clean.

Scan-specific prerequisites:

- **Self-hosted runners only.** OIDC → Vault, `nvcr.io`, and the Charon tunnel are all unreachable from GitHub-hosted runners.
- **nSpect registration.** Register the repository and set its ID as a repository variable `NSPECT_ID`, then pass it as `nspect_id`. The scanner accepts only the uppercase form, `NSPECT-XXXX-XXXX`, so the workflow refuses anything else before it pulls the image.
- **Platform variables**, provisioned for the organization by the GitHub-First platform team: `NV_VAULT_URL`, `NVCR_VAULT_ROLE`, `NVCR_VAULT_JWT_PATH`, `NVCR_VAULT_NAMESPACE`, `NVCR_VAULT_SECRET_PATH`. A missing one is named by the workflow rather than surfacing later as a Vault failure. The Charon tunnel settings are owned by the workflow, not read from variables: it fixes the production proxy, join token, application, and local port, so a caller cannot send the scan, or the job's OIDC token, through another proxy.
- **Scanner image pinned by digest inside the workflow** (the approved `1.3.0` release), so a caller cannot substitute another image, and every run records the digest it executed in the job summary and the `scanner_image_digest` output. Neither `MALWARE_SCAN_PULSE_IMAGE` nor `MALWARE_SCAN_PULSE_IMAGE_TAG` is read. A scanner upgrade is a digest change in this repository, so a new scanner release reaches callers as a new release of this workflow.
- **Optional `MALWARE_SCAN_TUNNEL_CLIENT_VERSION`** pins the Teleport tunnel client to an approved bare semver. Leave it unset and the version is resolved from the Charon proxy; pinning is the supply-chain-safer choice.
- **Trigger model**, identical to the secret scan: the workflow **rejects `pull_request` and `pull_request_target`**, so call it from `push`, `schedule`, or `workflow_dispatch`. Pull-request coverage comes from `copy-pr-bot`'s `pull-request/<n>` mirror branches, added to your `push` filter as the [pilot consumers already do](../../README.md#onboarding-a-repository).
- **Charon allowlist — refs *and* routes.** Charon authorizes per tenant, per ref, and per route, so the repository's tenant must list the calling ref and every nSpect and Pulse Malware Service route the scan uses. The scan-submission route is not in the set tenants are granted by default and needs platform approval. A ref or route the tenant does not list fails the scan; it never passes it. A tenant that does not list the copy-pr-bot mirror refs (`refs/heads/pull-request/*`) makes this scan a post-merge and scheduled gate rather than a merge gate.
- **The service must be able to read the repository.** It fetches the commit with its own GitHub access; a repository it cannot read fails the scan.

`failure_policy` decides only what a **SUSPICIOUS** verdict does: `strict` (default) blocks it, `malicious-only` reports it as a warning. **A MALICIOUS verdict blocks under both, and so does every scan that ends without a verdict** — a transport failure, timeout, scanner crash, FAILED scan, or a report that disagrees with the scanner's exit code is never a pass. The job log names the cause as a diagnostic category, and a sanitized copy of the scanner's output is printed and kept as a 3-day artifact: tokens, auth headers, cookies, and signed-URL credentials are redacted from it, and it is withheld entirely if anything credential-shaped survives. Prefer `strict`. `malicious-only` is a triage mode for repositories that must work through SUSPICIOUS results before they can gate on them, not a release gate: a release needs a CLEAN verdict, which only `strict` enforces.

A MALICIOUS verdict is a security event, not a flaky check: re-running the job scans the same commit again, so it is not a way to clear one. Escalate it to NVIDIA Product Security.

Every run scans the whole tree at the commit, not a diff; a commit the service has already scanned may be served from its cache.

`timeout_minutes` (default `60`, from 10 to 360) is the job timeout, and the scanner's report polling is derived from it: the sleep between attempts doubles from 2 seconds to a 120-second cap, and polling stops 5 minutes before the timeout, which leaves time for the steps around it. With the default, the scan waits up to about 54 minutes for its report. A scan that outlasts the budget fails as `timeout`, closed like every scan without a verdict, rather than as a cancelled job with no diagnostic. Raise it for repositories the service takes longer to scan.

Results are the job summary — verdict, flagged-item breakdown, allowlist and cache state, and the **Pulse scan ID**, the join key to the service's record of the scan — plus, with `upload_report: true`, the validated report as a 3-day artifact with the nSpect ID redacted. A report carrying anything credential-shaped is withheld from the artifact with a warning; the verdict is unaffected. Findings do not appear under code scanning.
The scanner image and the Charon tunnel are fixed in the workflow, but the runner and the Vault variables are still the *caller's*, so the service's record found by the Pulse scan ID — not the job's own verdict — is the record of account. The job summary and the `scanner_image_digest` output record the image digest each run used.

Key inputs: `nspect_id` (required), `runs-on` (default `linux-amd64-cpu4`), `failure_policy` (default `strict`), `upload_report` (default `false`), `timeout_minutes` (default `60`).
Outputs: `verdict`, `flagged_count`, `scanner_exit_code`, `scan_id`, `scanner_image_digest`.

```yaml
on:
  push:
    branches: [main]
  schedule:
    - cron: '23 4 * * 1'

permissions:
  id-token: write          # OIDC → Vault for the image pull, and → Charon for the scan

jobs:
  malware-scan:
    uses: NVIDIA/security-workflows/.github/workflows/malware-scan-pulse.yml@<COMMIT-SHA>
    with:
      nspect_id: ${{ vars.NSPECT_ID }}
    # Optional overrides — see the workflow file for the full interface:
    #   runs-on: linux-amd64-cpu4       # nv-gha-runners label
    #   failure_policy: malicious-only  # warn on SUSPICIOUS (default: strict — block it)
    #   upload_report: true
    #   timeout_minutes: 90             # job timeout; report polling is derived from it
```

### SAST — [`sast-scan-codeql.yml`](sast-scan-codeql.yml)

**Choose the right delivery model first.** CodeQL is native to GitHub, so the baseline for most repositories is **Default setup applied via an org/enterprise Security Configuration** — zero YAML in the repo, GitHub-managed CodeQL upgrades, auto-applied to current and future repos.

| Model | Use for | How |
|---|---|---|
| **Default setup** (Security Configuration) | The vast majority of repos | Org/enterprise owner enables it centrally; no file in the repo |
| **This reusable workflow** | Repos needing path filters, a non-default query suite, or a centrally-pinned action | Add a caller (below) |
| **Standalone advanced** | Rare repos with a bespoke, non-generalizable build | Repo-local `codeql.yml` |

Use `sast-scan-codeql.yml` only when you actually need the customization. If you don't, use Default setup.

Scan-specific prerequisites:

- **Licensing.** Public repos get code scanning free. Private/internal repos require GitHub Advanced Security (Code Security).
- **Default setup must not cover the same languages.** Default setup and this workflow both publish the `/language:<lang>` SARIF category, so any language covered by both makes the two uploads collide. Default setup covering *other* languages is fine and common — this repository runs exactly that way, with an org Security Configuration analyzing `python` while the self-test analyzes `actions`.
- **Runner toolchain.** `build-mode: none` needs no toolchain. `build-mode: autobuild` needs the language's build tools.
- **This workflow never fails a pull request.** It publishes findings to code scanning and always exits 0 — there is no `failure_policy` equivalent, unlike [`secret-scan-pulse.yml`](secret-scan-pulse.yml). Enabling it buys visibility, not a merge gate. Gating is a separate, repository-side decision: configure it through code-scanning alert rules and branch protection once the backlog is triaged. Plan the rollout that way deliberately — turning enforcement on fleet-wide on day one lights every repo red.
- **`queries` defaults to `security-extended`, which is broader than Default setup's `default` suite.** Expect a larger initial backlog than an equivalent Default-setup repo, and name a triage owner before enabling. Pass `queries: default` to match Default setup's volume.
- **GHCR-hosted query `packs` are not usable.** The workflow does not declare `packages: read` and a called workflow's token cannot exceed what it declares, so granting the scope in the caller has no effect.

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
