"""Physical feasibility on top of the financial match (Grid Operator).

Money does not get to violate a wire. Each cleared Match implies a power flow on a
line with a rated capacity. We walk matches in merit order and curtail the marginal
matches down to each line's rating, recording how much and why.

`feasible_flows(matches, lines, route)` is the v2 ADMM / optimal-power-flow seam:
an OPF solver satisfies the SAME signature, so v2 swaps the body, not the interface.
Pure/synchronous.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from .clearing import Match

_EPS = 1e-9


@dataclass(frozen=True)
class Line:
    line_id: str
    rating_kw: float


@dataclass(frozen=True)
class FeasResult:
    adjusted_matches: list[Match]                 # delivered flows after curtailment
    curtailed_kw: float                            # total trimmed
    per_line_flow_kw: dict[str, float]
    reasons: list[dict]                            # per curtailed match: {line_id, requested_kw, rating_kw, curtailed_kw}


def single_feeder_route(line_id: str = "FEEDER_1") -> Callable[[Match], str]:
    """Default star topology: every match loads one shared feeder."""
    return lambda _match: line_id


def feasible_flows(
    matches: list[Match],
    lines: dict[str, Line],
    route: Callable[[Match], str],
) -> FeasResult:
    flow: dict[str, float] = {lid: 0.0 for lid in lines}
    adjusted: list[Match] = []
    reasons: list[dict] = []
    total_curtailed = 0.0

    for m in matches:
        lid = route(m)
        line = lines[lid]
        headroom = line.rating_kw - flow.get(lid, 0.0)
        if m.qty_kw <= headroom + _EPS:
            flow[lid] = flow.get(lid, 0.0) + m.qty_kw
            adjusted.append(m)
            continue
        # Over capacity: curtail this marginal match to the remaining headroom.
        delivered = max(0.0, headroom)
        curtailed = m.qty_kw - delivered
        total_curtailed += curtailed
        flow[lid] = flow.get(lid, 0.0) + delivered
        reasons.append({
            "line_id": lid, "requested_kw": m.qty_kw, "rating_kw": line.rating_kw,
            "curtailed_kw": curtailed,
        })
        if delivered > _EPS:
            adjusted.append(replace(m, qty_kw=delivered))
        # else: match fully dropped (no headroom left)

    return FeasResult(
        adjusted_matches=adjusted,
        curtailed_kw=total_curtailed,
        per_line_flow_kw=flow,
        reasons=reasons,
    )


def lines_from_config(cfg: dict) -> dict[str, Line]:
    return {lid: Line(lid, spec["rating_kw"]) for lid, spec in cfg["network"]["lines"].items()}
