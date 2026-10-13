"""Normalize official A301 observations without filling missing measurements.

The official table export has no station column: the operator must attest A301
and its source URL. This imports runtime observations, never training data.
"""

import argparse
import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data.json_input import parse_json
from src.features.build_features import build_current_features


SOURCE_URL = "https://tempo.inmet.gov.br/TabelaEstacoes/A301"
STATE_PATH = Path(__file__).resolve().parents[2] / "app/.state/observations.json"
CSV_COLUMNS = {
    "precipitation_mm": "Chuva (mm)", "temperature_c": "Temp. Ins. (C)",
    "humidity_pct": "Umi. Ins. (%)", "pressure_station_mb": "Pressao Ins. (hPa)",
}


def measurement(value):
    if value is None or str(value).strip().lower() in {"", "null", "none", "nan"}:
        return None
    number = float(str(value).strip().replace(",", "."))
    if not math.isfinite(number) or abs(number) == 9999:
        return None
    return number


def table_records(text, station, source_url):
    if station != "A301" or source_url != SOURCE_URL:
        raise ValueError("Confirme A301 e a URL oficial da tabela; não é permitido substituir a estação.")
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")), delimiter=";")
    required = {"Data", "Hora (UTC)", *CSV_COLUMNS.values()}
    if not reader.fieldnames or not required.issubset(reader.fieldnames) or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("CSV precisa dos campos e unidades do export oficial do INMET.")
    records = []
    for row in reader:
        hour = row["Hora (UTC)"].strip()
        if not re.fullmatch(r"(?:[01]\d|2[0-3])00", hour):
            raise ValueError("Hora INMET inválida: use horas inteiras UTC no formato HH00.")
        time = datetime.strptime(row["Data"].strip(), "%d/%m/%Y").replace(hour=int(hour[:2]), tzinfo=timezone.utc)
        records.append({"datetime_utc": time.isoformat(), **{name: measurement(row[column]) for name, column in CSV_COLUMNS.items()}})
    return records


def latest_window(records):
    if not isinstance(records, list) or not records or not all(isinstance(row, dict) for row in records):
        raise ValueError("O INMET não forneceu observações.")
    ordered = sorted(records, key=lambda row: pd.Timestamp(row["datetime_utc"]))
    times = [row["datetime_utc"] for row in ordered]
    if len(times) != len(set(times)):
        raise ValueError("Há observações duplicadas no arquivo de origem.")
    measured = [i for i,row in enumerate(ordered) if any(row.get(name) is not None for name in CSV_COLUMNS)]
    if not measured:
        raise ValueError("Não há medições; ausência não significa chuva zero.")
    end = measured[-1] + 1
    window = ordered[max(0, end-7):end]
    # A partial latest measurement blocks inference; do not fall back to an older complete hour.
    build_current_features(window)
    return window


def import_table(path, station, source_url=SOURCE_URL, output=STATE_PATH, now=None):
    now = datetime.now(timezone.utc) if now is None else now
    raw = Path(path).read_bytes()
    window = latest_window(table_records(raw.decode("utf-8-sig"), station, source_url))
    if pd.Timestamp(window[-1]["datetime_utc"]) > pd.Timestamp(now):
        raise ValueError("A observação está no futuro; verifique a data e o relógio.")
    record = {"station_code": station, "source_url": source_url, "source_kind": "official_csv_import",
              "imported_at_utc": now.isoformat(), "source_sha256": hashlib.sha256(raw).hexdigest(),
              "station_attestation": "operator_confirmed_official_A301_table", "observations": window}
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    temporary.replace(output)
    return record


def read_runtime_observations(path=STATE_PATH):
    record = parse_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("station_code") != "A301" or record.get("source_url") != SOURCE_URL:
        raise ValueError("Origem das observações diferente da A301 oficial.")
    return record, latest_window(record.get("observations", []))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--station", required=True, choices=["A301"])
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--output", type=Path, default=STATE_PATH)
    args = parser.parse_args()
    try:
        record = import_table(args.csv, args.station, args.source_url, args.output)
        print(json.dumps({"station": record["station_code"], "latest_observation_utc": record["observations"][-1]["datetime_utc"],
                          "output": str(args.output), "source_sha256": record["source_sha256"]}))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f"Não foi possível importar observações: {exc}\n")


if __name__ == "__main__":
    main()
