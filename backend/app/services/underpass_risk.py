"""Underpass risk intelligence service for HydroSense.
Integrates historical rainfall limits, live Open-Meteo forecast, and risk assessment.
"""
from __future__ import annotations

import csv
import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings

IST = timezone(timedelta(hours=5, minutes=30))
TIERS = [(1.0, "red"), (0.8, "orange"), (0.5, "yellow")]
DISCLAIMER = "Prototype. Estimated risk, not an official warning."
LOOKAHEAD_HOURS = 24
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"
CACHE_SECONDS = 600  # 10 minutes


def tier_for(ratio: float) -> str:
    for cut, name in TIERS:
        if ratio >= cut:
            return name
    return "green"


def _ok(val: Any) -> bool:
    return (
        val is not None
        and isinstance(val, (int, float))
        and not math.isnan(val)
        and not math.isinf(val)
        and val > 0
    )


def rolling_sum(values: list[float | None], n: int) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < n:
            out.append(None)
            continue
        window = values[i + 1 - n : i + 1]
        out.append(None if any(v is None for v in window) else sum(v for v in window if v is not None))
    return out


def forecast_rows(
    times: list[datetime],
    precip: list[float | None],
    now: datetime,
    lookahead: int = LOOKAHEAD_HOURS,
) -> list[tuple[datetime, float | None, float | None]]:
    r1 = [None if v is None else float(v) for v in precip]
    r3 = rolling_sum(r1, 3)
    end = now + timedelta(hours=lookahead)
    return [(t, a, b) for t, a, b in zip(times, r1, r3) if now < t <= end]


def limits_for(hotspot_id: str, model: dict[str, Any]) -> dict[str, Any]:
    h = model.get("hotspots", {}).get(hotspot_id)
    if h:
        return {
            "rain1h_mm": h.get("rain1h_mm"),
            "rain3h_mm": h.get("rain3h_mm"),
            "own_threshold": bool(h.get("own_threshold")),
            "evidence": h.get("evidence", ""),
            "n_floods": int(h.get("n_floods", 0)),
            "n_clear": int(h.get("n_clear", 0)),
        }
    p = model.get("pooled", {})
    return {
        "rain1h_mm": p.get("rain1h_mm"),
        "rain3h_mm": p.get("rain3h_mm"),
        "own_threshold": False,
        "evidence": "limited evidence (pooled limit used)",
        "n_floods": 0,
        "n_clear": 0,
    }


def _round_opt(val: float | None) -> float | None:
    return None if val is None else round(float(val), 1)


def assess_hotspot(
    hotspot: dict[str, Any],
    model: dict[str, Any],
    rows: list[tuple[datetime, float | None, float | None]],
    flood_rain3h: list[float],
) -> dict[str, Any]:
    lim = limits_for(hotspot["id"], model)
    l1, l3 = lim["rain1h_mm"], lim["rain3h_mm"]
    base = {
        "id": hotspot["id"],
        "name": hotspot["name"],
        "lat": hotspot["lat"],
        "lon": hotspot["lon"],
        "limit": {
            "rain1h_mm": _round_opt(l1) if _ok(l1) else None,
            "rain3h_mm": _round_opt(l3) if _ok(l3) else None,
        },
        "limit_is_own": lim["own_threshold"],
        "evidence": lim["evidence"],
        "note": DISCLAIMER,
    }

    v1 = [a for _, a, _ in rows if a is not None]
    v3 = [b for _, _, b in rows if b is not None]
    if not v1:
        return {
            **base,
            "tier": "unknown",
            "ratio": None,
            "forecast": {
                "max_1h_mm": None,
                "max_3h_mm": None,
                "window_start": None,
                "window_end": None,
            },
            "history": None,
            "why": "Forecast is not available for this spot right now.",
        }

    max1 = max(v1)
    max3 = max(v3) if v3 else max(v1)
    ratios: list[float] = []
    if _ok(l1):
        ratios.append(max1 / l1)
    if _ok(l3):
        ratios.append(max3 / l3)
    ratio = max(ratios) if ratios else 0.0
    tier = tier_for(ratio)

    flagged = [
        t
        for t, a, b in rows
        if (_ok(l1) and a is not None and a >= l1) or (_ok(l3) and b is not None and b >= l3)
    ]
    window_start = flagged[0].isoformat() if flagged else None
    window_end = flagged[-1].isoformat() if flagged else None

    limit_text = f"about {_round_opt(l3)} mm in 3 h" if _ok(l3) else "not known"
    fc_text = f"up to {_round_opt(max3)} mm in 3 h, heaviest hour {_round_opt(max1)} mm"
    history: dict[str, Any] | None = None
    if tier == "green":
        why = f"Forecast rain for next 24 h ({fc_text}) is well below limit ({limit_text})."
    else:
        close = {"yellow": "getting closer to", "orange": "close to", "red": "at or above"}[tier]
        why = f"Forecast rain {fc_text} is {close} this spot's limit ({limit_text})."
        if flood_rain3h:
            k = sum(1 for x in flood_rain3h if x >= max3)
            history = {
                "recorded_floods": len(flood_rain3h),
                "floods_with_at_least_this_rain_3h": k,
            }
            why += f" {k} of {len(flood_rain3h)} recorded floods here had at least this much rain in 3 h."
        if window_start:
            why += " Estimated risk window is based on when forecast rain reaches the limit."
    why += f" Evidence: {lim['evidence']}."

    return {
        **base,
        "tier": tier,
        "ratio": round(ratio, 2),
        "forecast": {
            "max_1h_mm": _round_opt(max1),
            "max_3h_mm": _round_opt(max3),
            "window_start": window_start,
            "window_end": window_end,
        },
        "history": history,
        "why": why,
    }


