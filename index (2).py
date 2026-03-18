from http.server import BaseHTTPRequestHandler
import json, os, time

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    HAS_NACL = True
except ImportError:
    HAS_NACL = False

PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()

def verify(body: bytes, timestamp: str, signature: str) -> bool:
    if not PUBLIC_KEY or not HAS_NACL:
        return False
    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(
            timestamp.encode() + body,
            bytes.fromhex(signature)
        )
        return True
    except Exception:
        return False


class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        status = "OK - nacl loaded" if HAS_NACL else "ERROR - nacl missing"
        key_status = f"PUBLIC_KEY set ({len(PUBLIC_KEY)} chars)" if PUBLIC_KEY else "PUBLIC_KEY MISSING"
        self.wfile.write(f"R6 Bot online | {status} | {key_status}".encode())

    def do_POST(self):
        length    = int(self.headers.get("Content-Length", 0))
        body      = self.rfile.read(length)
        timestamp = self.headers.get("X-Signature-Timestamp", "")
        signature = self.headers.get("X-Signature-Ed25519", "")

        if not verify(body, timestamp, signature):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"invalid request signature")
            return

        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"bad json")
            return

        # PING — Discord sends this to verify the endpoint
        if payload.get("type") == 1:
            return self.send_json(200, {"type": 1})

        # COMMAND
        if payload.get("type") == 2:
            name = payload.get("data", {}).get("name", "")
            return self.send_json(200, {
                "type": 4,
                "data": {"content": f"Command `/{name}` received!", "flags": 64}
            })

        # fallback
        return self.send_json(200, {"type": 1})
