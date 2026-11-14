"""Live, no-secret smoke test for the documented OVH anonymous model route."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


ENDPOINT = "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1/chat/completions"
MODEL = "gpt-oss-120b"


def main() -> int:
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": "Reply with exactly this token and nothing else: MOMO_KEYLESS_OK",
            }
        ],
        "temperature": 0,
        "max_tokens": 32,
    }
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=75) as response:
            result = json.loads(response.read(1_000_000).decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read(500).decode("utf-8", "replace").replace("\n", " ")
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "provider": "ovh-anonymous",
                    "http_status": error.code,
                    "detail": detail,
                }
            )
        )
        return 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "provider": "ovh-anonymous",
                    "error_type": type(error).__name__,
                }
            )
        )
        return 1

    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(
            json.dumps(
                {
                    "status": "invalid-response",
                    "provider": "ovh-anonymous",
                    "top_level_keys": sorted(result) if isinstance(result, dict) else [],
                }
            )
        )
        return 1

    text = str(content or "").strip()
    passed = "MOMO_KEYLESS_OK" in text
    print(
        json.dumps(
            {
                "status": "passed" if passed else "unexpected-model-output",
                "provider": "ovh-anonymous",
                "model": MODEL,
                "response_characters": len(text),
            }
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
