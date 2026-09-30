from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import sys
import webbrowser

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "engine_core"))
from bpm_v10.web.release1_adapter import calculate_release1

INDEX = (ROOT / "index.html").read_bytes()
HOME = (ROOT / "home.html").read_bytes()
PRIVACY = (ROOT / "privacy.html").read_bytes()

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            self._send(200, HOME, "text/html; charset=utf-8")
        elif self.path == "/privacy":
            self._send(200, PRIVACY, "text/html; charset=utf-8")
        elif self.path == "/health":
            self._send(200, b"ok", "text/plain; charset=utf-8")
        elif self.path in ("/calculator", "/index.html"):
            self._send(200, INDEX, "text/html; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/api/release1-calculate":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            out = calculate_release1(payload)
            self._send(200, json.dumps(out), "application/json; charset=utf-8")
        except Exception as exc:
            self._send(400, json.dumps({"error": str(exc)}), "application/json; charset=utf-8")

    def log_message(self, *_):
        pass

if __name__ == "__main__":
    port = int(os.environ.get("BPM_PORT", "8765"))
    address = ("127.0.0.1", port)
    try:
        httpd = ThreadingHTTPServer(address, Handler)
    except OSError as exc:
        print(f"\nDe BPM Calculator kan poort {port} niet gebruiken.")
        print("Sluit een eerder geopend servervenster en start start_windows.bat opnieuw.")
        print(f"Details: {exc}")
        input("Druk op Enter om dit venster te sluiten...")
        raise SystemExit(1)
    url = f"http://127.0.0.1:{port}"
    print("BPM Calculator Release 1 is gestart.")
    print(f"Open in je browser: {url}")
    webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gestopt.")
    finally:
        httpd.server_close()
