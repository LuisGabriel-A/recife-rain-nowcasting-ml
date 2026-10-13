"""Real HTTP requests and existing-model integration; no production training."""

import contextlib
import io
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pandas as pd
import numpy as np

from app.server import ForecastApplication, create_server, load_examples
from src.features.build_features import build_current_features
from src.features.schema import FEATURE_COLUMNS, validate_features
from src.models.config import FINAL_CONFIGURATIONS, INPUT_PATH, OUTPUT_DIR
from src.models.predict import RainPredictor


def synthetic_records():
    return [{
        "datetime_utc": f"2020-06-01T0{hour}:00:00Z", "precipitation_mm": 0.0,
        "temperature_c": 25.0, "humidity_pct": 80.0, "pressure_station_mb": 1010.0,
    } for hour in range(7)]


class TestPredictor:
    thresholds = {h: c["threshold"] for h, c in FINAL_CONFIGURATIONS.items()}

    def predict(self, X):
        X = validate_features(X)
        return pd.DataFrame([{
            "sample_position": position, "horizon_hours": horizon,
            "model_name": config["model_name"], "probability": 0.5,
            "decision_threshold": config["threshold"], "alert": 0.5 >= config["threshold"],
        } for position in range(len(X)) for horizon, config in FINAL_CONFIGURATIONS.items()])


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = create_server(ForecastApplication(TestPredictor()), port=0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, payload=None, content_type="application/json", raw=None):
        data = raw if raw is not None else json.dumps(payload).encode() if payload is not None else None
        req = Request(self.url + path, data=data, headers={"Content-Type": content_type})
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                response = urlopen(req, timeout=10)
            except HTTPError as exc:
                response = exc
            with response:
                body = response.read()
                if response.headers.get_content_type() == "application/json":
                    body = json.loads(body)
                return response.status, body, response.headers

    def test_static_health_and_examples(self):
        for path in ("/", "/styles.css", "/app.js", "/api/health", "/api/examples", "/api/status", "/api/push/config", "/manifest.webmanifest", "/sw.js", "/icon.svg", "/icon-180.png", "/icon-192.png", "/icon-512.png", "/laboratorio", "/laboratory.js", "/laboratory.css"):
            with self.subTest(path=path):
                status, body, headers = self.request(path)
                self.assertEqual(status, 200)
                self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/api/health")[1]["thresholds"], [0.99, 0.06, 0.78, 0.79, 0.85, 0.67])

    def test_push_disabled_missing_demo_and_private_state_not_exposed(self):
        self.assertFalse(self.request("/api/push/config")[1]["enabled"])
        self.assertEqual(self.request("/api/push/subscribe", {"endpoint": "test"})[0], 503)
        self.assertEqual(self.request("/api/demo/1")[0], 404)
        self.assertEqual(self.request("/.state/vapid_private.pem")[0], 404)

    def test_cross_origin_requests_rejected(self):
        req = Request(self.url + "/api/push/subscribe", data=b"{}", headers={"Content-Type": "application/json", "Origin": "https://other.example"})
        with self.assertRaises(HTTPError) as result:
            urlopen(req, timeout=10)
        self.assertEqual(result.exception.code, 403)

    def test_citizen_home_has_no_measurement_form_and_status_has_no_scores(self):
        home = self.request("/")[1].decode("utf-8")
        self.assertNotIn("<input", home)
        self.assertIn("Receber avisos", home)
        body = self.request("/api/status")[1]
        self.assertIn(body["state"], ("attention", "no_signal", "unavailable"))
        self.assertNotIn("probability", str(body))
        self.assertEqual(body["station_code"], "A301")

    def test_history_predictions_have_six_correct_forecast_times(self):
        status, body, _ = self.request("/api/predict", {"observations": synthetic_records()})
        self.assertEqual(status, 200)
        self.assertEqual(body["prediction_time_utc"], "2020-06-01T06:00:00+00:00")
        self.assertFalse(body["score_is_calibrated"])
        self.assertEqual(len(body["predictions"]), 6)
        self.assertEqual(body["predictions"][-1]["forecast_at_utc"], "2020-06-01T12:00:00+00:00")

    def test_prepared_features_and_batch(self):
        features = build_current_features(synthetic_records()).iloc[0].to_dict()
        for values in (features, [features, features]):
            status, body, _ = self.request("/api/predict", {"features": values})
            self.assertEqual(status, 200)
            self.assertIsNone(body["prediction_time_utc"])
            self.assertEqual(len(body["predictions"]), 12 if isinstance(values, list) else 6)

    def test_invalid_json_content_type_and_size(self):
        self.assertEqual(self.request("/api/predict", raw=b"{broken")[0], 400)
        self.assertEqual(self.request("/api/predict", raw=b"{}", content_type="text/plain")[0], 415)
        self.assertEqual(self.request("/api/predict", raw=b" " * 65537)[0], 413)
        self.assertEqual(self.request("/api/predict", raw=b'{"features": {}}')[0], 400)
        self.assertEqual(self.request("/api/predict", raw=b'{"features": {}, "features": {}}')[0], 400)
        self.assertEqual(self.request("/api/predict", raw=b'{"features": {"precipitation_mm": NaN}}')[0], 400)

    def test_invalid_history_schema_and_future_columns(self):
        incomplete = synthetic_records()[:6]
        gapped = synthetic_records()
        gapped[-1]["datetime_utc"] = "2020-06-01T08:00:00Z"
        missing = synthetic_records()
        missing[0]["precipitation_mm"] = None
        for payload in (
            {"observations": incomplete}, {"observations": gapped}, {"observations": missing},
            {"features": dict.fromkeys([*FEATURE_COLUMNS, "target_1h"], 0.0)},
            {"features": {}, "observations": synthetic_records()},
            {"observations": synthetic_records() * 25},
        ):
            with self.subTest(payload=list(payload)):
                status, body, _ = self.request("/api/predict", payload)
                self.assertEqual(status, 400)
                self.assertIn("error", body)

    def test_unknown_paths_do_not_expose_workspace(self):
        for path in ("/../models/model_metadata.json", "/models/model_1h.joblib", "/api/missing"):
            self.assertEqual(self.request(path)[0], 404)


