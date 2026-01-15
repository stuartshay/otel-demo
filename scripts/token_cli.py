#!/usr/bin/env python3
"""
Fetch an OAuth2 access token (client credentials flow) for otel-demo.

Configurable via environment variables or CLI flags:
    COGNITO_TOKEN_URL     - Full token endpoint URL
    COGNITO_CLIENT_ID     - OAuth2 client ID
    COGNITO_CLIENT_SECRET - OAuth2 client secret
    COGNITO_SCOPE         - Space-delimited scopes (default: "openid email profile")
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _build_request(
    token_url: str, client_id: str, client_secret: str, scope: str
) -> urllib.request.Request:
    """Build a token request with Basic auth and form-encoded body."""
    body = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "scope": scope,
        }
    ).encode()

    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    req = urllib.request.Request(token_url, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", f"Basic {auth_header}")
    return req


def _print_token(payload: dict, output: str) -> None:
    """Print token in the requested format."""
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Token response missing access_token")

    if output == "header":
        print(f"Authorization: Bearer {token}")
    elif output == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(token)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch OAuth2 access token (client credentials)",
    )
    parser.add_argument(
        "--token-url",
        default=os.getenv("COGNITO_TOKEN_URL"),
        help="OAuth2 token endpoint URL (default: $COGNITO_TOKEN_URL)",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("COGNITO_CLIENT_ID"),
        help="OAuth2 client ID (default: $COGNITO_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-secret",
        default=os.getenv("COGNITO_CLIENT_SECRET"),
        help="OAuth2 client secret (default: $COGNITO_CLIENT_SECRET)",
    )
    parser.add_argument(
        "--scope",
        default=os.getenv("COGNITO_SCOPE", "openid email profile"),
        help='Space-delimited scopes (default: $COGNITO_SCOPE or "openid email profile")',
    )
    parser.add_argument(
        "--output",
        choices=["token", "header", "json"],
        default="token",
        help='Output format: token (default), header ("Authorization: Bearer ..."), or json',
    )

    args = parser.parse_args()

    missing = [
        name
        for name, val in {
            "token-url": args.token_url,
            "client-id": args.client_id,
            "client-secret": args.client_secret,
        }.items()
        if not val
    ]
    if missing:
        parser.error(f"Missing required values for: {', '.join(missing)}")

    req = _build_request(args.token_url, args.client_id, args.client_secret, args.scope)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        sys.stderr.write(f"Token request failed: {exc.code} {exc.reason}\n")
        try:
            detail = exc.read().decode()
            if detail:
                sys.stderr.write(f"Response: {detail}\n")
        except Exception:
            pass
        return 1
    except urllib.error.URLError as exc:
        sys.stderr.write(f"Token request failed: {exc}\n")
        return 1
    except json.JSONDecodeError:
        sys.stderr.write("Token request failed: invalid JSON response\n")
        return 1

    try:
        _print_token(payload, args.output)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Failed to print token: {exc}\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
