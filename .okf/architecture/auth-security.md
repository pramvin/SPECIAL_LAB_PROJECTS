---
type: Architecture
title: Auth and security
description: Login, password hashing, rate limit, password reset, and known limits (read from Backend/app/main.py)
tags: [architecture, security]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-11-01T06:40:00Z }
sources:
  - id: guide
    resource: AUTH_SECURITY_GUIDE.md
    title: Han's auth guide
    author: human:han
---

Author's full guide (Han): `AUTH_SECURITY_GUIDE.md`[^guide]

# What exists

- Passwords are **hashed with scrypt** + a random per-user salt (not encrypted) · 8–128 characters
- More than 5 failed logins in 15 minutes → 429 (per email + IP) · the error message is identical in every case
- Forgot password: random token stored as a SHA-256 hash, single use, expires in 30 minutes, request count is limited · without SMTP the link is printed to the terminal (production requires `SMTP_HOST`)
- `session` cookie: `httponly`, `samesite=lax`, `secure` only when `APP_ENV=production` · lives 7 days
- Auth events (login/logout/failures) are logged, never passwords or tokens

# Known limits

- **Session tokens are stored unhashed in the DB** (unlike reset tokens); if the DB file leaks, they can be used to log in until they expire
- The rate limit uses the caller's IP: behind the Next proxy everyone may look like one IP (not tested)
- No HTTPS in the code (set up at deploy time) · no 2FA · other DB data is not encrypted

[^guide]: AUTH_SECURITY_GUIDE.md
