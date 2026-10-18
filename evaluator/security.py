"""Immutable source retrieval, safe snapshots, and restricted Docker execution."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from urllib.request import Request, urlopen


MAX_SNAPSHOT_BYTES = 50 * 1024 * 1024
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES = 2_000
MAX_RUNTIME_SECONDS = 600
MAX_RESULT_BYTES = 100_000
DOCKER_IMAGE = os.environ.get("HIGGSLAB_SANDBOX_IMAGE", "higgslab-sandbox:local")
MAX_FETCH_FILE_BYTES = 256 * 1024 * 1024


class SandboxError(RuntimeError):
    pass


def _git_file_size_limit():
    """Cap any single Git object/pack/worktree file produced by a hostile public repo."""
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FETCH_FILE_BYTES, MAX_FETCH_FILE_BYTES))
    except (ImportError, OSError, ValueError):
        pass


def _git_limits():
    return {"preexec_fn": _git_file_size_limit} if os.name == "posix" else {}


def _git_environment() -> dict[str, str]:
    """Minimal environment for fetching public source commits."""
    env = {"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1"}
    # Windows git.exe needs OS runtime roots for DNS/TLS; never inherit HOME or tokens.
    for key in ("SYSTEMROOT", "WINDIR"):
        if key in os.environ:
            env[key] = os.environ[key]
    return env


def _docker_client_env() -> dict[str, str]:
    """Environment for the trusted Docker CLI only; never passed into a container."""
    keys = {
        "PATH", "DOCKER_CONFIG", "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY",
        "DOCKER_CERT_PATH", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
        "LOCALAPPDATA", "SYSTEMROOT", "WINDIR", "PATHEXT", "COMSPEC",
        "XDG_RUNTIME_DIR", "TMP", "TEMP",
    }
    return {key: os.environ[key] for key in keys if key in os.environ}


def canonical_repo_url(repo: str) -> str:
    parts = repo.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[A-Za-z0-9_.-]+", p) for p in parts):
        raise SandboxError("Expected OWNER/REPO")
    if any(p.startswith(".") for p in parts):
        raise SandboxError("Invalid GitHub repository name")
    return f"https://github.com/{parts[0]}/{parts[1]}.git"


def _check_sha(sha: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{40}", sha):
        raise SandboxError("Commit must be a full 40-character SHA")
    return sha.lower()


def snapshot_commit(repo: str, sha: str, destination: str | Path) -> Path:
    """Fetch exactly one public commit and export it after safe-tree checks."""
    sha = _check_sha(sha)
    url = canonical_repo_url(repo)
    verify_repository_commit(repo, sha)
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if any(target.iterdir()):
        raise SandboxError("Snapshot destination must be empty")
    with tempfile.TemporaryDirectory(prefix="higgslab-fetch-") as work:
        checkout = Path(work) / "repo"
        # Keep the fetch environment free of HOME, GitHub tokens, and the sealed seed.
        safe_env = _git_environment()
        limits = _git_limits()
        subprocess.run(["git", "init", "--quiet", str(checkout)], check=True, timeout=30, env=safe_env, **limits)
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin", url], check=True, timeout=30, env=safe_env, **limits)
        fetch = subprocess.run(
            ["git", "-C", str(checkout), "fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", sha],
            capture_output=True, text=True, timeout=90, env=safe_env, **limits,
        )
        if fetch.returncode:
            raise SandboxError("Could not fetch the declared commit from the public repository")
        actual = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "FETCH_HEAD"],
            check=True, capture_output=True, text=True, timeout=15, env=safe_env, **limits,
        ).stdout.strip().lower()
        if actual != sha:
            raise SandboxError("Fetched commit does not match the declared SHA")
        # Materialize only the designated submission subtree; unrelated fork files never enter
        # the trusted host snapshot and partial clone avoids downloading their blob contents.
        subprocess.run(["git", "-C", str(checkout), "checkout", "--quiet", sha, "--", "submission"],
                       check=True, timeout=60, env=safe_env, **limits)
        submission_dir = checkout / "submission"
        if not submission_dir.is_dir() or submission_dir.is_symlink():
            raise SandboxError("Pinned commit must contain a regular submission/ directory")
        _copy_safe_tree(submission_dir, target)
    return target


def verify_repository_commit(repo: str, sha: str) -> None:
    """Confirm GitHub associates this exact commit with the declared repository."""
    sha = _check_sha(sha)
    parts = repo.split("/")
    if len(parts) != 2:
        raise SandboxError("Expected OWNER/REPO")
    endpoint = f"https://api.github.com/repos/{parts[0]}/{parts[1]}/commits/{sha}"
    request = Request(endpoint, headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    try:
        with urlopen(request, timeout=20) as response:
            body = __import__("json").load(response)
    except Exception as exc:
        raise SandboxError("Could not verify the commit against the declared public repository") from exc
    if str(body.get("sha", "")).lower() != sha:
        raise SandboxError("GitHub returned a different commit SHA")
    repository = body.get("html_url", "").split("/commit/")[0].rstrip("/").lower()
    if repository != f"https://github.com/{repo}".lower():
        raise SandboxError("Commit does not belong to the declared repository")


def _copy_safe_tree(source: Path, target: Path) -> None:
    total = 0
    count = 0
    for item in source.rglob("*"):
        relative = item.relative_to(source)
        if ".git" in relative.parts:
            raise SandboxError("Submission snapshot must not contain Git metadata")
        if item.is_symlink():
            raise SandboxError(f"Submission contains a symlink: {relative.as_posix()}")
        if any(part.casefold() in {"data", "datasets", "mc", "sealed", "truth"} for part in relative.parts):
            raise SandboxError(f"Submission data paths are not allowed: {relative.as_posix()}")
        if item.is_dir():
            (target / relative).mkdir(parents=True, exist_ok=True)
            continue
        if not item.is_file():
            raise SandboxError(f"Submission contains a special file: {relative.as_posix()}")
        count += 1
        size = item.stat().st_size
        total += size
        if count > MAX_FILES or total > MAX_SNAPSHOT_BYTES or size > MAX_FILE_BYTES:
            raise SandboxError("Submission exceeds the file-count or snapshot-size limit")
        if item.suffix.lower() in {
            ".root", ".npz", ".npy", ".csv", ".tsv", ".parquet", ".h5", ".hdf5", ".feather",
            ".pkl", ".pickle", ".pt", ".pth", ".ckpt", ".onnx", ".safetensors",
        }:
            raise SandboxError(f"Submission data files are not allowed: {relative.as_posix()}")
        if item.name.lower() in {"events.json", "truth.json", "dataset.json", "pool.json"}:
            raise SandboxError(f"Submission data files are not allowed: {relative.as_posix()}")
        out = target / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, out)
        os.chmod(out, 0o444)


def run_in_docker(snapshot: str | Path, dataset: str | Path, output: str | Path,
                  timeout_seconds: int = MAX_RUNTIME_SECONDS, *,
                  memory_limit: str = "6g", pids_limit: int = 128) -> None:
    """Run a student entrypoint with no network, credentials, or writable source."""
    snapshot = Path(snapshot).resolve()
    dataset = Path(dataset).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if output.is_symlink() or any(output.iterdir()):
        raise SandboxError("Output destination must be a real, empty directory")
    if timeout_seconds < 1 or timeout_seconds > MAX_RUNTIME_SECONDS:
        raise SandboxError("Timeout exceeds the configured maximum")
    memory = re.fullmatch(r"([0-9]+)([mMgG])", memory_limit)
    if not memory:
        raise SandboxError("Invalid container memory limit")
    memory_bytes = int(memory.group(1)) * (1024 ** (3 if memory.group(2).lower() == "g" else 2))
    if memory_bytes < 128 * 1024 * 1024 or memory_bytes > 6 * 1024 ** 3:
        raise SandboxError("Container memory limit is outside the permitted range")
    if not isinstance(pids_limit, int) or pids_limit < 16 or pids_limit > 128:
        raise SandboxError("Container PID limit is outside the permitted range")
    runner = snapshot / "run.sh"
    if not runner.is_file() or runner.is_symlink():
        raise SandboxError("Pinned commit must contain submission/run.sh")
    container_name = f"higgslab-{uuid.uuid4().hex[:16]}"
    cmd = [
        "docker", "run", "--detach", "--pull=never", "--log-driver=none", "--name", container_name,
        "--network=none", "--read-only", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", f"--pids-limit={pids_limit}", f"--memory={memory_limit}",
        "--cpus=2", "--user=0:0", "--tmpfs=/tmp:rw,noexec,nosuid,size=512m,mode=1777",
        "--tmpfs=/output:rw,noexec,nosuid,size=16m,uid=65534,gid=65534,mode=755",
        "--mount", f"type=bind,src={snapshot},dst=/submission,readonly",
        "--mount", f"type=bind,src={dataset},dst=/data,readonly",
        "--workdir=/submission", DOCKER_IMAGE, "sleep", "infinity",
    ]
    # Docker Desktop may need DOCKER_CONFIG/USERPROFILE/DOCKER_CONTEXT to reach its
    # daemon. This environment is used only to launch the host Docker CLI; `docker exec`
    # receives no host environment and the student process runs with the image's defaults.
    clean_env = _docker_client_env()
    try:
        try:
            started = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     timeout=30, env=clean_env)
            if started.returncode:
                raise SandboxError("Could not start the isolated runner")
            # Keep PID 1 alive so tmpfs output survives until trusted extraction. Student code
            # runs under nobody and cannot forge the root-owned extractor or its stdout pipe.
            result = subprocess.run([
                "docker", "exec", "--user=65534:65534", "--workdir=/submission", container_name,
                "bash", "/submission/run.sh", "/data", "/output",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=timeout_seconds, env=clean_env)
            if result.returncode:
                raise SandboxError(f"Submission exited with status {result.returncode}; output was withheld")
            # Trusted root opens the fixed path without following symlinks, checks the opened
            # inode, then streams at most MAX_RESULT_BYTES to the host. No docker cp TOCTOU.
            extractor = """\
