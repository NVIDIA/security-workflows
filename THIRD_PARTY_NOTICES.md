# Third-Party Notices

NVIDIA Security Workflows is distributed as source code only. It does not
vendor or distribute third-party scanner source code, third-party scanner
binaries, or copyleft-licensed binaries. The tools below are either invoked
externally by workflow/pre-commit configuration or used as development-time
checks.

If this project later distributes binaries, vendors third-party code, modifies
third-party code, or adds new dependencies, the dependency set must be reviewed
again before distribution.

## Direct Tooling And Runtime References

| Component | Version / Pin | How it is used | License |
|---|---:|---|---|
| [TruffleHog](https://github.com/trufflesecurity/trufflehog) | `v3.95.9`, six SHA-256-pinned release archives | Downloaded directly from the official release during local pre-commit environment creation. `setuptools-download` verifies the archive before installing the executable in that environment. The archive and binary are not checked in or published by this repository. | [AGPL-3.0](https://github.com/trufflesecurity/trufflehog/blob/main/LICENSE) |
| [setuptools-download](https://github.com/asottile/setuptools-download) | `v1.0.1` | Pinned build-time helper for `secret-scan-trufflehog`; resolves only in the isolated hook build environment and verifies the configured release SHA-256 before extraction. | [MIT](https://github.com/asottile/setuptools-download/blob/v1.0.1/LICENSE) |
| [setuptools](https://github.com/pypa/setuptools) | `>=61` (root bridge), `>=70.1` (TruffleHog hook) | PEP 517 build backend; the hook uses its integrated wheel command to build a platform-specific local wheel. | [MIT](https://github.com/pypa/setuptools/blob/main/LICENSE) |
| [actions/checkout](https://github.com/actions/checkout) | `v6.0.2`, SHA `de0fac2e4500dabe0009e67214ff5f5447ce83dd` | Invoked externally by reusable workflows to check out repository contents. | [MIT](https://github.com/actions/checkout/blob/main/LICENSE) |
| [hashicorp/vault-action](https://github.com/hashicorp/vault-action) | `v3.4.0`, SHA `4c06c5ccf5c0761b6029f56cfb1dcf5565918a3b` | Fetches short-lived nvcr.io credentials via OIDC → Vault in Pulse scan workflows. | [MPL-2.0](https://github.com/hashicorp/vault-action/blob/main/LICENSE) |
| [docker/login-action](https://github.com/docker/login-action) | `v4.4.0`, SHA `af1e73f918a031802d376d3c8bbc3fe56130a9b0` | Authenticates to nvcr.io before pulling the Pulse scanner image. | [MIT](https://github.com/docker/login-action/blob/master/LICENSE) |
| [actions/setup-python](https://github.com/actions/setup-python) | `v6.3.0`, SHA `ece7cb06caefa5fff74198d8649806c4678c61a1` | Sets up Python for the repository CI lint (pre-commit) job. | [MIT](https://github.com/actions/setup-python/blob/main/LICENSE) |
| [github/codeql-action](https://github.com/github/codeql-action) (`upload-sarif`) | `v4.37.0`, SHA `99df26d4f13ea111d4ec1a7dddef6063f76b97e9` | Uploads redacted SARIF to GitHub code scanning. | [MIT](https://github.com/github/codeql-action/blob/main/LICENSE) |
| [pre-commit](https://github.com/pre-commit/pre-commit) | Developer/consumer installed | Framework that creates and owns the `secret-scan-trufflehog` environment; `pre-commit clean` removes its downloaded executable. | [MIT](https://github.com/pre-commit/pre-commit/blob/main/LICENSE) |
| [pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) | `v5.0.0` | Development-time hygiene hooks in this repository's `.pre-commit-config.yaml`. | [MIT](https://github.com/pre-commit/pre-commit-hooks/blob/main/LICENSE) |
| [yamllint](https://github.com/adrienverge/yamllint) | `v1.36.2` | Development-time YAML linting hook. | [GPL-3.0-or-later](https://github.com/adrienverge/yamllint/blob/master/LICENSE) |
| [actionlint](https://github.com/rhysd/actionlint) | `v1.7.12` | Development-time GitHub Actions workflow linting hook. | [MIT](https://github.com/rhysd/actionlint/blob/main/LICENSE.txt) |
| [codespell](https://github.com/codespell-project/codespell) | `v2.4.1` | Development-time spell-checking hook. | [GPL-2.0-only](https://github.com/codespell-project/codespell/blob/v2.4.1/COPYING); dictionaries are [CC BY-SA 3.0](https://github.com/codespell-project/codespell/blob/v2.4.1/COPYING.Dictionary) |

## Included Third-Party Text

| Material | How it is used | License / attribution |
|---|---|---|
| [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/1/4/code-of-conduct/) | Adapted in `CODE_OF_CONDUCT.md`. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

## NVIDIA Notices

NVIDIA-authored source/configuration files in this repository carry SPDX
copyright and license identifiers. The project-level NVIDIA notice is in
`NOTICE`, and the full Apache-2.0 license text is in `LICENSE`.
