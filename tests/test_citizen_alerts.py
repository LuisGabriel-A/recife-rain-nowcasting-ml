"""Freshness, historical isolation and public contracts over frozen decisions."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from app.server import ForecastApplication
from src.models.alert_status import citizen_forecast, current_status
from test_app import TestPredictor, synthetic_records


class CitizenAlertTests(unittest.TestCase):
    def setUp(self):
        self.app = ForecastApplication(TestPredictor(), [{"observations": synthetic_records()}])
        self.observation = pd.Timestamp("2020-06-01T06:00:00Z")

    def test_uses_fixed_decisions_local_time_without_probability_claims(self):
        result = citizen_forecast(self.app, synthetic_records(), self.observation + pd.Timedelta(minutes=30))
        self.assertEqual(result["state"], "attention")
        self.assertEqual([row["alert"] for row in result["hours"]], [False, True, False, False, False, False])
        self.assertEqual(result["hours"][1]["time_local"], "05h00")
        self.assertEqual(result["notification"]["event_id"], "2020-06-01T08:00:00+00:00")
        self.assertNotIn("probability", str(result))
        self.assertNotIn("threshold", str(result))

    def test_expired_horizon_is_excluded_from_summary(self):
        result = citizen_forecast(self.app, synthetic_records(), self.observation + pd.Timedelta(hours=2))
        self.assertEqual(result["state"], "no_signal")
        self.assertEqual([row["valid"] for row in result["hours"]], [False, False, True, True, True, True])
        self.assertIsNone(result["notification"])
        self.assertIsNone(result["hours"][1]["alert"])

    def test_stale_future_missing_and_malformed_data_have_no_forecast(self):
        for now in (self.observation + pd.Timedelta(hours=2, seconds=1), self.observation - pd.Timedelta(seconds=1)):
            result = citizen_forecast(self.app, synthetic_records(), now)
            self.assertEqual(result["state"], "unavailable")
            self.assertEqual(result["hours"], [])
            self.assertIsNone(result["notification"])
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "state.json"
            self.assertEqual(current_status(self.app, path)["state"], "unavailable")
            path.write_text("{invalid}")
            self.assertEqual(current_status(self.app, path)["state"], "unavailable")
            path.write_text("[]")
            self.assertEqual(current_status(self.app, path)["state"], "unavailable")

    def test_demo_keeps_historical_timestamp_and_never_sends_push(self):
        result = self.app.demo(0)
        self.assertTrue(result["demo"])
        self.assertEqual(result["observation_at_utc"], self.observation.isoformat())
        self.assertTrue(all(row["valid"] for row in result["hours"]))
        self.assertIsNone(result["notification"])

    def test_notification_expires_at_freshness_boundary(self):
        # A frozen +6h alert must not remain deliverable after observations expire.
        original = self.app.predict
        def later(payload):
            result = original(payload)
            for row in result["predictions"]:
                row["alert"] = row["horizon_hours"] == 6
            return result
        self.app.predict = later
        result = citizen_forecast(self.app, synthetic_records(), self.observation)
        self.assertEqual(pd.Timestamp(result["notification"]["expires_at_utc"]), self.observation + pd.Timedelta(hours=2))


if __name__ == "__main__":
    unittest.main()
