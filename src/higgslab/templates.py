"""Disjoint simulation templates normalized to expected process yields."""
import numpy as np
from .features import engineered

def build(events, pool, meta, scorer=None, bins=None):
    selected = pool['partition'] == 2
    mc = {k:v[selected] for k,v in pool.items()}
    if scorer is None:
        # Under/overflow are folded into edge bins, preserving every event.
        edges = bins or ([0,65,100,150,250,500], [0,40,75,120,350])
        def values(e):
            f = engineered(e)
            return f[:,[1,0]]
    else:
        edges = [np.linspace(0,1,9)] if bins is None else bins
        def values(e):
            score = np.asarray(scorer(e),dtype=float)
            if score.shape != (len(e['met_et']),) or not np.isfinite(score).all():
                raise ValueError('score must be one finite value per event')
            return score[:,None]
    def hist(e,weights=None):
        v = values(e).copy()
        for i,edge in enumerate(edges):
            v[:,i] = np.clip(v[:,i],edge[0],np.nextafter(float(edge[-1]),-np.inf))
        return np.histogramdd(v,bins=edges,weights=weights)[0].ravel()
    result = {'observed':hist(events)}
    for label,key,yield_key in ((1,'signal','signal_expected'),(0,'background','background_expected')):
        component = {k:v[mc['label']==label] for k,v in mc.items()}
        h = hist(component,component['weight'])
        # Half a typical simulation event per bin regularizes sparse MC tails.
        # Set before viewing data; tiny epsilon alone creates false discoveries
        # when a finite MC sample misses a valid background bin.
        h = h + .5*float(np.mean(component['weight']))
        result[key] = h/h.sum()*meta[yield_key]
    result['edges'] = [np.asarray(e).tolist() for e in edges]
    return result
