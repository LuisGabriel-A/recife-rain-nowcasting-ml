"""Citizen-facing presentation of frozen model decisions; no model selection."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from src.data.inmet_recent import STATE_PATH, read_runtime_observations


MAX_OBSERVATION_AGE = timedelta(hours=2)  # Operational freshness gate, not a fitted/model threshold.
LOCAL_ZONE = ZoneInfo("America/Fortaleza")


def citizen_forecast(application, observations, now, demo=False, source=None):
    now = pd.Timestamp(now)
    result = application.predict({"observations": observations})
    observation = pd.Timestamp(result["prediction_time_utc"])
    age = now-observation
    if not demo and (age < pd.Timedelta(0) or age > MAX_OBSERVATION_AGE):
        return unavailable("stale" if age >= pd.Timedelta(0) else "future", now, observation)
    hours = []
    for prediction in result["predictions"]:
        time = pd.Timestamp(prediction["forecast_at_utc"])
        valid = demo or time > now
        hours.append({"horizon_hours": prediction["horizon_hours"], "forecast_at_utc": time.isoformat(),
                      "time_local": time.tz_convert(LOCAL_ZONE).strftime("%Hh%M"),
                      "alert": bool(prediction["alert"]) if valid else None, "valid": valid,
                      "label": "Chuva forte" if valid and prediction["alert"] else "Sem indicação" if valid else "Horário encerrado"})
    warned = [row for row in hours if row["valid"] and row["alert"]]
    state = "attention" if warned else "no_signal"
    first = warned[0] if warned else None
    last = observations[-1]
    return {"state": state, "demo": demo, "station_code": "A301", "city": "Recife",
            "generated_at_utc": now.isoformat(), "observation_at_utc": observation.isoformat(),
            "observation_time_local": observation.tz_convert(LOCAL_ZONE).strftime("%Hh%M"),
            "source_kind": source.get("source_kind") if source else "historical_demo",
            "source_url": source.get("source_url") if source else None,
            "valid_until_utc": (observation + MAX_OBSERVATION_AGE).isoformat(),
            "title": "Atenção para chuva forte" if warned else "Sem indicação de chuva forte",
            "message": f"Há indicação de chuva forte perto das {first['time_local']} em Recife." if first else
                       "Os dados disponíveis não indicam chuva forte nas horas mostradas. Isso não elimina a possibilidade de chuva.",
            "hours": hours, "current": {name: last[name] for name in ("temperature_c", "humidity_pct", "precipitation_mm")},
            "notification": {"event_id": first["forecast_at_utc"], "title": "AlertaChuva Recife",
                             "body": f"Atenção: indicação de chuva forte perto das {first['time_local']}. Acompanhe os avisos oficiais.",
                             "expires_at_utc": min(pd.Timestamp(first["forecast_at_utc"]), observation + MAX_OBSERVATION_AGE).isoformat(),
                             "url": "/"} if first and not demo else None}


def unavailable(reason, now, observation=None):
    return {"state": "unavailable", "reason": reason, "demo": False, "city": "Recife", "station_code": "A301",
            "generated_at_utc": pd.Timestamp(now).isoformat(), "observation_at_utc": observation.isoformat() if observation is not None else None,
            "title": "Previsão indisponível agora", "message": "Estamos aguardando dados recentes e completos para atualizar o aviso de chuva.",
            "hours": [], "current": None, "notification": None}


def current_status(application, path=STATE_PATH, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    try:
        source, observations = read_runtime_observations(path)
        return citizen_forecast(application, observations, now, source=source)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return unavailable("missing_or_invalid_observations", now)
