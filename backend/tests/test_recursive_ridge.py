"""Step 3 tests: online recursive ridge + all 5 safety rails."""
import numpy as np

from sim.physics.recursive_ridge import RecursiveRidge, RidgeConfig


def _cfg(**kw):
    base = dict(d=2, alpha=1.0, f=0.999, cond_check_every=10_000, cond_max=1e12,
                buffer_k=64, pred_hard_cap_kw=500.0)
    base.update(kw)
    return RidgeConfig(**base)


def test_converges_on_known_linear_relation():
    # y = 30 + 50*u  ; train online, then predict
    rr = RecursiveRidge(_cfg())
    rng = np.random.default_rng(0)
    for _ in range(400):
        u = float(rng.uniform(0, 1))
        y = 30.0 + 50.0 * u
        rr.update(np.array([1.0, u]), y)
    pred = rr.predict(np.array([1.0, 0.5]))
    assert abs(pred - (30.0 + 50.0 * 0.5)) < 3.0   # within a few kW
    assert rr.is_warm()


def test_rail3_denom_underflow_skips_and_logs():
    logs = []
    # denom_eps absurdly high -> every update's denom falls below it -> skipped
    cfg = RidgeConfig(d=2, alpha=1.0, f=0.99, cond_check_every=10_000, cond_max=1e12,
                      buffer_k=8, pred_hard_cap_kw=500.0, denom_eps=10.0)
    rr = RecursiveRidge(cfg, log=logs.append)
    theta_before = rr.theta.copy()
    rr.update(np.array([1.0, 0.5]), 100.0)
    assert rr.skip_count == 1
    assert np.allclose(rr.theta, theta_before)     # update was skipped
    assert any("underflow" in m for m in logs)


def test_rail2_reanchor_fires_on_ill_conditioning():
    logs = []
    # cond_max tiny + check every tick -> watchdog re-anchors as soon as P deviates
    cfg = _cfg(cond_check_every=1, cond_max=1.0)
    rr = RecursiveRidge(cfg, log=logs.append)
    rng = np.random.default_rng(1)
    for _ in range(5):
        u = float(rng.uniform(0, 1))
        rr.update(np.array([1.0, u]), 10.0 + 5.0 * u)
    assert rr.reanchor_count >= 1
    assert any("re-anchored" in m for m in logs)


def test_rail4_prediction_clamped_to_bounds():
    rr = RecursiveRidge(_cfg(pred_hard_cap_kw=5.0))
    rng = np.random.default_rng(2)
    for _ in range(50):
        u = float(rng.uniform(0, 1))
        rr.update(np.array([1.0, u]), 1000.0)     # huge target
    assert rr.predict(np.array([1.0, 0.9])) <= 5.0
    # negative model output is clamped to >= 0
    rr2 = RecursiveRidge(_cfg())
    for _ in range(50):
        rr2.update(np.array([1.0, float(rng.uniform(0, 1))]), -500.0)
    assert rr2.predict(np.array([1.0, 0.5])) >= 0.0


def test_rail5_buffer_bounded():
    rr = RecursiveRidge(_cfg(buffer_k=10))
    for i in range(50):
        rr.update(np.array([1.0, float(i)]), float(i))
    assert len(rr._buffer) == 10                   # rolling, bounded


def test_invalid_forgetting_rejected():
    import pytest
    with pytest.raises(ValueError):
        RecursiveRidge(_cfg(f=0.0))
    with pytest.raises(ValueError):
        RecursiveRidge(_cfg(f=1.5))


def test_bias_term_not_zeroed_by_standardization():
    # With a constant bias column, standardization must leave it intact (== 1.0),
    # otherwise the intercept is destroyed.
    rr = RecursiveRidge(_cfg())
    for _ in range(20):
        rr.update(np.array([1.0, 0.5]), 42.0)
    std = rr._standardize(np.array([1.0, 0.5]))
    assert std[0] == 1.0
