# Physics bridge: what is being measured?

This page supplies enough physics vocabulary to understand the exercise. You can treat the provided event fields as structured numerical inputs while learning the analysis, then return here when you want the physical interpretation.

## From Higgs boson to event record

The exercise is inspired by the decay chain H → W⁺W⁻ → ℓνℓν. Each W boson can decay to a charged lepton (an electron or muon, written ℓ) and a neutrino (ν). Neutrinos pass through the detector without being directly recorded. Their presence is inferred from missing transverse momentum, commonly called MET. Jets are groups of particles reconstructed from quarks or gluons.

An **event** is one recorded or simulated collision candidate. A **signal** event is generated under the Higgs process of interest; a **background** event arises from another process that can resemble it. A classifier tries to separate the two, but the final analysis must account for how many events are expected and how signal-like their measured properties are.

!!! warning "Simulation and weights"
    In a real analysis, simulated events are weighted to represent expected yields for a stated integrated luminosity, selection, and physics model. Weights are not interchangeable with event counts. HiggsLab's current data use simplified synthetic yields and labels; their values teach the mechanics and have no ATLAS provenance.

## Four-vectors and useful observables

A particle's four-vector records energy and three-momentum. The reduced course ROOT tree stores `pt` and MET in GeV and `lep_E`/`jet_E` in MeV; the optional converter preserves the already-GeV `pt`/MET and ignores the energy branches for a massless reconstruction. Missing jet slots use `pt = -7` and are converted to zero padding. The HiggsLab synthetic `dataset-v1` schema uses `pt`, pseudorapidity `eta`, and azimuth `phi` with toy values in GeV. These conventions must be handled explicitly; the converter never divides source `pt` or MET by 1000. See [data and provenance](data.md) before using the optional ROOT path.

The **dilepton invariant mass** mℓℓ combines the two charged lepton four-vectors. The **transverse mass** mT uses transverse information and the missing momentum; it is useful when neutrinos prevent reconstructing the full Higgs mass. These observables are deliberately incomplete but carry signal/background information.

## Signal strength μ

The parameter μ scales the predicted signal yield relative to a reference prediction. μ = 0 means no signal contribution in the simplified fit; μ = 1 means the nominal reference yield; μ above one means an excess over that reference. The fit compares observed and expected event counts in bins while accounting for background normalization and statistical fluctuations.

The reported **uncertainty** describes the fit's expected spread under its model assumptions. A useful procedure checks both recovery (does the fitted μ follow injected μ?) and calibration (do the quoted uncertainties match the observed spread?). A small uncertainty on one sample is not enough evidence by itself.

## Physics and computer science meet

The exercise makes an important bridge: classification is an intermediate representation, while the measurement is the scientific outcome. Feature engineering, learned embeddings, and classifier scores can all help organize events. A binned likelihood then asks how compatible the observed counts are with different signal strengths and background values. See the [analysis map](analysis.md) for the full chain and the [fit page](fit.md) for the statistical interpretation.
