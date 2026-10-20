"""Deterministic CPU training and portable JSON inference for HiggsLab paths."""

from __future__ import annotations

import json
import math
import hashlib
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from .models import FeatureMLP, MiniHEP, MiniHEPClassifier, sample_hidden, state_to_json, state_from_json
from .data import load_dataset

MODES = ("classifier", "frozen", "finetuned", "scratch", "supervised", "minihep-frozen", "minihep-finetuned")
MODE_ALIASES = {"classifier": "supervised", "frozen": "minihep-frozen",
                "finetuned": "minihep-finetuned"}
SEED = 42


def select_labeled_subset(pool: dict[str, np.ndarray], *, fraction: float = 0.1,
                          count: int | None = None, seed: int = SEED) -> np.ndarray:
    """Select an exact, reproducible stratified budget using only train labels.

    Per-class permutations are fixed across budgets, yielding nested subsets.
    """
    train_idx = np.flatnonzero(pool["partition"] == 0)
    if not 0 < fraction <= 1:
        raise ValueError("label fraction must be in (0, 1]")
    budget = max(2, int(round(len(train_idx) * fraction))) if count is None else count
    if not isinstance(budget, (int, np.integer)) or not 2 <= budget <= len(train_idx):
        raise ValueError("label count must be an integer between 2 and the training pool size")
    labels = np.asarray(pool["label"])[train_idx]
    classes = [train_idx[labels == label] for label in (0, 1)]
    if any(len(rows) == 0 for rows in classes) or not np.isin(labels, [0, 1]).all():
        raise ValueError("training labels must contain both binary classes")
    n0 = int(np.clip(round(budget * len(classes[0]) / len(train_idx)),
                     max(1, budget - len(classes[1])), min(len(classes[0]), budget - 1)))
    rng = np.random.default_rng(seed)
    return np.sort(np.concatenate([rng.permutation(classes[0])[:n0],
                                   rng.permutation(classes[1])[:budget - n0]]))


