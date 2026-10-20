# Optional background: could MiniHEP generate events?

This is an explanation, not a workshop assignment. No implementation, compute run, or student deliverable is required. Return to the [encoder lesson](encoder.md) for the existing exercises.

## Why generation can be useful

A generative model learns to produce representative new examples. In particle physics, carefully validated generated samples can help explore event distributions or act as a surrogate for parts of expensive simulation. A useful generator must capture relationships between quantities, not just make each quantity's histogram look plausible. Its usefulness depends on its purpose and validation.

Learning a reusable representation is a foundation-model idea; generation is one possible use, not a property every foundation model has. A training objective and model design must explicitly support sampling.

## What MiniHEP currently does

MiniHEP uses a transformer encoder over five fixed slots: two leptons, two jets, and a MET proxy. It hides valid whole-object four-vectors and trains a deterministic reconstruction prediction with mean-squared error on their scaled components. Randomly choosing masks makes training varied; it does not define a probability distribution over complete events or an event-sampling procedure. At inference, a pooled embedding feeds a classification head.

For the [primer's toy event](minihep-concepts.md), predicting the hidden muon's features from the visible objects is a reconstruction task. One squared-error prediction does not describe the full range or probability of possible muons, much less sample an entire collision. The current reconstruction output is not a calibrated event generator, and the current checkpoint does not sample full events.

## What an extension would require

1. **Choose a generative formulation.** An autoregressive model could sample event components successively, conditioned on earlier ones. A diffusion approach could learn to turn noisy inputs into event samples. These are examples, not a proposed implementation or evidence that either works for MiniHEP.
2. **Design compatible training and sampling.** Introduce a stochastic generative objective and a compatible decoder or architecture adaptation. Define which properties condition a sample, how zero, one, or two jets (or other multiplicities) are represented, and how padding differs from physical objects. Define a sampling interface, including how randomness is supplied and how outputs become valid event-table fields. Reusing learned representations is a research possibility; adding a small head to the present checkpoint is not enough to establish a generator.
3. **Validate for a stated scientific use.** Check kinematic distributions and correlations, physical constraints and conservation conventions, rare tails, and the treatment of uncertainty. Test closure: does the method recover known quantities when the answer is controlled? Then check effects on downstream templates, fits, signal-strength recovery, and uncertainty calibration. Passing a few one-dimensional histogram checks is insufficient for scientific use.

A limited prototype could be a separate future project. A scientifically usable generator would require a substantial research and software extension, with broader validation than a short workshop exercise. There is no claim here about required runtime, staffing, or eventual measurement improvement.

## Keep provenance visible

The current sample is a synthetic teaching surrogate, not ATLAS data or a detector simulation. Examples generated from a model trained on it would remain derived teaching examples. They must not be represented as ATLAS events, independent Monte Carlo samples, or guaranteed improvements to measurement precision. Generating more rows does not create independent physical information or remove uncertainty in the training sample and model. See [data and provenance](data.md).
