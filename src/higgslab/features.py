"""Physics features and the one canonical five-token conversion, in GeV."""
import numpy as np

FEATURE_NAMES = ["mll", "mt", "ptll", "dphi_ll", "met", "jet_n"]

def tokens(events):
    n = len(events["met_et"])
    result = np.zeros((n, 5, 4), dtype=np.float32)
    for slot, prefix in enumerate(("lep_0", "lep_1", "jet_0", "jet_1")):
        kind, index = prefix.split("_")
        pt, eta, phi = (np.asarray(events[f"{kind}_{x}_{index}"]) for x in ("pt", "eta", "phi"))
        result[:, slot] = np.stack((pt*np.cos(phi), pt*np.sin(phi), pt*np.sinh(eta), pt*np.cosh(eta)), axis=-1)
    pt, phi = events["met_et"], events["met_phi"]
    result[:, 4] = np.stack((pt*np.cos(phi), pt*np.sin(phi), np.zeros(n), pt), axis=-1)
    return result

def token_mask(events):
    n = len(events["met_et"])
    mask = np.ones((n, 5), dtype=bool)
    mask[:, 2] = events["jet_n"] >= 1
    mask[:, 3] = events["jet_n"] >= 2
    return mask

def engineered(events):
    v = tokens(events)[:, :2].sum(axis=1).astype(float)
    mll = np.sqrt(np.maximum(0, v[:, 3]**2 - np.sum(v[:, :3]**2, axis=1)))
    ptll = np.hypot(v[:, 0], v[:, 1])
    met = events["met_et"]
    px = met*np.cos(events["met_phi"])
    py = met*np.sin(events["met_phi"])
    mt = np.sqrt(np.maximum(0, (np.sqrt(mll*mll + ptll*ptll)+met)**2 - (v[:,0]+px)**2 - (v[:,1]+py)**2))
    dphi = np.abs(np.arctan2(np.sin(events["lep_phi_0"]-events["lep_phi_1"]), np.cos(events["lep_phi_0"]-events["lep_phi_1"])))
    return np.column_stack((mll, mt, ptll, dphi, met, events["jet_n"]))
