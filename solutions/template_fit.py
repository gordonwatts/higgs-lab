"""Reference: use exactly the same seam as submission/analysis.py.

This is deliberately separate from the starter. Coarser bins may reduce finite
template noise while discarding shape information. Compare on a suite.
"""
from higgslab.templates import build
from higgslab.fit import fit

def measurement(events,pool,meta):
    templates=build(events,pool,meta,bins=([0,65,100,150,250,500],[0,40,75,120,350]))
    return fit(templates,background_unc=.10)
