import numpy as np

from plant_intelligence.models.wheat_gxe_mixture_robustness import (
    ETA_GRID,
    _mixture_cross_predict,
    _mixture_train_matvec,
)


def test_eta_grid_spans_complete_interaction_domain():
    assert min(ETA_GRID) == 0.0
    assert max(ETA_GRID) == 1.0
    assert 0.99 in ETA_GRID
    assert 0.995 in ETA_GRID


def test_normalized_mixture_structured_kernel_matches_dense_kernel():
    k = np.asarray(
        [
            [1.0, 0.2, -0.1],
            [0.2, 1.0, 0.3],
            [-0.1, 0.3, 1.0],
        ]
    )
    train_g = np.asarray([0, 0, 1, 1, 2, 2])
    train_e = np.asarray([0, 1, 0, 1, 0, 1])
    vector = np.asarray([0.4, -0.2, 1.1, 0.3, -0.8, 0.5])
    eta = 0.73

    kg = k[np.ix_(train_g, train_g)]
    kgxe = kg * (train_e[:, None] == train_e[None, :])
    dense = (1.0 - eta) * kg + eta * kgxe
    structured = _mixture_train_matvec(vector, train_g, train_e, k, eta)
    assert np.allclose(structured, dense @ vector)

    coefficients = np.asarray([0.1, -0.3, 0.6, 0.5, -0.2, 0.8])
    test_g = np.asarray([2, 0, 1])
    test_e = np.asarray([0, 1, 1])
    kg_cross = k[np.ix_(test_g, train_g)]
    kgxe_cross = kg_cross * (test_e[:, None] == train_e[None, :])
    dense_cross = (1.0 - eta) * kg_cross + eta * kgxe_cross
    structured_cross = _mixture_cross_predict(
        coefficients, train_g, train_e, test_g, test_e, k, eta
    )
    assert np.allclose(structured_cross, dense_cross @ coefficients)


def test_eta_one_is_pure_environment_specific_genomic_kernel():
    k = np.asarray([[1.0, 0.4], [0.4, 1.0]])
    train_g = np.asarray([0, 0, 1, 1])
    train_e = np.asarray([0, 1, 0, 1])
    vector = np.asarray([1.0, 2.0, 3.0, 4.0])
    structured = _mixture_train_matvec(vector, train_g, train_e, k, 1.0)
    kg = k[np.ix_(train_g, train_g)]
    pure = kg * (train_e[:, None] == train_e[None, :])
    assert np.allclose(structured, pure @ vector)
