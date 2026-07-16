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
| [pre-commit](https://github.com/pre-commit/pre-commit) | Developer/consumer installed | Framework that consumes `.pre-commit-hooks.yaml`; not distributed by this repository. | [MIT](https://github.com/pre-commit/pre-commit/blob/main/LICENSE) |
| [pre-commit-hooks](https://github.com/pre-commit/pre-commit-hooks) | `v5.0.0` | Development-time hygiene hooks in this repository's `.pre-commit-config.yaml`. | [MIT](https://github.com/pre-commit/pre-commit-hooks/blob/main/LICENSE) |
| [yamllint](https://github.com/adrienverge/yamllint) | `v1.36.2` | Development-time YAML linting hook. | [GPL-3.0-or-later](https://github.com/adrienverge/yamllint/blob/master/LICENSE) |
| [shellcheck-py](https://github.com/shellcheck-py/shellcheck-py) | `v0.11.0.1` | Development-time pre-commit wrapper for ShellCheck. | [MIT](https://github.com/shellcheck-py/shellcheck-py/blob/main/LICENSE) |
| [ShellCheck](https://github.com/koalaman/shellcheck) | Provided by `shellcheck-py` | Development-time shell script linting engine. | [GPL-3.0](https://github.com/koalaman/shellcheck/blob/master/LICENSE) |
| [actionlint](https://github.com/rhysd/actionlint) | `v1.7.7` | Development-time GitHub Actions workflow linting hook. | [MIT](https://github.com/rhysd/actionlint/blob/main/LICENSE.txt) |
| [codespell](https://github.com/codespell-project/codespell) | `v2.4.1` | Development-time spell-checking hook. | [GPL-2.0-only](https://github.com/codespell-project/codespell/blob/v2.4.1/COPYING); dictionaries are [CC BY-SA 3.0](https://github.com/codespell-project/codespell/blob/v2.4.1/COPYING.Dictionary) |

## Included Third-Party Text

| Material | How it is used | License / attribution |
|---|---|---|
| [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/1/4/code-of-conduct/) | Adapted in `CODE_OF_CONDUCT.md`. | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |

## NVIDIA Notices

NVIDIA-authored source/configuration files in this repository carry SPDX
copyright and license identifiers. The project-level NVIDIA notice is in
`NOTICE`, and the full Apache-2.0 license text is in `LICENSE`.
