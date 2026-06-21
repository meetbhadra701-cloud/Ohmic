"""Battery degradation cost (Agent A pricing) — pure, synchronous.

Per-cycle capacity loss is QUADRATIC in depth of discharge and depends on the
average SoC of the swing. The quadratic DoD term is what makes a near-empty
battery expensive to cycle — that nonlinearity is the whole point. Coefficients
are empirical stand-ins (see vault), not a specific cell datasheet.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DegradationParams:
    b0: float            # capacity-loss intercept (dimensionless)
    b1: float            # per-unit avg SoC
    b2: float            # per-(unit DoD)^2 — must dominate deep swings
    c_new_per_kwh: float # USD/kWh replacement cost of new capacity
    floor_price: float   # USD/kWh price floor
    margin: float        # USD/kWh ask markup

    @classmethod
    def from_config(cls, cfg: dict) -> "DegradationParams":
        d = cfg["degradation"]
        return cls(d["b0"], d["b1"], d["b2"], d["c_new_per_kwh"], d["floor_price"], d["margin"])


def marginal_degradation_cost(soc_t: float, soc_t1: float, p: DegradationParams) -> dict:
    """Marginal degradation cost of moving SoC from `soc_t` to `soc_t1` (both 0-1).

    Returns a dict with the intermediate terms (for telemetry/tests) plus:
      - marginal_cost_usd_kwh: the floor-clamped degradation cost
      - ask_price_usd_kwh:     marginal_cost + margin (Agent A's sell price)
    """
    soc_t = min(max(soc_t, 0.0), 1.0)
    soc_t1 = min(max(soc_t1, 0.0), 1.0)
    avg_soc = (soc_t + soc_t1) / 2.0
    dod = abs(soc_t1 - soc_t)
    # Clamp loss >= 0: a negative degradation cost is nonsensical (would pay to cycle).
    capacity_loss = max(0.0, p.b0 + p.b1 * avg_soc + p.b2 * dod ** 2)
    marginal_cost = max(p.floor_price, capacity_loss * p.c_new_per_kwh)
    return {
        "avg_soc": avg_soc,
        "dod": dod,
        "capacity_loss": capacity_loss,
        "marginal_cost_usd_kwh": marginal_cost,
        "ask_price_usd_kwh": marginal_cost + p.margin,
    }
