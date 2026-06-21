"""Step 3 tests: continuous double auction."""
import pytest

from sim.physics.clearing import Order, clear


def test_simple_full_match():
    bids = [Order("LOAD", 0.40, 45.0)]
    asks = [Order("BESS", 0.18, 60.0)]
    r = clear(bids, asks)
    assert len(r.matches) == 1
    assert r.matches[0].qty_kw == pytest.approx(45.0)
    assert r.clearing_price_usd_kwh == pytest.approx(0.18)   # last matched ask price
    assert r.unmet_kw == pytest.approx(0.0)
    assert r.surplus_kw == pytest.approx(15.0)               # ask had 60, sold 45


def test_no_trade_when_bid_below_ask():
    r = clear([Order("LOAD", 0.10, 50.0)], [Order("BESS", 0.30, 50.0)])
    assert r.matches == []
    assert r.clearing_price_usd_kwh is None
    assert r.unmet_kw == pytest.approx(50.0)


def test_merit_order_uniform_price_is_marginal_ask():
    # two asks at different prices; both partially needed -> clearing = pricier (marginal) ask
    bids = [Order("LOAD", 0.50, 80.0)]
    asks = [Order("CHEAP", 0.10, 50.0), Order("PRICEY", 0.30, 50.0)]
    r = clear(bids, asks)
    assert r.clearing_price_usd_kwh == pytest.approx(0.30)
    assert all(m.clearing_price_usd_kwh == pytest.approx(0.30) for m in r.matches)
    assert sum(m.qty_kw for m in r.matches) == pytest.approx(80.0)


def test_unmet_when_supply_insufficient():
    r = clear([Order("LOAD", 0.50, 100.0)], [Order("BESS", 0.20, 40.0)])
    assert sum(m.qty_kw for m in r.matches) == pytest.approx(40.0)
    assert r.unmet_kw == pytest.approx(60.0)


def test_deterministic_tiebreak_by_node_id():
    bids = [Order("LOAD", 0.50, 30.0)]
    asks = [Order("B_SELLER", 0.20, 20.0), Order("A_SELLER", 0.20, 20.0)]
    r = clear(bids, asks)
    # A_SELLER sorts first on tie -> it is matched first/fully
    assert r.matches[0].seller_id == "A_SELLER"
    assert r.matches[0].qty_kw == pytest.approx(20.0)


def test_empty_books():
    assert clear([], []).matches == []
    assert clear([], [Order("BESS", 0.2, 10.0)]).surplus_kw == pytest.approx(10.0)
