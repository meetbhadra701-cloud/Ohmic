"""Synthetic physical-model curves (pure, deterministic, numpy-only).

Step 2 uses these for solar generation and load demand. Step 7 swaps a CSV reader
behind the SAME signatures, so the agents never change. No MQTT, no asyncio.

Conventions: `day_phase` is 0.0-1.0 through the sim day (0.0/1.0 = midnight,
0.5 = noon). All power in kW, generation >= 0, demand >= 0.
"""
from __future__ import annotations

import math

import numpy as np

# Daylight window: dawn at phase 0.25 (06:00), dusk at 0.75 (18:00), peak at noon.
_DAWN = 0.25
_DUSK = 0.75


def solar_output_kw(day_phase: float, inverter_kw: float) -> float:
    """Deterministic solar generation from a time-of-day bell curve, capped by the
    inverter limit. Zero outside the daylight window; peak (== inverter_kw) at noon.
    """
    if not (_DAWN <= day_phase <= _DUSK):
        return 0.0
    x = (day_phase - _DAWN) / (_DUSK - _DAWN)   # 0..1 across daylight
    out = inverter_kw * math.sin(math.pi * x)   # 0 at dawn/dusk, peak at noon
    return float(min(max(out, 0.0), inverter_kw))


def load_demand_kw(
    day_phase: float,
    base_kw: float,
    peak_kw: float,
    noise_kw: float = 0.0,
    rng: np.random.Generator | None = None,
) -> float:
    """Daily load profile with morning + evening peaks over a flat base.

    `noise_kw` adds zero-mean Gaussian jitter (std = noise_kw) using `rng` if given
    (pass a seeded Generator for reproducible tests). Result is clamped to >= 0.
    """
    morning = math.exp(-(((day_phase - 0.33) / 0.08) ** 2))
    evening = math.exp(-(((day_phase - 0.79) / 0.10) ** 2))
    shape = max(morning, evening)               # 0..1
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
