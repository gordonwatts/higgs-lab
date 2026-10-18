# submission-v1

Submit a public GitHub repository and full 40-hex commit SHA. Only `submission/` executes. `submission/run.sh DATASET OUTPUT` must exit 0 and write regular, non-symlink `OUTPUT/RESULT.json`, less than 100 kB. Fix random seeds; repeat results exactly. No network; runtime includes Python 3.12, trusted higgslab, NumPy/SciPy and CPU PyTorch. Inference weights travel as JSON with code; no pickle or model executables. The evaluator applies a 600 second timeout, 6 GB memory, CPU/PID/file/output limits. See evaluator/security.py for exact snapshot restrictions (5 MB/file, 50 MB total, no symlinks/data/truth/binary models).

```json
{"pois":[{"name":"mu","value":1.0,"stat":0.1,"syst":0.0,"total":0.1}],"significance_obs":2.0,"discovery":false}
```

All numeric fields must be finite JSON numbers (booleans are not numbers). Total uncertainty must be positive and match `hypot(stat,syst)`; components nonnegative. Optional mH follows the same shape. Parameters cannot be duplicated. Discovery is a boolean, significance nonnegative. Baseline uses Z≥5 as its discovery rule. Signed fitted mu is allowed to avoid truncation bias at the null; significance is one-sided. Optional nuisance values and extra diagnostic keys do not affect scoring.

Issue syntax: `team-name: https://github.com/OWNER/FORK @ FULL_SHA`. Parser/version, immutable SHA validation, isolation and result validation apply before scoring. Latest submission per team counts, with previous attempts retained. Teams own their name through the authenticated commenter identity. No student code is imported by the trusted orchestration process.
