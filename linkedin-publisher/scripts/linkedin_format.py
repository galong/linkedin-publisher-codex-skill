#!/usr/bin/env python3
"""Format Markdown or plain text for LinkedIn posts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MAX_LINKEDIN_CHARS = 3000
SEE_MORE_HINT_CHARS = 210
DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━"
DEFAULT_BRAND_HASHTAG = "#Bamboodt"


class FormatError(RuntimeError):
    pass


def styled_char(char: str, style: str) -> str:
    code = ord(char)
    if style == "bold":
        if 65 <= code <= 90:
            return chr(0x1D5D4 + code - 65)
        if 97 <= code <= 122:
            return chr(0x1D5EE + code - 97)
        if 48 <= code <= 57:
            return chr(0x1D7EC + code - 48)
    if style == "italic":
        if 65 <= code <= 90:
            return chr(0x1D608 + code - 65)
        if 97 <= code <= 122:
            return chr(0x1D622 + code - 97)
    if style == "bold_italic":
        if 65 <= code <= 90:
            return chr(0x1D63C + code - 65)
        if 97 <= code <= 122:
            return chr(0x1D656 + code - 97)
    return char


def style_text(text: str, style: str) -> str:
    return "".join(styled_char(char, style) for char in text)


def read_source(args: argparse.Namespace) -> str:
    if bool(args.text) == bool(args.text_file):
        raise FormatError("Provide exactly one of --text or --text-file")
    if args.text_file:
        text = Path(args.text_file).expanduser().read_text(encoding="utf-8")
    else:
        text = args.text
    text = text.strip()
    if not text:
        raise FormatError("Source text is empty")
    return text


def strip_markdown_links(text: str, keep_links: bool) -> str:
    def replace(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        url = match.group(2).strip()
        return f"{label} ({url})" if keep_links else label

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace, text)


def apply_inline_markdown(text: str, mode: str) -> str:
    if mode == "light":
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
        text = re.sub(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)", r"\1", text)
        return text

    text = re.sub(r"\*\*(.+?)\*\*", lambda m: style_text(m.group(1), "bold"), text)
    text = re.sub(r"__(.+?)__", lambda m: style_text(m.group(1), "bold"), text)
    if mode == "strong":
        text = re.sub(
            r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)",
            lambda m: style_text(m.group(1), "italic"),
            text,
        )
        text = re.sub(
            r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)",
            lambda m: style_text(m.group(1), "italic"),
            text,
        )
    else:
        text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
        text = re.sub(r"(?<!_)_(?!\s)(.+?)(?<!\s)_(?!_)", r"\1", text)
    return text


def format_ordered_number(value: str, mode: str) -> str:
    if mode == "light":
        return value
    return style_text(value, "bold")


def normalize_blank_lines(lines: list[str]) -> list[str]:
    output: list[str] = []
    previous_blank = False
    for line in lines:
        blank = line.strip() == ""
        if blank and previous_blank:
            continue
        output.append("" if blank else line.rstrip())
        previous_blank = blank
    while output and output[0] == "":
        output.pop(0)
    while output and output[-1] == "":
        output.pop()
    return output


def normalized_hashtag(value: str) -> str:
    tag = value.strip()
    if not tag:
        raise FormatError("Brand hashtag cannot be empty")
    if not tag.startswith("#"):
        tag = f"#{tag}"
    if re.search(r"\s", tag):
        raise FormatError(f"Brand hashtag must not contain spaces: {value}")
    return tag


def append_brand_hashtag(text: str, brand_hashtag: str | None) -> str:
    if not brand_hashtag:
        return text
    tag = normalized_hashtag(brand_hashtag)
    pattern = re.compile(rf"(?<!\w){re.escape(tag)}(?!\w)", re.IGNORECASE)
    if pattern.search(text):
        return text

    lines = text.split("\n")
    last_nonempty = next((index for index in range(len(lines) - 1, -1, -1) if lines[index].strip()), None)
    if last_nonempty is None:
        return tag

    hashtag_line = lines[last_nonempty].strip()
    if hashtag_line.startswith("#") and all(part.startswith("#") for part in hashtag_line.split()):
        lines[last_nonempty] = f"{lines[last_nonempty].rstrip()} {tag}"
        return "\n".join(lines).strip()

    return f"{text.rstrip()}\n\n{tag}"


def format_blocks(text: str, mode: str, keep_links: bool) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = strip_markdown_links(text, keep_links)
    output: list[str] = []
    in_code_fence = False

    for raw_line in text.split("\n"):
        line = raw_line.strip()

        if line.startswith("```"):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            output.append(raw_line.rstrip())
            continue

        if not line:
            output.append("")
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            heading_text = apply_inline_markdown(heading.group(2).strip(), mode)
            output.append(style_text(heading_text, "bold") if mode != "light" else heading_text)
            continue

        if re.match(r"^[-*_]{3,}$", line):
            output.append(DIVIDER if mode != "light" else "")
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet:
            prefix = "◈ " if mode != "light" else "- "
            output.append(prefix + apply_inline_markdown(bullet.group(1).strip(), mode))
            continue

        ordered = re.match(r"^(\d+)[.)]\s+(.+)$", line)
        if ordered:
            number = format_ordered_number(ordered.group(1), mode)
            output.append(f"{number}. {apply_inline_markdown(ordered.group(2).strip(), mode)}")
            continue

        quote = re.match(r"^>\s*(.+)$", line)
        if quote:
            quote_text = apply_inline_markdown(quote.group(1).strip(), mode)
            output.append(style_text(quote_text, "italic") if mode == "strong" else quote_text)
            continue

        output.append(apply_inline_markdown(line, mode))

    return "\n".join(normalize_blank_lines(output)).strip()


def build_report(text: str) -> list[str]:
    first_paragraph = text.split("\n\n", 1)[0]
    report = [
        f"characters={len(text)}",
        f"first_block_characters={len(first_paragraph)}",
    ]
    if len(text) > MAX_LINKEDIN_CHARS:
        report.append(f"warning=over_linkedin_limit_{MAX_LINKEDIN_CHARS}")
    if len(first_paragraph) > SEE_MORE_HINT_CHARS:
        report.append(f"warning=first_block_over_{SEE_MORE_HINT_CHARS}_chars")
    if "http://" in text or "https://" in text:
        report.append("warning=body_contains_url")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Format Markdown or plain text for a LinkedIn post")
    parser.add_argument("--text", help="Source post text")
    parser.add_argument("--text-file", help="Markdown or text file containing source content")
    parser.add_argument("--output", help="Write formatted text to this file")
    parser.add_argument(
        "--mode",
        choices=("light", "standard", "strong"),
        default="standard",
        help="Formatting strength. Default: standard",
    )
    parser.add_argument(
        "--keep-links",
        action="store_true",
        help="Keep markdown link URLs in the body. Default strips URLs and keeps link labels.",
    )
    parser.add_argument(
        "--brand-hashtag",
        default=DEFAULT_BRAND_HASHTAG,
        help=f"Brand hashtag appended to the final hashtag line. Default: {DEFAULT_BRAND_HASHTAG}",
    )
    parser.add_argument(
        "--no-brand-hashtag",
        action="store_true",
        help="Do not append the default brand hashtag.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print character-count and risk report to stderr",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        formatted = format_blocks(read_source(args), args.mode, args.keep_links)
        formatted = append_brand_hashtag(
            formatted,
            None if args.no_brand_hashtag else args.brand_hashtag,
        )
        if args.output:
            output = Path(args.output).expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(formatted + "\n", encoding="utf-8")
            print(output)
        else:
            print(formatted)
        if args.report:
            print("\n".join(build_report(formatted)), file=sys.stderr)
        return 0
    except FormatError as exc:
        print(f"Format error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
