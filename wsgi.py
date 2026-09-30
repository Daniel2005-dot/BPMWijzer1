"""WSGI entry point for hosting BPM Calculator Release 1.

Run with a production WSGI server, for example Waitress:
    waitress-serve --listen=*:8080 wsgi:application
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "engine_core"))

from bpm_v10.web.release1_adapter import calculate_release1  # noqa: E402

INDEX = (ROOT / "index.html").read_bytes()
HOME = (ROOT / "home.html").read_bytes()
PRIVACY = (ROOT / "privacy.html").read_bytes()
MAX_BODY_BYTES = 16 * 1024


def _response(start_response, status: str, body: bytes, content_type: str):
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
            ("X-Content-Type-Options", "nosniff"),
            ("Cache-Control", "no-store"),
        ],
    )
    return [body]


def application(environ, start_response) -> Iterable[bytes]:
    """Serve the Release 1 page and its calculation endpoint."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/":
        return _response(start_response, "200 OK", HOME, "text/html; charset=utf-8")

    if method == "GET" and path == "/privacy":
        return _response(start_response, "200 OK", PRIVACY, "text/html; charset=utf-8")

    if method == "GET" and path == "/health":
        return _response(start_response, "200 OK", b"ok", "text/plain; charset=utf-8")

    if method == "GET" and path in ("/calculator", "/index.html"):
        return _response(start_response, "200 OK", INDEX, "text/html; charset=utf-8")

    if method != "POST" or path != "/api/release1-calculate":
        return _response(start_response, "404 Not Found", b"Not found", "text/plain; charset=utf-8")

    if "application/json" not in environ.get("CONTENT_TYPE", "").lower():
        body = json.dumps({"error": "Verstuur de gegevens als JSON."}, ensure_ascii=False).encode("utf-8")
        return _response(start_response, "415 Unsupported Media Type", body, "application/json; charset=utf-8")

    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
        if length < 1 or length > MAX_BODY_BYTES:
            raise ValueError("De aanvraag is leeg of te groot.")
        raw = environ["wsgi.input"].read(length)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("De invoer is ongeldig.")
        result = calculate_release1(payload)
        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        return _response(start_response, "200 OK", body, "application/json; charset=utf-8")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        body = json.dumps({"error": str(exc)}, ensure_ascii=False).encode("utf-8")
        return _response(start_response, "400 Bad Request", body, "application/json; charset=utf-8")
    except Exception:
        # Keep internal exceptions out of responses shown to website visitors.
        body = json.dumps({"error": "De berekening is niet gelukt. Probeer het opnieuw."}, ensure_ascii=False).encode("utf-8")
        return _response(start_response, "500 Internal Server Error", body, "application/json; charset=utf-8")
