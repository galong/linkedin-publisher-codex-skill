#!/usr/bin/env python3
"""Preview and publish LinkedIn text or single-image posts."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


POSTS_URL = "https://api.linkedin.com/rest/posts"
IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
DEFAULT_CONFIG_FILE = Path("~/.config/linkedin-publisher/config.json").expanduser()
DEFAULT_TOKEN_FILE = Path("~/.config/linkedin-publisher/token.json").expanduser()
DEFAULT_API_VERSION = "202605"


class PublishError(RuntimeError):
    pass


def config_file_path() -> Path:
    configured = os.environ.get("LINKEDIN_PUBLISHER_CONFIG")
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_FILE


def read_config() -> dict[str, Any]:
    path = config_file_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def config_value(key: str, env_name: str | None = None, default: str | None = None) -> str | None:
    if env_name and os.environ.get(env_name):
        return os.environ[env_name]
    value = read_config().get(key)
    if value is None or value == "":
        return default
    return str(value)


def token_file_path(value: str | None) -> Path:
    if value:
        return Path(value).expanduser()
    configured = config_value("token_file")
    return Path(configured).expanduser() if configured else DEFAULT_TOKEN_FILE


def read_token(path: Path) -> str:
    if not path.exists():
        raise PublishError(f"Token file not found: {path}. Run linkedin_auth.py exchange first.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    token = payload.get("access_token")
    if not token:
        raise PublishError(f"No access_token found in {path}. Re-run OAuth.")
    expires_at = payload.get("expires_at")
    if expires_at and int(expires_at) <= int(time.time()) + 60:
        raise PublishError("Access token is expired or about to expire. Run linkedin_auth.py refresh.")
    return str(token)


def api_version() -> str:
    return config_value("api_version", "LINKEDIN_API_VERSION", DEFAULT_API_VERSION) or DEFAULT_API_VERSION


def linkedin_headers(token: str, *, content_type: str = "application/json") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": api_version(),
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": content_type,
    }


def request_json(url: str, token: str, payload: dict[str, Any]) -> tuple[int, dict[str, str], dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=linkedin_headers(token),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else {}
            return response.status, dict(response.headers), data
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PublishError(f"LinkedIn API failed: HTTP {exc.code}: {detail}") from exc


def upload_bytes(upload_url: str, token: str, image_path: Path) -> None:
    content_type = mimetypes.guess_type(str(image_path))[0] or "application/octet-stream"
    request = urllib.request.Request(
        upload_url,
        data=image_path.read_bytes(),
        headers=linkedin_headers(token, content_type=content_type),
        method="PUT",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status not in (200, 201, 202):
                raise PublishError(f"Image upload returned HTTP {response.status}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise PublishError(f"Image upload failed: HTTP {exc.code}: {detail}") from exc


def build_author(args: argparse.Namespace) -> str:
    if args.author_urn:
        if not args.author_urn.startswith("urn:li:person:"):
            raise PublishError("--author-urn must start with urn:li:person:")
        return args.author_urn
    person_id = args.person_id or config_value("person_id")
    if not person_id:
        raise PublishError(f"--person-id is required unless {config_file_path()} contains person_id")
    return f"urn:li:person:{person_id}"


def read_text(args: argparse.Namespace) -> str:
    if bool(args.text) == bool(args.text_file):
        raise PublishError("Provide exactly one of --text or --text-file")
    if args.text_file:
        text = Path(args.text_file).expanduser().read_text(encoding="utf-8")
    else:
        text = args.text
    text = text.strip()
    if not text:
        raise PublishError("Post text is empty")
    return text


def build_post_payload(author: str, commentary: str, image_urn: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "author": author,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    if image_urn:
        payload["content"] = {"media": {"id": image_urn}}
    return payload


def preview(args: argparse.Namespace, author: str, text: str, image_path: Path | None) -> None:
    placeholder_image_urn = "urn:li:image:PREVIEW_ONLY" if image_path else None
    payload = build_post_payload(author, text, placeholder_image_urn)
    output = {
        "mode": "publish" if args.publish else "preview",
        "target": "person",
        "author": author,
        "api_version": api_version(),
        "text_characters": len(text),
        "image": str(image_path) if image_path else None,
        "post_payload": payload,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def initialize_image_upload(token: str, author: str) -> str:
    payload = {"initializeUploadRequest": {"owner": author}}
    _, _, data = request_json(IMAGES_URL, token, payload)
    value = data.get("value", data)
    upload_url = value.get("uploadUrl")
    image_urn = value.get("image")
    if not upload_url or not image_urn:
        raise PublishError("LinkedIn image initialize response did not include uploadUrl and image URN")
    return str(upload_url), str(image_urn)


def publish(args: argparse.Namespace, author: str, text: str, image_path: Path | None) -> None:
    if not args.yes:
        raise PublishError("Publishing requires --yes after user confirmation")

    token = read_token(token_file_path(args.token_file))
    image_urn = None
    if image_path:
        upload_url, image_urn = initialize_image_upload(token, author)
        upload_bytes(upload_url, token, image_path)

    payload = build_post_payload(author, text, image_urn)
    status, headers, data = request_json(POSTS_URL, token, payload)
    result = {
        "status": status,
        "linkedin_id": headers.get("x-restli-id") or headers.get("X-RestLi-Id"),
        "response": data,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def validate_image(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.exists():
        raise PublishError(f"Image file not found: {path}")
    if not path.is_file():
        raise PublishError(f"Image path is not a file: {path}")
    content_type = mimetypes.guess_type(str(path))[0]
    if not content_type or not content_type.startswith("image/"):
        raise PublishError(f"Image path does not look like a supported image file: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview or publish a LinkedIn post")
    parser.add_argument("--person-id", help="LinkedIn person ID for author URN")
    parser.add_argument("--author-urn", help="Full personal author URN. Overrides --person-id")
    parser.add_argument("--text", help="Post body text")
    parser.add_argument("--text-file", help="Markdown or text file containing the post body")
    parser.add_argument("--image", help="Optional single image path")
    parser.add_argument("--token-file", help=f"Token file path, default {DEFAULT_TOKEN_FILE}")
    parser.add_argument("--publish", action="store_true", help="Actually call LinkedIn APIs")
    parser.add_argument("--yes", action="store_true", help="Required with --publish after confirmation")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        author = build_author(args)
        text = read_text(args)
        image_path = validate_image(args.image)
        preview(args, author, text, image_path)
        if args.publish:
            publish(args, author, text, image_path)
        return 0
    except PublishError as exc:
        print(f"Publish error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
