import numpy as np
import pytest
import torch

from higgslab.models import MiniHEP, sample_hidden
from higgslab.training import _feature_scaler, _token_scaler


def test_train_only_scalers_ignore_validation_and_template_rows():
    values = np.array([[1.0, 4.0], [3.0, 8.0], [1000.0, -1000.0], [-500.0, 700.0]])
    mean, scale = _feature_scaler(values, np.array([0, 1]))
    np.testing.assert_allclose(mean, [2, 6])
    np.testing.assert_allclose(scale, [1, 2])


def test_token_scaler_fits_valid_training_tokens_only():
    vectors = np.ones((3, 5, 4), dtype=np.float32)
    valid = np.zeros((3, 5), dtype=bool)
    valid[:, :2] = True
    vectors[0, :2] = 10
    vectors[1, :2] = 30
    vectors[2] = 9000
    transformed, mean, _ = _token_scaler(vectors, valid, np.array([0, 1]))
    expected = (np.arcsinh(10 / 50) + np.arcsinh(30 / 50)) / 2
    np.testing.assert_allclose(mean, expected, rtol=1e-6)
    assert np.all(transformed[~valid] == 0)


def test_mask_sampler_never_hides_padding_and_always_hides_one_token():
    valid = torch.tensor([[True, True, False, False, True], [True, False, False, False, False]])
    hidden = sample_hidden(valid, probability=0.01, generator=torch.Generator().manual_seed(7))
    assert torch.all(hidden.any(dim=1))
    assert not torch.any(hidden & ~valid)


def test_encoder_reconstructs_shapes_and_rejects_masked_padding():
    model = MiniHEP(dropout=0)
    vectors = torch.randn(2, 5, 4)
    valid = torch.tensor([[True, True, True, False, True], [True, True, False, False, True]])
    hidden = torch.zeros_like(valid)
    hidden[:, 0] = True
    assert model(vectors, valid, hidden).shape == (2, 5, 4)
    assert model.encode_events(vectors, valid).shape == (2, 32)
    hidden[0, 3] = True
    with pytest.raises(ValueError, match="cannot hide padding"):
        model(vectors, valid, hidden)
