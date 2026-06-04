# LinkedIn API Reference Notes

This file records the API choices used by the local scripts. Verify LinkedIn's official documentation before changing request shapes or permission assumptions.

Official sources:

- Posts API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
- Images API: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api
- Authorization Code Flow: https://learn.microsoft.com/en-us/linkedin/shared/authentication/authorization-code-flow
- API versioning: https://learn.microsoft.com/en-us/linkedin/marketing/versioning

## OAuth

- Authorization endpoint: `https://www.linkedin.com/oauth/v2/authorization`
- Token endpoint: `https://www.linkedin.com/oauth/v2/accessToken`
- Client credentials come from environment variables:
  - `LINKEDIN_CLIENT_ID`
  - `LINKEDIN_CLIENT_SECRET`
  - `LINKEDIN_REDIRECT_URI`
- Token values are stored locally in `.linkedin/token.json`, which is ignored by git.
- Do not print token values. Status output should report only expiry and scope metadata.

## Posting

- Posts endpoint: `POST https://api.linkedin.com/rest/posts`
- Required request headers:
  - `Authorization: Bearer <access_token>`
  - `LinkedIn-Version: <YYYYMM>`
  - `X-Restli-Protocol-Version: 2.0.0`
  - `Content-Type: application/json`
- Default API version is read from `LINKEDIN_API_VERSION`, falling back to `202605`.

Base payload:

```json
{
  "author": "urn:li:person:{id}",
  "commentary": "Post text",
  "visibility": "PUBLIC",
  "distribution": {
    "feedDistribution": "MAIN_FEED",
    "targetEntities": [],
    "thirdPartyDistributionChannels": []
  },
  "lifecycleState": "PUBLISHED",
  "isReshareDisabledByAuthor": false
}
```

Single-image posts add:

```json
{
  "content": {
    "media": {
      "id": "urn:li:image:..."
    }
  }
}
```

## Image Upload

- Initialize upload endpoint: `POST https://api.linkedin.com/rest/images?action=initializeUpload`
- Request body:

```json
{
  "initializeUploadRequest": {
    "owner": "urn:li:person:{id}"
  }
}
```

- Response contains an image URN and an upload URL.
- Upload the image bytes to the returned upload URL before creating the post.

## URNs and Permissions

- Personal author URN: `urn:li:person:{person_id}`
- Personal posting requires `w_member_social`.
- Organization Page posting is intentionally out of scope for this version.

## Common Errors

- `401`: token missing, expired, malformed, or not accepted by LinkedIn.
- `403`: missing product permission or missing scope.
- `429`: LinkedIn rate limit. Do not retry aggressively.
- Image upload failure: stop before creating the post.
