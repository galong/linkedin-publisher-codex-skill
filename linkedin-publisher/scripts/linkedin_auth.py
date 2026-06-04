#!/usr/bin/env python3
"""OAuth helper for the linkedin-publisher skill.

This script intentionally never prints token values or client secrets.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
DEFAULT_CONFIG_FILE = Path("~/.config/linkedin-publisher/config.json").expanduser()
DEFAULT_TOKEN_FILE = Path("~/.config/linkedin-publisher/token.json").expanduser()
DEFAULT_API_VERSION = "202605"
DEFAULT_SCOPES = ("openid", "profile", "email", "w_member_social")


class ConfigError(RuntimeError):
    pass


def config_file_path(value: str | None = None) -> Path:
    configured = value or os.environ.get("LINKEDIN_PUBLISHER_CONFIG")
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_FILE


def read_config(path: Path | None = None) -> dict[str, Any]:
    selected = path or config_file_path()
    if not selected.exists():
        return {}
    return json.loads(selected.read_text(encoding="utf-8"))


def config_value(key: str, env_name: str | None = None, default: str | None = None) -> str | None:
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    value = read_config().get(key)
    if value is None or value == "":
        return default
    return str(value)


def env_required(name: str) -> str:
    key = name.removeprefix("LINKEDIN_").lower()
    value = config_value(key, name)
    if not value:
        raise ConfigError(f"Missing required configuration: {name} or {config_file_path()} key '{key}'")
    return value


def token_file_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    configured = config_value("token_file")
    return Path(configured).expanduser() if configured else DEFAULT_TOKEN_FILE


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Token file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def post_form(url: str, data: dict[str, str]) -> dict[str, Any]:
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LinkedIn token request failed: HTTP {exc.code}: {detail}") from exc


def api_version() -> str:
    return config_value("api_version", "LINKEDIN_API_VERSION", DEFAULT_API_VERSION) or DEFAULT_API_VERSION


def get_json(url: str, access_token: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"Authorization": f"Bearer {access_token}"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(
        url,
        headers=request_headers,
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LinkedIn GET request failed: HTTP {exc.code}: {detail}") from exc


def build_auth_url(state: str, scopes: list[str] | None) -> str:
    client_id = env_required("LINKEDIN_CLIENT_ID")
    redirect_uri = env_required("LINKEDIN_REDIRECT_URI")
    selected_scopes = scopes or list(DEFAULT_SCOPES)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(selected_scopes),
        "state": state,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


def exchange_code(code: str) -> dict[str, Any]:
    client_id = env_required("LINKEDIN_CLIENT_ID")
    client_secret = env_required("LINKEDIN_CLIENT_SECRET")
    redirect_uri = env_required("LINKEDIN_REDIRECT_URI")

    payload = post_form(
        TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    now = int(time.time())
    if "expires_in" in payload:
        payload["expires_at"] = now + int(payload["expires_in"])
    if "refresh_token_expires_in" in payload:
        payload["refresh_token_expires_at"] = now + int(payload["refresh_token_expires_in"])
    return payload


def command_auth_url(args: argparse.Namespace) -> int:
    print(build_auth_url(args.state, args.scope))
    return 0


def command_exchange(args: argparse.Namespace) -> int:
    payload = exchange_code(args.code)
    path = token_file_path(args.token_file)
    write_json(path, payload)
    print(f"Token saved to {path}. Values were not printed.")
    return 0


def command_authorize(args: argparse.Namespace) -> int:
    redirect_uri = env_required("LINKEDIN_REDIRECT_URI")
    parsed = urllib.parse.urlparse(redirect_uri)
    if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise ConfigError("authorize requires LINKEDIN_REDIRECT_URI to be a local http URL")
    if not parsed.port:
        raise ConfigError("authorize requires LINKEDIN_REDIRECT_URI to include a port")

    result: dict[str, str] = {}
    expected_path = parsed.path or "/"
    expected_state = args.state

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *values: object) -> None:
            return

        def do_GET(self) -> None:
            request_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(request_path.query)
            if request_path.path != expected_path:
                self.send_response(404)
                self.end_headers()
                return
            if query.get("state", [""])[0] != expected_state:
                result["error"] = "state mismatch"
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"LinkedIn authorization failed: state mismatch.")
                return
            if query.get("error"):
                result["error"] = query.get("error_description", query["error"])[0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"LinkedIn authorization failed. You may close this tab.")
                return
            code = query.get("code", [""])[0]
            if not code:
                result["error"] = "missing code"
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"LinkedIn authorization failed: missing code.")
                return
            result["code"] = code
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"LinkedIn authorization received. You may close this tab.")

    print("Open this LinkedIn authorization URL:")
    print(build_auth_url(expected_state, args.scope))
    print(f"Waiting for callback on {redirect_uri} ...")

    server = HTTPServer((parsed.hostname, parsed.port), CallbackHandler)
    server.timeout = args.timeout
    server.handle_request()
    server.server_close()

    if result.get("error"):
        raise RuntimeError(f"Authorization callback failed: {result['error']}")
    if not result.get("code"):
        raise RuntimeError("Timed out waiting for LinkedIn authorization callback")

    payload = exchange_code(result["code"])
    path = token_file_path(args.token_file)
    write_json(path, payload)
    print(f"Token saved to {path}. Values were not printed.")
    return 0


def command_refresh(args: argparse.Namespace) -> int:
    client_id = env_required("LINKEDIN_CLIENT_ID")
    client_secret = env_required("LINKEDIN_CLIENT_SECRET")
    path = token_file_path(args.token_file)
    current = read_json(path)
    refresh_token = current.get("refresh_token")
    if not refresh_token:
        raise ConfigError("No refresh_token is present. Re-run the authorization flow.")

    payload = post_form(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "refresh_token": str(refresh_token),
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if "refresh_token" not in payload:
        payload["refresh_token"] = refresh_token

    now = int(time.time())
    if "expires_in" in payload:
        payload["expires_at"] = now + int(payload["expires_in"])
    if "refresh_token_expires_in" in payload:
        payload["refresh_token_expires_at"] = now + int(payload["refresh_token_expires_in"])

    write_json(path, payload)
    print(f"Token refreshed in {path}. Values were not printed.")
    return 0


def command_status(args: argparse.Namespace) -> int:
    path = token_file_path(args.token_file)
    payload = read_json(path)
    now = int(time.time())
    expires_at = payload.get("expires_at")
    refresh_expires_at = payload.get("refresh_token_expires_at")

    print(f"token_file: {path}")
    print(f"has_access_token: {'yes' if payload.get('access_token') else 'no'}")
    print(f"has_refresh_token: {'yes' if payload.get('refresh_token') else 'no'}")
    if expires_at:
        remaining = int(expires_at) - now
        print(f"access_token_seconds_remaining: {remaining}")
    if refresh_expires_at:
        remaining = int(refresh_expires_at) - now
        print(f"refresh_token_seconds_remaining: {remaining}")
    if payload.get("scope"):
        print(f"scope: {payload['scope']}")
    return 0


def command_userinfo(args: argparse.Namespace) -> int:
    path = token_file_path(args.token_file)
    payload = read_json(path)
    access_token = payload.get("access_token")
    if not access_token:
        raise ConfigError(f"No access_token found in {path}")

    data = get_json(USERINFO_URL, str(access_token))
    safe = {
        key: data.get(key)
        for key in ("sub", "name", "given_name", "family_name", "email", "picture")
        if data.get(key) is not None
    }
    if safe.get("sub"):
        safe["person_urn"] = f"urn:li:person:{safe['sub']}"
    print(json.dumps(safe, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def command_config_status(args: argparse.Namespace) -> int:
    config_path = config_file_path(args.config_file)
    config = read_config(config_path)
    token_path = token_file_path(args.token_file)
    output = {
        "config_file": str(config_path),
        "config_exists": config_path.exists(),
        "token_file": str(token_path),
        "token_exists": token_path.exists(),
        "has_client_id": bool(config.get("client_id") or os.environ.get("LINKEDIN_CLIENT_ID")),
        "has_client_secret": bool(config.get("client_secret") or os.environ.get("LINKEDIN_CLIENT_SECRET")),
        "redirect_uri": config.get("redirect_uri") or os.environ.get("LINKEDIN_REDIRECT_URI"),
        "api_version": api_version(),
        "person_id": config.get("person_id"),
        "preview_name": config.get("preview_name"),
        "preview_headline": config.get("preview_headline"),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LinkedIn OAuth helper")
    parser.add_argument("--token-file", help=f"Token file path, default {DEFAULT_TOKEN_FILE}")
    parser.add_argument("--config-file", help=f"Config file path, default {DEFAULT_CONFIG_FILE}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_url = subparsers.add_parser("auth-url", help="Print LinkedIn authorization URL")
    auth_url.add_argument("--state", required=True, help="CSRF state value to verify after redirect")
    auth_url.add_argument(
        "--scope",
        action="append",
        help="OAuth scope. Repeat for multiple scopes. Defaults to posting scopes.",
    )
    auth_url.set_defaults(func=command_auth_url)

    authorize = subparsers.add_parser("authorize", help="Listen for local callback and save token")
    authorize.add_argument("--state", required=True, help="CSRF state value to verify after redirect")
    authorize.add_argument(
        "--scope",
        action="append",
        help="OAuth scope. Repeat for multiple scopes. Defaults to posting scopes.",
    )
    authorize.add_argument("--timeout", type=int, default=300, help="Seconds to wait for callback")
    authorize.set_defaults(func=command_authorize)

    exchange = subparsers.add_parser("exchange", help="Exchange authorization code for token")
    exchange.add_argument("--code", required=True, help="Authorization code from LinkedIn redirect")
    exchange.set_defaults(func=command_exchange)

    refresh = subparsers.add_parser("refresh", help="Refresh the access token when possible")
    refresh.set_defaults(func=command_refresh)

    status = subparsers.add_parser("status", help="Show token metadata without token values")
    status.set_defaults(func=command_status)

    userinfo = subparsers.add_parser("userinfo", help="Fetch OpenID userinfo without printing tokens")
    userinfo.set_defaults(func=command_userinfo)

    config_status = subparsers.add_parser("config-status", help="Show safe configuration status")
    config_status.set_defaults(func=command_config_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
