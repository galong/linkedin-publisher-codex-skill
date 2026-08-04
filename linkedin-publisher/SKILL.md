---
name: linkedin-publisher
description: Prepare, format, preview, and publish LinkedIn posts from Codex to a personal profile using LinkedIn OAuth and the Posts API, and prepare differentiated manual handoffs for LinkedIn Groups. Use when the user asks to draft, format, convert Markdown, preview, publish, or adapt LinkedIn content for a personal profile or group.
metadata:
  short-description: Format, preview, and publish LinkedIn posts
---

# LinkedIn Publisher

Use this skill to prepare, format, preview, and publish a LinkedIn post to a personal LinkedIn profile, then prepare a differentiated version for manual posting to a LinkedIn Group when configured.

This skill supports public text posts and public single-image posts on personal profiles, plus copy-and-open handoff for group posts. It can also format Markdown or plain text into LinkedIn-safe plain text before previewing or publishing. Do not use this skill for scheduled posts, edits, deletes, comments, videos, documents, carousels, or analytics.

## Safety Rules

- Never print, paste, or log `LINKEDIN_CLIENT_SECRET`, access tokens, refresh tokens, authorization codes, or `.linkedin/token.json` contents.
- Never publish without an explicit final user confirmation.
- Always run a preview first. The publish script is safe by default and only posts when called with both `--publish` and `--yes`.
- Never automate the final submission of a LinkedIn Group post. Generate, preview, and optionally open the configured group, then require the user to paste, review, and submit it manually.
- Do not publish to organization Pages in this version.
- Stop if image upload fails. Do not publish a text-only fallback unless the user explicitly asks.
- Formatting never calls LinkedIn APIs. When formatting is needed, do it before preview or publish.

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
~/.config/linkedin-publisher/workflow.json
```

Read config from the persistent file first. Environment variables may override config values. Do not store secrets in `SKILL.md`, `agents/openai.yaml`, or any repository-tracked file.

Use `workflow.json` only for non-secret publishing preferences. If the workspace contains `linkedin-workflow.json`, treat it as a project override. Apply settings in this order:

1. The user's explicit instruction for the current task.
2. Workspace `linkedin-workflow.json`.
3. Persistent `~/.config/linkedin-publisher/workflow.json`.

Recommended scopes:

- `w_member_social` for personal profile posting

## Formatting Workflow

Read `references/linkedin_formatting.md` when converting raw notes, Markdown, long articles, or pasted drafts into a LinkedIn-ready post.

Default approach:

1. Preserve the author's core ideas and domain tone.
2. Use `standard` formatting unless the user asks for minimal or stronger styling.
3. Save the formatted result to a workspace file when the post will also be previewed or published.
4. Generate the API preview and local HTML preview from the formatted file.
5. Ask for explicit confirmation before publishing.

Format Markdown or text:

```bash
python3 linkedin-publisher/scripts/linkedin_format.py \
  --text-file "./draft.md" \
  --mode standard \
  --output "./posts/linkedin-ready.md" \
  --report
```

The formatter appends `#Bamboodt` to the final hashtag line by default and avoids duplicating it if already present. Use `--no-brand-hashtag` only when the user explicitly asks to omit brand tagging.

Formatting modes:

- `light`: clean Markdown and spacing without Unicode styling
- `standard`: restrained LinkedIn styling for most professional posts
- `strong`: more visual structure when explicitly requested

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

Recommended end-to-end workflow:

```bash
python3 linkedin-publisher/scripts/linkedin_format.py \
  --text-file "./draft.md" \
  --output "./posts/linkedin-ready.md" \
  --report

python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./posts/linkedin-ready.md" \
  --image "./image.png"

python3 linkedin-publisher/scripts/linkedin_preview_html.py \
  --text-file "./posts/linkedin-ready.md" \
  --image "./image.png" \
  --output "./previews/linkedin-preview.html"
```

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

## Group Distribution Workflow

After preparing a personal-profile post, read the workflow configuration. When `group_posting.enabled` is true:

1. Complete the personal-profile preview and require explicit confirmation before publishing it.
2. Prepare a standalone group version after the personal post is approved or published.
3. Make the group version materially different: use a new opening, retain only the strongest one or two points, reduce the body to the configured length range, and end with a concrete practitioner question.
4. Preserve source attribution when the personal version relies on named external sources.
5. Format and generate a separate HTML preview for the group version.
6. Recommend the configured delay after the personal-profile post. Do not claim the post is scheduled unless a separate automation was explicitly created.
7. Optionally open `default_group.url` when the user asks to proceed, but do not paste or submit through browser automation. The user must review and submit the group post manually.

Do not merely repost the personal-profile text or link to it. A person may see both versions, so optimize the personal version for complete insight and the group version for focused discussion.

## References

Read `references/linkedin_api.md` when implementing, debugging API errors, or explaining required permissions.

Read `references/linkedin_formatting.md` when preparing or formatting LinkedIn copy.
