# Job Copilot web app

Next.js 16 (App Router) + Tailwind CSS 4 frontend for the Job Copilot API.

```bash
cp .env.example .env.local   # points at the API, default http://localhost:8000
npm install
npm run dev                  # http://localhost:3000
```

| Route | What it is |
|---|---|
| `/` | Application board, from "To review" through to "Offer" |
| `/resume` | Upload a PDF or paste your resume; shows the parsed profile |
| `/new` | Paste a job post and watch the agent work step by step (server-sent events) |
| `/applications/[id]` | Fit breakdown, tailored bullets with added words highlighted, cover letter, recruiter message, review and revise |

Code map: `lib/api.ts` (typed API client + SSE reader), `lib/diff.ts` (word-level LCS diff for the bullet highlights), `components/RequirementStrip.tsx` (the fit-score bar), `components/ApplicationView.tsx` (application page).
