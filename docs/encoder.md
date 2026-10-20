# MiniHEP event encoder path

Labeled examples tell a classifier which events are signal and which are background, but labels can be scarce or costly in a new task. Unlabeled examples still contain patterns: momenta, directions, and relationships between objects. **Pretraining** tries to learn those patterns first, so a later classifier can reuse them instead of learning everything from its labeled sample. Whether that reuse helps is a hypothesis to test.

MiniHEP demonstrates this idea with a small event encoder trained locally on the synthetic teaching sample. It maps each event to five object tokens (two leptons, two jet slots, and a MET proxy), learns to reconstruct hidden token features, then supplies a numerical event summary, or **embedding**, to a classifier. New to these terms? The [optional MiniHEP concepts primer](minihep-concepts.md) follows one toy event through the entire process; experienced readers can continue here.

## Pretrain, save, adapt, evaluate

1. **Pretrain once for reuse:** learn correlations from training events without their signal/background labels. The pretraining objective asks the encoder to reconstruct hidden object features.
2. **Save the representation and preprocessing:** the encoder's learned parameters and the training-only scaling statistics must travel together. Reusing parameters with different preprocessing changes what the encoder sees.
3. **Adapt to a labeled task:** train a classifier head while holding the encoder fixed (a frozen probe), or update both head and encoder (fine-tuning). This downstream objective uses labels to distinguish signal from background.
4. **Evaluate the measurement:** use the resulting scores to form templates and fit μ. Compare recovery, uncertainty, and calibration against the baseline. This scientific objective is different from both reconstruction and classification loss.

The commands below implement the existing end-to-end comparison. Each `train` call in these examples performs its own pretraining and adaptation, then saves a complete inference JSON containing model parameters and preprocessing; these commands do not share a pretraining checkpoint between modes. Saving a pretrained encoder separately for several adaptations is the reusable workflow described above. A final inference model and a reusable pretraining checkpoint serve different stages of that workflow.

## Run the comparison

Train the engineered-feature baseline, then compare the frozen and fine-tuned MiniHEP paths:

```bash
uv run higgslab train datasets/public output/model-classifier.json --mode classifier --epochs 4
uv run higgslab run datasets/public output/classifier-result --model output/model-classifier.json
uv run higgslab train datasets/public output/model.json --mode frozen --epochs 4
uv run higgslab run datasets/public output/frozen-result --model output/model.json
uv run higgslab train datasets/public output/model-finetuned.json --mode finetuned --epochs 4
uv run higgslab run datasets/public output/finetuned-result --model output/model-finetuned.json
```

The encoder uses a small model and a few epochs on this sample. It is a **foundation-model teaching prototype**, not a general pretrained collider model. No improvement in classification AUC, μ precision, or performance at larger scales is promised. Learned representations can also be useful in generative research, but current MiniHEP does not sample events. The [optional generation explanation](generative-modeling.md) describes the different objectives, architecture, and validation that would require; it adds no exercise.

## Fair comparison

Compare engineered features, frozen MiniHEP embeddings, and fine-tuned MiniHEP using the same public training/validation/template split, training budget, and fit configuration. Preprocessing uses training-only statistics. Padding masks distinguish absent jet tokens from present objects. Keep event identity and labels out of the unsupervised reconstruction inputs.

| Path | What is learned? | Questions |
| --- | --- | --- |
| Engineered features | A classifier on hand-built event variables. | Which variables carry useful separation? |
| Frozen MiniHEP | A probe head over embeddings from the pretrained encoder. | Are the learned representations useful without changing the encoder? |
| Fine-tuned MiniHEP | Encoder and classifier parameters for the labeled task. | Does task-specific training improve the measurement? |

## Exercise: present a useful negative result

Run the three modes with identical settings. Compare the diagnostic loss and any validation discrimination metrics, then score the same generated suite following the [model comparison guide](ablation.md). To evaluate your exported model through the editable submission, use the [classifier handoff instructions](classifier.md). If MiniHEP does not improve μ precision or calibration, explain plausible reasons: small data volume, short pretraining, objective mismatch, feature representation, or fit limitations. A well-supported negative result is a successful scientific outcome.

See the [physics bridge](physics.md) for four-vector and MET context and the [statistical fit](fit.md) for the common endpoint.

## Short low-label exercise

Load an instructor checkpoint and compare a frozen encoder with the feature
classifier using the same 10% labeled subset in the [low-label exercise](low-label.md).
A matched scratch/fine-tuned transformer comparison is an optional extension.
