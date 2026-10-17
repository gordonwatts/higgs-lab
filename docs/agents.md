# Optional coding-agent exercises

An AI coding assistant can help you inspect unfamiliar code or implement a small change. It is optional: every exercise can be completed by hand, and no exercise requires an API token. You may use OpenCode, another assistant, or an ordinary editor. Do not put tokens in notebooks, files, chat prompts, Git history, logs, or submissions.

Use one prompt at a time. Read the proposed diff, ask what assumptions it made, run the local checks yourself, and keep only changes you can explain.

## Optional OpenCode and NRP setup

The instructor should rehearse and record an OpenCode version for the cohort using the [official installation guide](https://docs.opencode.ai/docs/). After installation, check `opencode --version`, start it in your workshop checkout with `opencode`, and follow the [provider guide](https://opencode.ai/docs/providers/) to connect a provider you already have permission to use. Keep credentials in the tool's private credential store, outside this repository. No provider is required for the exercises below.

For NRP accounts, the [NRP API-access guide](https://nrp.ai/documentation/userdocs/ai/llm-managed/api-access/) explains group eligibility and access; the [NRP client configurations](https://nrp.ai/documentation/userdocs/ai/llm-managed/client-configs/) include OpenCode setup. Use the current model catalog and endpoint from those pages rather than copying an old workshop model name. The instructor supplies any approved account setup separately; never paste a token into a tutorial notebook, submission, issue comment, or agent prompt. If access is unavailable, continue manually with the same checks. For BinderHub notebooks, follow the host-specific persistence guidance in the [FAQ](faq.md#what-is-the-binder-data-directory-for).

## Prompt 1: inspect before editing

```text
Read docs/analysis.md and the relevant feature or fit function. Do not edit files yet.
Explain the inputs, outputs, units, and existing assumptions. Propose one small
change that could affect the measurement, and name a check that would reveal
whether it helped. Point out any possible train/validation leakage.
```

## Prompt 2: implement one component

```text
Implement only this change: [describe your chosen feature or fit variation].
Keep the shared result contract and data split unchanged. Do not add network
access or new dependencies. Explain the diff and tell me which command to run.
```

## Prompt 3: review the evidence

```text
Compare my baseline and changed outputs: [paste aggregate metrics only].
Separate classifier diagnostics from μ recovery and uncertainty calibration.
Explain what the evidence supports, what remains uncertain, and one plausible
reason the change did not help. Do not claim that synthetic data are ATLAS data.
```

Never paste private credentials, sealed evaluation data, per-event answers, or another student's private work into an assistant. Keep all implementation and verification local to your workshop repository.
