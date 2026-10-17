"""Public known-truth suite diagnostics; never used to publish sealed truth."""
import json
import subprocess
from pathlib import Path
import numpy as np
from .data import generate_dataset
from .pipeline import run

def score_local(output='output/suite',count=12,seed=71,model=None,submission=None):
    if count<6:
        raise ValueError('use at least six cases for calibration diagnostics')
    if model is not None and submission is not None:
        raise ValueError('choose a saved model or your submission entrypoint')
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed)
    rows=[]
    for i in range(count):
        mu=0. if i%4==0 else float(rng.uniform(.5,2))
        beta=float(rng.normal(1,.07))
        data=output/f'case_{i:03d}'
        truth=generate_dataset(data,seed+i,mu,beta)
        try:
            if submission is None:
                result=run(data,data/'fit',model)
            else:
                from .check import check_submission
                result=check_submission(submission,data,data/'student-fit')
            p=result['pois'][0]
            rows.append({'truth':truth,'value':p['value'],'unc':p['total'],'discovery':result['discovery'],'success':True})
        except (OSError,ValueError,RuntimeError,np.linalg.LinAlgError,subprocess.SubprocessError) as exc:
            rows.append({'truth':truth,'success':False,'error':str(exc)})
    good=[r for r in rows if r['success'] and r['truth']['mu']>0]
    x=np.array([r['truth']['mu'] for r in good]); y=np.array([r['value'] for r in good]); u=np.array([r['unc'] for r in good])
    null=[r for r in rows if r['success'] and r['truth']['mu']==0]
    strong=[r for r in rows if r['success'] and r['truth']['mu']>=1.5]
    metrics={'schema':'score-v1','count':count,'failures':sum(not r['success'] for r in rows),'recovery':sum(r['success'] for r in rows)/count,'bias':float(np.mean(y-x)) if len(x) else None,'mean_pull':float(np.mean((y-x)/u)) if len(x) else None,'slope':float(np.polyfit(x,y,1)[0]) if len(x)>1 else None,'pull_width':float(np.std((y-x)/u,ddof=1)) if len(x)>1 else None,'precision_rms':float(np.sqrt(np.mean((y-x)**2))) if len(x) else None,'mean_uncertainty':float(np.mean(u)) if len(x) else None,'false_discovery_rate':sum(r['discovery'] for r in null)/len(null) if null else None}
    metrics['discovery_power']=sum(r['discovery'] for r in strong)/len(strong) if strong else None
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
    (output/'local_truth_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(9,4))
    axes[0].errorbar(x,y,yerr=u,fmt='o'); axes[0].plot([0,2.2],[0,2.2],'k--'); axes[0].set(xlabel='Injected mu',ylabel='Recovered mu',title='Recovery (public local suite)')
    axes[1].hist((y-x)/u,bins=np.linspace(-4,4,13)); axes[1].set(xlabel='(Recovered - injected) / uncertainty',ylabel='Cases',title='Pulls: target mean 0, width 1')
    fig.tight_layout(); fig.savefig(output/'diagnostics.png'); plt.close(fig)
    interpretation='Bias should be near zero, slope near one and pull width near one. Smaller RMS is useful only alongside calibration and low failures. Small suites have noisy estimates; use 50+ cases before making a claim. A zero false-discovery fraction in a small null sample is not a precision bound. Finite-template effects can broaden pulls.'
    (output/'interpretation.txt').write_text(interpretation+'\n')
    metrics['interpretation']=interpretation
    return metrics
