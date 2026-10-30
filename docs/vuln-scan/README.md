# Vulnerability scans

Choose a scan for the code you are checking. Use a reviewed workflow commit SHA,
not a moving branch. Access must be approved for the calling repository and ref.

**Review candidate:** prepared-Python RAPID tests passed. Snippet matching was
verified in a reference integration, not this exact workflow. Registered release
and inventory write-back validation remain separate.

## Scan types

| Use | Inputs | State and limits |
| --- | --- | --- |
| Pull requests | `scan_mode: rapid` | Dependency analysis only. PR mirrors are RAPID-only; no persistent project/version or inventory update. |
| Unregistered source | `scan_mode: rapid`, omit `nspect_id` | No nSpect registration or approved-exception lookup. |
| Registered release branch | `scan_mode: persistent`, `nspect_id`, `registered_branch` | Full scan; creates or updates backend project/version state. Pilot-only until this workflow's registered integration is verified. |
| Release with snippets | Full-scan inputs plus `snippet_scan: true` | Registered full releases only; waits for results. Requires `inventory_writeback: false`. |
| Release inventory update | Full-scan inputs plus `sbom_name`, `inventory_writeback: true` | Replaces inventory for the selected registration. Queue acceptance is not completed processing. No job polling is added. |

`auto` chooses persistent only on the registered branch with an ID; otherwise it
chooses RAPID. Direct `pull_request` and `pull_request_target` events are rejected.
Use the approved PR-mirror push flow. Do not use persistent scans for PRs.

Signature-only STATELESS, binary, C/C++-specific scans and standalone SBOM uploads
are not selectable through this workflow. Separate CLI commands are not a promise
of reusable-workflow support. Local allowlisting in no-nSpect mode remains
unsupported pending validation; filtered findings are not approved exceptions.

## Examples

Inside a caller job that uses the pinned reusable workflow:

```yaml
with:
  scan_mode: rapid
  failure_policy: fail-on-vulnerability
  upload_report: true
  detect_properties: '{"detect.detector.search.depth": 4}'
```

For an approved, registered release branch:

```yaml
with:
  scan_mode: persistent
  nspect_id: ${{ vars.NSPECT_ID }}
  registered_branch: release
  sbom_name: library
  snippet_scan: true
  inventory_writeback: false
  timeout_seconds: 3600
```

The checked-out branch must match `registered_branch`. Registration uses the
calling repository's SSH URL and the matching branch and SBOM name. The workflow
does not register repositories. Use the matching SBOM name where a branch has
multiple registrations; inventory write-back always requires one.

## Controls and results

- `scan_path`: repository-relative directory, default `.`.
- `build`: scanner build mode, default `false`. It can execute repository build
  logic; it does not create a Python or GPU environment.