def _training_fingerprint(pool: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    rows = np.flatnonzero(pool["partition"] == 0)
    for key in sorted(set(pool) - {"label", "weight", "process", "partition"}):
        values = np.ascontiguousarray(pool[key][rows])
        digest.update(key.encode())
        digest.update(values.dtype.str.encode())
        digest.update(values.tobytes())
    return digest.hexdigest()


def load_encoder_checkpoint(path: str | Path) -> tuple[MiniHEP, dict]:
    """Load portable JSON weights and the exact pretrained input transform."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("invalid encoder checkpoint JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("encoder checkpoint must be an object")
    if payload.get("format") != "higgslab-encoder-v1" or payload.get("token_contract") != "five-slot-px-py-pz-E-v1":
        raise ValueError("unsupported encoder checkpoint format/token contract")
    required = {"architecture", "scaler", "weights", "training_fingerprint", "compute"}
    if not required.issubset(payload):
        raise ValueError("encoder checkpoint is missing required metadata")
    architecture = payload["architecture"]
    if (not isinstance(architecture, dict) or set(architecture) != {"width", "heads", "layers", "dropout"}
            or any(type(architecture[key]) is not int or not 0 < architecture[key] <= 1024
                   for key in ("width", "heads", "layers"))
            or architecture["width"] % architecture["heads"] != 0
            or not isinstance(architecture["dropout"], (int, float))
            or not 0 <= architecture["dropout"] < 1):
        raise ValueError("invalid checkpoint architecture")
    scaler = payload["scaler"]
    if not isinstance(scaler, dict) or not {"kind", "scale_gev", "mean", "scale"}.issubset(scaler):
        raise ValueError("invalid checkpoint preprocessing")
    if (scaler.get("kind") != "asinh" or scaler.get("scale_gev") != 50.0
            or np.shape(scaler["mean"]) != (4,) or np.shape(scaler["scale"]) != (4,)
            or not np.isfinite(scaler["mean"]).all() or not np.isfinite(scaler["scale"]).all()
            or np.any(np.array(scaler["scale"]) <= 0)):
        raise ValueError("invalid checkpoint preprocessing")
    encoder = MiniHEP(**payload["architecture"])
    weights = payload["weights"]
    if not isinstance(weights, dict):
        raise ValueError("invalid checkpoint weights")
    try:
        if any(not np.isfinite(np.asarray(value, dtype=float)).all() for value in weights.values()):
            raise ValueError("checkpoint weights must be finite")
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint weights must be finite numeric arrays") from exc
    try:
        state_from_json(encoder, payload["weights"])
    except (RuntimeError, TypeError) as exc:
        raise ValueError("checkpoint weights do not match the architecture") from exc
    encoder.eval()
    return encoder, payload


def pretrain_checkpoint(dataset_dir: str | Path, output: str | Path,
                        epochs: int = 4) -> Path:
    """Instructor-only reconstruction fit on all unlabeled partition-0 events."""
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    pool = _load_pool(dataset_dir)
    train_idx = np.flatnonzero(pool["partition"] == 0)
    features = _feature_api()
    events = _events(pool, np.arange(len(pool["label"])))
    valid = np.asarray(features.token_mask(events), dtype=bool)
    scaled, mean, scale = _token_scaler(np.asarray(features.tokens(events)), valid, train_idx)
    architecture = {"width": 32, "heads": 4, "layers": 2, "dropout": 0.1}
    encoder = MiniHEP(**architecture)
    start = time.perf_counter()
    history = _pretrain(encoder, torch.as_tensor(scaled), torch.as_tensor(valid),
                        train_idx, train_idx, epochs, SEED)
    payload = {"format": "higgslab-encoder-v1", "token_contract": "five-slot-px-py-pz-E-v1",
               "architecture": architecture, "weights": state_to_json(encoder), "seed": SEED,
               "scaler": {"kind": "asinh", "scale_gev": 50.0,
                          "mean": mean.tolist(), "scale": scale.tolist()},
               "training_fingerprint": _training_fingerprint(pool), "training_partition": 0,
               "compute": {"epochs": epochs, "events": len(train_idx), "batch_size": 64,
                           "optimizer_steps": epochs * math.ceil(len(train_idx) / 64),
                           "elapsed_seconds": time.perf_counter() - start},
               "reconstruction": history, "diagnostic_partition": 0,
               "torch_version": torch.__version__}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return output


def _load_pool(dataset_dir: str | Path) -> dict[str, np.ndarray]:
    # Use the package's validated dataset contract so duplicate identities,
    # cross-partition kinematic copies, and malformed weights fail before fit.
    _, pool, _ = load_dataset(dataset_dir)
    required = {"label", "weight", "partition"}
    if missing := required.difference(pool):
        raise ValueError(f"pool is missing required columns: {sorted(missing)}")
    n = len(pool["label"])
    if any(len(value) != n for value in pool.values()):
        raise ValueError("pool columns have inconsistent event counts")
    if not np.isin(pool["partition"], (0, 1, 2)).all():
        raise ValueError("partition values must be 0=train, 1=validation, 2=template")
    return pool


def _feature_api():
    from . import features
    return features


def _events(pool: dict[str, np.ndarray], indices: np.ndarray) -> dict[str, np.ndarray]:
    # Labels and weights are deliberately excluded from model inputs.
    return {key: value[indices] for key, value in pool.items()
            if key not in {"label", "weight", "process", "event_id", "partition"}}


def _weighted_bce(logits: torch.Tensor, labels: torch.Tensor,
                  weights: torch.Tensor) -> torch.Tensor:
    # dataset-v1 uses positive MC weights; signed-weight handling is advanced.
    per_event = nn.functional.binary_cross_entropy_with_logits(logits, labels, reduction="none")
    return (per_event * weights).sum() / weights.sum().clamp_min(1e-12)


def _batches(indices: np.ndarray, batch_size: int, rng: np.random.Generator):
    order = rng.permutation(indices)
    for start in range(0, len(order), batch_size):
        yield order[start:start + batch_size]


def _fit_classifier(model: nn.Module, x: torch.Tensor, y: torch.Tensor,
                    weights: torch.Tensor, train_idx: np.ndarray, epochs: int,
                    seed: int, batch_size: int = 128,
                    token_valid: torch.Tensor | None = None,
                    freeze_encoder: bool = False,
                    validation_indices: np.ndarray | None = None) -> dict[str, list[float]]:
    if freeze_encoder and isinstance(model, MiniHEPClassifier):
        model.encoder.eval()
        for parameter in model.encoder.parameters():
            parameter.requires_grad_(False)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=1e-3)
    rng = np.random.default_rng(seed + 10)
    history = {"train_loss": [], "validation_loss": []}

    def evaluate(indices: np.ndarray) -> float:
        model.eval()
        numerator = denominator = 0.0
        with torch.no_grad():
            for start in range(0, len(indices), batch_size):
                rows = indices[start:start + batch_size]
                if isinstance(model, MiniHEPClassifier):
                    assert token_valid is not None
                    logits = model(x[rows], token_valid[rows])
                else:
                    logits = model(x[rows])
                loss = nn.functional.binary_cross_entropy_with_logits(
                    logits, y[rows], reduction="none")
                numerator += float((loss * weights[rows]).sum())
                denominator += float(weights[rows].sum())
        return numerator / max(denominator, 1e-12)

    for _ in range(epochs):
        model.train()
        if freeze_encoder and isinstance(model, MiniHEPClassifier):
            model.encoder.eval()
        for rows in _batches(train_idx, batch_size, rng):
            optimizer.zero_grad(set_to_none=True)
            if isinstance(model, MiniHEPClassifier):
                assert token_valid is not None
                logits = model(x[rows], token_valid[rows])
            else:
                logits = model(x[rows])
            loss = _weighted_bce(logits, y[rows], weights[rows])
            loss.backward()
            optimizer.step()
        history["train_loss"].append(evaluate(train_idx))
        history["validation_loss"].append(
            evaluate(validation_indices if validation_indices is not None else train_idx))
    return history


def _pretrain(encoder: MiniHEP, x: torch.Tensor, valid: torch.Tensor,
              train_idx: np.ndarray, val_idx: np.ndarray, epochs: int,
              seed: int) -> dict[str, list[float]]:
    optimizer = torch.optim.AdamW(encoder.parameters(), lr=1e-3)
    rng = np.random.default_rng(seed + 20)
    mask_generator = torch.Generator(device="cpu").manual_seed(seed + 21)
    history = {"train_loss": [], "validation_loss": []}

    def evaluate(indices: np.ndarray) -> float:
        encoder.eval()
        generator = torch.Generator(device="cpu").manual_seed(seed + 1000)
        squared_error = 0.0
        component_count = 0
        with torch.no_grad():
            for start in range(0, len(indices), 64):
                rows = indices[start:start + 64]
                target, mask = x[rows], valid[rows]
                hidden = sample_hidden(mask, 0.25, generator)
                prediction = encoder(target, mask, hidden)
                squared_error += float((prediction[hidden] - target[hidden]).square().sum())
                component_count += int(hidden.sum()) * target.shape[-1]
        return squared_error / max(component_count, 1)

    for _ in range(epochs):
        encoder.train()
        squared_error = 0.0
        component_count = 0
        for rows in _batches(train_idx, 64, rng):
            target, mask = x[rows], valid[rows]
            hidden = sample_hidden(mask, 0.25, mask_generator)
            optimizer.zero_grad(set_to_none=True)
            prediction = encoder(target, mask, hidden)
            loss = (prediction[hidden] - target[hidden]).square().mean()
            loss.backward()
            optimizer.step()
            squared_error += float((prediction.detach()[hidden] - target[hidden]).square().sum())
            component_count += int(hidden.sum()) * target.shape[-1]
        history["train_loss"].append(squared_error / max(component_count, 1))
        history["validation_loss"].append(evaluate(val_idx))
    return history


def _feature_scaler(values: np.ndarray, train_idx: np.ndarray):
    mean = values[train_idx].mean(axis=0)
    scale = values[train_idx].std(axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)
    return mean.astype(np.float32), scale.astype(np.float32)


def _token_scaler(vectors: np.ndarray, valid: np.ndarray, train_idx: np.ndarray):
    transformed = np.arcsinh(vectors / 50.0)
    active = transformed[train_idx][valid[train_idx]]
    mean = active.mean(axis=0)
    scale = np.maximum(active.std(axis=0), 1e-6)
    result = ((transformed - mean) / scale).astype(np.float32)
    result[~valid] = 0.0
    return result, mean.astype(np.float32), scale.astype(np.float32)


def _json_linear_layers(model: FeatureMLP) -> list[dict[str, list]]:
    layers = []
    for module in model.network:
        if isinstance(module, nn.Linear):
            layers.append({"weight": module.weight.detach().cpu().numpy().tolist(),
                           "bias": module.bias.detach().cpu().numpy().tolist()})
    return layers


def train(dataset_dir: str | Path, output: str | Path, mode: str,
          epochs: int = 4, *, label_fraction: float = 1.0,
          label_count: int | None = None, subset_seed: int = SEED,
          checkpoint: str | Path | None = None) -> Path:
    """Train one path and export its full inference model as portable JSON.

    Partitions are fixed by the dataset contract: 0 trains, 1 validates, and
    2 supplies templates. Only partition 0 fits scalers or model parameters.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}")
    mode = MODE_ALIASES.get(mode, mode)
    if mode == "supervised" and checkpoint is not None:
        raise ValueError("checkpoint is only supported for transformer modes")
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    torch.set_num_threads(1)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    pool = _load_pool(dataset_dir)
    partition = np.asarray(pool["partition"])
    train_idx = np.flatnonzero(partition == 0)
    val_idx = np.flatnonzero(partition == 1)
    template_idx = np.flatnonzero(partition == 2)
    if min(len(train_idx), len(val_idx), len(template_idx)) == 0:
        raise ValueError("train, validation, and template partitions must all be non-empty")
    labeled_idx = select_labeled_subset(pool, fraction=label_fraction, count=label_count,
                                        seed=subset_seed)
    y = torch.as_tensor(pool["label"], dtype=torch.float32)
    if not torch.isfinite(y).all() or not torch.isin(y, torch.tensor([0.0, 1.0])).all():
        raise ValueError("label must contain only finite 0/1 values")
    # Training objective weights are normalized on the training partition only.
    raw_weights = np.asarray(pool["weight"], dtype=np.float64)
    if not np.isfinite(raw_weights).all() or raw_weights[train_idx].sum() <= 0:
        raise ValueError("training weights must have finite positive absolute sum")
    weights = raw_weights / raw_weights[train_idx].mean()
    weights = torch.as_tensor(weights.astype(np.float32))
    features = _feature_api()
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    if mode == "supervised":
        events = _events(pool, np.arange(len(y)))
        raw = np.asarray(features.engineered(events), dtype=np.float32)
        if raw.ndim != 2 or raw.shape[0] != len(y) or not np.isfinite(raw).all():
            raise ValueError("features.engineered must return a finite (events, features) array")
        mean, scale = _feature_scaler(raw, labeled_idx)
        x = torch.as_tensor((raw - mean) / scale, dtype=torch.float32)
        model = FeatureMLP(x.shape[1])
        classifier_history = _fit_classifier(model, x, y, weights, labeled_idx, epochs, SEED,
                                             validation_indices=val_idx)
        payload: dict[str, Any] = {
            "format": "higgslab-model-v1", "mode": mode,
            "seed": SEED, "epochs": epochs, "input_size": x.shape[1],
            "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
            "classification": classifier_history,
            "scaler": {"mean": mean.tolist(), "scale": scale.tolist()},
            "layers": _json_linear_layers(model),
        }
    else:
        events = _events(pool, np.arange(len(y)))
        vectors = np.asarray(features.tokens(events), dtype=np.float32)
        valid = np.asarray(features.token_mask(events), dtype=bool)
        if vectors.shape != (len(y), 5, 4) or valid.shape != (len(y), 5):
            raise ValueError("features.tokens/mask must return (events, 5, 4) and (events, 5)")
        if not np.isfinite(vectors).all() or np.any(valid.sum(axis=1) == 0):
            raise ValueError("token vectors must be finite and each event must contain a valid token")
        checkpoint_payload = None
        if checkpoint is not None:
            encoder, checkpoint_payload = load_encoder_checkpoint(checkpoint)
            if checkpoint_payload["training_fingerprint"] != _training_fingerprint(pool):
                raise ValueError("checkpoint was pretrained on a different partition-0 pool")
            scaler = checkpoint_payload["scaler"]
            mean, scale = np.array(scaler["mean"]), np.array(scaler["scale"])
            scaled = ((np.arcsinh(vectors / scaler["scale_gev"]) - mean) / scale).astype(np.float32)
            scaled[~valid] = 0.0
        else:
            scaled, mean, scale = _token_scaler(vectors, valid, train_idx)
        x = torch.as_tensor(scaled, dtype=torch.float32)
        token_valid = torch.as_tensor(valid, dtype=torch.bool)
        if checkpoint_payload is None or mode == "scratch":
            encoder = MiniHEP(**(checkpoint_payload["architecture"] if checkpoint_payload else {}))
        pretraining_history = {"train_loss": [], "validation_loss": []}
        if checkpoint_payload is None and mode != "scratch":
            pretraining_history = _pretrain(encoder, x, token_valid, train_idx, val_idx,
                                            epochs, SEED)
        # Match head initialization and adaptation randomness across scratch/fine-tuned arms.
        if checkpoint_payload is not None or mode == "scratch":
            torch.manual_seed(SEED + 30)
        architecture = checkpoint_payload["architecture"] if checkpoint_payload else {"width": 32, "heads": 4, "layers": 2}
        classifier = MiniHEPClassifier(encoder, width=architecture["width"])
        classifier_history = _fit_classifier(
            classifier, x, y, weights, labeled_idx, epochs, SEED,
            token_valid=token_valid, freeze_encoder=(mode == "minihep-frozen"),
            validation_indices=val_idx)
        classifier.eval()
        payload = {
            "format": "higgslab-model-v1", "mode": mode,
            "seed": SEED, "epochs": epochs,
            "scaler": {"kind": "asinh", "scale_gev": 50.0,
                       "mean": mean.tolist(), "scale": scale.tolist()},
            "weights": state_to_json(classifier),
            "architecture": architecture,
            "parameter_count": sum(parameter.numel() for parameter in classifier.parameters()),
            "encoder_parameter_count": sum(parameter.numel() for parameter in encoder.parameters()),
            "pretraining": pretraining_history,
            "classification": classifier_history,
        }
        payload["checkpoint"] = ({"sha256": hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
                                  "format": checkpoint_payload["format"],
                                  "training_fingerprint": checkpoint_payload["training_fingerprint"],
                                  "pretraining_compute": checkpoint_payload["compute"],
                                  "weights_loaded": mode != "scratch"}
                                 if checkpoint_payload else None)
    payload["label_budget"] = {"count": len(labeled_idx), "fraction": len(labeled_idx) / len(train_idx),
                               "subset_seed": subset_seed, "method": "class-stratified-v1",
                               "partition": 0, "pool_count": len(train_idx),
                               "indices": labeled_idx.tolist()}
    output.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return output