@unittest.skipUnless((OUTPUT_DIR / "model_metadata.json").exists() and INPUT_PATH.exists(),
                     "Local trained artifacts and dataset required for application integration.")
class RealApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = RainPredictor()
        cls.examples = load_examples()
        cls.app = ForecastApplication(cls.predictor, cls.examples)

    def test_examples_use_only_past_observations_and_match_dataset(self):
        self.assertEqual(len(self.examples), 2)
        df = pd.read_csv(INPUT_PATH, index_col="datetime_utc")
        df.index = pd.to_datetime(df.index, utc=True)
        for example in self.examples:
            self.assertEqual(set(example["observations"][0]), {
                "datetime_utc", "precipitation_mm", "temperature_c", "humidity_pct", "pressure_station_mb",
            })
            X = build_current_features(example["observations"])
            pd.testing.assert_series_equal(X.iloc[0], df.loc[X.index[0], FEATURE_COLUMNS], check_names=False, atol=1e-10)

    def test_existing_models_produce_same_history_and_prepared_outputs(self):
        for example in self.examples:
            result = self.app.predict({"observations": example["observations"]})
            X = build_current_features(example["observations"])
            direct = self.predictor.predict(X).to_dict("records")
            stripped = [{k: v for k, v in p.items() if k != "forecast_at_utc"} for p in result["predictions"]]
            for actual, expected in zip(stripped, direct):
                np.testing.assert_allclose(actual.pop("probability"), expected.pop("probability"), rtol=0, atol=1e-14)
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
