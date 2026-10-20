# Physics bridge: what is being measured?

This page supplies enough physics vocabulary to understand the exercise. You can treat the provided event fields as structured numerical inputs while learning the analysis, then return here when you want the physical interpretation.

## From Higgs boson to event record

The exercise is inspired by the decay chain H → W⁺W⁻ → ℓνℓν. Each W boson can decay to a charged lepton (an electron or muon, written ℓ) and a neutrino (ν). Neutrinos pass through the detector without being directly recorded. Their presence is inferred from missing transverse momentum, commonly called MET. Jets are groups of particles reconstructed from quarks or gluons.

An **event** is one recorded or simulated collision candidate. A **signal** event is generated under the Higgs process of interest; a **background** event arises from another process that can resemble it. A classifier tries to separate the two, but the final analysis must account for how many events are expected and how signal-like their measured properties are.

!!! warning "Simulation and weights"
    In a real analysis, simulated events are weighted to represent expected yields for a stated integrated luminosity, selection, and physics model. Weights are not interchangeable with event counts. HiggsLab's current data use simplified synthetic yields and labels; their values teach the mechanics and have no ATLAS provenance.

## One synthetic event

Here is an invented example in the same `dataset-v1` format as the teaching data. It illustrates one row, not an observed collision or a physically complete simulation.

| Object or slot | `pt` or MET magnitude (GeV) | `eta` | `phi` (radians) | Event-table fields |
| --- | --- | --- | --- | --- |
| Lepton 0: positively charged electron | 45 | 0.3 | 0.4 | `lep_pt_0`, `lep_eta_0`, `lep_phi_0`; `lep_charge_0 = 1`, `lep_type_0 = 11` |
| Lepton 1: negatively charged muon | 30 | −0.6 | 1.1 | `lep_pt_1`, `lep_eta_1`, `lep_phi_1`; `lep_charge_1 = -1`, `lep_type_1 = 13` |
| Jet 0: present | 55 | 1.2 | −2.0 | `jet_pt_0`, `jet_eta_0`, `jet_phi_0` |
| Jet 1: absent, zero padding | 0 | 0 | 0 | `jet_pt_1`, `jet_eta_1`, `jet_phi_1` |
| Missing transverse momentum (MET) | 40 | Not measured | −0.8 | `met_et`, `met_phi` |

The beam travels along one axis. **`pt` (transverse momentum)** describes motion across that axis, rather than along it. **`eta` (pseudorapidity)** describes direction relative to the beam: zero means sideways, and larger absolute values mean closer to either beam direction. **`phi` (azimuth)** is the angle around the beam. Momentum magnitudes use GeV in this dataset; `eta` is dimensionless and `phi` uses radians.

This event has `jet_n = 1`. Other rows can have zero or two jets. An absent slot's zeros are placeholders, not an extra physical object. MET has only a magnitude and a transverse direction: the table does not supply its longitudinal momentum. The [optional MiniHEP primer](minihep-concepts.md) follows this same event into five model input slots. Details of the optional ROOT conversion, including its units and missing-object convention, belong on the [data page](data.md#adapting-a-root-source-responsibly).

## Four-vectors and useful observables

A particle's **four-vector** records energy and three components of momentum. The tutorial constructs approximate four-vectors from the leptons' and jets' `pt`, `eta`, and `phi`, treating their masses as zero. You do not need to reconstruct a full collision to use these numerical inputs.

The **dilepton invariant mass** mℓℓ combines the two charged lepton four-vectors into a mass for the pair. In our example, that uses the electron and muon; it excludes the unobserved neutrinos. Their individual momenta along the beam are unknown, so we cannot reconstruct the full Higgs mass from this event record. The **transverse mass** mT instead combines the lepton pair's transverse information with MET. It gives a useful summary using the part of the momentum balance we can access. These observables carry signal/background information even though neither is a complete description of the decay.

## Signal strength μ

The parameter μ scales the predicted signal yield relative to a reference prediction. μ = 0 means no signal contribution in the simplified fit; μ = 1 means the nominal reference yield; μ above one means an excess over that reference. The fit compares observed and expected event counts in bins while accounting for background normalization and statistical fluctuations.

The reported **uncertainty** describes the fit's expected spread under its model assumptions. A useful procedure checks both recovery (does the fitted μ follow injected μ?) and calibration (do the quoted uncertainties match the observed spread?). A small uncertainty on one sample is not enough evidence by itself.

## Physics and computer science meet

The exercise makes an important bridge: classification is an intermediate representation, while the measurement is the scientific outcome. Feature engineering, learned embeddings, and classifier scores can all help organize events. A binned likelihood then asks how compatible the observed counts are with different signal strengths and background values. See the [analysis map](analysis.md) for the full chain and the [fit page](fit.md) for the statistical interpretation.
