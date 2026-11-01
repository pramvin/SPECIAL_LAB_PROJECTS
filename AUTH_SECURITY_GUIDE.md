# PlanWise AI: Login and Authentication Security Guide

This guide covers only the account/login changes added to the existing project. The recommendation engine, planning pages, and other app features were left unchanged.

## What was added

- **Forgot password page:** `frontend/src/app/forgot-password/page.tsx`
- **Reset password page:** `frontend/src/app/reset-password/page.tsx`
- **Forgot-password link:** added to the existing login page.
- **Backend reset endpoints:** `POST /api/auth/forgot-password` and `POST /api/auth/reset-password`.
- **Single-use, expiring reset tokens:** the database stores a SHA-256 hash of the token, not the raw token. Links expire after 30 minutes and cannot be reused.
- **Login rate limiting:** after five failed attempts for the same email + client IP within 15 minutes, sign-in is temporarily limited. A successful login clears that email/IP's failed-attempt counter.
- **Password-reset request rate limiting:** at most five reset requests from one IP in a 15-minute window.
- **Security event logging:** the `auth_events` table records registration, login success/failure, rate limiting, logout, and password-reset events. Passwords and raw reset tokens are never logged.
- **Session revocation after password reset:** all existing sessions for that account are removed, so the user must sign in again.
- **Cookie security setting:** the session cookie remains `HttpOnly` and `SameSite=Lax`. It uses `Secure` automatically when `APP_ENV=production`, unless explicitly overridden with `COOKIE_SECURE`.

## Local development: test password recovery

1. Start the backend as usual from `Backend`:

   ```bash
   uvicorn app.main:app --port 8000
   ```

2. Start the frontend as usual from `frontend`:

   ```bash
   npm run dev
   ```

3. Open `http://localhost:3000/login` and choose **Forgot password?**.
4. Enter the email address of an account that exists in the local database.
5. When no SMTP server is configured and `APP_ENV` is not `production`, the backend prints a development-only reset URL in the terminal running Uvicorn. Copy that URL into the browser to set a new password.
6. Sign in using the new password. The reset link should not work a second time.

The API deliberately returns the same general message whether or not an email belongs to an account, to make it harder to discover registered email addresses.

## Configure real email delivery

For real email delivery, set these environment variables in the backend environment (do not commit real values to Git):

- `SMTP_HOST` — SMTP server hostname
- `SMTP_PORT` — usually `587` for STARTTLS
- `SMTP_USER` — SMTP username, if required
- `SMTP_PASSWORD` — SMTP password/app password, if required
- `SMTP_FROM` — sender email address
- `FRONTEND_URL` — public frontend base URL, for example `https://your-site.example`
- `APP_ENV=production`

If `APP_ENV=production` and `SMTP_HOST` is missing, password-reset email delivery fails safely instead of printing a reset link to logs. Set `COOKIE_SECURE=1` when serving over HTTPS; production defaults it to on. Do not use the local development reset-link behavior on a public server.

## Beginner explanation: frontend, backend, and API

- **Frontend:** the pages users see and click. Here, the login and password-reset pages are React/Next.js files under `frontend/src/app/`.
- **Backend:** the Python FastAPI app in `Backend/app/main.py`. It checks credentials, updates the database, creates sessions, and validates reset tokens. The backend—not the frontend—must make security decisions.
- **API:** a URL the frontend calls to ask the backend to do something. For example, the forgot-password page sends an HTTP `POST` request to `/api/auth/forgot-password` with JSON containing the email address.
- **Database:** SQLite stores account records, sessions, reset-token hashes, rate-limit history, and security events.
- **Password hash:** the backend stores a derived value made with `scrypt`, a password-hashing function, plus a random salt. It does not store the user's actual password.
- **Reset token:** a long random secret sent in the reset link. The database stores only its hash; the raw token is accepted once, before its 30-minute expiration.
- **Rate limiting:** the backend counts repeated failed requests and temporarily rejects additional attempts to slow automated guessing.
- **Security event:** a timestamped record of an authentication action. Events do not include passwords or reset-token values.

## Current limits / next steps

This is a student-project implementation, not a full independent security audit. Before public production use, add automated tests to your project, configure real SMTP, serve only over HTTPS, review proxy/IP configuration for deployment, and consider CSRF protection and centralized rate limiting if running multiple backend instances. The local SQLite rate limit is intended for a single backend process using one database file.
