# VINCENT.md — Merging the Trade Ideas work

This guide is for the teammate combining everyone's branches into `main`.
It covers **`questionare-branch`** only, plus a short note on merge order.
The work is focused on the **Trade Ideas** tab and the backend endpoints that
feed it.

> **Important:** the per-stock questionnaire **UI was removed on purpose**.
> The backend table (`sentiment_responses`) and its API remain. Do not re-add
> the old “Your view” / “Your saved views” sections during the merge.

## 1. Branch facts

| Item | Value |
|---|---|
| Branch | `questionare-branch` |
| Commit | `425c7bc` |
| Based on | `main` at `2c73fbc` |
| Area | Trade Ideas tab + supporting backend |
| Shared-file risk | `Backend/app/main.py` (also edited by `Login-and-Security-Feature`) |

## 2. What changed

### Frontend (Trade Ideas)

| File | Change |
|---|---|
| `frontend/src/components/ideas/NewsSentiment.tsx` | **New.** Real Google News headlines, no SAMPLE watermark; sentiment shown only when scored. |
| `frontend/src/components/ideas/DataStatus.tsx` | **New.** Fixed status bar: live local+UTC clock, last news update, sentiment status, Refresh. Measures its own height. |
| `frontend/src/components/ideas/RefreshButton.tsx` | **New.** Calls `router.refresh()` to re-fetch the page. |
| `frontend/src/components/ideas/SocialSentiment.tsx` | **Deleted.** The mock panel is gone. |
| `frontend/src/components/ideas/IdeasView.tsx` | Uses `NewsSentiment` + `DataStatus`; no more `SocialSentiment`. |
| `frontend/src/app/(app)/page.tsx` | Fetches news sentiment + data status and passes them down. |
| `frontend/src/lib/recommendations.ts` | Adds `getNewsSentiment`, `getDataStatus`, and their types. |
| `frontend/src/components/layout/{AppShell,Header,MobileTopBar}.tsx` | Spacing / opaque headers so content does not bleed through. |
| `frontend/src/components/ui/Button.tsx` | Optional `iconClassName` (used by the refresh spinner). |
| `frontend/next.config.ts` | Adds `devIndicators: false`. **Keep the existing `/api` rewrites.** |

### Backend (`Backend/app/main.py`)

- Table `sentiment_responses` (one row per `(user_id, ticker)`).
- `GET /api/sentiment-responses` — saved answers for the signed-in user.
- `PUT /api/sentiment-response` — upsert one user's answers (auth required).
- `GET /api/news-sentiment?tickers=AAPL,MSFT&limit=3` — real headlines from
  `news_items`, with sentiment when `news_scores` has data.
- `GET /api/data-status` — latest news/sentiment refresh times.
- Demo account seed: `demo@planwise.ai` / `planwise123`.
- `Backend/requirements.txt` adds `requests` (used by `pipeline/news.py`).

`news_items` / `news_scores` are created by the pipeline, not by `main.py`.
If they are missing, the UI shows real headlines only when `pipeline.news` has
run; otherwise it shows an empty state. It never invents data.

## 3. Recommended merge order

1. Merge `Login-and-Security-Feature` **first** (or resolve it together with
   this branch).
2. Merge `questionare-branch`.
3. Merge the remaining branches.

Reason: `Login-and-Security-Feature` and this branch both edit
`Backend/app/main.py`, so it is easier to resolve that file once, with both
sets of changes visible.

## 4. Step-by-step

```bash
git fetch --all

git switch main
git pull --ff-only

git switch -c integration/merge-check
git merge --no-ff origin/questionare-branch
```

If Git reports conflicts, resolve them using the recipe in section 5, then:

```bash
git add <resolved-files>
git commit
```

Run the verification in section 6. When everything passes:

```bash
git switch main
git merge --no-ff integration/merge-check
git push origin main
```

## 5. Conflict recipe: `Backend/app/main.py`

This is the only expected collision with `Login-and-Security-Feature`.
**Do not resolve by taking “ours” or “theirs” wholesale.** Keep both feature
sets.

Keep **all imports**:

```python
import smtplib
from email.message import EmailMessage
from urllib.parse import quote
from datetime import datetime, timezone

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
```

