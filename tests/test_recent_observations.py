"""Official CSV normalization and causal runtime input, never training."""

import csv
import hashlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.data.inmet_recent import CSV_COLUMNS, SOURCE_URL, import_table, latest_window, measurement, read_runtime_observations, table_records


def official_csv():
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Data", "Hora (UTC)", *CSV_COLUMNS.values()])
    for hour in range(8):
        writer.writerow(["13/10/2026", f"{hour:02d}00", *(["0,0", "26,9", "70", "1012,3"] if hour < 7 else ["", "", "", ""])])
    return out.getvalue()


class RecentObservationTests(unittest.TestCase):
    def test_official_units_decimal_comma_utc_and_trailing_placeholders(self):
        rows = table_records(official_csv(), "A301", SOURCE_URL)
        self.assertEqual(rows[0]["pressure_station_mb"], 1012.3)
        self.assertEqual(rows[0]["temperature_c"], 26.9)
        self.assertEqual(rows[0]["datetime_utc"], "2026-10-13T00:00:00+00:00")
        self.assertEqual(len(latest_window(rows)), 7)
        self.assertIsNone(rows[-1]["precipitation_mm"])

    def test_missing_never_becomes_zero(self):
        for value in (None, "", "NaN", "null", -9999, "9999", "inf"):
            self.assertIsNone(measurement(value))
        self.assertEqual(measurement("0,0"), 0)
        rows = table_records(official_csv(), "A301", SOURCE_URL)
        rows[-1]["temperature_c"] = 25  # partial latest row must block, without fallback.
        with self.assertRaises(ValueError):
            latest_window(rows)

    def test_station_headers_timestamps_gaps_and_duplicates_rejected(self):
        for text, station, source in ((official_csv(), "A302", SOURCE_URL), (official_csv(), "A301", "https://example.com"),
                                      (official_csv().replace("Hora (UTC)", "Hora local"), "A301", SOURCE_URL),
                                      (official_csv().replace("0600", "0630"), "A301", SOURCE_URL)):
            with self.assertRaises(ValueError):
                table_records(text, station, source)
        rows = table_records(official_csv(), "A301", SOURCE_URL)[:7]
        with self.assertRaises(ValueError):
            latest_window(rows + [rows[-1]])
        with self.assertRaises(ValueError):
            latest_window(rows[:3] + rows[4:])

    def test_import_provenance_atomic_state_and_future_rejection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "official.csv"
            output = Path(directory) / "runtime/observations.json"
            raw = official_csv().encode("utf-8-sig")
            path.write_bytes(raw)
            now = datetime(2026, 10, 13, 7, tzinfo=timezone.utc)
            record = import_table(path, "A301", output=output, now=now)
            loaded, observations = read_runtime_observations(output)
            self.assertEqual(record["source_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(loaded["station_code"], "A301")
            self.assertEqual(len(observations), 7)
            self.assertFalse(output.with_suffix(".tmp").exists())
            with self.assertRaises(ValueError):
                import_table(path, "A301", output=output, now=datetime(2026, 10, 13, 5, tzinfo=timezone.utc))
            self.assertEqual(json.loads(output.read_text())["source_sha256"], record["source_sha256"])


if __name__ == "__main__":
    unittest.main()
