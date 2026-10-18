import json
import shutil
import numpy as np
import pytest
import torch

from higgslab.models import MiniHEP, MiniHEPClassifier
from higgslab.training import _fit_classifier
from higgslab.training import score, train
from higgslab.training import select_labeled_subset, pretrain_checkpoint, load_encoder_checkpoint


def _synthetic_pool(path):
    n = 30
    rng = np.random.default_rng(5)
    pool = {
        "lep_pt_0": rng.uniform(20, 80, n), "lep_pt_1": rng.uniform(15, 60, n),
        "lep_eta_0": rng.normal(0, 1, n), "lep_eta_1": rng.normal(0, 1, n),
        "lep_phi_0": rng.uniform(-3.14, 3.14, n), "lep_phi_1": rng.uniform(-3.14, 3.14, n),
        "jet_pt_0": rng.uniform(20, 70, n), "jet_pt_1": rng.uniform(20, 70, n),
        "jet_eta_0": rng.normal(0, 1, n), "jet_eta_1": rng.normal(0, 1, n),
        "jet_phi_0": rng.uniform(-3.14, 3.14, n), "jet_phi_1": rng.uniform(-3.14, 3.14, n),
        "jet_n": np.tile([0, 1, 2], 10),
        "met_et": rng.uniform(10, 100, n), "met_phi": rng.uniform(-3.14, 3.14, n),
        "lep_charge_0": np.ones(n), "lep_charge_1": -np.ones(n),
        "lep_type_0": rng.choice([11, 13], n), "lep_type_1": rng.choice([11, 13], n),
        "label": np.tile([0, 1], 15), "weight": np.ones(n),
        "process": np.where(np.tile([0, 1], 15) == 1, 345324, 363492),
        "event_id": np.arange(n), "partition": np.repeat([0, 1, 2], [20, 5, 5]),
    }
    for jet in (0, 1):
        absent = pool["jet_n"] <= jet
        for component in ("pt", "eta", "phi"):
            pool[f"jet_{component}_{jet}"][absent] = 0.0
    (path / "mc").mkdir(parents=True)
    (path / "data").mkdir()
    np.savez(path / "mc" / "pool.npz", **pool)
    from higgslab.data import _events
    observed = _events(rng,2,signal=True)
    observed["event_id"] = np.array([1000, 1001])
    np.savez(path / "data" / "events.npz", **observed)
    (path / "mc" / "pool_meta.json").write_text(json.dumps({
        "signal_expected": 15.0, "background_expected": 15.0,
    }))
    return pool


def test_supervised_exports_portable_finite_scores(tmp_path):
    pool = _synthetic_pool(tmp_path / "dataset")
    model_path = train(tmp_path / "dataset", tmp_path / "model.json", "classifier", epochs=1)
    repeated_path = train(tmp_path / "dataset", tmp_path / "repeat.json", "classifier", epochs=1)
    assert model_path.read_bytes() == repeated_path.read_bytes()
    payload = json.loads(model_path.read_text())
    assert payload["format"] == "higgslab-model-v1"
    assert payload["mode"] == "supervised"
    events = {name: values for name, values in pool.items()
              if name not in {"label", "weight", "event_id", "partition"}}
    predictions = score(events, model_path)
    assert predictions.shape == (30,)
    assert np.isfinite(predictions).all()
    assert ((predictions >= 0) & (predictions <= 1)).all()


@pytest.mark.parametrize("mode", ["minihep-frozen", "minihep-finetuned"])
def test_minibatch_encoder_paths_export_and_score(tmp_path, mode):
    pool = _synthetic_pool(tmp_path / "dataset")
    model_path = train(tmp_path / "dataset", tmp_path / f"{mode}.json", mode, epochs=1)
    events = {name: values for name, values in pool.items()
              if name not in {"label", "weight", "event_id", "partition"}}
    predictions = score(events, model_path)
    assert predictions.shape == (30,)
    assert np.isfinite(predictions).all()
    assert ((predictions >= 0) & (predictions <= 1)).all()


def test_frozen_encoder_does_not_change_during_probe_training():
    torch.set_num_threads(1)
    encoder = MiniHEP(dropout=0)
    model = MiniHEPClassifier(encoder)
    before = {name: value.detach().clone() for name, value in encoder.state_dict().items()}
    head_before = {name: value.detach().clone() for name, value in model.head.state_dict().items()}
    x = torch.randn(12, 5, 4)
    valid = torch.ones(12, 5, dtype=torch.bool)
    y = torch.arange(12, dtype=torch.float32) % 2
    weights = torch.ones(12)
    _fit_classifier(model, x, y, weights, np.arange(12), epochs=1, seed=17,
                    token_valid=valid, freeze_encoder=True)
    assert all(torch.equal(value, encoder.state_dict()[name]) for name, value in before.items())
    assert any(not torch.equal(value, model.head.state_dict()[name])
               for name, value in head_before.items())


def test_masked_pretraining_is_independent_of_class_labels(tmp_path):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    _synthetic_pool(first_dir)
    shutil.copytree(first_dir, second_dir)
    with np.load(second_dir / "mc" / "pool.npz", allow_pickle=False) as archive:
        changed = {name: archive[name] for name in archive.files}
    changed["label"] = 1 - changed["label"]
    changed["process"] = np.where(changed["label"] == 1, 345324, 363492)
    np.savez(second_dir / "mc" / "pool.npz", **changed)
    first_model = train(first_dir, tmp_path / "first.json", "frozen", epochs=1)
    second_model = train(second_dir, tmp_path / "second.json", "frozen", epochs=1)
    first_history = json.loads(first_model.read_text())["pretraining"]
    second_history = json.loads(second_model.read_text())["pretraining"]
    assert first_history == second_history