Keep **both sets of schema tables** inside `SCHEMA`:

- Login branch: `password_reset_tokens`, `auth_events`, `login_failures`, and
  their indexes.
- This branch: `sentiment_responses`.

Keep **both sets of models**:

- `SentimentResponse` (this branch).
- `ForgotPasswordRequest`, `ResetPasswordRequest` (login branch).

Keep the login branch's changed signatures:

```python
def register(body: Credentials, request: Request, response: Response):
def login(body: Credentials, request: Request, response: Response):
```

Keep **both endpoint groups**:

- Login branch: `/api/auth/forgot-password`, `/api/auth/reset-password`,
  `/api/auth/security-events`.
- This branch: `/api/sentiment-responses`, `/api/sentiment-response`,
  `/api/news-sentiment`, `/api/data-status`.

Keep the demo seed at the end of the file (it is idempotent). Do not remove
`record_auth_event`, `login_is_limited`, or `record_login_failure` from the
login branch.

### Other files

- `frontend/next.config.ts`: keep `turbopack`, `devIndicators: false`, **and**
  `async rewrites()` for `/api/:path*`. If the rewrites are gone, login returns
  404.
- `frontend/src/components/ideas/`: keep the **deletion** of
  `SocialSentiment.tsx`; confirm nothing imports it.
- `memory-bank/*`: merge entries newest-first; keep the team's task assignments.
- `README.md`: combine both sets of instructions.

## 6. Verification checklist

### Backend

```bash
cd Backend
.venv/bin/uvicorn app.main:app --port 8000
```

In another terminal:

```bash
curl -s http://127.0.0.1:8000/api/data-status | python3 -m json.tool
curl -s "http://127.0.0.1:8000/api/news-sentiment?tickers=MSFT" | python3 -m json.tool
```

Expected: `data-status` returns timestamps (sentiment may be `null`), and
`news-sentiment` returns real headlines.

### Frontend

```bash
cd frontend
npm install
npx tsc --noEmit
npm run lint
npm run build
npm run dev
```

Open http://localhost:3000, sign in with `demo@planwise.ai` / `planwise123`,
and check the Trade Ideas tab:

- The fixed status bar shows Now (local + UTC), News updated, Sentiment, and
  Refresh.
- Refresh re-fetches the page.
- The news panel shows real headlines (or a clear empty state).
- Mobile: the status bar uses 2 lines; no overlap with the Refresh button.

### Auth-protected endpoint

```bash
# after logging in via the app, reuse the session cookie
curl -s -b "session=<cookie>" http://127.0.0.1:8000/api/sentiment-responses
```

## 7. Runtime notes

- Populate real headlines with:

  ```bash
  cd Backend
  .venv/bin/python -m pipeline.news
  ```

- Sentiment scores require the existing Kaggle Laya/LLM gateway:

  ```bash
  cd Backend
  .venv/bin/python -m pipeline.analyze
  ```

  Until that runs, the UI correctly says **“not scored yet”**. Do not fake labels.

- The local SQLite DB (`Backend/planwise.db`) is git-ignored. Do not commit it.

## 8. Do not commit

- `Backend/planwise.db`
- `Backend/.venv/`
- `Backend/.env` or any secrets
- `frontend/node_modules/`
- `frontend/.next/`

## 9. Files in this branch

```text
Backend/app/main.py
Backend/requirements.txt
README.md
frontend/next.config.ts
frontend/src/app/(app)/page.tsx
frontend/src/components/ideas/DataStatus.tsx        (new)
frontend/src/components/ideas/IdeasView.tsx
frontend/src/components/ideas/NewsSentiment.tsx     (new)
frontend/src/components/ideas/RefreshButton.tsx     (new)
frontend/src/components/ideas/SocialSentiment.tsx   (deleted)
frontend/src/components/layout/AppShell.tsx
frontend/src/components/layout/Header.tsx
frontend/src/components/layout/MobileTopBar.tsx
frontend/src/components/ui/Button.tsx
frontend/src/lib/recommendations.ts
memory-bank/activeContext.md
memory-bank/log.md
memory-bank/progress.md
```
