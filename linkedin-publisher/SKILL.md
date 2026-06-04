---
name: linkedin-publisher
description: Publish prepared LinkedIn posts from Codex to a LinkedIn personal profile using LinkedIn OAuth, Posts API, and optional single-image upload. Use when the user asks to preview, prepare, or publish LinkedIn content from a text file or pasted draft.
metadata:
  short-description: Preview and publish LinkedIn posts
---

# LinkedIn Publisher

Use this skill to publish a prepared LinkedIn post to a personal LinkedIn profile.

The first version supports public text posts and public single-image posts. Do not use this skill for scheduled posts, edits, deletes, comments, videos, documents, carousels, or analytics.

## Safety Rules

- Never print, paste, or log `LINKEDIN_CLIENT_SECRET`, access tokens, refresh tokens, authorization codes, or `.linkedin/token.json` contents.
- Never publish without an explicit final user confirmation.
- Always run a preview first. The publish script is safe by default and only posts when called with both `--publish` and `--yes`.
- Do not publish to organization Pages in this version.
- Stop if image upload fails. Do not publish a text-only fallback unless the user explicitly asks.

## Setup

The user must create a LinkedIn Developer application and obtain the required products/scopes.

Required environment variables:

```bash
export LINKEDIN_CLIENT_ID="..."
export LINKEDIN_CLIENT_SECRET="..."
export LINKEDIN_REDIRECT_URI="http://localhost:8080/callback"
```

Preferred persistent config:

```text
~/.config/linkedin-publisher/config.json
~/.config/linkedin-publisher/token.json
```

Read config from the persistent file first. Environment variables may override config values. Do not store secrets in `SKILL.md`, `agents/openai.yaml`, or any repository-tracked file.

Recommended scopes:

- `w_member_social` for personal profile posting

## OAuth Workflow

Generate an authorization URL:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py auth-url --state "manual-check"
```

Recommended local callback flow:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py authorize --state "manual-check"
```

Manual fallback: after approving the LinkedIn application, exchange the returned `code`:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py exchange --code "<authorization_code>"
```

Refresh the token when a refresh token is available:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py refresh
```

Check token status without revealing token values:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py status
```

Check safe persistent configuration status:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py config-status
```

Fetch the OpenID user profile and derive the personal author URN:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py userinfo
```

## Publishing Workflow

Preview from a Markdown file:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md"
```

Preview pasted text:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text "Post body here"
```

Preview a single-image post:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./image.png"
```

Generate a local visual HTML preview:

```bash
python3 linkedin-publisher/scripts/linkedin_preview_html.py \
  --text-file "./post.md" \
  --image "./image.png" \
  --output "./previews/linkedin-preview.html"
```

Publish only after the user approves the preview:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./image.png" \
  --publish \
  --yes
```

## References

Read `references/linkedin_api.md` when implementing, debugging API errors, or explaining required permissions.
