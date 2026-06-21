"""Continuous double auction (Grid Operator) — a real CDA, not an if/else.

Sort bids by willingness-to-pay (desc) and asks by reservation price (asc), then
walk the merged curves matching while bid.price >= ask.price. Uniform clearing
price = the price of the LAST matched ask (merit-order convention, frozen in
CONTRACTS). Pure/synchronous.
"""
from __future__ import annotations

from dataclasses import dataclass

_QTY_EPS = 1e-9


@dataclass(frozen=True)
class Order:
    node_id: str
    price_usd_kwh: float        # bid: max willing-to-pay; ask: min acceptable
    qty_kw: float               # >= 0


@dataclass(frozen=True)
class Match:
    buyer_id: str
    seller_id: str
    qty_kw: float
    clearing_price_usd_kwh: float


@dataclass(frozen=True)
class ClearResult:
    matches: list[Match]
    clearing_price_usd_kwh: float | None    # None if no trade
    unmet_kw: float                          # bid qty left unmatched
    surplus_kw: float                        # ask qty left unmatched


def clear(bids: list[Order], asks: list[Order]) -> ClearResult:
    # Highest willing-to-pay first; cheapest power first. Deterministic tie-break.
    bids_sorted = sorted(bids, key=lambda o: (-o.price_usd_kwh, o.node_id))
    asks_sorted = sorted(asks, key=lambda o: (o.price_usd_kwh, o.node_id))
    b_rem = [o.qty_kw for o in bids_sorted]
    a_rem = [o.qty_kw for o in asks_sorted]

    provisional: list[tuple[str, str, float]] = []
    last_ask_price: float | None = None
    i = j = 0
    while i < len(bids_sorted) and j < len(asks_sorted):
        b, a = bids_sorted[i], asks_sorted[j]
        if b.price_usd_kwh + _QTY_EPS < a.price_usd_kwh:
            break                                   # no more profitable matches
        trade = min(b_rem[i], a_rem[j])
        if trade > _QTY_EPS:
            provisional.append((b.node_id, a.node_id, trade))
            last_ask_price = a.price_usd_kwh        # marginal matched pair
            b_rem[i] -= trade
            a_rem[j] -= trade
        if b_rem[i] <= _QTY_EPS:
            i += 1
        if a_rem[j] <= _QTY_EPS:
            j += 1

    price = last_ask_price
    matches = [Match(buyer, seller, qty, price) for (buyer, seller, qty) in provisional] if price is not None else []
    unmet = sum(b_rem[i:])
    surplus = sum(a_rem[j:])
    return ClearResult(matches=matches, clearing_price_usd_kwh=price, unmet_kw=unmet, surplus_kw=surplus)
