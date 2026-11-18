"""Single-destination Gemini relay for the isolated ARTEX lab.

The ARTEX container sees only a dummy OpenAI-compatible key and this relay.
The real Gemini credential exists only in this process. No arbitrary upstream,
proxy, URL, or non-Gemini model is accepted.
"""
from __future__ import annotations

import email.utils
import json
import os
import random
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
ALLOWED_MODELS = ("gemini-3.6-flash", "gemini-3.8-flash")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
BROKER_TOKEN = os.environ.get("BROKER_TOKEN", "")
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8080"))


def retry_delay(value: str | None, attempt: int) -> float:
    if value:
        try:
            return min(12.0, max(0.0, float(value.strip())))
        except ValueError:
            try:
                parsed = email.utils.parsedate_to_datetime(value)
                return min(12.0, max(0.0, parsed.timestamp() - time.time()))
            except (TypeError, ValueError, OverflowError):
                pass
    return min(8.0, 1.5 * (2 ** attempt)) + random.uniform(0, 0.35)


def ask_google(payload: dict, model: str) -> tuple[int, bytes, dict]:
    body = dict(payload)
    body["model"] = model
    body["stream"] = False
    asked_tokens = body.get("max_tokens")
    if not isinstance(asked_tokens, int) or asked_tokens <= 0:
        body["max_tokens"] = 4096
    else:
        body["max_tokens"] = min(4096, asked_tokens)

    request = urllib.request.Request(
        UPSTREAM,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=100) as response:
            raw = response.read(3_000_000)
            headers = dict(response.headers.items())
            return response.status, raw, headers
    except urllib.error.HTTPError as exc:
        raw = exc.read(12000)
        return exc.code, raw, dict(exc.headers.items() if exc.headers else [])


class Handler(BaseHTTPRequestHandler):
    server_version = "MOMO-Gemini-Redteam-Broker/1.0"

    def log_message(self, fmt, *args):
        # Never log credentials, prompt bodies, or model responses.
        print("broker " + (fmt % args), flush=True)

    def _send(self, status: int, body: bytes, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, b'{"ok":true,"upstream":"fixed-google-gemini-endpoint"}')
        return self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self._send(404, b'{"error":"only /v1/chat/completions is available"}')
        if self.headers.get("Authorization", "") != "Bearer " + BROKER_TOKEN:
            return self._send(401, b'{"error":"broker authentication failed"}')
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 2_000_000:
                return self._send(413, b'{"error":"request size outside broker limit"}')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("body must be a JSON object")
            asked_model = payload.get("model")
            if asked_model not in ALLOWED_MODELS:
                return self._send(400, b'{"error":"model is not in the approved Gemini allowlist"}')
            if not API_KEY:
                return self._send(503, b'{"error":"Gemini credential is unavailable in the broker"}')
        except (ValueError, json.JSONDecodeError):
            return self._send(400, b'{"error":"malformed request"}')

        model_chain = [asked_model]
        if asked_model == "gemini-3.6-flash":
            model_chain.append("gemini-3.8-flash")

        last_status, last_body, last_headers = 503, b'{"error":"upstream unavailable"}', {}
        for model in model_chain:
            for attempt in range(3):
                try:
                    status, raw, headers = ask_google(payload, model)
                except (urllib.error.URLError, TimeoutError, OSError):
                    status, raw, headers = 503, b'{"error":"upstream transport failure"}', {}
                last_status, last_body, last_headers = status, raw, headers
                if 200 <= status < 300:
                    try:
                        result = json.loads(raw)
                        if isinstance(result, dict):
                            result["model"] = model
                            raw = json.dumps(result, ensure_ascii=False).encode("utf-8")
                    except (ValueError, UnicodeDecodeError):
                        pass
                    print(f"broker served model={model} status={status}", flush=True)
                    return self._send(200, raw)
                if status not in {408, 425, 429, 500, 502, 503, 504}:
                    print(f"broker rejected upstream status={status}", flush=True)
                    return self._send(status, raw[:12000])
                if attempt < 2:
                    time.sleep(retry_delay(headers.get("Retry-After"), attempt))
            print(f"broker model exhausted model={model} status={last_status}", flush=True)

        safe_body = last_body[:12000] or b'{"error":"Gemini primary and fallback unavailable"}'
        return self._send(last_status if last_status >= 400 else 503, safe_body)


if __name__ == "__main__":
    if not BROKER_TOKEN:
        raise SystemExit("BROKER_TOKEN is required")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
