# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Scan the staged diff with NVIDIA's internal code-scanning service.

The service runs the GuardWords and secret scanners. It is reachable only from
the NVIDIA network and its client is distributed only to NVIDIA employees, so
this wrapper installs nothing: it runs a locally installed client when the
service can be reached and otherwise skips, so external contributors are never
blocked. ``--on-unavailable=fail`` turns every skip into a failure.
"""

import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

HOOK_ID = "guardwords-scan-code-scanning"
CLIENT_NAME = "code_scanning_git_client"
CLIENT_CONFIG = "code-scanning.client"
ENDPOINT_CONFIG = "code-scanning.endpoint"
DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 8.0  # the client's own default request timeout
PREFLIGHT_TIMEOUT = 2.0
KILL_GRACE = 2.0
BLOCKING_RESULTS = "blocking_results.txt"
INFORMATIONAL_RESULTS = "informational_results.txt"
DOCS = "https://github.com/NVIDIA/security-workflows/blob/main/hooks/guardwords/README.md"
SETUP_HELP = f"see {DOCS}#setup"
TROUBLESHOOTING_HELP = f"see {DOCS}#troubleshooting"
OFF_NETWORK = f"connect to the NVIDIA network or VPN to enable the scan ({TROUBLESHOOTING_HELP})"
NVIDIA_ONLY = (
    "GuardWords scans run only for NVIDIA employees; external contributors can ignore this notice.\n"
    f"NVIDIA employees: set up the client and endpoint, see {DOCS}#setup"
)
ARCH_ALIASES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


class Unavailable(Exception):
    """The scan could not produce a verdict."""

    def __init__(self, reason, note=None):
        super().__init__(reason)
        self.note = note


def _git(*args):
    """Return git's stripped stdout, or None if git fails."""
    try:
        result = subprocess.run(
            ["git", *args], input="", capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _client_names():
    machine = platform.machine().lower()
    arch = ARCH_ALIASES.get(machine, machine)
    if sys.platform == "win32":
        # Windows on Arm runs the published x64 build under emulation.
        system, suffix, archs = "windows", ".exe", [arch, "amd64"]
    elif sys.platform == "darwin":
        # An x86_64 Python under Rosetta can still launch the arm64 build.
        system, suffix, archs = "darwin", "", [arch, "arm64"]
    else:
        system, suffix, archs = sys.platform, "", [arch]
    names = []
    for candidate_arch in archs:
        name = f"{CLIENT_NAME}_{system}_{candidate_arch}{suffix}"
        if name not in names:
            names.append(name)
    return names + [CLIENT_NAME + suffix]


def _search_path(name):
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = entry.strip('"')
        # Relative entries, like the current directory shutil.which searches
        # on Windows, would resolve inside the repository being committed.
        if not os.path.isabs(entry):
            continue
        candidate = os.path.join(entry, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _find_client():
    configured = _git("config", "--get", CLIENT_CONFIG)
    if configured:
        path = os.path.expanduser(configured)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
        raise Unavailable(
            f"git config {CLIENT_CONFIG} is {configured!r}, which is not an executable file ({SETUP_HELP})"
        )
    for name in _client_names():
        path = _search_path(name)
        if path:
            return path
    raise Unavailable("NVIDIA code-scanning client not found", NVIDIA_ONLY)


def _endpoint(default):
    value = _git("config", "--get", ENDPOINT_CONFIG) or default
    if not value:
        raise Unavailable(
            f"no code-scanning endpoint configured (git config --global {ENDPOINT_CONFIG} HOST[:PORT]; {SETUP_HELP})"
        )
    host, separator, port = value.rpartition(":")
    if not separator:
        return value, DEFAULT_PORT
    if not host or not port.isdigit():
        raise Unavailable(f"code-scanning endpoint {value!r} is not HOST[:PORT] ({SETUP_HELP})")
    return host.strip("[]"), int(port)


def _check_reachable(host, port, timeout):
    """Fail fast off-network instead of waiting out the client's timeout."""
    deadline = time.monotonic() + timeout
    resolved = {}

    def resolve():
        try:
            resolved["addresses"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            resolved["error"] = exc

    # getaddrinfo has no timeout, and a resolver left behind by a dropped VPN
    # connection can stall it for much longer than the scan itself takes.
    resolver = threading.Thread(target=resolve, daemon=True)
    resolver.start()
    resolver.join(timeout)
    if resolver.is_alive():
        raise Unavailable(f"DNS lookup for {host} timed out; {OFF_NETWORK}")
    if "error" in resolved:
        raise Unavailable(f"cannot resolve {host}; {OFF_NETWORK}")

    error = "timed out"
    for family, socktype, proto, _, address in resolved["addresses"]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(remaining)
                sock.connect(address)
            return
        except OSError as exc:
            error = str(exc) or type(exc).__name__
    raise Unavailable(f"cannot connect to {host}:{port} ({error}); {OFF_NETWORK}")


def _base_ref():
    if _git("rev-parse", "--verify", "--quiet", "HEAD"):
        return "HEAD"
    # First commit: diff against the empty tree in this repository's hash format.
    empty_tree = _git("hash-object", "-t", "tree", "--stdin")
    if not empty_tree:
        raise Unavailable("cannot determine the base of the first commit")
    return empty_tree


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    except FileNotFoundError:
        return ""


def _last_line(output):
    lines = [line.strip() for line in output.decode("utf-8", "replace").splitlines() if line.strip()]
    return lines[-1][:300] if lines else "no output"


def _scan(client, host, port, timeout):
    """Return (exit status, client output, informational results, blocking results)."""
    workdir = tempfile.mkdtemp(prefix="guardwords-")
    try:
        command = [
            client,
            f"--addr={host}",
            f"--port={port}",
            f"--git_ref_a={_base_ref()}",
            "--git_ref_b=STAGED",
            f"--out={workdir}",
            "--source=SOURCE_UNSPECIFIED",
            f"--timeout={timeout:g}s",
        ]
        env = dict(os.environ)
        # The client's logger writes a file to the temp directory on every run;
        # keep it in the private directory that is removed below.
        for name in ("TMPDIR", "TMP", "TEMP"):
            env[name] = workdir
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                timeout=timeout + KILL_GRACE,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise Unavailable(
                f"code-scanning client did not finish within {timeout:g}s ({TROUBLESHOOTING_HELP})"
            ) from None
        except OSError as exc:
            raise Unavailable(f"cannot run {client}: {exc} ({TROUBLESHOOTING_HELP})") from None
        return (
            result.returncode,
            result.stdout,
            _read(os.path.join(workdir, INFORMATIONAL_RESULTS)),
            _read(os.path.join(workdir, BLOCKING_RESULTS)),
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _unavailable(reason, policy, note=None):
    if policy == "fail":
        print(f"GuardWords scan failed (--on-unavailable=fail): {reason}.")
    else:
        print(f"GuardWords scan skipped: {reason}.")
    if note:
        print(note)
    return 1 if policy == "fail" else 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog=HOOK_ID, description=__doc__.splitlines()[0])
    parser.add_argument(
        "--endpoint",
        metavar="HOST[:PORT]",
        help=f"service endpoint to use when git config {ENDPOINT_CONFIG} is unset",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        metavar="SECONDS",
        help="scan request timeout (default: %(default)s)",
    )
    parser.add_argument(
        "--on-unavailable",
        choices=("skip", "fail"),
        default="skip",
        help="result when the scan cannot run (default: %(default)s)",
    )
    # pass_filenames is false; tolerate consumers who re-enable it.
    parser.add_argument("filenames", nargs="*", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    try:
        client = _find_client()
        host, port = _endpoint(args.endpoint)
        _check_reachable(host, port, min(PREFLIGHT_TIMEOUT, args.timeout))
        returncode, output, informational, blocking = _scan(client, host, port, args.timeout)
    except Unavailable as exc:
        return _unavailable(str(exc), args.on_unavailable, exc.note)

    if informational:
        print("GuardWords scan: informational findings (not blocking):")
        print(informational)
    if blocking:
        print("GuardWords scan: BLOCKING ISSUES DETECTED:")
        print(blocking)
        return 1
    if returncode != 0:
        return _unavailable(
            f"code-scanning client exited with status {returncode} ({TROUBLESHOOTING_HELP}): {_last_line(output)}",
            args.on_unavailable,
        )
    if not informational:
        print("GuardWords scan passed: no findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
