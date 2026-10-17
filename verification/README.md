# Live Docker verification — 2026-10-17

These reports are evidence from actual Linux containers on Docker Desktop,
not mocked subprocess tests. Inputs were publicly defined synthetic samples.
They contain no workshop seed, credentials, or sealed evaluation results.

| Report | Outcome |
| --- | --- |
| [docker-isolation.json](docker-isolation.json) | All 10 hostile and positive-control checks passed; includes the tested implementation fingerprint and image ID. |
| [docker-paths.json](docker-paths.json) | Starter, classifier, frozen encoder and fine-tuned encoder each completed 30 cases and two byte-identical public repeats: 128 successful analysis runs. Public input hashes were unchanged. |
| [runtime-images.json](runtime-images.json) | The first build and the rebuild with a restricted build context had identical trusted Python source hashes and installed dependency versions. |

The hostile resource probes used a 128 MiB memory cap, 24-process cap and a
one-second timeout to test enforcement without exhausting the host. Production
defaults remain 6 GiB, 128 processes and 600 seconds per case. Both use a 16 MiB
output tmpfs. Student stdout/stderr are discarded; there is no retained Docker
log or claimed byte quota on discarded stdout. No rehearsal containers remained
after cleanup.

A published full commit was also fetched and run through the actual evaluator,
and the six-case controlled local submission command passed. These checks do
not establish GitHub issue/Actions/Pages orchestration or BinderHub availability,
nor do they prove protection against every possible container escape. Hosted
submissions remain closed until the separate workshop deployment rehearsal.

Reproduce from the repository root with a running Linux-container Docker engine:

```bash
uv run higgslab instructor isolation-check --report output/isolation-report.json
uv run python scripts/verify_container_paths.py --output output/docker-live --count 30
uv run python -m evaluator score-local --submission submission
```

Rerun the rehearsal on the intended scoring host before opening a workshop.
Historical reports do not replace that host-specific check.
