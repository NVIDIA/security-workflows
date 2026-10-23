# GuardWords hook — `guardwords-scan-code-scanning`

Flags terminology and content that conflicts with NVIDIA brand, legal, or inclusivity guidance before it is committed. The hook is a thin wrapper around NVIDIA's internal code-scanning service, which runs the GuardWords and secret scanners on the staged diff. The service is reachable only from the NVIDIA network and its client is distributed only to NVIDIA employees, so installing the hook downloads nothing, and each run decides what to do:

| Condition | Result |
|---|---|
| Client not installed, or no endpoint configured (every external contributor) | Skipped with a notice |
| Service unreachable (off the NVIDIA network or VPN), timed out, or failed | Skipped with a notice |
| Informational findings only | Printed; the commit proceeds |
| Blocking findings | Printed; the commit is blocked |

Every skip notice links to [Setup](#setup) or [Troubleshooting](#troubleshooting) on this page. `--on-unavailable=fail` turns every skip into a failure; use it only in repositories whose contributors are all on the NVIDIA network. There is no GuardWords CI workflow yet, so a skipped commit is not re-scanned before merge. Rules shared by every hook in this repository are in the [hook catalogue](../README.md).

## Setup

> **NVIDIA employees only.** GuardWords needs ProdSec's internal client and the NVIDIA network. External contributors have nothing to set up: the hook skips with a notice and the commit goes ahead.
>
> NVIDIA employees: the internal guide [Setting up pre-commit hook](http://nv/ghf-precommit) gives the GitLab project URL and the endpoint for step 2, and [GuardWords scan, step by step](http://nv/ghf-guardwords) walks through every scenario on a sample repository. The `nv/` links open on the NVIDIA network or VPN; if you can't open them, ask in the internal [`#github-first-security-scanning`](http://nv/ghf-scan-help) Slack channel.

1. **Add the hook** (maintainers, once per repository). Skip it on [pre-commit.ci](https://pre-commit.ci/), which has neither the client nor NVIDIA network access:

   ```yaml
   ci:
     skip: [guardwords-scan-code-scanning]

   repos:
     - repo: https://github.com/NVIDIA/security-workflows
       rev: <commit SHA>  # frozen: <release tag>
       hooks:
         - id: guardwords-scan-code-scanning
   ```

   Pin a commit that includes the hook; with an older one, pre-commit reports `` `guardwords-scan-code-scanning` is not present in repository ``.

2. **Install the client** (NVIDIA employees, once per machine). ProdSec publishes it for macOS on Apple silicon, Linux x86-64 and Windows x86-64 (Windows on Arm uses the x86-64 build); on other platforms the hook skips. Download [`install_client.py`](install_client.py) from the commit your `rev:` pins (releases up to v0.4.0 don't contain it), then run it with the GitLab project and endpoint from the [internal setup guide](http://nv/ghf-guardwords-client):

   ```bash
   curl -fsSLo install_client.py https://raw.githubusercontent.com/NVIDIA/security-workflows/<commit SHA>/hooks/guardwords/install_client.py \
     && python3 install_client.py --project-url <GITLAB-PROJECT-URL> --endpoint <HOST>:<PORT>
   ```

   On Windows, run the same two commands in PowerShell with `curl.exe` and `py` in place of `curl` and `python3`, and without the `\` line break.

   The script downloads the newest `prod-*` client release for the platform, installs it in `~/.local/bin` (or `~/bin` when only that is on `PATH`), and sets `code-scanning.client` and `code-scanning.endpoint` in the global Git configuration. It reads GitLab with `CODE_SCANNING_GITLAB_TOKEN` (a personal access token with `read_api` scope) when that is set, and otherwise with `glab`'s login for the project's host. `--release <TAG>` pins a release, `--bin-dir <DIR>` changes the install directory, and running it again upgrades the client.

   To set up by hand instead, download your platform's client from the project's newest `prod-*` release and install it on `PATH` as `code_scanning_git_client_<os>_<arch>` (`.exe` on Windows), without the release tag in the name; the hook looks for that name only. Then set the endpoint:

   ```bash
   chmod +x ~/.local/bin/code_scanning_git_client_darwin_arm64
   # macOS: clear the quarantine flag the browser adds to downloads:
   xattr -d com.apple.quarantine ~/.local/bin/code_scanning_git_client_darwin_arm64
   git config --global code-scanning.endpoint <HOST>:<PORT>
   # Only if your Git client does not inherit your shell PATH, as some GUI clients do not:
   git config --global code-scanning.client <PATH-TO-CLIENT>
   ```

3. **Activate the hooks** (everyone, once per clone) with `pre-commit install`. Until then no hook runs. If the clone already has a Git hook that pre-commit didn't create, such as ProdSec's standalone code-scanning hook, pre-commit prints `Running in migration mode with existing hooks at …` and runs both on every commit. `guardwords-scan-code-scanning` replaces ProdSec's hook, so run `pre-commit install -f` to drop it (copy it elsewhere first if you still need it).

4. **Check the setup** (NVIDIA employees). Stage a change and run `pre-commit run guardwords-scan-code-scanning`. It prints `GuardWords scan passed: no findings.` or a list of findings; `GuardWords scan skipped:` means a prerequisite is missing.

Neither the hook nor the setup script has the project or endpoint built in, so this public repository names no internal host. A private repository can set the endpoint for every contributor with `args: [--endpoint=<HOST>:<PORT>]` instead.

## Troubleshooting

pre-commit reports `Passed` for a skipped scan too, so read the line that follows it. A skip lets the commit proceed unscanned. External contributors can ignore every GuardWords notice. NVIDIA employees: the internal guide's [troubleshooting section](http://nv/ghf-precommit) has the exact endpoint to compare against.

| `GuardWords scan skipped:` message | Cause | Fix |
|---|---|---|
| `NVIDIA code-scanning client not found`, followed by `GuardWords scans run only for NVIDIA employees …` | No client on `PATH`: an external contributor, an NVIDIA machine not yet set up, a platform without a published client, or a client installed by hand under its download name | External contributors: nothing to do. NVIDIA employees: [install the client](#setup), named `code_scanning_git_client_<os>_<arch>`; until then your commits are not scanned. |
| `git config code-scanning.client is '…', which is not an executable file` | The configured client path is wrong | Run the setup script again, or correct `code-scanning.client`. |
| `no code-scanning endpoint configured` | `code-scanning.endpoint` is not set | Run the setup script again, or set it by hand as in [Setup](#setup). |
| `code-scanning endpoint '…' is not HOST[:PORT]` | The configured endpoint is malformed | Set `code-scanning.endpoint` to `<HOST>:<PORT>`. |
| `cannot resolve …`, `cannot connect to …` or `DNS lookup for … timed out` | Off the NVIDIA network or VPN, or a wrong endpoint host or port | Connect to the VPN and commit again. Already on the VPN? Compare `git config --get code-scanning.endpoint` with the setup guide, and run the setup script again to reset it. A commit made while the scan skipped is not re-scanned later. |
| `code-scanning client did not finish within …s` | The service was slow | Commit again; `args: [--timeout=<SECONDS>]` raises the limit. |
| `code-scanning client exited with status …` or `cannot run …` | The client failed | Run the setup script again to upgrade the client. If it still fails, [ask for help](#help). |

The setup script stops with `error: <message>` when it can't finish:

| Setup script message | Fix |
|---|---|
| `cannot reach <host> (…); connect to the NVIDIA network or VPN` | Connect to the VPN and run it again. |
| `no GitLab login for <host>` | Run `glab auth login --hostname <host>`, or set `CODE_SCANNING_GITLAB_TOKEN` to a personal access token with `read_api` scope. |
| `GitLab rejected the credentials` | Log in to `glab` again, or replace the token. |
| `GitLab has no project …, or your account cannot see it` or `your GitLab account cannot read …` | Check `--project-url` against the setup guide. If it is right, ask ProdSec for access to the project. |
| `… has no client for <os>/<arch>` or `no code-scanning client is published for …` | No client exists for your platform yet; the hook skips there. |
| `the installed client does not run …` or `the downloaded file is not an executable …` | Run the script again; if it still fails, [ask for help](#help). |

It also prints two notices that need no action: `Warning: cannot reach <endpoint> now` (commits are scanned once the service is reachable) and `Note: <directory> is not on PATH` (the hook finds the client through Git configuration).

## Help

NVIDIA employees: ask in the internal [`#github-first-security-scanning`](http://nv/ghf-scan-help) Slack channel, not in a GitHub issue, because this repository is public. Never paste a flagged term, an internal host name or client output into an issue, pull request or chat; refer to the file and line instead. A finding whose `Scanner:` line names the secret scanner is a secret: remove it from the change, and rotate the credential if it is real.
