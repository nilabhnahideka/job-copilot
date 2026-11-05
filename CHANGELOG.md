# Changelog

What changed in each step of the project, newest first.

## Unreleased

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
