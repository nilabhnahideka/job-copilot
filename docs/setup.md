# Setup guide

This guide takes you from nothing to Job Copilot running on your own computer. No prior experience with these tools is assumed. Each step says what it does and why.

There are two parts to run:

- **Backend (the "brain")**: a Python server that talks to OpenAI and stores your data. It runs at `http://localhost:8000`.
- **Frontend (the website)**: the pages you click around in. It runs at `http://localhost:3000` and talks to the backend.

You can run both with **Docker** (one command), or run each part **directly** (better while developing, because changes show up instantly).

---

## 1. Install the tools

You need these once per computer:

| Tool | Why | Check it's installed |
|---|---|---|
| [Git](https://git-scm.com/downloads) | Downloads the code and saves your changes | `git --version` |
| [Python 3.11+](https://www.python.org/downloads/) | Runs the backend | `python --version` (or `python3 --version`) |
| [Node.js 22+](https://nodejs.org/) | Runs the frontend | `node --version` |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) (optional) | Runs everything with one command | `docker --version` |

Run the "check" commands in a terminal (Terminal on Mac, PowerShell on Windows). If they print a version number, you're set.

## 2. Get the code

```bash
git clone https://github.com/nilabhnahideka/job-copilot.git
cd job-copilot
```

`git clone` downloads the project and its full history into a folder called `job-copilot`.

## 3. Add your OpenAI key

The backend needs an OpenAI API key to call the AI model. You can create one at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).

```bash
cd backend
cp .env.example .env        # on Windows: copy .env.example .env
```

Open the new `backend/.env` file in any text editor and replace `sk-...` with your key:

```
OPENAI_API_KEY=sk-your-real-key-here
```

You can leave `JWT_SECRET` empty on your own computer; the app then uses a development secret and prints a warning. It must be set when deploying (the app refuses to start in production without it).

> **Keep this key secret.** `.env` is listed in `.gitignore`, so Git will never upload it to GitHub. Never paste the key into code, chats or screenshots. If it ever leaks, delete it on the OpenAI site and create a new one.

---

## Option A: Run everything with Docker

From the project's top folder (`job-copilot/`):

```bash
docker compose up --build
```

The first run takes a few minutes while it builds. When it's done:

- Website: http://localhost:3000
- API docs: http://localhost:8000/docs

Press `Ctrl+C` to stop.

---

## Option B: Run each part directly

### Backend (terminal 1)

```bash
cd backend
python -m venv .venv                 # create an isolated Python environment for this project
source .venv/bin/activate            # turn it on (Windows: .venv\Scripts\activate)
pip install -e ".[dev]"              # install the backend and its developer tools
uvicorn app.main:app --reload        # start the server; --reload restarts it when you edit code
```

Leave this terminal running. Visit http://localhost:8000/docs to see every API endpoint and try them in the browser.

### Frontend (terminal 2)

```bash
cd frontend
cp .env.example .env.local           # tells the website where the backend is
npm install                          # download the frontend's libraries (first time only)
npm run dev                          # start the website
```

Open http://localhost:3000.

---

## 4. Try it

1. Click **Sign up** and create an account (any email and a password of 8+ characters; it stays on your computer).
2. Go to **Profile** and upload your resume as a PDF. Empty fields like your name and phone are filled from it.
3. Fill in the rest of your profile. The page lists what's still missing.
4. Click **Analyse a job** and paste a full job description.
5. Watch the steps tick off. You'll land on the results page with your fit score, gaps and drafts.
6. Ask for a change to a draft, or click **Approve drafts**.
7. Go back to **Applications** and move the job along the board as you apply.

## 5. Run the checks

These are the same checks GitHub runs automatically on every push (the "Actions" tab):

```bash
cd backend
ruff check .              # code style and common mistakes
pytest -q                 # offline tests; no API key needed, takes ~10 seconds
python -m evals.run_evals # quality checks against the real AI model (uses your key; costs a few cents)

cd ../frontend
npm run lint              # code style
npm run build             # makes sure the website compiles
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Website says "Can't reach the API" | The backend isn't running, or isn't on port 8000. Start it (terminal 1). |
| `OPENAI_API_KEY is not set` | You haven't created `backend/.env`, or the key line is wrong. See step 3. |
| `command not found: python` | Try `python3` instead, or install Python (step 1). |
| A port is "already in use" | Something else is using 3000 or 8000. Stop it, or close the old terminal running the app. |
| Errors about missing tables or columns after updating the code | Your local database is from an older version. The API upgrades it on start; if it still fails, delete the `backend/data/` folder (this deletes your local test data) and restart. |
| "Log in to continue" everywhere | Your login expired (after 7 days) or the backend's `JWT_SECRET` changed. Log in again. |
| Resume upload says it can't read the PDF | The PDF is probably a scanned image. Export a text-based PDF instead (e.g. "Save as PDF" or "Download as PDF" from Word or Google Docs). |
