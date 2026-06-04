#!/usr/bin/env python3
"""Generate a local LinkedIn-style visual preview HTML file."""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import os
import sys
from pathlib import Path


DEFAULT_CONFIG_FILE = Path("~/.config/linkedin-publisher/config.json").expanduser()
DEFAULT_OUTPUT = Path("previews/linkedin-preview.html")


class PreviewError(RuntimeError):
    pass


def config_file_path() -> Path:
    configured = os.environ.get("LINKEDIN_PUBLISHER_CONFIG")
    return Path(configured).expanduser() if configured else DEFAULT_CONFIG_FILE


def read_config() -> dict[str, str]:
    path = config_file_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def config_value(key: str, default: str) -> str:
    value = read_config().get(key)
    if value is None or value == "":
        return default
    return str(value)


def read_text(args: argparse.Namespace) -> str:
    if bool(args.text) == bool(args.text_file):
        raise PreviewError("Provide exactly one of --text or --text-file")
    if args.text_file:
        text = Path(args.text_file).expanduser().read_text(encoding="utf-8")
    else:
        text = args.text
    text = text.strip()
    if not text:
        raise PreviewError("Post text is empty")
    return text


def image_data_uri(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value).expanduser()
    if not path.exists():
        raise PreviewError(f"Image file not found: {path}")
    if not path.is_file():
        raise PreviewError(f"Image path is not a file: {path}")
    content_type = mimetypes.guess_type(str(path))[0]
    if not content_type or not content_type.startswith("image/"):
        raise PreviewError(f"Image path does not look like a supported image file: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def render_post_text(text: str) -> str:
    escaped = html.escape(text)
    return escaped.replace("\n", "<br>\n")


def initials(name: str) -> str:
    parts = [part[0] for part in name.split() if part]
    return "".join(parts[:2]).upper() or "IN"


def render_html(args: argparse.Namespace, text: str, image_uri: str | None) -> str:
    display_name = args.name or config_value("preview_name", "LinkedIn User")
    display_headline = args.headline or config_value("preview_headline", "LinkedIn post preview")
    name = html.escape(display_name)
    headline = html.escape(display_headline)
    avatar = html.escape(initials(display_name))
    body = render_post_text(text)
    image_html = ""
    if image_uri:
        image_html = f'<img class="post-image" src="{image_uri}" alt="LinkedIn post cover">'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LinkedIn Post Preview</title>
  <style>
    :root {{
      --bg: #f3f2ef;
      --card: #ffffff;
      --text: #191919;
      --muted: #666666;
      --line: #d6d6d6;
      --blue: #0a66c2;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
      font-size: 14px;
      line-height: 1.45;
    }}

    .page {{
      width: min(100%, 760px);
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}

    .toolbar {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 13px;
    }}

    .post {{
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--card);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
    }}

    .author {{
      display: grid;
      grid-template-columns: 48px 1fr;
      gap: 10px;
      padding: 14px 16px 8px;
      align-items: center;
    }}

    .avatar {{
      display: grid;
      width: 48px;
      height: 48px;
      place-items: center;
      border-radius: 50%;
      background: var(--blue);
      color: #fff;
      font-weight: 700;
      letter-spacing: 0;
    }}

    .name {{
      font-size: 15px;
      font-weight: 700;
      line-height: 1.2;
    }}

    .headline,
    .meta {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.25;
    }}

    .content {{
      padding: 0 16px 14px;
      white-space: normal;
      overflow-wrap: anywhere;
    }}

    .post-image {{
      display: block;
      width: 100%;
      max-height: 640px;
      object-fit: contain;
      border-top: 1px solid var(--line);
      background: #f8f8f8;
    }}

    .actions {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 4px;
      border-top: 1px solid var(--line);
      padding: 4px 8px;
      color: var(--muted);
      font-weight: 600;
    }}

    .action {{
      padding: 10px 6px;
      text-align: center;
      border-radius: 4px;
    }}

    .note {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
    }}

    @media (max-width: 520px) {{
      .page {{
        padding: 0 0 24px;
      }}

      .toolbar,
      .note {{
        padding: 0 12px;
      }}

      .post {{
        border-left: 0;
        border-right: 0;
        border-radius: 0;
      }}

      .actions {{
        font-size: 12px;
      }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <div class="toolbar">
      <strong>LinkedIn local preview</strong>
      <span>Not published</span>
    </div>
    <article class="post">
      <header class="author">
        <div class="avatar" aria-hidden="true">{avatar}</div>
        <div>
          <div class="name">{name}</div>
          <div class="headline">{headline}</div>
          <div class="meta">Now · Public</div>
        </div>
      </header>
      <section class="content">{body}</section>
      {image_html}
      <footer class="actions">
        <div class="action">Like</div>
        <div class="action">Comment</div>
        <div class="action">Repost</div>
        <div class="action">Send</div>
      </footer>
    </article>
    <p class="note">This is a local visual approximation for review. LinkedIn may render fonts, spacing, and truncation differently.</p>
  </main>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a local LinkedIn-style HTML preview")
    parser.add_argument("--text", help="Post body text")
    parser.add_argument("--text-file", help="Markdown or text file containing the post body")
    parser.add_argument("--image", help="Optional single image path")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output HTML path")
    parser.add_argument("--name", help="Display name for the preview")
    parser.add_argument(
        "--headline",
        help="Headline shown under the display name",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        text = read_text(args)
        image_uri = image_data_uri(args.image)
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_html(args, text, image_uri), encoding="utf-8")
        print(output)
        return 0
    except PreviewError as exc:
        print(f"Preview error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
