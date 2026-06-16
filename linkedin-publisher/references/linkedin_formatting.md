# LinkedIn Formatting Guide

Use this reference when preparing raw notes, Markdown, articles, or pasted drafts before previewing or publishing with `linkedin-publisher`.

## Goal

Produce a LinkedIn-ready post that is clear, professional, and easy to scan while preserving the author's original point of view. Avoid forcing every post into the same viral template.

## Default Style

For B2B fintech, payments, digital wallet, prepaid card, tolling, or enterprise technology posts:

- Use a restrained professional tone.
- Keep paragraphs short: one idea per paragraph.
- Use Unicode emphasis only for section labels, core claims, and numbered steps.
- Prefer concrete architecture, tradeoffs, and implementation details over generic motivation.
- Avoid hype, excessive emoji, and aggressive engagement bait.
- Avoid large visual dividers by default. Use `━━━━━━━━━━━━━━━━━━━━━━` only for long or clearly multi-section technical posts where section boundaries materially improve readability. For opinion, commentary, or medium-length B2B posts, prefer natural paragraphs, bold key lines, and bullets instead.

## Formatting Modes

- `light`: Clean Markdown syntax and normalize spacing without Unicode styling.
- `standard`: Use Unicode bold for headings, numbered steps, and key phrases. This is the default.
- `strong`: Add more visual structure, including italic emphasis for quotes and subtle phrases.

Use `standard` for most posts. Use `strong` only when the user explicitly wants a more stylized LinkedIn post.

## Recommended Workflow

1. Prepare or rewrite the raw content into a LinkedIn post.
2. Save the prepared post to a workspace Markdown file.
3. Run `scripts/linkedin_format.py` to convert Markdown markers into LinkedIn-safe plain text.
4. Run `scripts/linkedin_publish.py` without `--publish` to inspect the API payload.
5. Run `scripts/linkedin_preview_html.py` to create the local visual preview.
6. Publish only after explicit user confirmation.

## Content Heuristics

- The first block should create interest within about 210 characters.
- Keep the full post under LinkedIn's 3000-character post limit.
- Put hashtags at the end.
- Use 3 to 8 hashtags.
- Always include `#Bamboodt` in the final hashtag line for brand presence, unless the user explicitly asks to omit brand tagging.
- Avoid URLs in the main body unless the user insists.
- If the source content is long, compress before formatting.
- If a post uses a cover image, the opening text should not repeat all text already visible in the image.
- Do not add visual dividers just to make a post look like a LinkedIn template. Add them only when they solve a real readability problem.

## Structure Patterns

### Technical Explanation

Use for architecture, product, integration, risk, compliance, and payments content:

```text
[Strong practical question or claim]

[Short context]

━━━━━━━━━━━━━━━━━━━━━━

[Problem]

[Why it matters]

━━━━━━━━━━━━━━━━━━━━━━

[Better model or solution]

1. [Step]
2. [Step]
3. [Step]

━━━━━━━━━━━━━━━━━━━━━━

[Takeaway]

[Question or practical CTA]

#Hashtags
```

### Case Study

Use for project experience, customer scenario, or before/after posts:

```text
[Observed customer problem]

[Why the usual solution breaks]

━━━━━━━━━━━━━━━━━━━━━━

[What changed]

[3 to 5 specific implementation choices]

━━━━━━━━━━━━━━━━━━━━━━

[Result or lesson]

#Hashtags
```

### Tool Experience

Use for Codex, AI workflow, automation, and tooling posts:

```text
[What I tried]

[The friction before]

━━━━━━━━━━━━━━━━━━━━━━

[What I built or changed]

[What became easier]

━━━━━━━━━━━━━━━━━━━━━━

[What this says about the workflow]

#Hashtags
```

## Unicode Rules

LinkedIn posts are plain text. Unicode characters simulate bold and italic styling. Do not use Markdown markers in the final post body.

- Convert `**text**` to Unicode bold in `standard` and `strong` modes.
- Convert Markdown headings to Unicode bold headings in `standard` and `strong` modes.
- Convert Markdown bullets to `◈` in `standard` and `strong` modes.
- Convert ordered list digits to Unicode bold digits in `standard` and `strong` modes.
- Strip Markdown links by default and keep only the visible label.
- Append `#Bamboodt` to the final hashtag line by default and do not duplicate it if it already exists.

## Safety

Formatting is separate from publishing. Formatting scripts must not call LinkedIn APIs, read token files, or print secrets.
