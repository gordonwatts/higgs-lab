"""Choose ONE seam. Copy your finished implementation into submission/."""
from higgslab.features import engineered
from higgslab.templates import build
from higgslab.fit import fit

def features(events):
    # Exercise: add one useful observable; explain its units and physics.
    return engineered(events)

def templates(events, pool, meta):
    # Exercise: change one mass bin edge; compare a local suite before/after.
    return build(events,pool,meta)

def measurement(templates):
    # Exercise: vary the background constraint and check pull calibration.
    return fit(templates,background_unc=.10)
