"""Aggregate-only score-v1 diagnostics and sealed-suite construction."""

from __future__ import annotations

import hashlib
import hmac
import math
import random
from statistics import mean, stdev


SUITE_SIZE = 30


def make_sealed_suite(secret: str) -> list[tuple[int, float, float]]:
    """Make deterministic (seed, mu, beta) cases without exposing truths."""
    if not secret:
        raise ValueError("Sealed seed is not configured")
    digest = hmac.new(secret.encode(), b"higgslab-suite-v1", hashlib.sha256).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    points = [(i, 0.0, rng.uniform(0.8, 1.2)) for i in range(10)]
    signal_mus = (0.5, 0.8, 1.0, 1.2, 1.5, 2.0)
    for i in range(10, SUITE_SIZE):
        points.append((i, rng.choice(signal_mus), rng.uniform(0.8, 1.2)))
    return [(_suite_seed(secret, i), mu, beta) for i, mu, beta in points]


def _suite_seed(secret: str, index: int) -> int:
    digest = hmac.new(secret.encode(), f"higgslab-suite-v1:{index}".encode(), hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big")


def _mu(result: dict) -> tuple[float, float]:
    poi = next((p for p in result.get("pois", []) if p.get("name") == "mu"), None)
    if poi is None:
        raise ValueError("Validated result is missing mu")
    return float(poi["value"]), float(poi["total"])


def _linear_fit(x: list[float], y: list[float]) -> tuple[float, float]:
    if len(x) < 2:
        return 0.0, mean(y) if y else 0.0
    xm, ym = mean(x), mean(y)
    denom = sum((a - xm) ** 2 for a in x)
    if denom == 0:
        return 0.0, ym
    slope = sum((a - xm) * (b - ym) for a, b in zip(x, y)) / denom
    return slope, ym - slope * xm


def _rms(values: list[float]) -> float:
    return math.sqrt(mean(v * v for v in values)) if values else 0.0


def summarize(results: list[dict], truths: list[float], *, baseline_results: list[dict] | None = None,
              total_cases: int | None = None, min_valid_fraction: float = 0.8) -> dict:
    """Compute score-v1 diagnostics, reporting no per-case values or truths."""
    if len(results) != len(truths):
        raise ValueError("Results and truth values must have equal length")
    total = total_cases if total_cases is not None else len(results)
    if total < len(results) or total < 1:
        raise ValueError("total_cases must cover the nonempty suite")
    if not results:
        return {
            "n": 0, "total_cases": total, "failures": total, "recovery_fraction": 0.0,
            "mu_mean": 0.0, "mu_bias": 0.0, "mu_recovery_slope": 0.0,
            "mu_recovery_intercept": 0.0, "pull_mean": 0.0, "pull_width": 0.0,
            "mu_rms_residual": 0.0, "baseline_rms_residual": 0.0, "mu_precision": 0.0,
            "false_discovery_rate": 1.0, "discovery_power": 0.0,
            "score": 0.0, "rankable": False,
        }
    pairs = [_mu(r) for r in results]
    mus = [p[0] for p in pairs]
    sigmas = [p[1] for p in pairs]
    residuals = [value - truth for value, truth in zip(mus, truths)]
    pulls = [residual / sigma for residual, sigma in zip(residuals, sigmas)]
    slope, intercept = _linear_fit(truths, mus)
    null_indices = [i for i, truth in enumerate(truths) if truth == 0]
    signal_indices = [i for i, truth in enumerate(truths) if truth >= 1.5]
    false_discovery = mean(1.0 if results[i].get("discovery", False) else 0.0 for i in null_indices) if null_indices else 1.0
    discovery_power = mean(1.0 if results[i].get("discovery", False) else 0.0 for i in signal_indices) if signal_indices else 0.0
    baseline_rms = 0.0
    if baseline_results is not None:
        if len(baseline_results) != len(results):
            raise ValueError("Baseline results must align with valid submitted results")
        baseline_mus = [_mu(r)[0] for r in baseline_results]
        baseline_rms = _rms([v - t for v, t in zip(baseline_mus, truths)])
    rms = _rms(residuals)
    pull_width = stdev(pulls) if len(pulls) > 1 else 0.0
    honesty = min(pull_width, 1.0 / pull_width) if pull_width > 0 and math.isfinite(pull_width) else 0.0
    precision = baseline_rms / rms if baseline_rms > 0 and rms > 0 else 0.0
    recovery = len(results) / total
    valid_enough = recovery >= min_valid_fraction
    calibration_ok = 0.0 < pull_width < math.inf and abs(mean(pulls)) <= 1.0
    gates = valid_enough and slope > 0.2 and false_discovery <= 0.2 and calibration_ok and rms > 0
    score = 100.0 * precision * honesty * recovery if gates else 0.0
    return {
        "n": len(results), "total_cases": total, "failures": total - len(results),
        "recovery_fraction": recovery,
        "mu_mean": mean(mus), "mu_bias": mean(residuals),
        "mu_recovery_slope": slope, "mu_recovery_intercept": intercept,
        "pull_mean": mean(pulls), "pull_width": pull_width,
        "mu_rms_residual": rms, "baseline_rms_residual": baseline_rms,
        "mu_precision": mean(sigmas), "false_discovery_rate": false_discovery,
        "discovery_power": discovery_power, "honesty": honesty,
        "precision_ratio": precision, "score": score, "rankable": bool(gates),
    }