def score(events: dict[str, np.ndarray], model_path: str | Path) -> np.ndarray:
    """Return classifier probabilities for events using an exported JSON model."""
    path = Path(model_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "higgslab-model-v1":
        raise ValueError("unsupported model JSON format")
    features = _feature_api()
    if payload["mode"] == "supervised":
        raw = np.asarray(features.engineered(events), dtype=np.float32)
        scaler = payload["scaler"]
        scaled = (raw - np.asarray(scaler["mean"])) / np.asarray(scaler["scale"])
        logits = _numpy_mlp(scaled, payload["layers"])
    else:
        vectors = np.asarray(features.tokens(events), dtype=np.float32)
        valid = np.asarray(features.token_mask(events), dtype=bool)
        if vectors.shape != (len(valid), 5, 4) or valid.shape[1:] != (5,):
            raise ValueError("features.tokens/mask must return (events, 5, 4) and (events, 5)")
        scaler = payload["scaler"]
        scaled = (np.arcsinh(vectors / scaler["scale_gev"]) - np.asarray(scaler["mean"])) / np.asarray(scaler["scale"])
        scaled[~valid] = 0.0
        torch.set_num_threads(1)
        model = MiniHEPClassifier(MiniHEP(**payload["architecture"]), width=payload["architecture"]["width"])
        expected = model.state_dict()
        incoming = payload["weights"]
        if incoming.keys() != expected.keys():
            raise ValueError("model weight names do not match this architecture")
        state = {key: torch.as_tensor(incoming[key], dtype=value.dtype) for key, value in expected.items()}
        model.load_state_dict(state, strict=True)
        model.eval()
        prediction_chunks = []
        with torch.no_grad():
            for start in range(0, len(scaled), 256):
                end = start + 256
                batch = model(torch.as_tensor(scaled[start:end], dtype=torch.float32),
                              torch.as_tensor(valid[start:end], dtype=torch.bool))
                prediction_chunks.append(batch.numpy())
        logits = np.concatenate(prediction_chunks) if prediction_chunks else np.empty(0)
    # Stable sigmoid without overflow.
    from scipy.special import expit
    return expit(logits)


def _numpy_mlp(values: np.ndarray, layers: list[dict]) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    for i, layer in enumerate(layers):
        x = x @ np.asarray(layer["weight"]).T + np.asarray(layer["bias"])
        if i != len(layers) - 1:
            # GELU's exact erf form.
            from math import erf
            x = 0.5 * x * (1 + np.vectorize(erf)(x / np.sqrt(2)))
    return x[:, 0]


def score_callback(model_path: str | Path):
    """Bind a saved model to the event-score callback expected by fit code."""
    return lambda events: score(events, model_path)
