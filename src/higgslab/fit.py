"""Binned Poisson likelihood with a constrained background normalization."""
import numpy as np
from scipy.optimize import minimize, minimize_scalar, brentq

def fit(templates, background_unc=.10):
    n,s,b = (np.asarray(templates[k],dtype=float) for k in ('observed','signal','background'))
    if background_unc <= 0:
        raise ValueError('positive background constraint required')
    def nll(mu,beta):
        expectation = mu*s + beta*b
        if np.any(expectation <= 0):
            return 1e30 + float(np.minimum(expectation,0).dot(np.minimum(expectation,0)))
        return float(np.sum(expectation-n*np.log(expectation)) + .5*((beta-1)/background_unc)**2)
    opt = minimize(lambda p:nll(*p),[1.,1.],method='Nelder-Mead',options={'xatol':1e-9,'fatol':1e-9,'maxiter':4000})
    if not opt.success or not np.isfinite(opt.fun):
        raise RuntimeError('likelihood optimization failed')
    mu,beta = map(float,opt.x)
    expectation = mu*s+beta*b
    h = np.array([[np.sum(n*s*s/expectation**2),np.sum(n*s*b/expectation**2)],[np.sum(n*s*b/expectation**2),np.sum(n*b*b/expectation**2)+1/background_unc**2]])
    covariance = np.linalg.inv(h)
    def profile(x):
        lower = max(.000001, float(np.max(-x*s/b))+1e-8)
        optimum = minimize_scalar(lambda z:nll(x,z),bounds=(lower,max(lower+10,10)),method='bounded', options={'xatol':1e-10})
        return float(optimum.fun)
    # Delta NLL=0.5 endpoints, including nuisance profiling.
    scale = float(np.sqrt(covariance[0,0]))
    endpoints=[]
    for direction in (-1,1):
        width=scale
        for _ in range(30):
            edge=mu+direction*width
            if profile(edge)-opt.fun >= .5:
                break
            width*=2
        endpoints.append(brentq(lambda x:profile(x)-opt.fun-.5,min(mu,edge),max(mu,edge)))
    total=(endpoints[1]-endpoints[0])/2
    stat=min(total,float(1/np.sqrt(h[0,0])))
    syst=float(np.sqrt(max(0,total*total-stat*stat)))
    z=float(np.sqrt(max(0,2*(profile(0)-opt.fun)))) if mu>0 else 0.
    return {'pois':[{'name':'mu','value':mu,'stat':stat,'syst':syst,'total':total}], 'significance_obs':z,'discovery':bool(z>=5), 'nuisances':{'hww_bkg_norm':{'value':beta,'unc':float(np.sqrt(covariance[1,1]))}}, 'interval_mu':endpoints, 'schema':'submission-v1'}
