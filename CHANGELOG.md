# Changelog

What changed in each step of the project, newest first.

## Unreleased

## 0.3.0: Accounts and profile (step 1)

### Added
- Accounts: sign up and log in with email + password (Argon2 hashes, 7-day JWT login tokens).
- Every resume, application and saved answer belongs to a user; users can't see each other's data.
- Profile API: personal details, education, work, job preferences, common form answers and optional demographics, with a list of what's still missing before applying.
- Saved answers API for extra form questions, de-duplicated by question.
- Resume uploads keep the original file (downloadable) and fill empty profile fields; the newest upload becomes the active resume.
- Postgres support (`DATABASE_URL`), including the agent's checkpoints, and Alembic database migrations applied on startup.
- Production safety checks: the API refuses to start without a strong `JWT_SECRET`, a Postgres database and an OpenAI key.
- Tests for accounts, profile, data isolation and migrations (37 in total), run on both SQLite and Postgres in CI.

### Changed
- API endpoints split into `app/routers/` by topic.
- `resume_id` is optional when analysing a job; the active resume is used.

## 0.2.1: Documentation

### Added
- `docs/` folder: [setup guide](docs/setup.md), [how it works](docs/architecture.md), [decisions log](docs/decisions.md).
- `CONTRIBUTING.md` with the commit message and documentation rules.
- A header comment in every code file explaining what it's for.

## 0.2.0: Web app

### Added
- Next.js website: application board, resume upload, "analyse a job" page with live progress, and the application page with fit breakdown, tailored drafts and review.
- API endpoint `POST /api/applications/stream` that streams progress, one event per agent step.
- Frontend Dockerfile, `docker-compose.yml` for the whole app, and frontend checks in CI.

## 0.1.0: Agent and API

### Added
- LangGraph agent: parse job → match resume → (rewrite bullets with fact-check loop | cover letter | recruiter message) → your review → revise or approve.
- Score calculated by a formula from the AI's per-requirement labels.
- FastAPI backend with resume upload (PDF/text), application tracker and SQLite storage.
- 16 offline tests with a fake AI, an evaluation suite for the real AI, Dockerfile, and GitHub Actions CI.
