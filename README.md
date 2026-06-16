# LinkedIn Publisher Codex Skill

[中文文档](README.zh-CN.md)

`linkedin-publisher` is a Codex skill for formatting, preparing, previewing, and publishing LinkedIn personal profile posts through the LinkedIn Posts API.

It supports:

- personal LinkedIn profile posts
- text posts
- single-image posts
- Markdown/plain-text to LinkedIn-safe formatting
- OAuth setup helpers
- local LinkedIn-style HTML previews
- safe publish confirmation through `--publish --yes`

It does not support LinkedIn organization Page posting, scheduled posts, edits, deletes, comments, analytics, videos, documents, or carousels.

## Requirements

- Python 3.9+
- A LinkedIn Developer application
- LinkedIn products/scopes:
  - `Share on LinkedIn`
  - `Sign In with LinkedIn using OpenID Connect`
  - OAuth scope `w_member_social`
- OAuth redirect URL configured in LinkedIn Developer:

```text
http://localhost:8080/callback
```

## Install as a Codex Skill

Clone this repository, then copy the skill folder into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R linkedin-publisher ~/.codex/skills/linkedin-publisher
```

Restart Codex or start a new Codex thread so the skill metadata is reloaded.

## Configure

Create one user-level config file. This is shared by every Codex workspace:

```bash
mkdir -p ~/.config/linkedin-publisher
cp linkedin-publisher/config.example.json ~/.config/linkedin-publisher/config.json
```

Edit:

```text
~/.config/linkedin-publisher/config.json
```

Required fields:

```json
{
  "client_id": "your-linkedin-client-id",
  "client_secret": "your-linkedin-client-secret",
  "redirect_uri": "http://localhost:8080/callback",
  "person_id": "your-linkedin-person-id",
  "token_file": "~/.config/linkedin-publisher/token.json"
}
```

Environment variables still work and override the config file:

```bash
export LINKEDIN_CLIENT_ID="your-client-id"
export LINKEDIN_CLIENT_SECRET="your-client-secret"
export LINKEDIN_REDIRECT_URI="http://localhost:8080/callback"
```

Never commit `~/.config/linkedin-publisher/config.json`, token files, access tokens, refresh tokens, or client secrets.

## Authorize LinkedIn

Run the local OAuth callback flow:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py authorize \
  --state "linkedin-publisher-setup"
```

After approving the LinkedIn application, the token is saved to:

```text
~/.config/linkedin-publisher/token.json
```

Check token status without printing token values:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py status
```

Fetch your personal author ID:

```bash
python3 linkedin-publisher/scripts/linkedin_auth.py userinfo
```

Use the returned `sub` value as `--person-id`, or use the returned `person_urn` with `--author-urn`.

If you save `person_id` in `~/.config/linkedin-publisher/config.json`, future publish commands do not need `--person-id`.

## Format

Format Markdown or plain text before previewing:

```bash
python3 linkedin-publisher/scripts/linkedin_format.py \
  --text-file "./draft.md" \
  --mode standard \
  --output "./posts/linkedin-ready.md" \
  --report
```

Formatting modes:

- `light`: clean Markdown and spacing without Unicode styling
- `standard`: restrained LinkedIn styling for most professional posts
- `strong`: more visual structure when explicitly requested

The formatter does not call LinkedIn APIs and does not read token files.

By default, the formatter appends `#Bamboodt` to the final hashtag line for brand presence. If the tag already exists, it is not duplicated. To omit it for a specific post:

```bash
python3 linkedin-publisher/scripts/linkedin_format.py \
  --text-file "./draft.md" \
  --output "./posts/linkedin-ready.md" \
  --no-brand-hashtag
```

## Preview

Create a text-only API preview:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md"
```

Create a single-image API preview:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./cover.png"
```

Create a local visual HTML preview:

```bash
python3 linkedin-publisher/scripts/linkedin_preview_html.py \
  --text-file "./post.md" \
  --image "./cover.png" \
  --output "./previews/linkedin-preview.html" \
  --name "Your Name" \
  --headline "Your LinkedIn headline"
```

Open the generated HTML file in a browser to review the post layout approximation.

## Publish

Only publish after reviewing the preview:

```bash
python3 linkedin-publisher/scripts/linkedin_publish.py \
  --text-file "./post.md" \
  --image "./cover.png" \
  --publish \
  --yes
```

The script prints the LinkedIn share URN when publishing succeeds.

## Safety Notes

- The publish script does not publish unless both `--publish` and `--yes` are present.
- Token status and userinfo commands do not print access token values.
- Image upload failure stops the post before it is created.
- Organization Page posting is intentionally out of scope for this version.

## Skill Files

```text
linkedin-publisher/
├── SKILL.md
├── agents/openai.yaml
├── references/linkedin_api.md
├── references/linkedin_formatting.md
└── scripts/
    ├── linkedin_auth.py
    ├── linkedin_format.py
    ├── linkedin_preview_html.py
    └── linkedin_publish.py
```
