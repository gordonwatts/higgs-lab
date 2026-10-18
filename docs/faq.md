# FAQ and troubleshooting

## Do I need particle-physics experience?

No. The [physics bridge](physics.md) defines the terms used in the exercise, and the baseline commands work before you understand every observable. You can take the programming route first and return to the physics explanations as needed.

## Is this ATLAS data?

No. The current files are generated synthetic teaching data, not ATLAS data or a detector simulation. The [data page](data.md) explains the schema and what would be required for a real ROOT conversion.

## Do I need a GPU, API key, or coding agent?

No. CPU is supported, and all required exercises are manual. Agent prompts are optional and should not include tokens or private data.

## Why did a high AUC not improve μ?

AUC summarizes ranking across signal and background events. The fit also depends on yield modeling, score-bin population, background treatment, and uncertainty calibration. Compare generated-suite μ bias, precision, recovery slope, pull width, and failures; see [analysis map](analysis.md).

## The install or command failed. What should I check?

- Confirm Python is 3.12 and that you are in the repository root.
- Re-run `uv sync --extra ml --extra dev` after changing branches or pulling updates.
- Confirm the command uses paths that exist in this checkout, such as `datasets/public` and an output folder you can write.
- Read the first specific error and compare it with the command examples in [quickstart](setup.md).
- If the problem remains, send your instructor the command and relevant error text. Remove tokens and private paths first.

## What is the Binder `/data` directory for?

The optional Binder environment may mount persistent user storage at `/data`. Whether that mount exists, survives a session, or is backed up depends on the host configuration. Do not assume it is persistent: save important work to a Git fork or follow the host-specific instructions from your instructor. If `/data` is unavailable, use the local setup in [quickstart](setup.md).

For an NRP BinderHub workshop, the instructor should use the actual hub address and persistence instructions supplied by that deployment's administrator, then launch a fresh session and confirm that `/data` is mounted and survives the session behavior students will use. This repository does not publish an unverified BinderHub launch URL. The bundled Binder environment is an optional notebook environment; the local command-line path remains available.

## Can I submit from a private fork?

The hosted evaluator must fetch a public, pinned commit under the current submission contract. Ask your instructor for an approved alternative if your work cannot be public. Do not publish credentials or sensitive data.
