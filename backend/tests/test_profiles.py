"""Step 2 tests: synthetic physical-model curves (no broker).
Step 7 tests: CSV-backed override behind the same signatures.
"""
import pathlib

import numpy as np
import pytest

from sim.physics.profiles import (
    load_csv_profiles,
    load_demand_kw,
    reset_csv_profiles,
    solar_output_kw,
    split_load,
)

_DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


class TestSolar:
    def test_zero_at_night(self):
        assert solar_output_kw(0.0, 80.0) == 0.0
        assert solar_output_kw(0.1, 80.0) == 0.0
        assert solar_output_kw(0.9, 80.0) == 0.0

    def test_peak_at_noon(self):
        assert solar_output_kw(0.5, 80.0) == pytest.approx(80.0)

    def test_capped_by_inverter(self):
        for phase in np.linspace(0, 1, 50):
            assert 0.0 <= solar_output_kw(float(phase), 80.0) <= 80.0

    def test_bell_shape_monotonic_to_noon(self):
        morning = [solar_output_kw(p, 80.0) for p in (0.30, 0.40, 0.50)]
        assert morning[0] < morning[1] < morning[2]

    def test_zero_at_dawn_dusk_edges(self):
        assert solar_output_kw(0.25, 80.0) == pytest.approx(0.0, abs=1e-9)
        assert solar_output_kw(0.75, 80.0) == pytest.approx(0.0, abs=1e-9)


class TestLoad:
    def test_base_at_night(self):
        # away from peaks the demand collapses to the base
        assert load_demand_kw(0.0, 40.0, 120.0) == pytest.approx(40.0, abs=1.0)

    def test_peaks_exceed_base(self):
        morning = load_demand_kw(0.33, 40.0, 120.0)
        evening = load_demand_kw(0.79, 40.0, 120.0)
        assert morning > 100.0 and evening > 100.0

    def test_within_band(self):
        for p in np.linspace(0, 1, 100):
            d = load_demand_kw(float(p), 40.0, 120.0)
            assert 40.0 - 1e-9 <= d <= 120.0 + 1e-9

    def test_noise_is_reproducible_with_seed(self):
        a = load_demand_kw(0.5, 40.0, 120.0, noise_kw=5.0, rng=np.random.default_rng(7))
        b = load_demand_kw(0.5, 40.0, 120.0, noise_kw=5.0, rng=np.random.default_rng(7))
        assert a == b

    def test_demand_never_negative(self):
        d = load_demand_kw(0.0, 1.0, 2.0, noise_kw=100.0, rng=np.random.default_rng(0))
        assert d >= 0.0


class TestSplit:
    def test_split_sums_to_total(self):
        crit, noncrit = split_load(100.0, 0.4)
        assert crit == pytest.approx(40.0)
        assert noncrit == pytest.approx(60.0)
        assert crit + noncrit == pytest.approx(100.0)

    def test_fraction_clamped(self):
        assert split_load(100.0, 1.5) == (100.0, 0.0)
        assert split_load(100.0, -0.5) == (0.0, 100.0)


class TestCsvProfiles:
    """Step 7: CSV-backed curves behind the same function signatures."""

    def setup_method(self):
        load_csv_profiles(_DATA / "solar_day.csv", _DATA / "load_day.csv")

    def teardown_method(self):
        reset_csv_profiles()

    def test_solar_zero_at_night(self):
        assert solar_output_kw(0.0, 80.0) == pytest.approx(0.0, abs=1e-3)
        assert solar_output_kw(0.24, 80.0) == pytest.approx(0.0, abs=0.5)

    def test_solar_positive_midday(self):
        # CSV has a slight cloud dip at 14:00 but noon should still be high.
        assert solar_output_kw(0.5, 80.0) > 60.0

    def test_solar_bounded(self):
        for p in np.linspace(0, 1, 50):
            v = solar_output_kw(float(p), 80.0)
            assert 0.0 <= v <= 80.0

    def test_load_morning_peak(self):
        # CSV morning peak ~08:30 (phase 0.354)
        peak_demand = load_demand_kw(0.354, 40.0, 120.0)
        night_demand = load_demand_kw(0.0, 40.0, 120.0)
        assert peak_demand > night_demand

    def test_load_bounded(self):
        for p in np.linspace(0, 1, 50):
            d = load_demand_kw(float(p), 40.0, 120.0)
            assert d >= 0.0

    def test_reset_restores_synthetic(self):
        reset_csv_profiles()
        # Synthetic: peak exactly at noon.
        assert solar_output_kw(0.5, 80.0) == pytest.approx(80.0)
