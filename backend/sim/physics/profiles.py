"""Physical-model curves for solar generation and load demand.

Step 2: synthetic bell curves (pure, no state).
Step 7: call ``load_csv_profiles(solar_csv, load_csv)`` once before the sim
starts to swap in CSV-backed interpolation — the function signatures below are
UNCHANGED so no agent code needs to be touched.

Conventions: ``day_phase`` is 0.0–1.0 through the sim day (0.0/1.0 = midnight,
0.5 = noon). All power in kW, generation >= 0, demand >= 0.
"""
from __future__ import annotations

import math
import pathlib

import numpy as np

# Daylight window: dawn at phase 0.25 (06:00), dusk at 0.75 (18:00), peak at noon.
_DAWN = 0.25
_DUSK = 0.75

# CSV-backed override state (None = use synthetic formulas).
# Each array has shape (N,) with rows sorted by day_phase.
_csv_solar_phase: np.ndarray | None = None   # day_phase column
_csv_solar_frac: np.ndarray | None = None    # output_fraction column
_csv_load_phase: np.ndarray | None = None    # day_phase column
_csv_load_frac: np.ndarray | None = None     # load_fraction column (scaled by config)


def load_csv_profiles(
    solar_csv: str | pathlib.Path,
    load_csv: str | pathlib.Path,
) -> None:
    """Load CSV-backed profiles (call once before starting the sim).

    solar_csv must have columns: day_phase, output_fraction (0–1).
    load_csv  must have columns: day_phase, load_fraction  (0–1).

    When loaded, ``solar_output_kw`` interpolates output_fraction and scales by
    inverter_kw; ``load_demand_kw`` interpolates load_fraction and scales by
    (peak_kw - base_kw) + base_kw, then adds optional noise — exactly as the
    synthetic formula does, so agent config knobs still work.
    """
    global _csv_solar_phase, _csv_solar_frac, _csv_load_phase, _csv_load_frac
    s = np.loadtxt(solar_csv, delimiter=",", skiprows=1)
    l_ = np.loadtxt(load_csv, delimiter=",", skiprows=1)
    _csv_solar_phase, _csv_solar_frac = s[:, 0], s[:, 1]
    _csv_load_phase, _csv_load_frac = l_[:, 0], l_[:, 1]


def reset_csv_profiles() -> None:
    """Clear CSV state (used in tests to restore synthetic behaviour)."""
    global _csv_solar_phase, _csv_solar_frac, _csv_load_phase, _csv_load_frac
    _csv_solar_phase = _csv_solar_frac = _csv_load_phase = _csv_load_frac = None


def solar_output_kw(day_phase: float, inverter_kw: float) -> float:
    """Solar generation capped by the inverter limit.

    Synthetic: deterministic sin bell over the daylight window.
    CSV-backed: interpolates output_fraction from the loaded CSV.
    """
    if _csv_solar_phase is not None:
        frac = float(np.interp(day_phase, _csv_solar_phase, _csv_solar_frac))
        return float(min(max(frac * inverter_kw, 0.0), inverter_kw))
    # Synthetic fallback.
    if not (_DAWN <= day_phase <= _DUSK):
        return 0.0
    x = (day_phase - _DAWN) / (_DUSK - _DAWN)
    out = inverter_kw * math.sin(math.pi * x)
    return float(min(max(out, 0.0), inverter_kw))


def load_demand_kw(
    day_phase: float,
    base_kw: float,
    peak_kw: float,
    noise_kw: float = 0.0,
    rng: np.random.Generator | None = None,
) -> float:
    """Daily load profile.

    Synthetic: morning + evening Gaussian peaks over a flat base.
    CSV-backed: interpolates load_fraction and scales by (peak_kw - base_kw),
                then adds base_kw and optional Gaussian noise — same scaling
                semantics as the synthetic version.
    """
    if _csv_load_phase is not None:
        shape = float(np.interp(day_phase, _csv_load_phase, _csv_load_frac))
    else:
        morning = math.exp(-(((day_phase - 0.33) / 0.08) ** 2))
        evening = math.exp(-(((day_phase - 0.79) / 0.10) ** 2))
        shape = max(morning, evening)
    demand = base_kw + (peak_kw - base_kw) * shape
    if noise_kw and rng is not None:
        demand += float(rng.normal(0.0, noise_kw))
    return float(max(demand, 0.0))


def split_load(total_kw: float, critical_fraction: float) -> tuple[float, float]:
    """Split total demand into (critical_kw, non_critical_kw). Critical is must-serve;
    non-critical is sheddable in a fault.
    """
    cf = min(max(critical_fraction, 0.0), 1.0)
    critical = total_kw * cf
    return critical, total_kw - critical