def test_label_budget_is_nested_stratified_and_ignores_heldout_labels(tmp_path):
    pool = _synthetic_pool(tmp_path / "dataset")
    small = select_labeled_subset(pool, count=4, seed=7)
    large = select_labeled_subset(pool, count=10, seed=7)
    assert len(small) == 4 and len(large) == 10
    assert set(small).issubset(large)
    assert (pool["partition"][large] == 0).all()
    assert np.bincount(pool["label"][small]).tolist() == [2, 2]
    pool["label"][pool["partition"] != 0] = 99
    np.testing.assert_array_equal(small, select_labeled_subset(pool, count=4, seed=7))
    assert not np.array_equal(small, select_labeled_subset(pool, count=4, seed=8))
    with pytest.raises(ValueError, match="label count"):
        select_labeled_subset(pool, count=21)


def test_checkpoint_roundtrip_and_no_heldout_preprocessing_fit(tmp_path):
    dataset = tmp_path / "dataset"
    pool = _synthetic_pool(dataset)
    first = pretrain_checkpoint(dataset, tmp_path / "first.json", epochs=1)
    encoder, payload = load_encoder_checkpoint(first)
    assert payload["compute"]["events"] == 20
    assert payload["compute"]["optimizer_steps"] == 1
    from higgslab.models import state_from_json
    restored = MiniHEP(**payload["architecture"])
    state_from_json(restored, payload["weights"])
    restored.eval()
    x, valid = torch.randn(3, 5, 4), torch.ones(3, 5, dtype=torch.bool)
    with torch.no_grad():
        torch.testing.assert_close(encoder.encode_events(x, valid), restored.encode_events(x, valid), rtol=0, atol=0)
    # Reconstruction and scaling must not depend on labels or heldout inputs.
    pool["label"] = 1 - pool["label"]
    pool["process"] = np.where(pool["label"] == 1, 345324, 363492)
    pool["met_et"][pool["partition"] != 0] *= 100
    np.savez(dataset / "mc/pool.npz", **pool)
    second = pretrain_checkpoint(dataset, tmp_path / "second.json", epochs=1)
    _, changed = load_encoder_checkpoint(second)
    for key in ("weights", "scaler", "training_fingerprint", "reconstruction"):
        assert payload[key] == changed[key]


def test_checkpoint_adaptation_shared_subset_and_scratch_skips_pretraining(tmp_path, monkeypatch):
    import higgslab.training as training
    dataset = tmp_path / "dataset"
    _synthetic_pool(dataset)
    checkpoint = pretrain_checkpoint(dataset, tmp_path / "encoder.json", epochs=1)
    encoder, original = load_encoder_checkpoint(checkpoint)
    def fail_pretrain(*args, **kwargs):
        pytest.fail("loaded-checkpoint and scratch adaptation must skip pretraining")
    monkeypatch.setattr(training, "_pretrain", fail_pretrain)
    payloads = {}
    for mode in ("classifier", "frozen", "scratch", "finetuned"):
        path = train(dataset, tmp_path / f"{mode}.json", mode, epochs=1,
                     label_count=4, subset_seed=9, checkpoint=checkpoint if mode != "classifier" else None)
        payloads[mode] = json.loads(path.read_text())
    assert all(value["label_budget"] == payloads["classifier"]["label_budget"] for value in payloads.values())
    for mode in ("frozen", "scratch", "finetuned"):
        assert payloads[mode]["scaler"] == original["scaler"]
        assert payloads[mode]["pretraining"] == {"train_loss": [], "validation_loss": []}
    assert payloads["scratch"]["checkpoint"]["weights_loaded"] is False
    assert payloads["finetuned"]["checkpoint"]["weights_loaded"] is True
    assert payloads["scratch"]["architecture"] == payloads["finetuned"]["architecture"]
    assert all(payloads["frozen"]["weights"][f"encoder.{key}"] == value for key, value in original["weights"].items())


def test_checkpoint_rejects_invalid_metadata_and_nonfinite_weights(tmp_path):
    dataset = tmp_path / "dataset"
    _synthetic_pool(dataset)
    checkpoint = pretrain_checkpoint(dataset, tmp_path / "encoder.json", epochs=1)
    valid = json.loads(checkpoint.read_text())
    for field, replacement, message in (
            ("architecture", {**valid["architecture"], "heads": 0}, "architecture"),
            ("architecture", {**valid["architecture"], "dropout": float("nan")}, "architecture"),
            ("scaler", {**valid["scaler"], "scale": [0, 1, 1, 1]}, "preprocessing"),
            ("weights", {**valid["weights"], "mask_embedding": [float("inf")] * 32}, "finite")):
        checkpoint.write_text(json.dumps({**valid, field: replacement}))
        with pytest.raises(ValueError, match=message):
            load_encoder_checkpoint(checkpoint)
    with pytest.raises(ValueError, match="transformer modes"):
        train(dataset, tmp_path / "bad.json", "classifier", checkpoint=checkpoint)
    checkpoint.write_text("not JSON")
    with pytest.raises(ValueError, match="JSON"):
        load_encoder_checkpoint(checkpoint)
