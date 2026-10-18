# MiniHEP concepts: one event through the model

This optional background page explains the [encoder exercise](encoder.md). It adds no required task or computation. MiniHEP demonstrates a foundation-model approach: learn a reusable representation before adapting it to a labeled task. Here the model is small and trained locally on synthetic teaching data; it is not a general pretrained collider model.

## 1. Turn one event into five tokens

Use the [synthetic event in the physics bridge](physics.md#one-synthetic-event): an electron with `pt = 45`, a muon with `pt = 30`, one jet with `pt = 55`, an absent second jet, and MET of 40 GeV. A **token** is one object's numerical input to the model, rather like one item in a short sequence. Each slot has a fixed meaning:

| Slot | What our event contributes |
| --- | --- |
| Lepton 0 | Electron momentum from `pt = 45`, `eta = 0.3`, `phi = 0.4` |
| Lepton 1 | Muon momentum from `pt = 30`, `eta = -0.6`, `phi = 1.1` |
| Jet 0 | Present jet momentum from `pt = 55`, `eta = 1.2`, `phi = -2.0` |
| Jet 1 | Zero padding, marked absent |
| MET proxy | Transverse missing momentum from `met_et = 40`, `met_phi = -0.8` |

The feature code turns each present object's fields into four numbers `(px, py, pz, E)`, using a massless approximation. MET gets a transverse proxy with `pz = 0` and `E = met_et`; this is a bookkeeping input, not a measured neutrino four-vector. Training-only scaling brings these numbers onto manageable numerical scales. The current tokens use kinematics and slot identity; the electron/muon type and charge help describe the event but are not additional token components.

A **padding mask** tells the model that jet 1 is absent. It must not treat the placeholder as a real jet. The encoder can relate each present token to the other tokens through attention: for example, it can learn that the two lepton directions together carry information that neither direction contains alone.

## 2. Hide an object and learn to reconstruct it

During **masked-reconstruction pretraining**, suppose we hide our muon's four input numbers. The model sees the electron, present jet, MET proxy, and a marker for the hidden muon slot. It predicts the hidden numbers, and training penalizes their squared differences from the original scaled inputs. Many events and different hidden slots provide practice at learning correlations.

The original event supplies the target, so this stage does not need a signal/background label. A hidden, present muon is different from the absent jet: the muon is a reconstruction target; padding is excluded. The code hides whole valid object vectors, not selected scalar components. The objective teaches a useful representation only if the learned correlations also matter for the later task; low reconstruction error alone does not establish that.

## 3. Summarize the event as an embedding

After pretraining, give the encoder our full event with no deliberately hidden tokens. Each present slot receives a learned numerical state informed by the other objects. Averaging the valid states produces a 32-number **embedding** for this event. The absent jet is left out of the average.

An embedding is a compressed description, not a signal label or a reconstructed Higgs mass. Save encoder parameters together with their preprocessing state so future events are described consistently. Other events get different embeddings from the same encoder.

## 4. Train a frozen probe using labels

Attach a small classifier, called a **head**, to the embedding. Now use the training sample's signal/background labels to train the head while leaving the encoder unchanged. This is a **frozen probe**: it asks whether the representation already contains information useful for classification.

For our event, the head maps its 32-number summary to one signal-like score. It cannot recover details discarded by the fixed encoder. The score is still an intermediate analysis output; it is not the signal strength μ.

## 5. Fine-tune and evaluate the scientific result

In **fine-tuning**, label-based classification training can update both encoder and head. Our event's embedding can therefore change to emphasize distinctions relevant to the signal/background task. This flexibility may help, but can also overfit a small labeled sample.

Compare both approaches with the engineered-feature classifier using the same splits and evaluation settings. Their scores feed templates and a μ fit. Reconstruction loss tests the pretraining task; classification diagnostics test label prediction; recovery, uncertainty, and calibration test the measurement. None guarantees success at the next stage.

Return to the [encoder commands and comparison](encoder.md#run-the-comparison). For an optional explanation of why reconstructing a hidden muon does not make MiniHEP an event generator, read [generative modeling](generative-modeling.md).