- `python_wheels_artifact` and `python_project`: default empty. Set both for the
  [prepared-Python scan](#python-projects); leave both empty for existing behavior.
- `snippet_scan`: default `false`. Adds snippet matching to registered full release
  scans only; set `inventory_writeback: false`.
- `detect_properties`: default `{}`. A JSON object using the
  [typed allowlist](#detect-property-allowlist), not arbitrary Detect options.
- `timeout_seconds`: 60-3600, default 1800. Passed to Pulse and Detect. This is
  not a promise to extend every downstream service's request timeout.
- `failure_policy`: default `report-only`; also accepts `fail-on-vulnerability`.
  Applies only to validated findings. Scanner, transport, missing/incomplete or
  unsafe report, and cleanup failures fail under either policy. The CLI runs with
  `--no-fail`; a nonzero scanner exit always fails. A backend policy violation with
  no reported findings, including a license-only violation, is refused, not passed.
- `upload_report`: default `false`. A validated report is a three-day artifact;
  raw and filtered lists remain separate. It is not SARIF or a license-only gate.
- `show_console`: default `false`. Prints the redacted scanner log when enabled.
- `debug_logging`: default `false`. Requests Pulse DEBUG logging, not an
  unrestricted Detect logging property. Use with `show_console: true` for diagnostics.

Credential redaction and service-destination abstraction are mandatory in published
scanner logs and reports; there is no unmasking option. Diagnostics are limited to
DEBUG logging and redacted console output. Raw diagnostic ZIP files are not
supported or published. Logs are bounded to 2 MB. If a credential field cannot be
parsed safely, the remaining log is withheld.

Check detailed Detect status and completed analysis, not just an empty findings
list. For snippets, inspect actual snippet matches, not just a nonempty BOM.

The suite uses hyphenated `vuln-` names: `vuln-python-wheels-artifact`,
`vuln-python-project`, `vuln-snippet-scan`, `vuln-detect-properties`,
`vuln-show-console` and `vuln-debug-logging`. The shared ID remains `nspect-id`.

## Detect property allowlist

Pass a JSON object to `detect_properties`. Booleans and numbers must be JSON
booleans and numbers, not strings. Unknown names, duplicate keys and unsafe values
are rejected before scanner credentials are obtained. The names and values below
were checked against Detect 11.5.0 and the pinned scanner's forwarding rules.
That does not mean every combination has been tested against a live backend.

| Property | Value / purpose |
| --- | --- |
| `detect.included.detector.types` | Comma-separated detector names, for example `NPM,MAVEN`. Limits analysis; use only for a deliberate scope. |
| `detect.excluded.detector.types` | Named detectors to omit; not `ALL`. Do not exclude a failing detector to claim complete coverage. |
| `detect.required.detector.types` | Named detectors that must apply, for example `NPM`. |
| `detect.detector.search.depth` | Integer 0-100; search depth for package-manager projects. |
| `detect.excluded.directories` | Comma-separated directory names or patterns. Changes coverage. |
| `detect.excluded.directories.defaults.disabled` | Boolean; whether to stop applying default directory exclusions. |
| `detect.accuracy.required` | `ALL`, `NONE`, or named detectors. `NONE` permits lower-accuracy results; it does not repair resolution failures. |
| `detect.pip.project.name` | Installed Python distribution to inspect. Does not install it. |
| `detect.pip.project.version.name` | Python project version-name override when Detect cannot infer it. Not a version assertion. |
| `detect.pip.only.project.tree` | Boolean; request the selected project's dependency tree. Not a general test-extra exclusion. |
| `detect.npm.dependency.types.excluded` | Comma-separated `NONE`, `DEV`, `PEER`, `OPTIONAL`. |
| `detect.maven.excluded.scopes` | Comma-separated Maven scopes, for example `test`. |
| `detect.gradle.included.configurations` | Comma-separated Gradle configurations, for example `runtimeClasspath`. |
| `detect.poetry.dependency.groups.excluded` | Comma-separated Poetry groups, for example `test,dev`. |
| `detect.uv.dependency.groups.excluded` | Comma-separated UV group or extra names. Requires usable metadata and dependency resolution. |
| `detect.blackduck.signature.scanner.individual.file.matching` | Full scans only: `NONE`, `SOURCE`, `BINARY`, `ALL`. This is not the binary-analysis command. |
| `detect.blackduck.signature.scanner.reduced.persistence` | Full scans only: `DEFAULT`, `RETAIN_UNMATCHED`, `DISCARD_UNMATCHED`. Controls unmatched-file retention, not project/version persistence. |
| `detect.blackduck.signature.scanner.license.search` | Full scans only: boolean, enables license-text search. Not license-policy enforcement. |
| `detect.blackduck.signature.scanner.copyright.search` | Full scans only: boolean, enables copyright-text search. |
| `detect.blackduck.signature.scanner.memory` | Full scans only: integer 1-65536 MB. Must fit the runner's available memory. |

Strings are bounded to 512 ASCII characters, with letters, digits, spaces and
`_.,/*?+@-` only. Detector names must match the pinned version's supported names.
Property existence and local forwarding checks do not prove every combination
against a live backend. Check the effective scanner configuration when tuning.

In wheel mode, properties that override prepared-Python detector selection, scan
root or project settings are rejected. Do not supply included, excluded or required
detector types, required accuracy, search depth, or PIP project name, version or
tree properties in this mode. Python/PIP executable paths and other workflow-owned
paths are never caller-settable.

The workflow owns the scan engines, identity, service routing, project names,
paths, snippet switch, result waiting and timeout. Do not pass credentials,
arbitrary commands, executable paths or TLS changes. For persistent scans it sets
`detect.wait.for.results=true`; `snippet_scan` sets
`detect.blackduck.signature.scanner.snippet.matching=SNIPPET_MATCHING`.

Reference documentation (Detect 11.5.0):
[detector settings](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/detector.html),
[PIP](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/pip.html),
[NPM](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/npm.html),
[Maven](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/maven.html),
[Gradle](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/gradle.html),
[UV](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/uv.html),
[signature settings](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/signature-scanner.html),
[complete upstream catalogue](https://docs.blackduck.com/r/detect/11.5.0/black-duck-detect/all-properties.html).

## Build environments

Source files alone may not tell the scanner which dependency versions are used.
Prepare the environment for the version and configuration being scanned.

`build: true` enables scanner build mode; it does not install Python dependencies.
For an installed-package scan, the optional wheel inputs prepare a separate Python
environment inside the approved scanner image. Leave them empty for existing behavior.

### Python projects

Use your normal, reviewed build job to produce the project wheel and **all intended
runtime dependency wheels** from the commit being scanned. Select the right CUDA
variant. Upload them as one flat artifact; do not include source distributions,
credentials, setup scripts or test extras unless those dependencies are in scope.

Add this step to the existing build job:

```yaml
- uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
  with:
    name: python-wheels
    path: wheelhouse/*.whl
    if-no-files-found: error
```

Make the scan job depend on that build job with `needs`, and add these reusable
workflow inputs. Keep the caller's reviewed workflow SHA and permissions unchanged:

```yaml
with:
  scan_mode: rapid
  registered_branch: main
  scan_path: .
  build: false
  python_wheels_artifact: python-wheels
  python_project: cuda-core
```

Use your installed distribution name. For a `cuda-python` package scan, select
its wheel and runtime dependencies instead. Use the repository root when package
directories link to shared repository files; source containment checks stay on.
`python_project` selects the installed dependency tree. No nSpect ID is needed
for an unregistered RAPID scan.

The workflow downloads only that named artifact from the **same workflow run**.
It installs offline, runs `pip check`, verifies the selected package is installed,
and supplies Detect's Python/PIP paths and PIP-only selection. It inspects only
the selected installed package, not nested sample requirements. Missing/incompatible
dependencies fail before scanning. The environment is read-only during the scan.

### Wheel-mode limits

- Wheels must support **Python 3.12, Linux amd64**. The workflow does not install a
  CUDA toolkit, GPU stack or a different interpreter, and does not build wheels
  or native GPU code.
- Setup is allowed only on the selected `registered_branch` ref, never PR mirrors.
  This is a trust restriction for executable build artifacts, not registration.
  Ordinary PR RAPID scans without these inputs keep their existing behavior.
- Use `build: false` with wheel inputs. This path inspects the installed Python
  dependency tree, not every package manager in a mixed-language repository.
- `.pth` startup hooks are removed before dependency checks or scanning. This is
  dependency inspection, not an application runtime test. Replacement Python startup
  modules, packaged scripts/data schemes and packaging tools are rejected.
  Arbitrary setup commands and overrides of the prepared-Python settings are not
  allowed; see the [property restrictions](#detect-property-allowlist).

Keep build tools and test extras out of a runtime-only environment. If tests or
optional features are in scope, include their dependencies deliberately. Do not
remove genuine runtime dependencies just to make the scan pass.

### Common problems

- **Missing build dependencies:** follow the project's supported setup instructions.
  Do not assume scanner build mode supplies the required tools or Python packages.
- **Dynamic package metadata or dependency-resolution errors:** installed-package
  inspection can be an alternative, provided it covers the intended dependency set.
  PIP-only selection is not a whole-repository solution for mixed-language projects.
- **Dependencies installed in another job:** they are not automatically available
  inside the scanner container. Transfer the matching wheels using the artifact
  inputs; do not copy virtual environments across incompatible systems.

## Check the result

Check detailed scanner status, a complete report, and the expected dependency names
and versions. A successful exit or empty vulnerability report alone does not prove
dependencies were found. Do not hide analysis failures to get a pass.

Use the approved scanner image and trusted build artifacts. Keep credentials out
of setup commands, properties and logs. Do not modify the scanner's own Python
environment or bypass its authentication controls.

Internal help: [registration](http://nv/kMe), [access onboarding](http://nv/kMf),
[support](http://nv/kMg), [CLI guide](http://nv/kMh). Keep internal destinations,
program IDs, project links and credential details out of public issues and logs.