import os, stat, sys
fd = os.open('/output/RESULT.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
status = os.fstat(fd)
if not stat.S_ISREG(status.st_mode) or status.st_size > 100000:
    sys.exit(3)
chunks = []
remaining = status.st_size
while remaining:
    part = os.read(fd, min(remaining, 65536))
    if not part:
        break
    chunks.append(part)
    remaining -= len(part)
data = b''.join(chunks)
if remaining or len(data) > 100000:
    sys.exit(4)
sys.stdout.buffer.write(data)
"""
            extracted = subprocess.run([
                "docker", "exec", "--user=0:0", "--workdir=/", container_name,
                "/usr/local/bin/python", "-I", "-S", "-c", extractor,
            ], capture_output=True, timeout=15, env=clean_env)
            if extracted.returncode:
                raise SandboxError("Submission result must be a regular file under 100 kB")
            if len(extracted.stdout) > MAX_RESULT_BYTES:
                raise SandboxError("Result file exceeds the size limit")
            result_path = output / "RESULT.json"
            with result_path.open("xb") as result_file:
                result_file.write(extracted.stdout)
            os.chmod(result_path, 0o444)
        except subprocess.TimeoutExpired as exc:
            raise SandboxError("Submission exceeded the runtime limit") from exc
    finally:
        failed_before_cleanup = sys.exc_info()[0] is not None
        try:
            cleaned = subprocess.run(["docker", "rm", "--force", container_name],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=15, env=clean_env)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            if not failed_before_cleanup:
                raise SandboxError("Could not remove the isolated runner") from exc
        else:
            if cleaned.returncode and not failed_before_cleanup:
                raise SandboxError("Could not remove the isolated runner")
