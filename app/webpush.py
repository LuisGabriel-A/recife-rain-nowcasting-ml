"""Opt-in standards Web Push; private keys/subscriptions stay in ignored state."""

import base64
from contextlib import contextmanager
import ipaddress
import json
import socket
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


STATE_DIR = Path(__file__).resolve().parent / ".state"
PUSH_CONTACT = "https://github.com/LuisGabriel-A/recife-rain-nowcasting-ml"


def decode_key(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError("Chave da inscrição inválida.")
    try:
        return base64.b64decode(value + "="*(-len(value)%4), altchars=b"-_", validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Chave da inscrição inválida.") from exc


def validate_subscription(subscription, resolve=False):
    if not isinstance(subscription, dict) or set(subscription)-{"endpoint", "keys", "expirationTime"}:
        raise ValueError("Formato da inscrição inválido.")
    endpoint = subscription.get("endpoint")
    if not isinstance(endpoint, str) or len(endpoint) > 3000:
        raise ValueError("Endereço de push inválido.")
    parsed = urlsplit(endpoint)
    host = parsed.hostname or ""
    allowed = host in {"fcm.googleapis.com", "updates.push.services.mozilla.com", "web.push.apple.com"} or host.endswith(".notify.windows.com")
    if not allowed or parsed.scheme != "https" or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Serviço de push não permitido.")
    keys = subscription.get("keys")
    if not isinstance(keys, dict) or set(keys) != {"p256dh", "auth"}:
        raise ValueError("Inscrição sem chaves de criptografia válidas.")
    public, auth = decode_key(keys["p256dh"]), decode_key(keys["auth"])
    if len(public) != 65 or public[0] != 4 or len(auth) != 16:
        raise ValueError("Tamanho de chave inválido.")
    from cryptography.hazmat.primitives.asymmetric import ec
    ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), public)
    if resolve:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        if not addresses or not all(ipaddress.ip_address(item[4][0]).is_global for item in addresses):
            raise ValueError("Destino de push não público.")
    return {"endpoint": endpoint, "keys": dict(keys)}


class PushService:
    def __init__(self, directory=STATE_DIR, contact=PUSH_CONTACT):
        self.directory = Path(directory)
        contact_url = urlsplit(contact)
        if contact_url.scheme != "https" or not contact_url.hostname or contact_url.username or contact_url.password:
            raise ValueError("Use uma URL HTTPS pública de contato para o operador.")
        self.contact = contact
        self.lock = threading.RLock()
        self.enabled = False
        try:
            from py_vapid import Vapid
            from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
            import pywebpush
        except ImportError:
            self.public_key = None
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.key_path = self.directory / "vapid_private.pem"
        if not self.key_path.exists():
            vapid = Vapid()
            vapid.generate_keys()
            vapid.save_key(str(self.key_path))
            self.key_path.chmod(0o600)
        vapid = Vapid.from_file(str(self.key_path))
        # RFC 8292 permits HTTPS contact URLs with paths. py-vapid's legacy
        # regex rejects paths, so validate the URL above and use its supported option.
        vapid.conf["no-strict"] = True
        self.vapid = vapid
        self.public_key = base64.urlsafe_b64encode(vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)).decode().rstrip("=")
        self.database = self.directory / "subscriptions.sqlite3"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS subscriptions (endpoint TEXT PRIMARY KEY, payload TEXT NOT NULL, last_event TEXT)")
        self.enabled = True

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def config(self):
        return {"enabled": self.enabled, "public_key": self.public_key,
                "requires_https_on_phone": True, "requires_server_running": True}

    def subscribe(self, subscription):
        if not self.enabled:
            raise ValueError("Instale requirements-webpush.txt para habilitar avisos neste servidor.")
        subscription = validate_subscription(subscription)
        with self.lock, self.connect() as db:
            if db.execute("SELECT count(*) FROM subscriptions").fetchone()[0] >= 1000 and not db.execute("SELECT 1 FROM subscriptions WHERE endpoint=?", (subscription["endpoint"],)).fetchone():
                raise ValueError("Limite do protótipo atingido.")
            db.execute("INSERT INTO subscriptions(endpoint,payload) VALUES (?,?) ON CONFLICT(endpoint) DO UPDATE SET payload=excluded.payload",
                       (subscription["endpoint"], json.dumps(subscription)))
        return {"enabled": True}

    def unsubscribe(self, subscription):
        if self.enabled:
            subscription = validate_subscription(subscription)
            with self.lock, self.connect() as db:
                db.execute("DELETE FROM subscriptions WHERE endpoint=?", (subscription["endpoint"],))
        return {"enabled": False}

    def send(self, subscription, notification, now=None):
        from pywebpush import webpush
        import requests

        now = datetime.now(timezone.utc) if now is None else now
        expiry = datetime.fromisoformat(notification["expires_at_utc"])
        ttl = min(600, int((expiry-now).total_seconds()))
        if ttl <= 0:
            return False
        subscription = validate_subscription(subscription, resolve=True)

        class NoRedirectSession(requests.Session):
            def post(self, url, **kwargs):
                kwargs["allow_redirects"] = False
                return super().post(url, **kwargs)

        headers = {"X-WNS-Type": "wns/raw"} if urlsplit(subscription["endpoint"]).hostname.endswith(".notify.windows.com") else {}
        with NoRedirectSession() as session:
            session.trust_env = False
            response = webpush(subscription, data=json.dumps(notification, ensure_ascii=False),
                               vapid_private_key=self.vapid, vapid_claims={"sub": self.contact},
                               requests_session=session, headers=headers, ttl=ttl, timeout=10)
        return 200 <= response.status_code < 300

    def dispatch(self, status, now=None):
        if not self.enabled or status.get("demo") or status.get("state") != "attention" or not status.get("notification"):
            return 0
        now = datetime.now(timezone.utc) if now is None else now
        if datetime.fromisoformat(status["valid_until_utc"]) <= now:
            return 0
        notification = status["notification"]
        sent = 0
        with self.lock, self.connect() as db:
            rows = db.execute("SELECT endpoint,payload,last_event FROM subscriptions").fetchall()
            for endpoint, payload, last in rows:
                if last == notification["event_id"]:
                    continue
                try:
                    if self.send(json.loads(payload), notification, now):
                        db.execute("UPDATE subscriptions SET last_event=? WHERE endpoint=?", (notification["event_id"], endpoint))
                        sent += 1
                except Exception as exc:
                    # Never print capability URLs, private keys or remote response bodies.
                    response = getattr(exc, "response", None)
                    if response is not None and response.status_code in (404, 410):
                        db.execute("DELETE FROM subscriptions WHERE endpoint=?", (endpoint,))
                    else:
                        print("Não foi possível entregar um aviso; tentaremos novamente.", flush=True)
        return sent
