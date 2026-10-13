"""Local academic prototype: standard-library HTTP adapter, no automatic training."""

import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from src.features.build_features import build_current_features
from src.data.json_input import parse_json
from src.features.schema import OBSERVATION_COLUMNS
from src.models.config import INPUT_PATH, OUTPUT_DIR
from src.models.predict import RainPredictor


STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_BODY_BYTES = 65536


def load_examples(dataset_path=INPUT_PATH):
    """Choose reproducible historical dry/rain examples using observed rainfall only.

    Never select examples using future targets or model scores. No example values
    are bundled with the code; data availability/provenance remains a local concern.
    """
    if not Path(dataset_path).exists():
        return []
    df = pd.read_csv(dataset_path, usecols=["datetime_utc", *OBSERVATION_COLUMNS])
    df.datetime_utc = pd.to_datetime(df.datetime_utc, utc=True)
    complete = df[OBSERVATION_COLUMNS].notna().all(axis=1).rolling(7).sum().eq(7)
    examples = []
    for name, condition in (
        ("Histórico: hora sem chuva", df.precipitation_mm.eq(0)),
        ("Histórico: chuva observada ≥10 mm/h", df.precipitation_mm.ge(10)),
    ):
        for index in df.index[complete & condition]:
            history = df.iloc[index - 6:index + 1][["datetime_utc", *OBSERVATION_COLUMNS]].copy()
            try:
                build_current_features(history)
            except ValueError:
                continue
            history.datetime_utc = history.datetime_utc.map(lambda time: time.isoformat())
            examples.append({"name": name, "observations": history.to_dict("records")})
            break
    return examples


class ForecastApplication:
    def __init__(self, predictor, examples=None):
        self.predictor = predictor
        self.examples = [] if examples is None else examples

    def predict(self, payload):
        if not isinstance(payload, dict) or set(payload) not in ({"observations"}, {"features"}):
            raise ValueError("Envie exatamente 'observations' ou 'features' em um objeto JSON.")
        timestamp = None
        if "observations" in payload:
            observations = payload["observations"]
            if not isinstance(observations, list) or len(observations) > 168:
                raise ValueError("Envie uma lista de 7 a 168 observações horárias.")
            X = build_current_features(observations)
            timestamp = X.index[-1]
        else:
            features = payload["features"]
            if isinstance(features, list):
                if len(features) > 100:
                    raise ValueError("O protótipo aceita no máximo 100 amostras por consulta.")
                X = pd.DataFrame(features)
            else:
                X = features
        predictions = self.predictor.predict(X).to_dict("records")
        for row in predictions:
            row["forecast_at_utc"] = (
                (timestamp + pd.Timedelta(hours=row["horizon_hours"])).isoformat()
                if timestamp is not None else None
            )
        return {
            "station_code": "A301", "prediction_time_utc": timestamp.isoformat() if timestamp is not None else None,
            "severe_rainfall_threshold_mm_h": 10.0, "score_is_calibrated": False,
            "predictions": predictions,
        }


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, application, **kwargs):
        self.application = application
        super().__init__(*args, **kwargs)

    def _reply(self, status, body, content_type="application/json; charset=utf-8"):
        data = json.dumps(body, ensure_ascii=False, allow_nan=False).encode("utf-8") if isinstance(body, dict) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._reply(200, {
                "status": "ok", "station_code": "A301", "horizons": list(range(1, 7)),
                "thresholds": [self.application.predictor.thresholds[h] for h in range(1, 7)],
            })
        elif path == "/api/examples":
            self._reply(200, {"examples": self.application.examples})
        elif path in ("/", "/index.html", "/styles.css", "/app.js"):
            filename = "index.html" if path == "/" else path[1:]
            mime = {"index.html": "text/html", "styles.css": "text/css", "app.js": "text/javascript"}[filename]
            self._reply(200, (STATIC_DIR / filename).read_bytes(), mime + "; charset=utf-8")
        else:
            self._reply(404, {"error": "Rota não encontrada."})

    def do_POST(self):
        if urlsplit(self.path).path != "/api/predict":
            self._reply(404, {"error": "Rota não encontrada."})
            return
        if self.headers.get_content_type() != "application/json":
            self._reply(415, {"error": "Use Content-Type: application/json."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY_BYTES:
                self._reply(413, {"error": "O corpo JSON deve ter entre 1 e 65536 bytes."})
                return
            payload = parse_json(self.rfile.read(length))
            self._reply(200, self.application.predict(payload))
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError) as exc:
            self._reply(400, {"error": f"Entrada inválida: {exc}"})

    def log_message(self, format, *args):
        # Log request/status only; never log the user's observation payload.
        print(format % args, flush=True)


def create_server(application, port=8000):
    return ThreadingHTTPServer(("127.0.0.1", port), partial(RequestHandler, application=application))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    try:
        predictor = RainPredictor(args.model_dir)
        application = ForecastApplication(predictor, load_examples())
        server = create_server(application, args.port)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Não foi possível iniciar o protótipo: {exc}\n")
    print(f"Recife Rain | http://127.0.0.1:{server.server_port} | Ctrl+C para encerrar", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
