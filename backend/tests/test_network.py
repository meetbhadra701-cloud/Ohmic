"""Step 3 tests: physical feasibility / line-capacity curtailment."""
import pytest

from sim.physics.clearing import Match
from sim.physics.network import Line, feasible_flows, single_feeder_route


def _m(qty, price=0.27):
    return Match("LOAD_CAMPUS", "BESS_01", qty, price)


def test_under_capacity_passes_through():
    lines = {"FEEDER_1": Line("FEEDER_1", 80.0)}
    r = feasible_flows([_m(45.0)], lines, single_feeder_route())
    assert r.curtailed_kw == pytest.approx(0.0)
    assert r.adjusted_matches[0].qty_kw == pytest.approx(45.0)
    assert r.per_line_flow_kw["FEEDER_1"] == pytest.approx(45.0)
    assert r.reasons == []


def test_marginal_match_curtailed_to_rating():
    lines = {"FEEDER_1": Line("FEEDER_1", 80.0)}
    # 60 + 40 = 100 over an 80 line -> second match trimmed to 20
    r = feasible_flows([_m(60.0), _m(40.0)], lines, single_feeder_route())
    assert r.per_line_flow_kw["FEEDER_1"] == pytest.approx(80.0)
    assert r.curtailed_kw == pytest.approx(20.0)
    qtys = sorted(m.qty_kw for m in r.adjusted_matches)
    assert qtys == pytest.approx([20.0, 60.0])
    assert r.reasons[0]["line_id"] == "FEEDER_1"
    assert r.reasons[0]["curtailed_kw"] == pytest.approx(20.0)


def test_match_fully_dropped_when_no_headroom():
    lines = {"FEEDER_1": Line("FEEDER_1", 50.0)}
    r = feasible_flows([_m(50.0), _m(30.0)], lines, single_feeder_route())
    assert r.per_line_flow_kw["FEEDER_1"] == pytest.approx(50.0)
    assert r.curtailed_kw == pytest.approx(30.0)
    assert len(r.adjusted_matches) == 1            # second match dropped entirely


def test_energy_accounting_conserved():
    lines = {"FEEDER_1": Line("FEEDER_1", 80.0)}
    matches = [_m(60.0), _m(40.0)]
    r = feasible_flows(matches, lines, single_feeder_route())
    requested = sum(m.qty_kw for m in matches)
    delivered = sum(m.qty_kw for m in r.adjusted_matches)
    assert delivered + r.curtailed_kw == pytest.approx(requested)
