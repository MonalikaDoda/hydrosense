"""Underpass risk intelligence service for HydroSense.
Integrates historical rainfall limits, live Open-Meteo forecast, and risk assessment.
"""
from __future__ import annotations

import csv
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas import UnderpassEvaluationMetrics, UnderpassEventRecord, UnderpassHotspot

IST = timezone(timedelta(hours=5, minutes=30))
TIERS = [(1.0, "red"), (0.8, "orange"), (0.5, "yellow")]
DISCLAIMER = "Prototype. Estimated risk, not an official warning."
LOOKAHEAD_HOURS = 24
OPEN_METEO_API = "https://api.open-meteo.com/v1/forecast"


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
    max3 = max(v3) if v3 else None
    ratios: list[float] = []
    if _ok(l1):
        ratios.append(max1 / l1)
    if _ok(l3) and max3 is not None:
        ratios.append(max3 / l3)
    if not ratios:
        return {
            **base,
            "tier": "unknown",
            "ratio": None,
            "forecast": {
                "max_1h_mm": _round_opt(max1),
                "max_3h_mm": _round_opt(max3),
                "window_start": None,
                "window_end": None,
            },
            "history": None,
            "why": "A matching rainfall threshold is not available for this spot.",
        }
    ratio = max(ratios)
    tier = tier_for(ratio)

    flagged = [
        t
        for t, a, b in rows
        if (_ok(l1) and a is not None and a >= l1) or (_ok(l3) and b is not None and b >= l3)
    ]
    window_start = flagged[0].isoformat() if flagged else None
    window_end = flagged[-1].isoformat() if flagged else None

    if _ok(l3) and max3 is not None:
        limit_text = f"about {_round_opt(l3)} mm in 3 h"
        fc_text = f"up to {_round_opt(max3)} mm in 3 h, heaviest hour {_round_opt(max1)} mm"
    else:
        limit_text = f"about {_round_opt(l1)} mm in 1 h"
        fc_text = f"heaviest hour up to {_round_opt(max1)} mm"
    history: dict[str, Any] | None = None
    if tier == "green":
        why = f"Forecast rain for next 24 h ({fc_text}) is well below limit ({limit_text})."
    else:
        close = {"yellow": "getting closer to", "orange": "close to", "red": "at or above"}[tier]
        why = f"Forecast rain {fc_text} is {close} this spot's limit ({limit_text})."
        if flood_rain3h and max3 is not None:
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

    @property
    def is_available(self) -> bool:
        return bool(self.hotspots and self.model and self.metrics and self.events)

    def _resolve_data_dir(self, explicit: Path | None) -> Path:
        if explicit is not None:
            return explicit.resolve()
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
        required = ["hotspots.json", "thresholds.json", "metrics.json", "events.csv"]
        if any(not (d / name).is_file() for name in required):
            return

        try:
            hotspot_payload = json.loads((d / "hotspots.json").read_text(encoding="utf-8"))
            self.hotspots = [
                UnderpassHotspot.model_validate(item).model_dump()
                for item in hotspot_payload["hotspots"]
            ]
            self.model = json.loads((d / "thresholds.json").read_text(encoding="utf-8"))
            if not isinstance(self.model.get("pooled"), dict) or not isinstance(
                self.model.get("hotspots", {}), dict
            ):
                raise ValueError("Thresholds must contain pooled and hotspots objects.")
            self.metrics = UnderpassEvaluationMetrics.model_validate_json(
                (d / "metrics.json").read_text(encoding="utf-8")
            ).model_dump()
            with (d / "events.csv").open(encoding="utf-8") as file:
                self.events = [
                    UnderpassEventRecord.model_validate(row).model_dump()
                    for row in csv.DictReader(file)
                ]
            if not self.events:
                raise ValueError("At least one reviewed event is required.")

            if (d / "features.csv").exists():
                try:
                    with (d / "features.csv").open(encoding="utf-8") as file:
                        for row in csv.DictReader(file):
                            if row.get("outcome") == "flooded":
                                self.floods.setdefault(row["hotspot_id"], []).append(
                                    float(row["rain3h_mm"])
                                )
                except (KeyError, OSError, TypeError, ValueError):
                    self.floods = {}
        except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError):
            self.hotspots = []
            self.model = {}
            self.floods = {}
            self.metrics = {}
            self.events = []

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
            with urllib.request.urlopen(
                url, timeout=self.settings.forecast_request_timeout_seconds
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data if isinstance(data, list) else [data]), wanted
        except Exception:
            # fallback to default model or empty
            try:
                url = f"{OPEN_METEO_API}?{urllib.parse.urlencode(params, safe=',')}"
                with urllib.request.urlopen(
                    url, timeout=self.settings.forecast_request_timeout_seconds
                ) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                return (data if isinstance(data, list) else [data]), "open-meteo default"
            except Exception:
                return [], "unavailable"

    @staticmethod
    def _rows_from_result(
        result: dict[str, Any], now: datetime
    ) -> list[tuple[datetime, float | None, float | None]]:
        try:
            hourly = result["hourly"]
            raw_times = hourly["time"]
            precipitation = hourly["precipitation"]
            if not isinstance(raw_times, list) or not isinstance(precipitation, list):
                return []
            if len(raw_times) != len(precipitation):
                return []
            times = [datetime.fromisoformat(value).replace(tzinfo=IST) for value in raw_times]
            return forecast_rows(times, precipitation, now)
        except (KeyError, TypeError, ValueError):
            return []

    def _results_are_usable(self, results: list[dict[str, Any]], now: datetime) -> bool:
        if len(results) != len(self.hotspots):
            return False
        for result in results:
            rows = self._rows_from_result(result, now)
            if len(rows) != LOOKAHEAD_HOURS:
                return False
            if any(
                next_row[0] - current_row[0] != timedelta(hours=1)
                for current_row, next_row in zip(rows, rows[1:])
            ):
                return False
            if any(
                one_hour is None
                or not math.isfinite(one_hour)
                or one_hour < 0
                or three_hours is None
                or not math.isfinite(three_hours)
                or three_hours < 0
                for _, one_hour, three_hours in rows
            ):
                return False
        return True

    def get_risk_assessment(self, force_refresh: bool = False) -> dict[str, Any]:
        now = datetime.now(IST)
        cached = self._cache.get("forecast")
        cache_age = int(time.time() - cached["at"]) if cached else None
        forecast_status = "unavailable"
        if (
            not force_refresh
            and cached
            and cache_age is not None
            and cache_age < self.settings.forecast_cache_seconds
            and self._results_are_usable(cached["results"], now)
        ):
            results = cached["results"]
            model_used = cached["model_used"]
            forecast_status = "cached"
        else:
            fetched_results, fetched_model = self._fetch_live_forecast()
            if self._results_are_usable(fetched_results, now):
                results = fetched_results
                model_used = fetched_model
                self._cache["forecast"] = {
                    "at": time.time(),
                    "results": results,
                    "model_used": model_used,
                }
                cache_age = 0
                forecast_status = "live"
            elif (
                cached
                and cache_age is not None
                and cache_age <= self.settings.forecast_stale_cache_seconds
                and self._results_are_usable(cached["results"], now)
            ):
                results = cached["results"]
                model_used = cached["model_used"]
                forecast_status = "stale"
            else:
                results = []
                model_used = "unavailable"
                cache_age = None

        out = []
        if results and len(results) == len(self.hotspots):
            for h, res in zip(self.hotspots, results):
                rows = self._rows_from_result(res, now)
                out.append(assess_hotspot(h, self.model, rows, self.floods.get(h["id"], [])))
        else:
            for h in self.hotspots:
                out.append(assess_hotspot(h, self.model, [], self.floods.get(h["id"], [])))

        return {
            "generated_at": now.isoformat(),
            "forecast_model_used": model_used,
            "forecast_status": forecast_status,
            "forecast_age_seconds": cache_age,
            "lookahead_hours": LOOKAHEAD_HOURS,
            "disclaimer": DISCLAIMER,
            "credit": "Weather data by Open-Meteo.com",
            "hotspots": out,
        }
