"""Step 3 tests: battery degradation cost."""
import pytest

from sim.physics.degradation import DegradationParams, marginal_degradation_cost

P = DegradationParams(b0=5e-5, b1=1e-4, b2=2e-3, c_new_per_kwh=150.0, floor_price=0.02, margin=0.005)


def test_quadratic_dod_term_dominates_deep_swings():
    # The b2*dod^2 term must be what makes a deep swing expensive — not b0/b1.
    shallow = marginal_degradation_cost(0.55, 0.50, P)   # dod=0.05
    deep = marginal_degradation_cost(0.80, 0.10, P)      # dod=0.70
    assert deep["capacity_loss"] > shallow["capacity_loss"]
    # the increase is dominated by the quadratic term
    quad_contribution = P.b2 * (0.70 ** 2)
    lin_contribution = abs(P.b1 * (deep["avg_soc"] - shallow["avg_soc"]))
    assert quad_contribution > 5 * lin_contribution


def test_floor_price_enforced():
    # tiny swing -> degradation cost below floor -> floor applies
    r = marginal_degradation_cost(0.50, 0.50, P)
    assert r["marginal_cost_usd_kwh"] == pytest.approx(P.floor_price)


def test_ask_is_marginal_plus_margin():
    r = marginal_degradation_cost(0.80, 0.10, P)
    assert r["ask_price_usd_kwh"] == pytest.approx(r["marginal_cost_usd_kwh"] + P.margin)


def test_capacity_loss_clamped_nonnegative():
    bad = DegradationParams(b0=-1.0, b1=0.0, b2=0.0, c_new_per_kwh=150.0, floor_price=0.02, margin=0.0)
    r = marginal_degradation_cost(0.5, 0.4, bad)
    assert r["capacity_loss"] == 0.0
    assert r["marginal_cost_usd_kwh"] == pytest.approx(0.02)   # floor, never negative


def test_soc_inputs_clamped():
    r = marginal_degradation_cost(1.5, -0.5, P)   # out of range -> clamped to [0,1]
    assert r["dod"] == pytest.approx(1.0)
    assert r["avg_soc"] == pytest.approx(0.5)
