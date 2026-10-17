"""Local hostile-container rehearsal. Hosted scoring stays disabled until this passes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .security import DOCKER_IMAGE, SandboxError, run_in_docker


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
    (snapshot / "run.sh").write_text("#!/bin/bash\nset -eu\n" + script + "\n", encoding="utf-8")


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
        "output_and_log_limits_enforced": False,
        "valid_result_collected": False,
    }
    safe_env = {"PATH": os.environ.get("PATH", "")}
    try:
        build = subprocess.run(
            ["docker", "build", "--tag", DOCKER_IMAGE, "--file", "evaluator/Dockerfile", "."],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600, env=safe_env,
        )
        if build.returncode:
            raise SandboxError("Could not build the local sandbox image")
        checks["docker_image_built"] = True
        with tempfile.TemporaryDirectory(prefix="higgslab-isolation-") as temporary:
            root = Path(temporary)
            snapshot = root / "snapshot"
            data = root / "data"
            output = root / "output"
            snapshot.mkdir(); data.mkdir(); output.mkdir()
            def fresh_output(name):
                destination = root / name
                destination.mkdir()
                return destination
            host_secret = root / "secret.txt"
            other_team = root / "other-team.txt"
            host_secret.write_text("HIGGSLAB_HOST_SECRET_SENTINEL", encoding="utf-8")
            other_team.write_text("HIGGSLAB_OTHER_TEAM_SENTINEL", encoding="utf-8")
            (data / "events.json").write_text("{\"input\":true}", encoding="utf-8")

            # A failed assertion means the container could observe a credential, host path,
            # another team's file, the network, or write to its pinned source tree.
            _runner(snapshot, f"""
python - <<'PY'
import os, socket, sys
assert not any('HIGGSLAB_HOST_SECRET_SENTINEL' in x for x in os.environ.values())
assert not any('HIGGSLAB_ISOLATION_SENTINEL' in k for k in os.environ)
assert not os.path.exists({str(host_secret)!r})
assert not os.path.exists({str(other_team)!r})
try:
    socket.create_connection(('1.1.1.1', 443), timeout=1)
except OSError:
    pass
else:
    raise SystemExit(21)
try:
    open('/submission/run.sh', 'a').write('# forbidden')
except OSError:
    pass
else:
    raise SystemExit(22)
open('/output/RESULT.json','w').write('{{"probe":true}}')
PY
""")
            os.environ["HIGGSLAB_ISOLATION_SENTINEL"] = "HIGGSLAB_HOST_SECRET_SENTINEL"
            try:
                run_in_docker(snapshot, data, output, timeout_seconds=15)
            finally:
                os.environ.pop("HIGGSLAB_ISOLATION_SENTINEL", None)
            checks["no_network_or_host_state_or_secrets"] = True
            checks["submission_snapshot_read_only"] = True

            _runner(snapshot, "ln -sf /etc/passwd /output/RESULT.json")
            try:
                run_in_docker(snapshot, data, fresh_output("symlink-output"), timeout_seconds=15)
            except SandboxError:
                checks["result_symlinks_rejected"] = True
            else:
                raise SandboxError("Sandbox accepted a symlinked result")

            _runner(snapshot, "sleep 4; exit 0")
            try:
                run_in_docker(snapshot, data, fresh_output("timeout-output"), timeout_seconds=1)
            except SandboxError as exc:
                checks["runtime_limit_enforced"] = "runtime limit" in str(exc).lower()
            else:
                raise SandboxError("Sandbox did not stop an over-time submission")

            _runner(snapshot, "yes HIGGSLAB_LOG_SENTINEL | head -c 8388608; dd if=/dev/zero of=/output/full bs=1M count=20 2>/dev/null")
            try:
                run_in_docker(snapshot, data, fresh_output("overflow-output"), timeout_seconds=15)
            except SandboxError:
                checks["output_and_log_limits_enforced"] = True
            else:
                raise SandboxError("Sandbox accepted output beyond the tmpfs limit")

            valid_result = '{"pois":[{"name":"mu","value":1.0,"stat":0.2,"syst":0.1,"total":0.22360679775}],"significance_obs":2.0,"discovery":false}'
            _runner(snapshot, f"cat > /output/RESULT.json <<'EOF'\n{valid_result}\nEOF")
            valid_output = fresh_output("valid-output")
            run_in_docker(snapshot, data, valid_output, timeout_seconds=15)
            result_path = valid_output / "RESULT.json"
            if not result_path.is_file() or result_path.is_symlink() or result_path.stat().st_size > 100_000:
                raise SandboxError("Sandbox did not safely collect a valid result")
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
            "checks": checks,
            "passed": all(checks.values()),
            "failure_type": failure if "failure" in locals() else "SandboxError",
        }
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
