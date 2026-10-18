# MiniHEP event encoder path

MiniHEP is a small event-encoder teaching prototype. It maps an event to five object tokens (two leptons, two jet slots, and a MET proxy), learns to reconstruct masked token features, then supplies embeddings to a classifier. The tutorial compares a supervised model, a frozen-encoder probe, and a fine-tuned encoder.

```bash
uv run higgslab train datasets/public output/model.json --mode frozen --epochs 4
uv run higgslab run datasets/public output/frozen-result --model output/model.json
uv run higgslab train datasets/public output/model-finetuned.json --mode finetuned --epochs 4
```

The encoder uses a small model and a few epochs on this sample. It is a **foundation-model teaching prototype**, not a general pretrained collider model. Masked reconstruction is a pretraining objective, not a measurement objective. A useful analysis continues through the supervised probe, templates, and μ fit.

## Fair comparison

Compare engineered features, frozen MiniHEP embeddings, and fine-tuned MiniHEP using the same public training/validation/template split, training budget, and fit configuration. Preprocessing uses training-only statistics. Padding masks distinguish absent jet tokens from present objects. Keep event identity and labels out of the unsupervised reconstruction inputs.

| Path | What is learned? | Questions |
| --- | --- | --- |
| Engineered features | A classifier on hand-built event variables. | Which variables carry useful separation? |
| Frozen MiniHEP | A probe head over embeddings from the pretrained encoder. | Are the learned representations useful without changing the encoder? |
| Fine-tuned MiniHEP | Encoder and classifier parameters for the labeled task. | Does task-specific training improve the measurement? |

## Exercise: present a useful negative result

Run the three modes with identical settings. Compare the diagnostic loss and any validation discrimination metrics, then score the same generated suite. If MiniHEP does not improve μ precision or calibration, explain plausible reasons: small data volume, short pretraining, objective mismatch, feature representation, or fit limitations. A well-supported negative result is a successful scientific outcome.

See the [physics bridge](physics.md) for four-vector and MET context and the [statistical fit](fit.md) for the common endpoint.