class UnderpassRiskService:
    def __init__(self, settings: Settings, data_dir: Path | None = None) -> None:
        self.settings = settings
        self.data_dir = self._resolve_data_dir(data_dir)
        self._cache: dict[str, Any] = {}
        self.hotspots: list[dict[str, Any]] = []
        self.model: dict[str, Any] = {}
        self.floods: dict[str, list[float]] = {}
        self.metrics: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []
        self._load_datasets()

    def _resolve_data_dir(self, explicit: Path | None) -> Path:
        if explicit and explicit.exists():
            return explicit
        candidates = [
            Path("data/underpass"),
            Path("backend/data/underpass"),
            Path("../backend/data/underpass"),
            Path("delhi-underpass-warning/data"),
            Path("../delhi-underpass-warning/data"),
        ]
        for c in candidates:
            if (c / "thresholds.json").exists():
                return c.resolve()
        return (Path(__file__).resolve().parent.parent.parent / "data" / "underpass").resolve()

    def _load_datasets(self) -> None:
        d = self.data_dir
        if (d / "hotspots.json").exists():
            self.hotspots = json.loads((d / "hotspots.json").read_text(encoding="utf-8"))["hotspots"]
        if (d / "thresholds.json").exists():
            self.model = json.loads((d / "thresholds.json").read_text(encoding="utf-8"))
        if (d / "metrics.json").exists():
            self.metrics = json.loads((d / "metrics.json").read_text(encoding="utf-8"))
        if (d / "features.csv").exists():
            with open(d / "features.csv", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r.get("outcome") == "flooded":
                        self.floods.setdefault(r["hotspot_id"], []).append(float(r["rain3h_mm"]))
        if (d / "events.csv").exists():
            with open(d / "events.csv", encoding="utf-8") as f:
                self.events = list(csv.DictReader(f))

    def get_hotspots(self) -> list[dict[str, Any]]:
        return self.hotspots

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics

    def get_events(
        self,
        outcome: str | None = None,
        hotspot_id: str | None = None,
        date: str | None = None,
    ) -> list[dict[str, Any]]:
        evs = self.events
        if outcome:
            evs = [e for e in evs if e.get("outcome") == outcome]
        if hotspot_id:
            evs = [e for e in evs if e.get("hotspot_id") == hotspot_id]
        if date:
            evs = [e for e in evs if e.get("date") == date]
        return evs

    def _fetch_live_forecast(self) -> tuple[list[dict[str, Any]], str]:
        if not self.hotspots:
            return [], "none"
        params = {
            "latitude": ",".join(str(h["lat"]) for h in self.hotspots),
            "longitude": ",".join(str(h["lon"]) for h in self.hotspots),
            "hourly": "precipitation",
            "timezone": "Asia/Kolkata",
            "past_days": 1,
            "forecast_days": 2,
        }
        wanted = getattr(self.settings, "forecast_model", "ecmwf_ifs")
        try:
            url = f"{OPEN_METEO_API}?{urllib.parse.urlencode({**params, 'models': wanted}, safe=',')}"
            with urllib.request.urlopen(url, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data if isinstance(data, list) else [data]), wanted
        except Exception:
            # fallback to default model or empty
            try:
                url = f"{OPEN_METEO_API}?{urllib.parse.urlencode(params, safe=',')}"
                with urllib.request.urlopen(url, timeout=6) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return (data if isinstance(data, list) else [data]), "open-meteo default"
            except Exception:
                return [], "offline_mock"

    def get_risk_assessment(self, force_refresh: bool = False) -> dict[str, Any]:
        now = datetime.now(IST)
        cached = self._cache.get("forecast")
        if (
            not force_refresh
            and cached
            and (time.time() - cached["at"] < CACHE_SECONDS)
        ):
            results = cached["results"]
            model_used = cached["model_used"]
        else:
            results, model_used = self._fetch_live_forecast()
            if results:
                self._cache["forecast"] = {
                    "at": time.time(),
                    "results": results,
                    "model_used": model_used,
                }
            elif cached:
                results = cached["results"]
                model_used = cached["model_used"]

        out = []
        if results and len(results) == len(self.hotspots):
            for h, res in zip(self.hotspots, results):
                times = [
                    datetime.fromisoformat(t).replace(tzinfo=IST)
                    for t in res["hourly"]["time"]
                ]
                rows = forecast_rows(times, res["hourly"]["precipitation"], now)
                out.append(assess_hotspot(h, self.model, rows, self.floods.get(h["id"], [])))
        else:
            # Generate deterministic fallback/mock for dry/offline demo conditions
            for h in self.hotspots:
                out.append(
                    assess_hotspot(
                        h,
                        self.model,
                        [(now + timedelta(hours=i), 0.0, 0.0) for i in range(1, 25)],
                        self.floods.get(h["id"], []),
                    )
                )

        return {
            "generated_at": now.isoformat(),
            "forecast_model_used": model_used,
            "lookahead_hours": LOOKAHEAD_HOURS,
            "disclaimer": DISCLAIMER,
            "credit": "Weather data by Open-Meteo.com",
            "hotspots": out,
        }
