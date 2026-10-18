"""Local hostile-container rehearsal. Hosted scoring stays disabled until this passes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .security import DOCKER_IMAGE, SandboxError, _docker_client_env, run_in_docker


def isolation_fingerprint() -> str:
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256()
    digest.update(DOCKER_IMAGE.encode())
    for path in (root / "evaluator/security.py", root / "evaluator/isolation.py",
                 root / "evaluator/Dockerfile", root / "evaluator/requirements-sandbox.txt"):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _runner(snapshot: Path, script: str):
    # Bash in the Linux image requires LF. Path.write_text's default newline conversion
    # on Windows would otherwise generate CRLF scripts and invalidate the rehearsal.
    with (snapshot / "run.sh").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("#!/bin/bash\nset -eu\n" + script.strip() + "\n")


def _probe(snapshot: Path, data: Path, output: Path, script: str, *,
           timeout_seconds: int = 15, memory_limit: str = "128m", pids_limit: int = 24) -> dict:
    _runner(snapshot, script)
    run_in_docker(snapshot, data, output, timeout_seconds=timeout_seconds,
                  memory_limit=memory_limit, pids_limit=pids_limit)
    try:
        payload = json.loads((output / "RESULT.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SandboxError("Isolation probe did not return its status record") from exc
    if not isinstance(payload, dict) or payload.get("probe") is not True:
        raise SandboxError("Isolation probe status record is invalid")
    return payload


def perform_isolation_check(report_path: str | Path) -> dict:
    """Build the trusted image and exercise hostile behaviors before event activation."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    checks = {
        "docker_image_built": False,
        "no_network_or_host_state_or_secrets": False,
        "submission_snapshot_read_only": False,
        "result_symlinks_rejected": False,
        "runtime_limit_enforced": False,
        "memory_limit_enforced": False,
        "pid_limit_enforced": False,
        "output_and_log_limits_enforced": False,
        "root_sitecustomize_not_executed": False,
        "valid_result_collected": False,
    }
    failure_stage = "docker_build"
    image_id = None
    try:
        build = subprocess.run(
            ["docker", "build", "--tag", DOCKER_IMAGE, "--file", "evaluator/Dockerfile", "."],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600,
            env=_docker_client_env(),
        )
        if build.returncode:
            raise SandboxError("Could not build the local sandbox image")
        checks["docker_image_built"] = True
        inspect = subprocess.run(
            ["docker", "image", "inspect", "--format={{.Id}}", DOCKER_IMAGE],
            check=True, capture_output=True, text=True, timeout=30, env=_docker_client_env(),
        )
        image_id = inspect.stdout.strip()
        if not image_id:
            raise SandboxError("Could not identify the built sandbox image")
        with tempfile.TemporaryDirectory(prefix="higgslab-isolation-") as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            data = root / "data"
            snapshot.mkdir(); data.mkdir()
            (data / "events.json").write_text('{"input":true}', encoding="utf-8")

            host_secret = root / "secret.txt"
            other_team = root / "other-team.txt"
            host_secret.write_text("HIGGSLAB_HOST_SECRET_SENTINEL", encoding="utf-8")
            other_team.write_text("HIGGSLAB_OTHER_TEAM_SENTINEL", encoding="utf-8")
            sentinel_key = "HIGGSLAB_ISOLATION_SENTINEL"
            previous = os.environ.get(sentinel_key)
            os.environ[sentinel_key] = "HIGGSLAB_HOST_SECRET_SENTINEL"
            try:
                failure_stage = "host_and_network_isolation"
                access = _probe(snapshot, data, root / "host-probe", f"""
python - <<'PY'
import json, os, socket
secret = {str(host_secret)!r}
other = {str(other_team)!r}
assert os.environ.get({sentinel_key!r}) != 'HIGGSLAB_HOST_SECRET_SENTINEL', 'host env leaked'
assert 'HIGGSLAB_HOST_SECRET_SENTINEL' not in os.environ.values(), 'host secret leaked'
assert not os.path.exists(secret), 'host secret path is mounted'
assert not os.path.exists(other), 'another team path is mounted'
try:
    socket.create_connection(('1.1.1.1', 443), timeout=2)
except OSError:
    network_blocked = True
else:
    network_blocked = False
    raise SystemExit(31)
try:
    with open('/submission/run.sh', 'a') as stream:
        stream.write('# forbidden')
except OSError:
    source_read_only = True
else:
    source_read_only = False
    raise SystemExit(32)
with open('/output/RESULT.json', 'w') as result:
    json.dump({{'probe': True, 'network_blocked': network_blocked,
               'source_read_only': source_read_only}}, result)
PY
""", timeout_seconds=20)
            finally:
                if previous is None:
                    os.environ.pop(sentinel_key, None)
                else:
                    os.environ[sentinel_key] = previous
            if access.get("network_blocked") is not True:
                raise SandboxError("Network isolation probe did not confirm blocked access")
            if access.get("source_read_only") is not True:
                raise SandboxError("Source isolation probe did not confirm read-only access")
            checks["no_network_or_host_state_or_secrets"] = True
            checks["submission_snapshot_read_only"] = True

            symlink_output = root / "symlink-output"
            symlink_output.mkdir()
            failure_stage = "symlink_result_rejection"
            _runner(snapshot, "ln -s /etc/passwd /output/RESULT.json")
            try:
                run_in_docker(snapshot, data, symlink_output, timeout_seconds=15,
                              memory_limit="128m", pids_limit=24)
            except SandboxError as exc:
                if "regular file" not in str(exc).lower():
                    raise
                checks["result_symlinks_rejected"] = True
            else:
                raise SandboxError("Sandbox accepted a symlinked result")

            timeout_output = root / "timeout-output"
            timeout_output.mkdir()
            failure_stage = "runtime_limit"
            _runner(snapshot, "sleep 5")
            try:
                run_in_docker(snapshot, data, timeout_output, timeout_seconds=1,
                              memory_limit="128m", pids_limit=24)
            except SandboxError as exc:
                if "runtime limit" not in str(exc).lower():
                    raise
                checks["runtime_limit_enforced"] = True
            else:
                raise SandboxError("Sandbox did not stop an over-time submission")

            memory_output = root / "memory-output"
            memory_output.mkdir()
            failure_stage = "memory_limit"
            _runner(snapshot, """
python - <<'PY'
data = bytearray(512 * 1024 * 1024)
for index in range(0, len(data), 4096):
    data[index] = 1
PY
""")
            try:
                run_in_docker(snapshot, data, memory_output, timeout_seconds=15,
                              memory_limit="128m", pids_limit=24)
            except SandboxError as exc:
                if "exited with status 137" not in str(exc).lower():
                    raise
                checks["memory_limit_enforced"] = True
            else:
                raise SandboxError("Sandbox did not stop an over-memory submission")

            pid_output = root / "pid-output"
            pid_output.mkdir()
            failure_stage = "pid_limit"
            pid_payload = _probe(snapshot, data, pid_output, """
python - <<'PY'
import json, subprocess
children = []
denied = False
try:
    for _ in range(100):
        try:
            children.append(subprocess.Popen(['sleep', '60']))
        except OSError:
            denied = True
            break
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait(timeout=3)
assert denied and len(children) < 24, 'PID limit was not reached'
with open('/output/RESULT.json', 'w') as result:
    json.dump({'probe': True, 'pid_limit': len(children)}, result)
PY
""", timeout_seconds=15, memory_limit="128m", pids_limit=24)
            if not 1 <= pid_payload.get("pid_limit", 24) < 24:
                raise SandboxError("PID isolation probe did not reach the configured limit")
            checks["pid_limit_enforced"] = True

            overflow_output = root / "overflow-output"
            overflow_output.mkdir()
            failure_stage = "output_and_log_limit"
            output_probe = _probe(snapshot, data, overflow_output, """
python - <<'PY'
import json, os, sys
sys.stdout.write('HIGGSLAB_LOG_SENTINEL' * 400000)
sys.stdout.flush()
try:
    with open('/output/full', 'wb') as stream:
        stream.write(b'x' * (20 * 1024 * 1024))
except OSError:
    output_limited = True
    try:
        os.unlink('/output/full')
    except FileNotFoundError:
        pass
else:
    output_limited = False
    os.unlink('/output/full')
with open('/output/RESULT.json', 'w') as result:
    json.dump({'probe': True, 'output_limited': output_limited}, result)
PY
""", timeout_seconds=20, memory_limit="128m", pids_limit=24)
            if output_probe.get("output_limited") is not True:
                raise SandboxError("Sandbox did not enforce the output tmpfs limit")
            checks["output_and_log_limits_enforced"] = True

            valid_result = ('{"pois":[{"name":"mu","value":1.0,"stat":0.2,'
                            '"syst":0.1,"total":0.22360679775}],'
                            '"significance_obs":2.0,"discovery":false}')
            valid_output = root / "valid-output"
            valid_output.mkdir()
            failure_stage = "isolated_result_extraction"
            # Python's default site startup would import this file from /submission while
            # the trusted extractor is UID 0. A safe extractor must bypass cwd and site.
            (snapshot / "sitecustomize.py").write_text(
                "import os\n"
                "if os.getuid() == 0:\n"
                "    os.write(1, b'HIGGSLAB_ROOT_SITECUSTOMIZE_RAN')\n",
                encoding="utf-8", newline="\n",
            )
            _runner(snapshot, f"cat > /output/RESULT.json <<'EOF'\n{valid_result}\nEOF")
            run_in_docker(snapshot, data, valid_output, timeout_seconds=15,
                          memory_limit="128m", pids_limit=24)
            from higgslab.contract import validate_result
            validate_result(valid_output / "RESULT.json")
            checks["root_sitecustomize_not_executed"] = True
            checks["valid_result_collected"] = True
    except Exception as exc:
        # Do not copy subprocess output or user data into the reusable report.
        failure = type(exc).__name__
    else:
        failure = None
    finally:
        report = {
            "schema_version": 1,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fingerprint": isolation_fingerprint(),
            "image": DOCKER_IMAGE,
            "image_id": image_id,
            "limits": {
                "production": {"runtime_seconds": 600, "memory": "6g", "pids": 128,
                               "output_tmpfs": "16m", "stdout": "devnull",
                               "container_log_driver": "none"},
                "rehearsal": {"memory": "128m", "pids": 24,
                              "output_tmpfs": "16m", "stdout": "devnull",
                              "container_log_driver": "none",
                              "stdout_probe_bytes": 8 * 1024 * 1024},
            },
            "log_handling": "Student stdout/stderr are sent to DEVNULL; the container uses log-driver=none.",
            "checks": checks,
            "passed": all(checks.values()),
            "failure_type": failure if "failure" in locals() else "SandboxError",
            "failure_stage": failure_stage if "failure" in locals() and failure else None,
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
