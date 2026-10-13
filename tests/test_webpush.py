"""Opt-in storage, encrypted delivery, endpoint restrictions and stale suppression."""

import base64
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import threading

from app.webpush import PushService, validate_subscription
from app.server import ForecastApplication, create_server
from test_app import TestPredictor


@unittest.skipUnless(find_spec("pywebpush"), "Optional requirements-webpush.txt required")
class WebPushTests(unittest.TestCase):
    def setUp(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.service = PushService(self.temp.name)
        public = ec.generate_private_key(ec.SECP256R1()).public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
        self.subscription = {"endpoint": "https://fcm.googleapis.com/fcm/send/test-capability", "keys": {"p256dh": encode(public), "auth": encode(b"0123456789abcdef")}}
        self.now = datetime.now(timezone.utc)
        self.notice = {"event_id": "forecast-hour", "body": "Aviso de teste", "expires_at_utc": (self.now + timedelta(minutes=5)).isoformat(), "url": "/"}
        self.status = {"state": "attention", "demo": False, "notification": self.notice, "valid_until_utc": self.notice["expires_at_utc"]}

    def test_keys_persist_and_subscription_can_be_revoked(self):
        self.assertEqual(self.service.public_key, PushService(self.temp.name).public_key)
        self.assertTrue(self.service.subscribe(self.subscription)["enabled"])
        self.service.subscribe(self.subscription)
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM subscriptions").fetchone()[0], 1)
        self.assertFalse(self.service.unsubscribe(self.subscription)["enabled"])
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM subscriptions").fetchone()[0], 0)

    def test_http_opt_in_and_revocation_reach_private_storage(self):
        server = create_server(ForecastApplication(TestPredictor(), push_service=self.service), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{server.server_port}"
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                with urlopen(url + "/api/push/config", timeout=10) as response:
                    config = json.load(response)
                self.assertEqual(config["public_key"], self.service.public_key)
                self.assertTrue(config["enabled"])
                for route, expected in (("subscribe", True), ("unsubscribe", False)):
                    req = Request(url + "/api/push/" + route, data=json.dumps(self.subscription).encode(), headers={"Content-Type": "application/json", "Origin": url})
                    with urlopen(req, timeout=10) as response:
                        self.assertEqual(json.load(response)["enabled"], expected)
                    with self.service.connect() as db:
                        self.assertEqual(db.execute("SELECT count(*) FROM subscriptions").fetchone()[0], int(expected))
                req = Request(url + "/api/push/subscribe", data=b'{"endpoint":"http://127.0.0.1"}', headers={"Content-Type": "application/json"})
                with self.assertRaises(HTTPError) as error:
                    urlopen(req, timeout=10)
                self.assertEqual(error.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_malformed_keys_private_hosts_and_redirect_destinations_rejected(self):
        for endpoint in ("http://fcm.googleapis.com/test", "https://127.0.0.1/test", "https://fcm.googleapis.com.attacker.example/test", "https://fcm.googleapis.com:8080/test", "https://user@fcm.googleapis.com/test", "https://fcm.googleapis.com/test#fragment"):
            with self.assertRaises(ValueError):
                validate_subscription({**self.subscription, "endpoint": endpoint})
        with self.assertRaises(ValueError):
            validate_subscription({**self.subscription, "keys": {"p256dh": "abcd", "auth": "abcd"}})
        with patch("app.webpush.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(ValueError):
                validate_subscription(self.subscription, resolve=True)

    def test_actual_webpush_encrypts_payload_and_disables_http_redirects(self):
        from requests import Response
        response = Response(); response.status_code = 201
        with patch("app.webpush.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]), patch("requests.Session.post", return_value=response) as post:
            self.assertTrue(self.service.send(self.subscription, self.notice, self.now))
        sent = post.call_args.kwargs
        self.assertFalse(sent["allow_redirects"])
        self.assertEqual(sent["headers"]["Content-Encoding"], "aes128gcm")
        self.assertIn("Authorization", sent["headers"])
        self.assertNotIn(self.notice["body"].encode(), sent["data"])
        self.assertLessEqual(int(sent["headers"]["TTL"]), 300)

    def test_windows_push_uses_raw_type(self):
        from requests import Response
        response = Response(); response.status_code = 201
        subscription = {**self.subscription, "endpoint": "https://test.notify.windows.com/?token=test"}
        with patch("app.webpush.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]), patch("requests.Session.post", return_value=response) as post:
            self.assertTrue(self.service.send(subscription, self.notice, self.now))
        self.assertEqual(post.call_args.kwargs["headers"]["X-WNS-Type"], "wns/raw")

    def test_deduplicates_only_delivered_events_and_suppresses_demo_and_stale(self):
        self.service.subscribe(self.subscription)
        with patch.object(self.service, "send", return_value=True) as send:
            self.assertEqual(self.service.dispatch(self.status, self.now), 1)
            self.assertEqual(self.service.dispatch(self.status, self.now), 0)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(self.service.dispatch({**self.status, "demo": True}, self.now), 0)
            self.assertEqual(self.service.dispatch(self.status, self.now + timedelta(hours=1)), 0)
        self.assertFalse(self.service.send(self.subscription, self.notice, self.now + timedelta(hours=1)))

    def test_expired_subscriptions_removed_transient_errors_retry(self):
        self.service.subscribe(self.subscription)
        failure = RuntimeError("private remote response")
        failure.response = SimpleNamespace(status_code=410)
        with patch.object(self.service, "send", side_effect=failure):
            self.assertEqual(self.service.dispatch(self.status, self.now), 0)
        with self.service.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM subscriptions").fetchone()[0], 0)
        self.service.subscribe(self.subscription)
        with contextlib.redirect_stdout(io.StringIO()) as output, patch.object(self.service, "send", side_effect=RuntimeError("secret endpoint")):
            self.service.dispatch(self.status, self.now)
        self.assertNotIn("secret", output.getvalue())
        with patch.object(self.service, "send", return_value=True):
            self.assertEqual(self.service.dispatch(self.status, self.now), 1)


if __name__ == "__main__":
    unittest.main()
