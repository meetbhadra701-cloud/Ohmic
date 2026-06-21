"""Online recursive ridge forecast (Agent B) — Sherman-Morrison + forgetting factor.

This is the most numerically delicate module in the system. The FIVE safety rails
below are load-bearing, not optional — removing any one reintroduces silent drift:

  Rail 1  Standardize features (running mean/std, Welford); bias term unstandardized.
  Rail 2  Condition watchdog: every N ticks, if cond(P) blows past a threshold,
          re-anchor by refitting ridge from the rolling buffer and resetting P,b. Log it.
  Rail 3  Underflow guard on the Sherman-Morrison denominator (skip + log).
  Rail 4  Sanity-clamp the prediction to physical bounds (>=0, <= hard cap).
  Rail 5  Rolling buffer of the last K samples, specifically to enable re-anchor.

Pure/synchronous: no MQTT, no asyncio. `log` is an injected callable(str) so the
agent can route re-anchors/skips to the vault without this module doing I/O.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class RidgeConfig:
    d: int                      # feature dimension incl. bias
    alpha: float                # ridge reg; P0 = (1/alpha) I_d
    f: float                    # forgetting factor in (0,1]
    cond_check_every: int       # ticks between condition watchdog runs
    cond_max: float             # condition-number threshold to re-anchor
    buffer_k: int               # rolling re-anchor window size
    pred_hard_cap_kw: float     # rail-4 upper physical bound
    denom_eps: float = 1e-9     # rail-3 underflow guard

    @classmethod
    def from_config(cls, cfg: dict, d: int) -> "RidgeConfig":
        r = cfg["ridge"]
        return cls(
            d=d, alpha=float(r["alpha"]), f=float(r["forgetting"]),
            cond_check_every=int(r["cond_check_every"]), cond_max=float(r["cond_max"]),
            buffer_k=int(r["buffer_k"]), pred_hard_cap_kw=float(r["pred_hard_cap_kw"]),
        )


class RecursiveRidge:
    def __init__(self, cfg: RidgeConfig, log: Callable[[str], None] | None = None):
        if not (0.0 < cfg.f <= 1.0):
            raise ValueError(f"forgetting factor f must be in (0,1], got {cfg.f}")
        self.cfg = cfg
        self._log = log or (lambda _m: None)
        d = cfg.d
        self.P = np.eye(d) / cfg.alpha
        self.theta = np.zeros(d)
        # Welford running stats for standardization (rail 1)
        self._mean = np.zeros(d)
        self._M2 = np.zeros(d)
        self._n = 0
        # Rolling buffer of raw (x, y) for re-anchor (rail 5)
        self._buffer: deque[tuple[np.ndarray, float]] = deque(maxlen=cfg.buffer_k)
        self._ticks = 0
        # Telemetry
        self.reanchor_count = 0
        self.skip_count = 0

    # ----- rail 1: standardization -------------------------------------------
    def _update_stats(self, x: np.ndarray) -> None:
        """Welford online mean/variance (numerically stable)."""
        self._n += 1
        delta = x - self._mean
        self._mean += delta / self._n
        self._M2 += delta * (x - self._mean)

    def _std(self) -> np.ndarray:
        if self._n < 2:
            return np.ones(self.cfg.d)
        var = self._M2 / (self._n - 1)
        std = np.sqrt(var)
        std[std == 0.0] = 1.0       # guard zero-variance features
        return std

    def _standardize(self, x_raw: np.ndarray) -> np.ndarray:
        std = self._std()
        out = (x_raw - self._mean) / std
        out[0] = x_raw[0]           # bias (index 0) passes through unstandardized
        return out

    # ----- public API ---------------------------------------------------------
    def is_warm(self) -> bool:
        """True once enough samples have been seen to trust the model."""
        return self._n >= self.cfg.d

    def update(self, x_raw: np.ndarray, y: float) -> None:
        x_raw = np.asarray(x_raw, dtype=float)
        self._ticks += 1
        self._buffer.append((x_raw.copy(), float(y)))     # rail 5
        self._update_stats(x_raw)                          # rail 1 (stats first)
        x = self._standardize(x_raw)

        Px = self.P @ x
        denom = self.cfg.f + x @ Px
        if denom < self.cfg.denom_eps:                     # rail 3
            self.skip_count += 1
            self._log(f"ridge denom underflow ({denom:.2e}) at tick {self._ticks}; update skipped")
            return
        self.P = (self.P - np.outer(Px, Px) / denom) / self.cfg.f
        self.theta = self.theta + (Px / denom) * (y - x @ self.theta)

        if self._ticks % self.cfg.cond_check_every == 0:   # rail 2
            self._watchdog()

    def predict(self, x_raw: np.ndarray) -> float:
        x = self._standardize(np.asarray(x_raw, dtype=float))
        yhat = float(x @ self.theta)
        return min(max(yhat, 0.0), self.cfg.pred_hard_cap_kw)   # rail 4

    # ----- rail 2: condition watchdog + re-anchor -----------------------------
    def condition(self) -> float:
        return float(np.linalg.cond(self.P))

    def _watchdog(self) -> None:
        c = self.condition()
        if np.isfinite(c) and c <= self.cfg.cond_max:
            return
        if len(self._buffer) < 2:
            return  # not enough to refit; wait
        self._reanchor(c)

    def _reanchor(self, cond_value: float) -> None:
        """Refit ridge from the buffered window and reset P, theta (rail 2)."""
        X = np.array([self._standardize(x) for x, _ in self._buffer])
        ys = np.array([y for _, y in self._buffer])
        d = self.cfg.d
        # numpy closed-form ridge (primary; sklearn intentionally optional).
        A = X.T @ X + self.cfg.alpha * np.eye(d)
        self.theta = np.linalg.solve(A, X.T @ ys)
        self.P = np.eye(d) / self.cfg.alpha               # throw away stale confidence
        self.reanchor_count += 1
        self._log(f"ridge re-anchored at tick {self._ticks} (cond={cond_value:.2e}); P,theta reset")

    def state(self) -> dict:
        """Telemetry for the WebSocket frame."""
        return {
            "cond": self.condition(),
            "reanchor_count": self.reanchor_count,
            "skip_count": self.skip_count,
            "warm": self.is_warm(),
        }
