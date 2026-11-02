# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Install NVIDIA's code-scanning client and configure Git for the GuardWords hook.

Run once per NVIDIA machine, and again to upgrade. It downloads the client build
for this platform from the GitLab project that publishes it, installs it, and
records the client path and the service endpoint in the global Git
configuration, where guardwords-scan-code-scanning reads them. The project and
endpoint are arguments, so this public repository names no internal host.
"""

import argparse
import contextlib
import json
import os
import platform
import posixpath
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

CLIENT_NAME = "code_scanning_git_client"
CLIENT_CONFIG = "code-scanning.client"
ENDPOINT_CONFIG = "code-scanning.endpoint"
TOKEN_ENV = "CODE_SCANNING_GITLAB_TOKEN"
RELEASE_PREFIX = "prod-"
DEFAULT_PORT = 443
CONNECT_TIMEOUT = 5.0
API_TIMEOUT = 60.0
ARCH_ALIASES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}
# Release assets are named code_scanning_git_client_<tag>_<os>_<arch>[.exe].
ASSET_NAME = re.compile(r"^code_scanning_git_client_.+_(darwin|linux|windows)_(amd64|arm64)(?:\.exe)?$")
JOB_ARTIFACT = re.compile(r"/-/jobs/(\d+)/artifacts/raw/(.+)$")
# ELF, PE, 64-bit Mach-O, universal Mach-O.
EXECUTABLE_MAGIC = (b"\x7fELF", b"MZ", b"\xcf\xfa\xed\xfe", b"\xca\xfe\xba\xbe")


class SetupError(Exception):
    """Setup cannot continue; the message says why."""


def _last_line(output):
    if isinstance(output, bytes):
        output = output.decode("utf-8", "replace")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1][:300] if lines else "no output"


def _split_endpoint(value):
    host, separator, port = value.rpartition(":")
    if not separator:
        host, port = value, str(DEFAULT_PORT)
    host = host.strip("[]")
    if not host or "/" in host or not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError(value)
    return host, int(port)


def _endpoint_arg(value):
    try:
        _split_endpoint(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{value!r} is not HOST[:PORT]") from None
    return value


def _project_arg(value):
    url = urllib.parse.urlsplit(value)
    # Accept the project page or any page under it, such as its releases.
    path = url.path.split("/-/", 1)[0].strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if url.scheme != "https" or not url.hostname or url.username or url.query or url.fragment or not path:
        raise argparse.ArgumentTypeError(f"{value!r} is not an https:// GitLab project URL")
    return url.netloc, path


def _which(name):
    """Find an executable on PATH, ignoring relative entries such as the current directory."""
    names = [name]
    if sys.platform == "win32":
        names = [name + extension for extension in os.environ.get("PATHEXT", ".EXE").split(os.pathsep) if extension]
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = entry.strip('"')
        if not os.path.isabs(entry):
            continue
        for candidate in names:
            path = os.path.join(entry, candidate)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    return None


def _on_path(directory):
    target = os.path.normcase(os.path.realpath(directory))
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        entry = entry.strip('"')
        if os.path.isabs(entry) and os.path.normcase(os.path.realpath(entry)) == target:
            return True
    return False


def _default_bin_dir():
    home = os.path.expanduser("~")
    candidates = [os.path.join(home, ".local", "bin"), os.path.join(home, "bin")]
    for directory in candidates:
        if _on_path(directory):
            return directory
    return candidates[0]


def _sysctl(name):
    try:
        result = subprocess.run(
            ["/usr/sbin/sysctl", "-n", name], stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip()


def _builds():
    """Return the (os, arch) client builds that can run here, best first."""
    machine = platform.machine().lower()
    arch = ARCH_ALIASES.get(machine, machine)
    if sys.platform == "win32":
        # Windows on Arm runs the x64 build under emulation.
        return [("windows", arch)] + ([("windows", "amd64")] if arch != "amd64" else [])
    if sys.platform == "darwin":
        # An x86_64 Python under Rosetta reports x86_64 on Apple silicon.
        if arch == "amd64" and _sysctl("hw.optional.arm64") == "1":
            arch = "arm64"
        return [("darwin", arch)]
    if sys.platform.startswith("linux"):
        return [("linux", arch)]
    raise SetupError(f"no code-scanning client is published for {sys.platform}")


def _connect_error(host, port, timeout):
    """Return None if host:port accepts a TCP connection, otherwise the reason it does not."""
    deadline = time.monotonic() + timeout
    resolved = {}

    def resolve():
        try:
            resolved["addresses"] = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            resolved["error"] = exc

    # getaddrinfo has no timeout of its own.
    resolver = threading.Thread(target=resolve, daemon=True)
    resolver.start()
    resolver.join(timeout)
    if resolver.is_alive():
        return "DNS lookup timed out"
    if "error" in resolved:
        return "cannot resolve the host name"

    error = "timed out"
    for family, socktype, proto, _, address in resolved["addresses"]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            with socket.socket(family, socktype, proto) as sock:
                sock.settimeout(remaining)
                sock.connect(address)
            return None
        except OSError as exc:
            error = str(exc) or type(exc).__name__
    return error


def _http_problem(status, what):
    if status == 401:
        return "GitLab rejected the credentials; log in to glab again or replace the token"
    if status == 403:
        return f"your GitLab account cannot read {what}"
    if status == 404:
        return f"GitLab has no {what}, or your account cannot see it"
    return f"GitLab returned HTTP {status} for {what}"


class _TokenAPI:
    """GitLab REST API authenticated with a personal access token."""

    def __init__(self, netloc, token):
        self.netloc = netloc
        self.base = f"https://{netloc}/api/v4/"
        self.token = token

    def _get(self, path, what, read):
        request = urllib.request.Request(self.base + path)
        # Unredirected, so the token is not forwarded if the artifact is served from object storage.
        request.add_unredirected_header("PRIVATE-TOKEN", self.token)
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
                return read(response)
        except urllib.error.HTTPError as exc:
            exc.close()
            raise SetupError(_http_problem(exc.code, what)) from None
        except (urllib.error.URLError, OSError) as exc:
            raise SetupError(f"cannot read {what} from {self.netloc}: {getattr(exc, 'reason', exc)}") from None

    def json(self, path, what):
        return json.loads(self._get(path, what, lambda response: response.read()))

    def download(self, path, what, handle):
        self._get(path, what, lambda response: shutil.copyfileobj(response, handle, 1 << 20))


class _GlabAPI:
    """GitLab REST API through glab's stored login."""

    def __init__(self, glab, netloc):
        self.command = [glab, "api", "--hostname", netloc]

    def _run(self, path, what, stdout):
        try:
            result = subprocess.run(
                self.command + [path], stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.PIPE, check=False
            )
        except OSError as exc:
            raise SetupError(f"cannot run glab: {exc}") from None
        if result.returncode != 0:
            status = re.search(rb"HTTP (\d{3})", result.stderr)
            if status:
                raise SetupError(_http_problem(int(status.group(1)), what))
            raise SetupError(f"glab could not read {what}: {_last_line(result.stderr)}")
        return result

    def json(self, path, what):
        return json.loads(self._run(path, what, subprocess.PIPE).stdout)

    def download(self, path, what, handle):
        self._run(path, what, handle)


