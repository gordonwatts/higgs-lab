"""submission-v1: strict finite JSON measurements, never pickle."""
import json
import math
from pathlib import Path

def validate_result(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 100_000:
        raise ValueError("RESULT.json must be a regular file under 100 kB")
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    result = json.loads(path.read_text(), object_pairs_hook=unique_pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    def inspect(value):
        if isinstance(value,dict):
            for item in value.values(): inspect(item)
        elif isinstance(value,list):
            for item in value: inspect(item)
        elif isinstance(value,float) and not math.isfinite(value):
            raise ValueError('nonfinite number')
    inspect(result)
    if not isinstance(result,dict):
        raise ValueError('result must be a JSON object')
    def finite(x):
        return type(x) in (int, float) and math.isfinite(x)
    pois = result.get("pois")
    if not isinstance(pois, list) or not pois:
        raise ValueError("pois must contain mu")
    names = set()
    for poi in pois:
        if not isinstance(poi,dict):
            raise ValueError('each parameter must be an object')
        name = poi.get("name")
        if name not in ("mu", "mH") or name in names:
            raise ValueError("unknown or duplicate parameter")
        names.add(name)
        if not all(finite(poi.get(k)) for k in ("value", "stat", "syst", "total")):
            raise ValueError("parameter values must be finite numbers")
        if poi["stat"] < 0 or poi["syst"] < 0 or poi["total"] <= 0:
            raise ValueError("uncertainties must be nonnegative, total positive")
        if not math.isclose(math.hypot(poi["stat"],poi["syst"]),poi["total"],rel_tol=1e-5,abs_tol=1e-8):
            raise ValueError("total must equal stat and syst in quadrature")
    if "mu" not in names or not finite(result.get("significance_obs")) or result["significance_obs"] < 0 or type(result.get("discovery")) is not bool:
        raise ValueError("mu, nonnegative significance_obs and boolean discovery required")
    return result
