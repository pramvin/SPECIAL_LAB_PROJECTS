# PlanWise AI

Project knowledge lives in the **OKF** (Open Knowledge Format) bundle at `.okf/`, replacing the old `memory-bank/`.
Tools: the `okf` and `validate` skills are in `.claude/skills/` (Claude Code loads them automatically when this project is opened).
For the frontend, see the extra rules in `frontend/AGENTS.md`.

## Rule: read `.okf/` before doing anything (consume mode)

Before starting any work in this repo (editing code, running commands, answering project questions, planning):

1. Open `.okf/index.md`, then always read `/project/brief.md` and `/project/active-context.md`
2. Open only the concepts relevant to the task, based on the list and `description` in `index.md`, for example:
   - changing the pipeline/scores → `/architecture/system-patterns.md`, `/architecture/scoring.md`
   - login/security → `/architecture/auth-security.md`
   - running data/opening Kaggle → `/runbooks/`
   - citing model results → `/experiments/results.md`
   - what is done/who does what → `/project/progress.md`, `/project/team.md`
3. Do not load all of `.okf/`, and do not load the whole of `PIPELINE_SPEC.md` if a concept already answers the question
4. A concept with `status: draft`/`deprecated`, or without `verified` = check it against the code before trusting it
5. If `.okf/` conflicts with the code or the real state → trust the real state, then fix `.okf/`

## Rule: update `.okf/` after working (maintain mode)

When finishing work that changes status, a decision, or an open problem, use the `okf` skill (maintain):

- Edit the affected concepts **all in one pass** (usually `/project/active-context.md` and `/project/progress.md`) and update `generated: { by, at }`
  - `by` follows the actor convention: agent = `<name>/<version>` e.g. `claude-code/claude-sonnet-5-5` · human = `human:<id>` · automated job = `process:<id>`
  - Use `human:` when a person wrote or confirmed it themselves
- **Every time work is finished, add the new information and delete the old information it replaces in the same pass:** write the new state over the old one. Never append so that old and new sit side by side or contradict each other (except `log.md`, which must never be deleted from)
- **Keep only the current state:** delete solved problems/finished work from the concept (history is in git). Do not leave them struck through
- A concept that is no longer used → `status: deprecated` and note it in `log.md`, or delete it if it has no value left
- `log.md` is only for lifecycle events (bundle created, deprecated, replaced, regenerated after the source changed, verified) · ordinary edits are not logged · never delete or edit old entries · newest on top
- Keep the format: 1 file = 1 topic, links as `/path/file.md`, short files (should not exceed ~3 KB)
- Do not put in secrets/tokens, and do not store what can already be read from the code or git history
- When done, validation must pass before saying the work is finished:

```bash
uv run .claude/skills/validate/scripts/okf_validate.py .okf --strict
```

- New concept: start from `.claude/skills/okf/templates/concept.md`, then add a line to `.okf/index.md`
- The only hard requirement of OKF: every `.md` other than `index.md`/`log.md` must have frontmatter and a non-empty `type` · a `description` containing `: ` must be quoted

## Quick facts

Reply to the user in simple, short Thai · ask before committing/installing/downloading/setting up a scheduled job · the full rules are in `.okf/project/brief.md`