def _gitlab(netloc):
    """Return a GitLab API client and a description of the credentials it uses."""
    token = os.environ.get(TOKEN_ENV, "").strip()
    if token:
        return _TokenAPI(netloc, token), TOKEN_ENV
    glab = _which("glab")
    if glab:
        try:
            logged_in = (
                subprocess.run(
                    [glab, "auth", "status", "--hostname", netloc],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    check=False,
                ).returncode
                == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            logged_in = False
        if logged_in:
            return _GlabAPI(glab, netloc), "glab login"
    raise SetupError(
        f"no GitLab login for {netloc}: run `glab auth login --hostname {netloc}`, "
        f"or set {TOKEN_ENV} to a personal access token with read_api scope"
    )


def _release(api, project, tag):
    encoded = urllib.parse.quote(project, safe="")
    try:
        if tag:
            release = api.json(
                f"projects/{encoded}/releases/{urllib.parse.quote(tag, safe='')}", f"release {tag} in {project}"
            )
        else:
            releases = api.json(f"projects/{encoded}/releases?per_page=100", f"project {project}")
            if not isinstance(releases, list):
                raise ValueError("not a release list")
            release = next(
                (item for item in releases if str(item.get("tag_name", "")).startswith(RELEASE_PREFIX)), None
            )
            if release is None:
                raise SetupError(f"{project} has no {RELEASE_PREFIX}* release; pass --release TAG")
        if not isinstance(release.get("tag_name"), str):
            raise ValueError("no tag name")
    except (ValueError, AttributeError):
        raise SetupError(f"unexpected response from GitLab for the {project} releases") from None
    return release


def _asset(release, builds):
    """Return the best (os, arch) build in the release and its download URL."""
    published = {}
    for link in (release.get("assets") or {}).get("links") or []:
        url = link.get("url", "")
        match = ASSET_NAME.match(posixpath.basename(urllib.parse.urlsplit(url).path))
        if match:
            published.setdefault(match.groups(), url)
    for build in builds:
        if build in published:
            return build, published[build]
    available = ", ".join("/".join(build) for build in sorted(published)) or "none"
    raise SetupError(
        f"{release['tag_name']} has no client for {'/'.join(builds[0])} (published: {available}); "
        "ask ProdSec for a build"
    )


def _api_path(netloc, project, url):
    """Translate a release asset link into a GitLab API path, so the download is authenticated."""
    releases_page = f"https://{netloc}/{project}/-/releases"
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.netloc != netloc:
        raise SetupError(f"the client is published outside {netloc}; download it from {releases_page}")
    artifact = JOB_ARTIFACT.search(parts.path)
    if artifact:
        job, file_path = artifact.groups()
        return (
            f"projects/{urllib.parse.quote(project, safe='')}/jobs/{job}/artifacts/"
            f"{urllib.parse.quote(urllib.parse.unquote(file_path))}"
        )
    if parts.path.startswith("/api/v4/"):
        return parts.path[len("/api/v4/") :] + (f"?{parts.query}" if parts.query else "")
    raise SetupError(f"cannot download {url} through the GitLab API; download it from {releases_page}")


def _install(api, path, directory, name):
    """Download to a temporary file beside the target and move it into place, so a failure leaves no partial client."""
    try:
        os.makedirs(directory, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(dir=directory, prefix=f".{name}.", delete=False)
    except OSError as exc:
        raise SetupError(f"cannot write to {directory}: {exc}") from None
    try:
        with handle:
            api.download(path, "the client download", handle)
        with open(handle.name, "rb") as downloaded:
            if not downloaded.read(4).startswith(EXECUTABLE_MAGIC):
                raise SetupError("the downloaded file is not an executable; check the release assets")
        size = os.path.getsize(handle.name)
        os.chmod(handle.name, 0o755)
        destination = os.path.join(directory, name)
        os.replace(handle.name, destination)
    except BaseException as exc:
        with contextlib.suppress(OSError):
            os.unlink(handle.name)
        if isinstance(exc, OSError):
            raise SetupError(f"cannot install the client in {directory}: {exc}") from None
        raise
    return destination, size


def _check_client(client):
    try:
        result = subprocess.run(
            [client, "-help"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError(f"the installed client does not run: {exc}") from None
    if result.returncode < 0 or b"-addr" not in result.stdout:
        raise SetupError(
            f"the installed client does not run (exit status {result.returncode}: {_last_line(result.stdout)})"
        )


def _set_git_config(key, value):
    try:
        result = subprocess.run(
            ["git", "config", "--global", key, value],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        raise SetupError("git is not installed or not on PATH") from None
    if result.returncode != 0:
        raise SetupError(f"git config --global {key} failed: {_last_line(result.stderr)}")


def _setup(args):
    netloc, project = args.project_url
    gitlab = urllib.parse.urlsplit(f"https://{netloc}")
    builds = _builds()
    problem = _connect_error(gitlab.hostname, gitlab.port or DEFAULT_PORT, CONNECT_TIMEOUT)
    if problem:
        raise SetupError(f"cannot reach {netloc} ({problem}); connect to the NVIDIA network or VPN")
    api, credentials = _gitlab(netloc)
    release = _release(api, project, args.release)
    build, url = _asset(release, builds)
    directory = os.path.abspath(os.path.expanduser(args.bin_dir or _default_bin_dir()))
    name = f"{CLIENT_NAME}_{build[0]}_{build[1]}{'.exe' if build[0] == 'windows' else ''}"

    print(f"Downloading {release['tag_name']} ({'/'.join(build)}) from {netloc}/{project} using {credentials}")
    client, size = _install(api, _api_path(netloc, project, url), directory, name)
    _check_client(client)
    print(f"Installed {client} ({size / 1e6:.1f} MB)")
    _set_git_config(CLIENT_CONFIG, client)
    _set_git_config(ENDPOINT_CONFIG, args.endpoint)
    print(f"Set git config --global {CLIENT_CONFIG} {client}")
    print(f"Set git config --global {ENDPOINT_CONFIG} {args.endpoint}")

    problem = _connect_error(*_split_endpoint(args.endpoint), CONNECT_TIMEOUT)
    if problem:
        print(f"Warning: cannot reach {args.endpoint} now ({problem}); commits are scanned once it is reachable.")
    if not _on_path(directory):
        print(f"Note: {directory} is not on PATH. The hook finds the client through git config; add the directory")
        print("to PATH to run the client by hand.")
    print("Setup complete. Run `pre-commit install` in each repository that uses guardwords-scan-code-scanning.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="install_client.py",
        description=__doc__.splitlines()[0],
        epilog=(
            f"GitLab access uses {TOKEN_ENV} (a personal access token with read_api scope) when it is set, "
            "otherwise glab's login for the project's host."
        ),
    )
    parser.add_argument(
        "--project-url",
        required=True,
        type=_project_arg,
        metavar="URL",
        help="GitLab project that publishes the client releases",
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        type=_endpoint_arg,
        metavar="HOST[:PORT]",
        help=f"code-scanning service endpoint to store in git config {ENDPOINT_CONFIG}",
    )
    parser.add_argument(
        "--release",
        metavar="TAG",
        help=f"release to install (default: the newest {RELEASE_PREFIX}* release)",
    )
    parser.add_argument(
        "--bin-dir",
        metavar="DIR",
        help="directory to install the client in (default: ~/.local/bin, or ~/bin when only that is on PATH)",
    )
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _setup(args)
    except SetupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
